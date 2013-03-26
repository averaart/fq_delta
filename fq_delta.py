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


def create_delta(original_file=sys.stdin, processed_file=sys.stdin, delta_name='', output_processed=False):
    """This function creates a delta file based on an original file and a processed file. Either files could come from
    standard in."""

    # Raise an Exception if both "files" turn out to be sys.stdin.
    if original_file == sys.stdin and processed_file == sys.stdin:
        raise InputError("Only one of the inputfiles can be STDIN.")

    # Convert file names to files, and open quip-files while we're at it.
    if isinstance(original_file, str):
        original_file = _open(original_file)

    if isinstance(processed_file, str):
        processed_file = _open(processed_file)

    md5 = hashlib.md5()
    if delta_name == '':
        delta_name = processed_file.name

    open(delta_name, 'w').close()
    delta_file = open(delta_name, 'a')

    while True:
        id1 = original_file.readline().strip()
        id2 = processed_file.readline().strip()
        seq1 = original_file.readline().strip()
        seq2 = processed_file.readline().strip()
        com1 = original_file.readline().strip()
        com2 = processed_file.readline().strip()
        qua1 = original_file.readline().strip()
        qua2 = processed_file.readline().strip()
        if id2 == '':
            break
        md5.update(id2)
        md5.update(seq2)
        md5.update(com2)
        md5.update(qua2)
        while id1.partition('\t')[0] != id2.partition('\t')[0]:
            delta_file.write('-' + str(len(id1.strip())) + '\n')
            delta_file.write('-' + str(len(seq1.strip())) + '\n')
            delta_file.write('-' + str(len(com1.strip())) + '\n')
            delta_file.write('-' + str(len(qua1.strip())) + '\n')
            id1 = original_file.readline().strip()
            seq1 = original_file.readline().strip()
            com1 = original_file.readline().strip()
            qua1 = original_file.readline().strip()
            if id1 == '':
                break
        for (t1, t2) in ((id1, id2), (seq1, seq2), (com1, com2), (qua1, qua2)):
            diff = dmp.diff_main(t1.strip(), t2.strip())
            delta = dmp.diff_toDelta(diff) + '\n'
            delta_file.write(delta)
            if output_processed:
                print t2

    delta_file.close()

    # Copy the delta file to a compressed archive, and remove the delta file
    zf = zipfile.ZipFile(delta_name + '.zip', mode='w')
    try:
        zf.write(delta_name, compress_type=compression)
        zf.writestr('md5_checksum', md5.digest(), compress_type=compression)
        os.remove(delta_name)
    finally:
        zf.close()


def rebuild_fastq(delta_filename, original_file=sys.stdin, out=sys.stdout, to_stdout=False):
    """Recreates the processed file from the original and delta files."""

    # Convert file names to files, and open quip-files while we're at it.
    if isinstance(original_file, str):
        original_file = _open(original_file)

    if isinstance(out, str):
        out = open(out, 'w')

    if out == sys.stdout:
        to_stdout = False

    md5 = hashlib.md5()

    # Extract the checksum and delta files.

    # If there is no checksum file in the zipfile, bail out.
    # ("I'm not touching that with a 10 foot pole!")

    zf = zipfile.ZipFile(delta_filename)
    namelist = zf.namelist()
    if 'md5_checksum' not in namelist:
        raise ChecksumError('No checksum found.')
    else:
        namelist.pop(namelist.index("md5_checksum"))
        checksum = zf.open('md5_checksum', "r").read()

    # For the delta file, first assume the filename is the same as the archive's name
    # minus ".zip". If that fails, find the first file that contains the word "delta".
    # Else just extract the first file you can find. Ugly, I know... :D

    filename = delta_filename.rpartition('.')[0]
    try:
        zf.extract(filename)
    except KeyError:
        delta_names = [s for s in namelist if "delta" in s]
        if len(delta_names) > 0:
            filename = delta_names[0]
        else:
            filename = namelist[0]
        zf.extract(filename)

    deltas = open(filename, "r")

    # Read both files line by line, and print the results as long as the delta file has lines to offer.
    while True:
        t1 = original_file.readline()
        delta = deltas.readline().strip()
        if delta == '':
            break
        diff = dmp.diff_fromDelta(t1.strip(), delta.strip())
        t2 = dmp.diff_text2(diff)
        if t2 != '':
            md5.update(t2)
            out.write(t2 + '\n')
            if to_stdout:
                print t2

    # Clean up the uncompressed delta file
    deltas.close()
    os.remove(filename)

    if not md5.digest() == checksum:
        raise ChecksumError("Checksum did not match!")

class DeltaFile():
    def __init__(self, mode, delta_filename, original_file=sys.stdin):
        if mode == 'r':
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
        elif mode == 'w':
            print "Not just yet..."
        else:
            raise Exception('Illegal mode: ' + str(mode))

    def __iter__(self):
        return self

    def next(self):
        if self.original_file.closed or self.deltas.closed:
            raise IOError("Trying to iterate over closed files...")

        t1 = self.original_file.readline()
        delta = self.deltas.readline().strip()
        if delta == '':
            # End of File
            # Clean up the uncompressed delta file
            self.deltas.close()
            os.remove(self.filename)
            # Check the checksum...
            if not self.md5.digest() == self.checksum:
                raise ChecksumError("Checksum did not match!")
            # Kill the iterator
            raise StopIteration

        diff = dmp.diff_fromDelta(t1.strip(), delta.strip())
        t2 = dmp.diff_text2(diff)
        if t2 != '':
            self.md5.update(t2)
            return t2
        else:
            # Keep looking until you have another line to offer
            return self.next()

    def readline(self):
        return self.next()

    def readlines(self):
        return [line for line in self]

    def close(self):
        if not self.deltas.closed:
            self.deltas.close()
        try:
            os.remove(self.filename)
        except IOError:
            pass