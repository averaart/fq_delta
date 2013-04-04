__author__ = 'averaart'
"""This module offers a means to store multiple versions of the same fastq file, by only storing the differences between
them and recreating the processed file based on the original file and the differences."""

# Batteries included
import os
import sys
from subprocess import Popen, PIPE
import hashlib
import zipfile
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except ImportError:
    compression = zipfile.ZIP_STORED


# 3rd party imports
import diff_match_patch as dmp_module


class InputError(Exception):
    pass


class ChecksumError(Exception):
    pass


# global variables
dmp = dmp_module.diff_match_patch()
dmp.Diff_Timeout = 0.0005     # default is 1
dmp.Match_Distance = 1000   # default is 1000
dmp.Match_MaxBits = 0       # default is 32, 0 is advised for python


def _open(name):
    """Opens a file, or streams an unquiping archive."""
    if name[-3:] == '.qp':
        return Popen('unquip -c ' + name, shell=True, stdout=PIPE).stdout
    else:
        try:
            return open(name, 'r')
        except IOError:
            print "Couldn't find the file..."


def create_delta(original_file=sys.stdin, processed_file=sys.stdin, delta_filename='', output_processed=False):
    """This function creates a delta file based on an original file and a processed file. Either files could come from
    standard in."""

    if isinstance(processed_file, str):
        processed_file = _open(processed_file)

    if delta_filename == '':
        delta_filename = processed_file.name

    delta_file = DeltaFile('w', delta_filename, original_file)

    for line in processed_file:
        delta_file.write(line)
        if output_processed:
            print line,

    delta_file.close()


def rebuild_fastq(delta_filename, original_file=sys.stdin, out=sys.stdout, to_stdout=False):
    """Recreates the processed file from the original and delta files."""

    # Convert file names to files, and open quip-files while we're at it.
    if isinstance(original_file, str):
        original_file = _open(original_file)

    if isinstance(out, str):
        out = open(out, 'w')

    if out == sys.stdout:
        to_stdout = False

    processed_file = DeltaFile('r', delta_filename, original_file)

    for line in processed_file:
        out.write(line + '\n')
        if to_stdout:
            sys.stdout.write(line + '\n')


