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

"""Test the `member-moderation` and `nonmember-moderation` rules."""

__all__ = [
    'TestModeration',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.interfaces.action import Action
from mailman.interfaces.member import MemberRole
from mailman.interfaces.usermanager import IUserManager
from mailman.rules import moderation
from mailman.testing.helpers import specialized_message_from_string as mfs
from mailman.testing.layers import ConfigLayer
from zope.component import getUtility



class TestModeration(unittest.TestCase):
    """Test the approved handler."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')

    def test_member_and_nonmember(self):
        user_manager = getUtility(IUserManager)
        anne = user_manager.create_address('anne@example.com')
        user_manager.create_address('bill@example.com')
        self._mlist.subscribe(anne, MemberRole.member)
        rule = moderation.NonmemberModeration()
        msg = mfs("""\
From: anne@example.com
Sender: bill@example.com
To: test@example.com
Subject: A test message
Message-ID: <ant>
MIME-Version: 1.0

A message body.
""")
        # Both Anne and Bill are in the message's senders list.
        self.assertIn('anne@example.com', msg.senders)
        self.assertIn('bill@example.com', msg.senders)
        # The NonmemberModeration rule should *not* hit, because even though
        # Bill is in the list of senders he is not a member of the mailing
        # list.  Anne is also in the list of senders and she *is* a member, so
        # she takes precedence.
        result = rule.check(self._mlist, msg, {})
        self.assertFalse(result, 'NonmemberModeration rule should not hit')
        # After the rule runs, Bill becomes a non-member.
        bill_member = self._mlist.nonmembers.get_member('bill@example.com')
        self.assertIsNotNone(bill_member)
        # Bill is not a member.
        bill_member = self._mlist.members.get_member('bill@example.com')
        self.assertIsNone(bill_member)

    def test_moderation_reason(self):
        # When a message is moderated, a reason is added to the metadata.
        user_manager = getUtility(IUserManager)
        anne = user_manager.create_address('anne@example.com')
        msg = mfs("""\
From: anne@example.com
To: test@example.com
Subject: A test message
Message-ID: <ant>
MIME-Version: 1.0

A message body.
""")
        # Anne is in the message's senders list.
        self.assertIn('anne@example.com', msg.senders)
        # Now run the rule.
        rule = moderation.NonmemberModeration()
        msgdata = {}
        result = rule.check(self._mlist, msg, msgdata)
        self.assertTrue(result, 'NonmemberModeration rule should hit')
        # The reason for moderation should be in the msgdata.
        reasons = msgdata['moderation_reasons']
        self.assertEqual(reasons, ['The message is not from a list member'])
        # Now make Anne a moderated member...
        anne_member = self._mlist.subscribe(anne, MemberRole.member)
        anne_member.moderation_action = Action.hold
        # ...and run the rule again.
        rule = moderation.MemberModeration()
        msgdata = {}
        result = rule.check(self._mlist, msg, msgdata)
        self.assertTrue(result, 'MemberModeration rule should hit')
        # The reason for moderation should be in the msgdata.
        reasons = msgdata['moderation_reasons']
        self.assertEqual(
            reasons, ['The message comes from a moderated member'])

    def test_these_nonmembers(self):
        # Test the legacy *_these_nonmembers attributes.
        user_manager = getUtility(IUserManager)
        actions = {
            'anne@example.com': 'accept',
            'bill@example.com': 'hold',
            'chris@example.com': 'reject',
            'dana@example.com': 'discard',
            '^anne-.*@example.com': 'accept',
            '^bill-.*@example.com': 'hold',
            '^chris-.*@example.com': 'reject',
            '^dana-.*@example.com': 'discard',
            }
        rule = moderation.NonmemberModeration()
        user_manager = getUtility(IUserManager)
        for address, action_name in actions.items():
            setattr(self._mlist,
                    '{}_these_nonmembers'.format(action_name),
                    [address])
            if address.startswith('^'):
                # It's a pattern, craft a proper address.
                address = address[1:].replace('.*', 'something')
            user_manager.create_address(address)
            msg = mfs("""\
From: {}
To: test@example.com
Subject: A test message
Message-ID: <ant>
MIME-Version: 1.0

A message body.
""".format(address))
            msgdata = {}
            result = rule.check(self._mlist, msg, msgdata)
            self.assertTrue(result, 'NonmemberModeration rule should hit')
            self.assertIn('moderation_action', msgdata)
            self.assertEqual(msgdata['moderation_action'], action_name,
                'Wrong action for {}: {}'.format(address, action_name))
