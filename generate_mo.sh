#!/bin/bash

# This script generates .mo files from all the .po files in the source.

echo 'Generating mo files for GNU Mailman ...'
for file in `find . -name 'mailman.po'`
do
    echo $file
    msgfmt $file -o ${file/po/mo} -v
done