class DeltaFile():

    def __init__(self, mode, delta_filename, original_file=sys.stdin, processed_file=sys.stdin, reuse=False):

        self.leftover = list()
        self.mode = mode
        self.reuse = reuse

        # Open an existing deltafile to read the processed file
        if self.mode == 'r':
            self.delta_filename = delta_filename

            # Convert file names to files, and open quip-files while we're at it.
            if isinstance(original_file, str):
                self.original_file = _open(original_file)
            else:
                self.original_file = original_file

            self.md5 = hashlib.md5()

            # Extract the checksum and delta files.

            # If there is no checksum file in the zipfile, bail out.
            # ("I'm not touching that with a 10 foot pole!")

            zf = zipfile.ZipFile(delta_filename)
            namelist = zf.namelist()
            if 'md5_checksum' not in namelist:
                raise ChecksumError('No checksum found.')
            else:
                namelist.pop(namelist.index("md5_checksum"))
                self.checksum = zf.open('md5_checksum', "r").read()

            # For the delta file, first assume the filename is the same as the archive's name
            # minus ".zip". If that fails, find the first file that contains the word "delta".
            # Else just extract the first file you can find. Ugly, I know... :D

            self.filename = self.delta_filename.rpartition('.')[0]
            try:
                zf.extract(self.filename)
            except KeyError:
                delta_names = [s for s in namelist if "delta" in s]
                if len(delta_names) > 0:
                    self.filename = delta_names[0]
                else:
                    self.filename = namelist[0]
                zf.extract(self.filename)

            self.deltas = open(self.filename, "r")

        # Write a new deltafile from the processed data.
        elif self.mode == 'w':

            # Raise an Exception if both "files" turn out to be sys.stdin.
            if original_file == sys.stdin and processed_file == sys.stdin:
                raise InputError("Only one of the inputfiles can be STDIN.")

            # Convert file names to files, and open quip-files while we're at it.
            if isinstance(original_file, str):
                self.original_file = _open(original_file)
            else:
                self.original_file = original_file

            if isinstance(processed_file, str):
                self.processed_file = _open(processed_file)
            else:
                self.processed_file = processed_file

            self.md5 = hashlib.md5()

            if delta_filename == '':
                self.delta_filename = processed_file.name
            else:
                self.delta_filename = delta_filename

            # Remove .zip if entered as delta_filename argument.
            # It'll be added when the file is zipped.
            if self.delta_filename[-4:] == '.zip':
                self.delta_filename = self.delta_filename[:-4]

            self.delta_file = open(self.delta_filename, 'a')

        else:
            raise Exception('Illegal mode: ' + str(mode))

    def __iter__(self):
        return self

    def reset(self):
        self.deltas.seek(0)
        self.original_file.seek(0)
        self.leftover = list()
        self.md5 = hashlib.md5()

    def next(self):
        self.check_reading()

        if self.original_file.closed or self.deltas.closed:
            raise IOError("Trying to iterate over closed files...")

        delta = ''
        t1 = ''
        t2 = ''

        while t2 == '':
            t1 = self.original_file.readline()
            delta = self.deltas.readline().strip()
            if delta == '':
                # End of File
                # Check the checksum...
                if not self.md5.digest() == self.checksum:
                    raise ChecksumError("Checksum did not match!")

                if self.reuse:
                    self.reset()
                else:
                    # Clean up the uncompressed delta file
                    self.deltas.close()
                    os.remove(self.filename)

                # Kill the iterator
                raise StopIteration
            diff = dmp.diff_fromDelta(t1.strip(), delta.strip())
            t2 = dmp.diff_text2(diff)

        self.md5.update(t2)
        return t2

    def readline(self):
        self.check_reading()
        return self.next()

    def readlines(self):
        self.check_reading()
        return [line for line in self]

    def writelines(self, lines, output_processed=False, close_file=False):
        lines = self.leftover + lines

        while len(lines) >= 4:
            id1 = self.original_file.readline().strip()
            id2 = lines.pop(0).strip()
            seq1 = self.original_file.readline().strip()
            seq2 = lines.pop(0).strip()
            com1 = self.original_file.readline().strip()
            com2 = lines.pop(0).strip()
            qua1 = self.original_file.readline().strip()
            qua2 = lines.pop(0).strip()
            if id2 == '':
                break
            self.md5.update(id2)
            self.md5.update(seq2)
            self.md5.update(com2)
            self.md5.update(qua2)
            while id1.partition('\t')[0] != id2.partition('\t')[0]:
                self.delta_file.write('-' + str(len(id1.strip())) + '\n')
                self.delta_file.write('-' + str(len(seq1.strip())) + '\n')
                self.delta_file.write('-' + str(len(com1.strip())) + '\n')
                self.delta_file.write('-' + str(len(qua1.strip())) + '\n')
                id1 = self.original_file.readline().strip()
                seq1 = self.original_file.readline().strip()
                com1 = self.original_file.readline().strip()
                qua1 = self.original_file.readline().strip()
                if id1 == '':
                    break
            for (t1, t2) in ((id1, id2), (seq1, seq2), (com1, com2), (qua1, qua2)):
                diff = dmp.diff_main(t1.strip(), t2.strip())
                delta = dmp.diff_toDelta(diff) + '\n'
                self.delta_file.write(delta)
                if output_processed:
                    print t2

        self.leftover = lines

        if close_file:
            self.close()

    def write(self, string, output_processed=False, close_file=False):
        lines = string.strip().split('\n')
        self.writelines(lines, output_processed, close_file)

    def close(self):
        if self.mode is 'r':
            if not self.deltas.closed:
                self.deltas.close()
            try:
                os.remove(self.filename)
            except OSError:
                pass
        else:
            self.delta_file.close()

            # Copy the delta file to a compressed archive, and remove the delta file
            self.zf = zipfile.ZipFile(self.delta_filename + '.zip', mode='w')
            try:
                self.zf.write(self.delta_filename, self.delta_filename.rpartition('/')[2], compress_type=compression)
                self.zf.writestr('md5_checksum', self.md5.digest(), compress_type=compression)
                os.remove(self.delta_filename)
            finally:
                self.zf.close()

    def check_reading(self):
        if self.mode is not 'r':
            raise IOError('File not open for reading')
