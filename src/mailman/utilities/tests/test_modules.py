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

"""Tests for mailman.utilities.modules."""

import os
import sys
import unittest

from contextlib import ExitStack
from mailman.interfaces.styles import IStyle
from mailman.utilities.modules import find_components
from tempfile import TemporaryDirectory


class TestModuleImports(unittest.TestCase):
    def test_find_modules_with_dotfiles(self):
        # Emacs creates lock files when a single file is opened by more than
        # one user. These files look like .#<filename>.py because of which
        # find_components tries to import them but fails. All such files should
        # be ignored by default.
        with ExitStack() as resources:
            # Creating a temporary directory and adding it to sys.path.
            temp_package = resources.enter_context(TemporaryDirectory())
            sys.path.insert(1, temp_package)
            # Create a module inside the above package along with a good, bad
            # and __iniit__ file so that we can import form it.
            module_path = os.path.join(temp_package, 'mypackage')
            os.mkdir(module_path)
            init_file = os.path.join(module_path, '__init__.py')
            good_file = os.path.join(module_path, 'goodfile.py')
            bad_file = os.path.join(module_path, '.#badfile.py')
            fd_init = os.open(init_file, os.O_CREAT)
            fd_good = os.open(good_file, os.O_CREAT)
            fd_bad = os.open(bad_file, os.O_CREAT)
            # Check if the file was created.
            self.assertNotEqual(fd_init, 0)
            self.assertNotEqual(fd_good, 0)
            self.assertNotEqual(fd_bad, 0)
            # Add a dummy implementer of the interface inside goodfile.
            with open(good_file, 'w') as fd:
                fd.write("""\
from mailman import public
from mailman.interfaces.styles import IStyle
from zope.interface import implementer

@public
@implementer(IStyle)
class DummyStyleClass():
    name = 'dummy-style-class'
    def apply(self):
        pass
                """)
            # Try importing all modules from this path i.e. iterate over the
            # iterator returned by find_components.
            pkgs = list(find_components('mypackage', IStyle))
            self.assertEqual(len(pkgs), 1)
            self.assertEqual(pkgs[0].name, 'dummy-style-class')
        # Finally remove the temporary package from path and sys.modules
        sys.path.remove(temp_package)
        del sys.modules['mypackage']
