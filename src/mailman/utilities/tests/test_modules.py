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
import unittest

from mailman.interfaces.styles import IStyle
from mailman.utilities.modules import find_components
from pkg_resources import resource_filename


class TestModuleImports(unittest.TestCase):

    def test_find_modules_with_dotfiles(self):
        # Emacs creates lock files when a single file is opened by more than
        # one user. These files look like .#<filename>.py because of which
        # find_components tries to import them but fails. All such files should
        # be ignored by default.
        bad_file = resource_filename('mailman.styles', '.#bad_file.py')
        # create the bad file by opening it.
        fd = os.open(bad_file, os.O_CREAT)
        # Check if the file was created.
        self.assertNotEqual(fd, 0)
        os.close(fd)
        # try importing all modules from this path i.e. iterate over the
        # iterator returned by find_components.
        list(find_components('mailman.styles', IStyle))
        # remove the bad file.
        errno = os.remove(bad_file)
        self.assertNotEqual(errno, 0)
