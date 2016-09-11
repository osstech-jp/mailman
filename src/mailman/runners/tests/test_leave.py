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

"""Test mailing list un-subscriptions."""

import unittest

from email.iterators import body_line_iterator
from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.database.transaction import transaction
from mailman.interfaces.usermanager import IUserManager
from mailman.interfaces.mailinglist import SubscriptionPolicy
from mailman.runners.command import CommandRunner
from mailman.testing.helpers import (
    get_queue_messages, make_testable_runner,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer
from mailman.testing.helpers import set_preferred
from zope.component import getUtility


class TestLeave(unittest.TestCase):
    """Test mailing list un-subscriptions"""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.send_welcome_message = False
        self._mlist.unsubscription_policy = SubscriptionPolicy.open
        self._commandq = config.switchboards['command']
        self._runner = make_testable_runner(CommandRunner, 'command')

    def test_leave(self):
        with transaction():
            anne = getUtility(IUserManager).create_user('anne@example.org')
            set_preferred(anne)
        self._mlist.subscribe(list(anne.addresses)[0])
        msg = mfs("""\
From: anne@example.org
To: test-leave@example.com

leave
""")
        self._commandq.enqueue(msg, dict(listid='test.example.com',
                                         subaddress='leave'))
        self._runner.run()
        items = get_queue_messages('virgin', sort_on='subject',
                                   expected_count=1)
        self.assertTrue(str(items[0].msg['subject']).startswith('confirm'))
        confirmation_lines = []
        in_results = False
        for line in body_line_iterator(items[0].msg):
            line = line.strip()
            if in_results:
                if line.startswith('- Done'):
                    break
                if len(line) > 0:
                    confirmation_lines.append(line)
            if line.strip() == '- Results:':
                in_results = True
                # There should be exactly one confirmation line.
        self.assertEqual(len(confirmation_lines), 1)
        # And the confirmation line should name Anne's email address.
        self.assertIn('anne@example.org', confirmation_lines[0])
