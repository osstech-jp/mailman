# Copyright (C) 2011-2016 by the Free Software Foundation, Inc.
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

"""Test users."""

import unittest

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.database.transaction import transaction
from mailman.interfaces.address import (
    AddressAlreadyLinkedError, AddressNotLinkedError)
from mailman.interfaces.member import MemberRole
from mailman.interfaces.user import UnverifiedAddressError
from mailman.interfaces.usermanager import IUserManager
from mailman.model.preferences import Preferences
from mailman.testing.helpers import set_preferred
from mailman.testing.layers import ConfigLayer
from mailman.utilities.datetime import now
from sqlalchemy import inspect
from zope.component import getUtility


class TestUser(unittest.TestCase):
    """Test users."""

    layer = ConfigLayer

    def setUp(self):
        self._manager = getUtility(IUserManager)
        self._mlist = create_list('test@example.com')
        self._anne = self._manager.create_user(
            'anne@example.com', 'Anne Person')
        set_preferred(self._anne)

    def test_preferred_address_memberships(self):
        self._mlist.subscribe(self._anne)
        memberships = list(self._anne.memberships.members)
        self.assertEqual(len(memberships), 1)
        self.assertEqual(memberships[0].address.email, 'anne@example.com')
        self.assertEqual(memberships[0].user, self._anne)
        addresses = list(self._anne.memberships.addresses)
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses[0].email, 'anne@example.com')

    def test_preferred_and_address_memberships(self):
        self._mlist.subscribe(self._anne)
        aperson = self._anne.register('aperson@example.com')
        self._mlist.subscribe(aperson)
        memberships = list(self._anne.memberships.members)
        self.assertEqual(len(memberships), 2)
        self.assertEqual(set(member.address.email for member in memberships),
                         set(['anne@example.com', 'aperson@example.com']))
        self.assertEqual(memberships[0].user, memberships[1].user)
        self.assertEqual(memberships[0].user, self._anne)
        emails = set(address.email
                     for address in self._anne.memberships.addresses)
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails,
                         set(['anne@example.com', 'aperson@example.com']))

    def test_uid_is_immutable(self):
        with self.assertRaises(AttributeError):
            self._anne.user_id = 'foo'

    def test_addresses_may_only_be_linked_to_one_user(self):
        user = self._manager.create_user()
        # Anne's preferred address is already linked to her.
        with self.assertRaises(AddressAlreadyLinkedError) as cm:
            user.link(self._anne.preferred_address)
        self.assertEqual(cm.exception.address, self._anne.preferred_address)

    def test_unlink_from_address_not_linked_to(self):
        # You cannot unlink an address from a user if that address is not
        # already linked to the user.
        user = self._manager.create_user()
        with self.assertRaises(AddressNotLinkedError) as cm:
            user.unlink(self._anne.preferred_address)
        self.assertEqual(cm.exception.address, self._anne.preferred_address)

    def test_unlink_address_which_is_not_linked(self):
        # You cannot unlink an address which is not linked to any user.
        address = self._manager.create_address('bart@example.com')
        user = self._manager.create_user()
        with self.assertRaises(AddressNotLinkedError) as cm:
            user.unlink(address)
        self.assertEqual(cm.exception.address, address)

    def test_set_unverified_preferred_address(self):
        # A user's preferred address cannot be set to an unverified address.
        new_preferred = self._manager.create_address(
            'anne.person@example.com')
        with self.assertRaises(UnverifiedAddressError) as cm:
            self._anne.preferred_address = new_preferred
        self.assertEqual(cm.exception.address, new_preferred)

    def test_preferences_deletion_on_user_deletion(self):
        # LP: #1418276 - deleting a user did not delete their preferences.
        with transaction():
            # This has to happen in a transaction so that both the user and
            # the preferences objects get valid ids.
            user = self._manager.create_user()
        # The user's preference is in the database.
        preferences = config.db.store.query(Preferences).filter_by(
            id=user.preferences.id)
        self.assertEqual(preferences.count(), 1)
        self._manager.delete_user(user)
        # The user's preference has been deleted.
        preferences = config.db.store.query(Preferences).filter_by(
            id=user.preferences.id)
        self.assertEqual(preferences.count(), 0)

    def test_absorb_addresses(self):
        anne_addr = self._anne.preferred_address
        with transaction():
            # This has to happen in a transaction so that both the user and
            # the preferences objects get valid ids.
            bill = self._manager.create_user(
                'bill@example.com', 'Bill Person')
            bill_addr_2 = self._manager.create_address('bill2@example.com')
            bill.link(bill_addr_2)
        self._anne.absorb(bill)
        self.assertIn(
            'bill@example.com',
            list(a.email for a in self._anne.addresses))
        self.assertIn(
            'bill2@example.com',
            list(a.email for a in self._anne.addresses))
        # The preferred address shouldn't change.
        self.assertEqual(self._anne.preferred_address, anne_addr)
        self.assertEqual(
            self._manager.get_user('bill@example.com'), self._anne)
        self.assertEqual(
            self._manager.get_user('bill2@example.com'), self._anne)
        self.assertIsNone(self._manager.get_user_by_id(bill.user_id))

    def test_absorb_memberships(self):
        mlist2 = create_list('test2@example.com')
        mlist3 = create_list('test3@example.com')
        with transaction():
            # This has to happen in a transaction so that both the user and
            # the preferences objects get valid ids.
            bill = self._manager.create_user(
                'bill@example.com', 'Bill Person')
            bill_address = list(bill.addresses)[0]
            bill_address.verified_on = now()
            bill.preferred_address = bill_address
        # Subscribe both users to self._mlist.
        self._mlist.subscribe(self._anne, MemberRole.member)
        self._mlist.subscribe(bill, MemberRole.moderator)
        # Subscribe only bill to mlist2.
        mlist2.subscribe(bill, MemberRole.owner)
        # Subscribe only bill's address to mlist3.
        mlist3.subscribe(bill.preferred_address, MemberRole.moderator)
        # Do the absorption.
        self._anne.absorb(bill)
        # Check that bill has been deleted.
        self.assertEqual(len(list(self._manager.users)), 1)
        self.assertEqual(list(self._manager.users)[0], self._anne)
        # Check that there is no leftover membership from user bill.
        self.assertEqual(len(list(self._manager.members)), 3)
        # Check that anne is subscribed to all lists.
        self.assertEqual(self._anne.memberships.member_count, 3)
        memberships = {}
        for member in self._anne.memberships.members:
            memberships[member.list_id] = member
        self.assertEqual(
            set(memberships.keys()),
            set([
                'test.example.com',
                'test2.example.com',
                'test3.example.com',
                ]))
        # The subscription to test@example.com already existed, it must not be
        # overwritten.
        self.assertEqual(
            memberships['test.example.com'].role, MemberRole.member)
        # Check that the subscription roles were imported
        self.assertEqual(
            memberships['test2.example.com'].role, MemberRole.owner)
        self.assertEqual(
            memberships['test3.example.com'].role, MemberRole.moderator)
        # The user bill was subscribed, the subscription must thus be
        # transferred to anne's primary address.
        self.assertEqual(
            memberships['test2.example.com'].address,
            self._anne.preferred_address)
        # The address was subscribed, it must not be changed
        self.assertEqual(
            memberships['test3.example.com'].address.email,
            'bill@example.com')

    def test_absorb_preferences(self):
        with transaction():
            # This has to happen in a transaction so that both the user and
            # the preferences objects get valid ids.
            bill = self._manager.create_user(
                'bill@example.com', 'Bill Person')
        bill.preferences.acknowledge_posts = True
        self.assertIsNone(self._anne.preferences.acknowledge_posts)
        self._anne.absorb(bill)
        self.assertEqual(self._anne.preferences.acknowledge_posts, True)
        # Check that Bill's preferences were deleted (requires a DB flush).
        config.db.store.flush()
        self.assertTrue(inspect(bill.preferences).deleted)

    def test_absorb_properties(self):
        props = {
            'password': 'dummy',
            'is_server_owner': True
        }
        with transaction():
            # This has to happen in a transaction so that both the user and
            # the preferences objects get valid ids.
            bill = self._manager.create_user(
                'bill@example.com', 'Bill Person')
        for prop, value in props.items():
            setattr(bill, prop, value)
        self._anne.absorb(bill)
        for prop, value in props.items():
            self.assertEqual(getattr(self._anne, prop), value)
        # This was not empty so it must not be overwritten
        self.assertEqual(self._anne.display_name, 'Anne Person')

    def test_absorb_delete_user(self):
        # Make sure the user was deleted
        with transaction():
            # This has to happen in a transaction so that both the user and
            # the preferences objects get valid ids.
            bill = self._manager.create_user(
                'bill@example.com', 'Bill Person')
        bill_user_id = bill.user_id
        self._anne.absorb(bill)
        self.assertIsNone(self._manager.get_user_by_id(bill_user_id))

    def test_absorb_self(self):
        # Absorbing oneself should be a no-op (it must not delete the user)
        self._mlist.subscribe(self._anne)
        self._anne.absorb(self._anne)
        new_anne = self._manager.get_user_by_id(self._anne.user_id)
        self.assertIsNotNone(new_anne)
        self.assertEqual(
            [a.email for a in new_anne.addresses], ['anne@example.com'])
        self.assertEqual(new_anne.memberships.member_count, 1)
