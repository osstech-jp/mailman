#! /usr/bin/env python
# Author: Abhilash Raj
# Date: Sept 26 2020
#
# The purpose of this script is to generate a multi-lingual en po file for
# Mailman Core. Multi-lingual PO files use both a .pot file and a reference po
# file. The reference in our case is en and is what is displayed in Weblate
# when translating.
#
# Since there are no utilities to create multi-lingual reference PO file, this
# script exists to solve that purpose. Here is how it works:
#
# It will read the default en po file and set all msgstr to be same as
# msgid. The only exception to this is email templates, where the msgid is the
# filename of the template and msgstr is the content of that file.

from pathlib import Path
try:
    from babel.messages.pofile import read_po, write_po
except ImportError:
    print('Please install `babel` to run this script.')
    exit(1)

PO_PATH = Path('src/mailman/messages/en/LC_MESSAGES/mailman.po')
TEMPLATE_BASE_PATH = Path('src/mailman/templates/en')


def get_po(path):
    "Read the po file path and return a Catalog object."
    with path.open() as fd:
        catalog = read_po(fd)
    return catalog

def put_po(path, catalog):
    "Write the catalog object to the po file path."
    with path.open('bw') as fd:
        write_po(fd, catalog, include_previous=True, width=85, )

def get_template(name):
    "Get the template text with the name if it exists."
    template_path = TEMPLATE_BASE_PATH / name
    if not template_path.exists():
        return ''
    return template_path.read_text().rstrip('\n')


def main():
    catalog = get_po(PO_PATH)
    for each in catalog:
        if each.id.endswith('.txt'):
            each.string = get_template(each.id)
        else:
            each.string = each.id
    put_po(PO_PATH, catalog)
    print(f'Updated {PO_PATH}')

main()
