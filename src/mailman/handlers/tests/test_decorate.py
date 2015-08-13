# Copyright (C) 2014-2015 by the Free Software Foundation, Inc.
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

"""Test the decorate handler."""

__all__ = [
    'TestDecorate',
]

import os
import tempfile
import unittest
from mock import patch

from mailman.app.lifecycle import create_list
from mailman.archiving.prototype import Prototype
from mailman.config import config
from mailman.handlers import decorate
from mailman.testing.helpers import configuration
from mailman.testing.helpers import specialized_message_from_string as mfs
from mailman.testing.layers import ConfigLayer


class TestArchiver:
    "A test archiver"

    name = "testarchiver"
    is_enabled = False

    @staticmethod
    def permalink(mlist, msg):
        return "http://example.com/link_to_message"


class TestDecorate(unittest.TestCase):
    """Test the cook_headers handler."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._msg = mfs("""\
To: test@example.com
From: aperson@example.com
Message-ID: <somerandomid.example.com>
Content-Type: text/plain;

This is a test message.
""")
        template_dir = tempfile.mkdtemp()
        site_dir = os.path.join(template_dir, 'site', 'en')
        os.makedirs(site_dir)
        config.push('templates', """
        [paths.testing]
        template_dir: {0}
        """.format(template_dir))
        self.footer_path = os.path.join(site_dir, 'myfooter.txt')


    @patch('mailman.archiving.prototype.Prototype', TestArchiver)
    @configuration('archiver.prototype', enable='yes')
    def test_decorate_footer_with_arcihve_url(self):
        with open(self.footer_path, 'w') as fp:
            print("${testarchiver_url}", file=fp)
        self._mlist.footer_uri = 'mailman:///myfooter.txt'
        self._mlist.preferred_language = 'en'
        decorate.process(self._mlist, self._msg, {})
        self.assertIn("http://example.com/link_to_message",
                      self._msg.as_string())
