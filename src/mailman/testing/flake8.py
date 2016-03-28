# Copyright (C) 2016 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Flake8 extensions for Mailman coding style."""


from ast import NodeVisitor
from collections import namedtuple
from enum import Enum


class ImportType(Enum):
    non_from = 0
    from_import = 1


ImportRecord = namedtuple('ImportRecord', 'itype lineno colno, module, names')


class ImportVisitor(NodeVisitor):
    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        if node.col_offset != 0:
            # Ignore nested imports.
            return
        names = [alias.name for alias in node.names]
        self.imports.append(
            ImportRecord(ImportType.non_from, node.lineno, node.col_offset,
                         None, names))

    def visit_ImportFrom(self, node):
        if node.col_offset != 0:
            # Ignore nested imports.
            return
        names = [alias.name for alias in node.names]
        self.imports.append(
            ImportRecord(ImportType.from_import, node.lineno, node.col_offset,
                         node.module, names))


class ImportOrder:
    name = 'mm-import-order'
    version = '0.1'

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

    def _error(self, record, code, text):
        return (record.lineno, record.colno,
                '{} {}'.format(code, text), ImportOrder)

    def run(self):
        visitor = ImportVisitor()
        visitor.visit(self.tree)
        last_import = None
        for record in visitor.imports:
            if last_import is None:
                last_import = record
                continue
            if record.itype is ImportType.non_from:
                if len(record.names) != 1:
                    yield self._error(record, 'B402',
                                      'Multiple names on non-from import')
                if last_import.itype is ImportType.from_import:
                    yield self._error(record, 'B401',
                                      'Non-from import follows from-import')
                if len(last_import.names[0]) > len(record.names[0]):
                    yield self._error(
                        record, 'B403',
                        'Shorter non-from import follows longer')
                # It's also possible that the imports are the same length, in
                # which case they must be sorted alphabetically.
                if (len(last_import.names[0]) == len(record.names[0]) and
                        last_import.names[0] > record.names[0]):
                    yield self._error(
                        record, 'B404',
                        'Non-from imports not alphabetically sorted')
                if last_import.lineno + 1 != record.lineno:
                    yield self._error(
                        record, 'B405',
                        'Unexpected blank line since last non-from import')
            else:
                assert record.itype is ImportType.from_import
                if (last_import.itype is ImportType.non_from and
                        record.lineno != last_import.lineno + 2):
                    yield self._error(
                        record, 'B406',
                        'Expected one blank line since last non-from import')
                if last_import.itype is ImportType.non_from:
                    last_import = record
                    continue
                if last_import.module > record.module:
                    yield self._error(
                        record, 'B407',
                        'From-imports not sorted alphabetically')
                # All imports from the same module should show up in the same
                # multiline import.
                if last_import.module == record.module:
                    yield self._error(
                        record, 'B408',
                        'Importing from same module on different lines')
                # Check the sort order of the imported names.
                if sorted(record.names) != record.names:
                    yield self._error(
                        record, 'B409',
                        'Imported names are not sorted alphabetically')
                # How to check for no blank lines between from imports?
            # Update the last import.
            last_import = record
