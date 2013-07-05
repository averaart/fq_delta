__author__ = 'averaart'
#!/usr/bin/env python

from distutils.core import setup

setup(name='fq_delta',
      version='1.0',
      description='Efficient storage of processed versions of fastq files',
      author='Andra Veraart',
      author_email='mail@andra.nl',
      url='https://github.com/averaart/fq_delta',
      packages=['fq_delta', 'diff_match_patch'],
      )