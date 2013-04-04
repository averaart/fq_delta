#!/usr/bin/python
__author__ = 'averaart'

# Batteries included
import os
import sys
from subprocess import Popen, PIPE
import hashlib
import argparse
import zipfile

# 3rd party imports
import diff_match_patch as dmp_module

# Custom modules
import fq_delta

# function to either read a file, or unquip an archive
def openf(name):
    if name[-3:] == '.qp':
        return Popen('unquip -c ' + name, shell=True, stdout=PIPE).stdout
    else:
        return open(name, 'r')


# build argument parser

parser = argparse.ArgumentParser(description='This script recreates a version of a fastq file based on its originating '
                                             'file and a delta file. The delta file is assumed to be inside a .zip '
                                             'file.',
                                 epilog='The original file can either be fastq files, or a file compressed with Quip '
                                        '(http://homes.cs.washington.edu/~dcjones/quip/). Quip files are recognised by'
                                        'their .qp extension. This ofcourse requires Quip to be installed and '
                                        'available on PATH. Exit code 1 indicates a failed checksum. Exit code 2 '
                                        'indicates a missing checksum in the zipfile.')
parser.add_argument('file1',
                    type=str,
                    help='the original file, or the delta file if -si is set')
parser.add_argument('file2',
                    nargs='?',
                    type=str,
                    help='the delta file, or the output file if -si is set')
parser.add_argument('file3',
                    nargs='?',
                    type=str,
                    help='the output file, defaults to stdout')
parser.add_argument("-si", "--stdin",
                    action="store_true",
                    help="use stdin as the original file")
parser.add_argument("-so", "--stdout",
                    action="store_true",
                    help="output to both an output file and stdout")


# setup
dmp = dmp_module.diff_match_patch()
args = parser.parse_args()
md5 = hashlib.md5()

if args.stdin:
    f1 = sys.stdin
    f2 = args.file1
    if args.file2 is None:
        out = sys.stdout
        args.stdout = False
    else:
        out = open(args.file2, 'w')
else:
    f1 = openf(args.file1)
    f2 = args.file2
    if args.file3 is None:
        out = sys.stdout
        args.stdout = False
    else:
        out = open(args.file3, 'w')

fq_delta.rebuild_fastq(f2, f1, out)