# Copyright (C) 2015 by the Free Software Foundation, Inc.
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

"""Test preferences."""

__all__ = [
    'TestPreferences',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.database.transaction import transaction
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.member import DeliveryMode, DeliveryStatus
from mailman.interfaces.usermanager import IUserManager
from mailman.model.preferences import Preferences
from mailman.testing.layers import ConfigLayer
from zope.component import getUtility



class TestPreferences(unittest.TestCase):
    """Test preferences."""

    layer = ConfigLayer

    def setUp(self):
        self._manager = getUtility(IUserManager)
        with transaction():
            # This has to happen in a transaction so that both the user and
            # the preferences objects get valid ids.
            self._mlist = create_list('test@example.com')
            self._anne = self._manager.create_user(
                'anne@example.com', 'Anne Person')
            self._bill = self._manager.create_user(
                'bill@example.com', 'Bill Person')

    def test_absorb_all_attributes(self):
        attributes = {
            'acknowledge_posts': True,
            'hide_address': True,
            'preferred_language':
                getUtility(ILanguageManager)['fr'],
            'receive_list_copy': True,
            'receive_own_postings': True,
            'delivery_mode': DeliveryMode.mime_digests,
            'delivery_status': DeliveryStatus.by_user,
            }
        bill_prefs = self._bill.preferences
        for name, value in attributes.items():
            setattr(bill_prefs, name, value)
        self._anne.preferences.absorb(self._bill.preferences)
        for name, value in attributes.items():
            self.assertEqual(getattr(self._anne.preferences, name), value)

    def test_absorb_overwrite(self):
        # Only overwrite the pref if it is unset in the absorber
        anne_prefs = self._anne.preferences
        bill_prefs = self._bill.preferences
        self.assertIsNone(self._anne.preferences.acknowledge_posts)
        self.assertIsNone(self._anne.preferences.hide_address)
        self.assertIsNone(self._anne.preferences.receive_list_copy)
        anne_prefs.acknowledge_posts = False
        bill_prefs.acknowledge_posts = True
        anne_prefs.hide_address = True
        bill_prefs.receive_list_copy = True
        self._anne.preferences.absorb(self._bill.preferences)
        # set for both anne and bill, don't overwrite
        self.assertFalse(self._anne.preferences.acknowledge_posts)
        # set only for anne
        self.assertTrue(self._anne.preferences.hide_address)
        # set only for bill, overwrite anne's default value
        self.assertTrue(self._anne.preferences.receive_list_copy)
