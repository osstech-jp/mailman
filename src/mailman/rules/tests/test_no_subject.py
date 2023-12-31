# Copyright (C) 2016-2023 by the Free Software Foundation, Inc.
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
# GNU Mailman.  If not, see <https://www.gnu.org/licenses/>.

"""Test the `no_subject` header rule."""

import unittest

from email.header import Header
from mailman.app.lifecycle import create_list
from mailman.email.message import Message
from mailman.rules import no_subject
from mailman.testing.layers import ConfigLayer


class TestNoSubject(unittest.TestCase):
    """Test the no_subject rule."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._rule = no_subject.NoSubject()

    def test_header_instance_empty(self):
        msg = Message()
        msg['Subject'] = Header('')
        result = self._rule.check(self._mlist, msg, {})
        self.assertTrue(result)

    def test_header_instance_not_empty(self):
        msg = Message()
        msg['Subject'] = Header('Test subject')
        result = self._rule.check(self._mlist, msg, {})
        self.assertFalse(result)

    def test_no_subject_returns_reason(self):
        msg = Message()
        msg['Subject'] = Header('')
        msgdata = {}
        result = self._rule.check(self._mlist, msg, msgdata)
        self.assertTrue(result)
        self.assertEqual(msgdata['moderation_reasons'],
                         ['Message has no subject'])
