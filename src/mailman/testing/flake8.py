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


class ImportVisitor(NodeVisitor):
    def __init__(self):
        self.last_import = None

    def visit_Import(self, node):
        if node.col_offset != 0:
            # Ignore nested imports.
            return
        


class ImportOrder:
    name = 'mm-import-order'
    version = '0.1'

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

    def run(self):
        print('Running', self.name, self.version)
