#!/usr/bin/env python
__author__ = 'averaart'

from distutils.core import setup
from distutils.sysconfig import get_python_lib
from os import chmod
from sys import argv

setup(name='fq_delta',
      version='1.0',
      description='Efficient storage of processed versions of fastq files',
      author='Andra Veraart',
      author_email='mail@andra.nl',
      url='https://github.com/averaart/fq_delta',
      packages=['fq_delta', 'diff_match_patch'],
      package_dir={'fq_delta': 'fq_delta'},
      package_data={'fq_delta': ['*.sh']},
      scripts=['scripts/delta', 'scripts/rebuild', 'scripts/test_fq_delta']
      )