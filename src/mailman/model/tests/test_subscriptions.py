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

"""Test the subscription service."""

import unittest

from mailman.app.lifecycle import create_list
from mailman.interfaces.listmanager import NoSuchListError
from mailman.interfaces.member import MemberRole
from mailman.interfaces.subscriptions import (
    ISubscriptionService, TooManyMembersError)
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import set_preferred, subscribe
from mailman.testing.layers import ConfigLayer
from mailman.utilities.datetime import now
from zope.component import getUtility


class TestSubscriptionService(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.admin_immed_notify = False
        self._user_manager = getUtility(IUserManager)
        self._service = getUtility(ISubscriptionService)

    def test_find_member_address_no_user(self):
        # Find address-based memberships when no user is linked to the address.
        address = self._user_manager.create_address(
            'anne@example.com', 'Anne Address')
        self._mlist.subscribe(address)
        members = self._service.find_members('anne@example.com')
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].address, address)

    def test_find_member_address_with_user(self):
        # Find address-based memberships when a user is linked to the address.
        user = self._user_manager.create_user(
            'anne@example.com', 'Anne User')
        address = set_preferred(user)
        # Subscribe the address.
        self._mlist.subscribe(address)
        members = self._service.find_members('anne@example.com')
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].user, user)

    def test_find_member_user(self):
        # Find user-based memberships by address.
        user = self._user_manager.create_user(
            'anne@example.com', 'Anne User')
        set_preferred(user)
        # Subscribe the user.
        self._mlist.subscribe(user)
        members = self._service.find_members('anne@example.com')
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].user, user)

    def test_find_member_user_secondary_address(self):
        # Find user-based memberships using a secondary address.
        user = self._user_manager.create_user(
            'anne@example.com', 'Anne User')
        set_preferred(user)
        # Create a secondary address.
        address_2 = self._user_manager.create_address(
            'anne2@example.com', 'Anne User 2')
        address_2.user = user
        # Subscribe the user.
        self._mlist.subscribe(user)
        # Search for the secondary address.
        members = self._service.find_members('anne2@example.com')
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].user, user)

    def test_wont_find_member_secondary_address(self):
        # A user is subscribed with one of their address, and a search is
        # performed on another of their addresses.  This is not supported; the
        # subscription is not returned.
        user = self._user_manager.create_user(
            'anne@example.com', 'Anne User')
        set_preferred(user)
        # Create a secondary address.
        address_2 = self._user_manager.create_address(
            'anne2@example.com', 'Anne User 2')
        address_2.verified_on = now()
        address_2.user = user
        # Subscribe the secondary address.
        self._mlist.subscribe(address_2)
        # Search for the primary address.
        members = self._service.find_members('anne@example.com')
        self.assertEqual(len(members), 0)

    def test_find_member_user_id(self):
        # Find user-based memberships by user_id.
        user = self._user_manager.create_user(
            'anne@example.com', 'Anne User')
        set_preferred(user)
        # Subscribe the user.
        self._mlist.subscribe(user)
        members = self._service.find_members(user.user_id)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].user, user)

    def test_find_member_user_id_controlled_addresses(self):
        # Find address-based memberships by user_id when a secondary address is
        # subscribed.
        user = self._user_manager.create_user(
            'anne@example.com', 'Anne User')
        set_preferred(user)
        # Create a secondary address.
        address_2 = self._user_manager.create_address(
            'anne2@example.com', 'Anne User 2')
        address_2.verified_on = now()
        address_2.user = user
        # Create a third address.
        address_3 = self._user_manager.create_address(
            'anne3@example.com', 'Anne User 3')
        address_3.verified_on = now()
        address_3.user = user
        # Subscribe the secondary address only.
        self._mlist.subscribe(address_2)
        members = self._service.find_members(user.user_id)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].address, address_2)

    def test_find_member_sorting(self):
        # Check that the memberships are properly sorted.
        user = self._user_manager.create_user(
            'anne1@example.com', 'Anne User')
        address = set_preferred(user)
        # Create a secondary address.
        address_2 = self._user_manager.create_address(
            'anne2@example.com', 'Anne User 2')
        address_2.verified_on = now()
        address_2.user = user
        # Create a third address.
        address_3 = self._user_manager.create_address(
            'anne3@example.com', 'Anne User 3')
        address_3.verified_on = now()
        address_3.user = user
        # Create three lists.
        mlist1 = create_list('test1@example.com')
        mlist1.admin_immed_notify = False
        mlist2 = create_list('test2@example.com')
        mlist2.admin_immed_notify = False
        mlist3 = create_list('test3@example.com')
        mlist3.admin_immed_notify = False
        # Subscribe the addresses in random order
        # https://www.xkcd.com/221/
        mlist3.subscribe(address_3, MemberRole.moderator)
        mlist3.subscribe(address_3, MemberRole.owner)
        mlist3.subscribe(address_3, MemberRole.member)
        mlist3.subscribe(address_2, MemberRole.member)
        mlist3.subscribe(address_2, MemberRole.owner)
        mlist3.subscribe(address_2, MemberRole.moderator)
        mlist3.subscribe(address, MemberRole.owner)
        mlist3.subscribe(address, MemberRole.member)
        mlist3.subscribe(address, MemberRole.moderator)
        mlist2.subscribe(address_2, MemberRole.moderator)
        mlist2.subscribe(address_2, MemberRole.member)
        mlist2.subscribe(address_2, MemberRole.owner)
        mlist2.subscribe(address_3, MemberRole.moderator)
        mlist2.subscribe(address_3, MemberRole.member)
        mlist2.subscribe(address_3, MemberRole.owner)
        mlist2.subscribe(address, MemberRole.owner)
        mlist2.subscribe(address, MemberRole.moderator)
        mlist2.subscribe(address, MemberRole.member)
        mlist1.subscribe(address_2, MemberRole.moderator)
        mlist1.subscribe(address, MemberRole.member)
        mlist1.subscribe(address_3, MemberRole.owner)
        # The results should be sorted first by list id, then by address, then
        # by member role.
        members = self._service.find_members(user.user_id)
        self.assertEqual(len(members), 21)
        self.assertListEqual(
            [(m.list_id.partition('.')[0],
              m.address.email.partition('@')[0],
              m.role)
             for m in members],
            [('test1', 'anne1', MemberRole.member),
             ('test1', 'anne2', MemberRole.moderator),
             ('test1', 'anne3', MemberRole.owner),
             ('test2', 'anne1', MemberRole.member),
             ('test2', 'anne1', MemberRole.owner),
             ('test2', 'anne1', MemberRole.moderator),
             ('test2', 'anne2', MemberRole.member),
             ('test2', 'anne2', MemberRole.owner),
             ('test2', 'anne2', MemberRole.moderator),
             ('test2', 'anne3', MemberRole.member),
             ('test2', 'anne3', MemberRole.owner),
             ('test2', 'anne3', MemberRole.moderator),
             ('test3', 'anne1', MemberRole.member),
             ('test3', 'anne1', MemberRole.owner),
             ('test3', 'anne1', MemberRole.moderator),
             ('test3', 'anne2', MemberRole.member),
             ('test3', 'anne2', MemberRole.owner),
             ('test3', 'anne2', MemberRole.moderator),
             ('test3', 'anne3', MemberRole.member),
             ('test3', 'anne3', MemberRole.owner),
             ('test3', 'anne3', MemberRole.moderator),
             ])

    def test_find_no_members(self):
        members = self._service.find_members()
        self.assertEqual(len(members), 0)

    def test_find_members_no_results(self):
        members = self._service.find_members('zack@example.com')
        self.assertEqual(len(members), 0)
        self.assertEqual(list(members), [])

    def test_find_member_error(self):
        # .find_member() can only return zero or one memberships.  Anything
        # else is an error.
        subscribe(self._mlist, 'Anne')
        subscribe(self._mlist, 'Anne', MemberRole.owner)
        with self.assertRaises(TooManyMembersError) as cm:
            self._service.find_member('aperson@example.com')
        self.assertEqual(cm.exception.subscriber, 'aperson@example.com')
        self.assertEqual(cm.exception.list_id, None)
        self.assertEqual(cm.exception.role, None)

    def test_leave_no_such_list(self):
        # Trying to leave a nonexistent list raises an exception.
        self.assertRaises(NoSuchListError, self._service.leave,
                          'bogus.example.com', 'anne@example.com')

    def test_unsubscribe_members_no_such_list(self):
        # Raises an exception if an invalid list_id is passed
        self.assertRaises(NoSuchListError, self._service.unsubscribe_members,
                          'bogus.example.com', 'anne@example.com')

    def test_unsubscribe_members(self):
        # Check that memberships are properly unsubscribed
        # Create lists for testing.
        mlist1 = create_list('test1@example.com')
        mlist1.admin_immed_notify = False
        mlist2 = create_list('test2@example.com')
        mlist2.admin_immed_notify = False
        # Create users and addresses
        user = self._user_manager.create_user(
            'anne1@example.com', 'Anne User')
        address_1 = set_preferred(user)
        address_2 = self._user_manager.create_address(
            'anne2@example.com', 'Anne User 2')
        address_2.verified_on = now()
        address_2.user = user
        address_3 = self._user_manager.create_address(
            'anne3@example.com', 'Anne User 3')
        address_3.verified_on = now()
        address_3.user = user
        address_4 = self._user_manager.create_address(
            'addr1@example.com', 'Address 1')
        address_4.verified_on = now()
        address_5 = self._user_manager.create_address(
            'addr2@example.com', 'Address 2')
        address_5.verified_on = now()
        address_6 = self._user_manager.create_address(
            'addr3@example.com', 'Address 3')
        address_6.verified_on = now()
        user_1 = self._user_manager.create_user(
            'user1@example.com', 'User 1')
        set_preferred(user_1)
        address_8 = self._user_manager.create_address(
            'user2@example.com', 'User 2')
        address_8.verified_on = now()
        address_8.user = user_1
        # Subscribe the addresses to mailing lists
        mlist1.subscribe(user, MemberRole.member)
        mlist1.subscribe(user, MemberRole.moderator)
        mlist1.subscribe(user, MemberRole.owner)
        mlist1.subscribe(address_1, MemberRole.member)
        mlist1.subscribe(address_2, MemberRole.member)
        mlist1.subscribe(address_2, MemberRole.moderator)
        mlist1.subscribe(address_3, MemberRole.member)
        mlist1.subscribe(address_4, MemberRole.member)
        mlist1.subscribe(address_5, MemberRole.member)
        mlist1.subscribe(address_5, MemberRole.moderator)
        mlist1.subscribe(address_6, MemberRole.member)
        mlist1.subscribe(user_1, MemberRole.member)
        mlist1.subscribe(address_8, MemberRole.member)
        mlist2.subscribe(user, MemberRole.member)
        mlist2.subscribe(user, MemberRole.moderator)
        mlist2.subscribe(address_1, MemberRole.member)
        mlist2.subscribe(address_1, MemberRole.moderator)
        mlist2.subscribe(address_2, MemberRole.member)
        mlist2.subscribe(address_2, MemberRole.owner)
        mlist2.subscribe(address_4, MemberRole.member)
        mlist2.subscribe(address_5, MemberRole.member)
        mlist2.subscribe(address_6, MemberRole.member)
        mlist2.subscribe(address_6, MemberRole.moderator)
        # Unsubscribe members from mlist1
        success, fail = self._service.unsubscribe_members(mlist1.list_id,
                                                          ['anne1@example.com',
                                                           'anne2@example.com',
                                                           'addr1@example.com',
                                                           'addr2@example.com',
                                                           'user2@example.com',
                                                           'bogus@example.com',
                                                           ])
        self.assertListEqual(success, ['anne1@example.com',
                                       'anne2@example.com',
                                       'addr1@example.com',
                                       'addr2@example.com',
                                       'user2@example.com',
                                       ])
        self.assertListEqual(fail, ['bogus@example.com'])
        # Obtain rosters
        members_1 = mlist1.get_roster(MemberRole.member)
        moderators_1 = mlist1.get_roster(MemberRole.moderator)
        owners_1 = mlist1.get_roster(MemberRole.owner)
        members_2 = mlist2.get_roster(MemberRole.member)
        moderators_2 = mlist2.get_roster(MemberRole.moderator)
        owners_2 = mlist2.get_roster(MemberRole.owner)
        self.assertListEqual(
            [address.email for address in members_1.addresses],
            ['anne3@example.com',
             'addr3@example.com',
             'user1@example.com',
             ])
        self.assertListEqual(
            [address.email for address in moderators_1.addresses],
            ['anne1@example.com',
             'anne2@example.com',
             'addr2@example.com',
             ])
        self.assertListEqual(
            [address.email for address in owners_1.addresses],
            ['anne1@example.com'])
        self.assertListEqual(
            [address.email for address in members_2.addresses],
            ['anne1@example.com',
             'anne1@example.com',
             'anne2@example.com',
             'addr1@example.com',
             'addr2@example.com',
             'addr3@example.com',
             ])
        self.assertListEqual(
            [address.email for address in moderators_2.addresses],
            ['anne1@example.com',
             'anne1@example.com',
             'addr3@example.com',
             ])
        self.assertListEqual(
            [address.email for address in owners_2.addresses],
            ['anne2@example.com'])
