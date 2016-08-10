# Copyright (C) 2014-2016 by the Free Software Foundation, Inc.
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

"""Test the cook_headers handler."""

import unittest

from mailman.app.lifecycle import create_list
from mailman.handlers import cook_headers
from mailman.interfaces.member import DeliveryMode
from mailman.testing.helpers import (
    get_queue_messages, LogFileMark, make_digest_messages, subscribe)
from mailman.testing.layers import ConfigLayer


class TestCookHeaders(unittest.TestCase):
    """Test the cook_headers handler."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.send_welcome_message = False

    def test_process_digest(self):
        # MIME digests messages are multiparts.
        anne = subscribe(self._mlist, 'Anne')
        anne.preferences.delivery_mode = DeliveryMode.mime_digests
        bart = subscribe(self._mlist, 'Bart')
        bart.preferences.delivery_mode = DeliveryMode.plaintext_digests
        make_digest_messages(self._mlist)
        items = get_queue_messages('virgin', expected_count=2)
        for item in items:
            try:
                cook_headers.process(self._mlist, item.msg, {})
            except AttributeError as error:
                # LP: #1130696 would raise an AttributeError on .sender
                self.fail(error)

    def test_uheader_multiline(self):
        # Multiline headers should be truncated (GL#273).
        mark = LogFileMark('mailman.error')
        header = cook_headers.uheader(
            self._mlist, 'A multiline\ndescription', 'X-Header')
        self.assertEqual(
            header.encode(), 'A multiline [...]')
        log_messages = mark.read()
        self.assertIn(
            'Header X-Header contains a newline, truncating it', log_messages)
