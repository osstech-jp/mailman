#!/bin/bash

# This script update the mailman.pot file with new strings.

pot_file="src/mailman/messages/mailman.pot"

# First, update the pot file with the new strings.
ls src/mailman/*/*.py | xargs xgettext -o $pot_file -w 115

# Then, update all the existing .po files.
for each in src/mailman/templates/en/*.txt; do
    filename=$(basename $each)
    echo -e "\nmsgid \"$filename\"" >> $pot_file
    echo "msgstr \"\"" >> $pot_file
done

# Then, update all the po files.
for each in src/mailman/messages/*/*/*.po; do
    msgmerge --update -w 85 --no-fuzzy-matching --no-wrap $each $pot_file
done

# Finally, update the engligh PO file.
python3 update_po.py
