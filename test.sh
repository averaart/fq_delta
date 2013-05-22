#!/bin/bash

# This script runs a few tests on fq_delta.
# It assumes there is access to the internet to download the testfile.
# It also requires delta.py, rebuild.py and cutadapt to be available in PATH.

# Download a test-file
echo
echo "Downloading a fastq-file to run the tests on."
curl ftp://anonymous@ftp.ddbj.nig.ac.jp/ddbj_database/dra/fastq/SRA064/SRA064221/SRX216164/SRR647485.fastq.bz2 -o SRR647485.fastq.bz2

# Decompress
bunzip2 SRR647485.fastq.bz2


printf "\n\n\n"


# Apply cutadapt to create a new fastq-file
cutadapt -a GATCGGAAGAGCACACGTCTGAACTCCAGTCACCGATGTATCTCGTATGC SRR647485.fastq > SRR647485.ca.fastq 2> /dev/null

# Create delta-file
delta.py SRR647485.fastq SRR647485.ca.fastq SRR647485.ca.delta

# Demonstrate difference in file-size between the delta-file and the actual second version
echo "Here's the difference between the processed file and the delta-file after running cutadapt."
ls -l SRR647485.ca.*

# Rebuild the processed file using the original and the delta-file
rebuild.py SRR647485.fastq SRR647485.ca.delta.zip SRR647485.ca.rebuilt.fastq

# Compare the processed file with the rebuilt file
echo "Comparing the processed file with the rebuilt file. The next line should be empty."
cmp SRR647485.ca.fastq SRR647485.ca.rebuilt.fastq
echo

# Rename and copy zip-files for later use
mv SRR647485.ca.delta.zip SRR647485.rem_md5.delta.zip
cp SRR647485.rem_md5.delta.zip SRR647485.cha_md5.delta.zip
cp SRR647485.rem_md5.delta.zip SRR647485.cha_fq.delta.zip

# Clean up newly created files
rm SRR647485.ca.*


printf "\n\n\n"


# Create a file where lines are removed from head, center and tail.
split -l 31952 SRR647485.fastq part
cat partab partad > SRR647485.rem.fastq
rm parta*

# Create delta-file
delta.py SRR647485.fastq SRR647485.rem.fastq SRR647485.rem.delta

# Demonstrate difference in file-size between the delta-file and the actual second version
echo "Here's the difference between the processed file and the delta-file after removing lines."
ls -l SRR647485.rem.*

# Rebuild the processed file using the original and the delta-file
rebuild.py SRR647485.fastq SRR647485.rem.delta.zip SRR647485.rem.rebuilt.fastq

# Compare the processed file with the rebuilt file
echo "Comparing the processed file with the rebuilt file. The next line should be empty."
cmp SRR647485.rem.fastq SRR647485.rem.rebuilt.fastq
echo

# Clean up newly created files, but leave the checksum for a later test.
unzip SRR647485.rem.delta.zip md5_checksum > /dev/null
rm SRR647485.rem.*


printf "\n\n\n"


# Remove md5_checksum from zip-file
echo "Removing md5_checksum from zip-file"
zip SRR647485.rem_md5.delta.zip -d md5_checksum > /dev/null

# Try to rebuild the processed file
echo "The following command will raise an error in Python."
rebuild.py SRR647485.fastq SRR647485.rem_md5.delta.zip SRR647485.rem_md5.fastq


printf "\n\n\n"


# Replace the checksum with that of a different delta-file
echo "Replacing md5_checksum in zip-file"
zip SRR647485.cha_md5.delta.zip md5_checksum > /dev/null

# Try to rebuild the processed file
echo "The following command will raise an error in Python."
rebuild.py SRR647485.fastq SRR647485.cha_md5.delta.zip SRR647485.cha_md5.fastq

# Clean up the mess
rm md5_* *.cha_md5.*


printf "\n\n\n"


echo "Creating a delta-file that breaks during rebuild, because the length of source and"
echo "target strings do not match up. Basically a feature of the underlying dmp-library."
unzip SRR647485.cha_fq.delta.zip SRR647485.ca.delta > /dev/null
mv SRR647485.ca.delta SRR647485.ca.delta.old
printf "=59\n=100\n=59\n=100\n" > SRR647485.ca.delta
tail -n +5 SRR647485.ca.delta.old >> SRR647485.ca.delta
zip SRR647485.cha_fq.delta.zip SRR647485.ca.delta > /dev/null

# Try to rebuild the processed file
echo "The following command will raise an error in Python."
rebuild.py SRR647485.fastq SRR647485.cha_fq.delta.zip SRR647485.cha_fq.fastq


printf "\n\n\n"


echo "Creating a delta-file that breaks after rebuild, because the checksums don't match up."
printf "=59\n=100\t-1\n=59\n=100\t-1\n" > SRR647485.ca.delta
tail -n +5 SRR647485.ca.delta.old >> SRR647485.ca.delta
zip SRR647485.cha_fq.delta.zip SRR647485.ca.delta > /dev/null

# Try to rebuild the processed file
echo "The following command will raise an error in Python."
rebuild.py SRR647485.fastq SRR647485.cha_fq.delta.zip SRR647485.cha_fq.fastq

# Clean up the mess
rm *.delta.*

echo