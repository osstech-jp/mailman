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

"""Test mailing list un-subscriptions."""

import unittest

from email.iterators import body_line_iterator
from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.database.transaction import transaction
from mailman.interfaces.mailinglist import SubscriptionPolicy
from mailman.interfaces.usermanager import IUserManager
from mailman.runners.command import CommandRunner
from mailman.testing.helpers import (
    get_queue_messages,
    make_testable_runner,
    set_preferred,
    specialized_message_from_string as mfs,
)
from mailman.testing.layers import ConfigLayer
from zope.component import getUtility


def confirmation_line(msg):
    confirmation_lines = []
    in_results = False
    for line in body_line_iterator(msg):
        line = line.strip()
        if in_results:
            if line.startswith('- Done'):
                break
            if len(line) > 0:
                confirmation_lines.append(line)
        if line.strip() == '- Results:':
            in_results = True
    # There should be exactly one confirmation line.
    assert len(confirmation_lines) == 1, confirmation_lines
    return confirmation_lines[0]


class TestLeave(unittest.TestCase):
    """Test mailing list un-subscriptions"""

    layer = ConfigLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('test@example.com')
            self._mlist.send_goodbye_message = False
            self._mlist.send_welcome_message = False
        self._commandq = config.switchboards['command']
        self._runner = make_testable_runner(CommandRunner, 'command')

    def test_leave(self):
        with transaction():
            self._mlist.unsubscription_policy = SubscriptionPolicy.confirm
            anne = getUtility(IUserManager).create_user('anne@example.org')
            set_preferred(anne)
            self._mlist.subscribe(anne.preferred_address)
        msg = mfs("""\
From: anne@example.org
To: test-leave@example.com

leave
""")
        self._commandq.enqueue(msg, dict(listid='test.example.com',
                                         subaddress='leave'))
        self._runner.run()
        # One message with confirmation of her unsubscription event should be
        # sent.
        items = get_queue_messages('virgin', expected_count=1)
        confirmation = items[0].msg
        self.assertTrue(str(confirmation['subject']).startswith('Your conf'))

    def test_double_leave(self):
        # In this case, the user can be unsubscribed immediately because the
        # policy does not require confirmation, however because the email is
        # sent to the -leave address and it contains the 'leave' command, we
        # should only process one command per email.
        with transaction():
            self._mlist.unsubscription_policy = SubscriptionPolicy.open
            anne = getUtility(IUserManager).create_user('anne@example.org')
            set_preferred(anne)
            self._mlist.subscribe(anne.preferred_address)
        msg = mfs("""\
From: anne@example.org
To: test-leave@example.com

leave
""")
        self._commandq.enqueue(msg, dict(listid='test.example.com',
                                         subaddress='leave'))
        self._runner.run()
        get_queue_messages('virgin', sort_on='subject', expected_count=0)

    def test_leave_no_user_produces_response(self):
        msg = mfs("""\
From: anne@example.org
To: test-leave@example.com

leave
""")
        self._commandq.enqueue(msg, dict(listid='test.example.com',
                                         subaddress='leave'))
        self._runner.run()
        # This should send out an error email.
        get_queue_messages('virgin', expected_count=1)

    def test_leave_unverified_produces_response(self):
        with transaction():
            self._mlist.unsubscription_policy = SubscriptionPolicy.confirm
            anne = getUtility(IUserManager).create_user('anne@example.org')
            set_preferred(anne)
            self._mlist.subscribe(anne.preferred_address)
            # Set address unverified.
            anne.preferred_address.verified_on = None
        msg = mfs("""\
From: anne@example.org
To: test-leave@example.com

leave
""")
        # Clear virgin queue.
        get_queue_messages('virgin')
        self._commandq.enqueue(msg, dict(listid='test.example.com',
                                         subaddress='leave'))
        self._runner.run()
        # This should send out an error email.
        get_queue_messages('virgin', expected_count=1)
