# Copyright (C) 2013-2016 by the Free Software Foundation, Inc.
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

"""Test MailingLists and related model objects.."""

__all__ = [
    'TestAcceptableAliases',
    'TestDisabledListArchiver',
    'TestListArchiver',
    'TestMailingList',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.database.transaction import transaction
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.mailinglist import (
    IAcceptableAliasSet, IHeaderMatchSet, IListArchiverSet)
from mailman.interfaces.member import (
    AlreadySubscribedError, MemberRole, MissingPreferredAddressError)
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import configuration, get_queue_messages
from mailman.testing.layers import ConfigLayer
from mailman.utilities.datetime import now
from zope.component import getUtility



class TestMailingList(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('ant@example.com')

    def test_no_duplicate_subscriptions(self):
        # A user is not allowed to subscribe more than once to the mailing
        # list with the same role.
        anne = getUtility(IUserManager).create_user('anne@example.com')
        # Give the user a preferred address.
        preferred = list(anne.addresses)[0]
        preferred.verified_on = now()
        anne.preferred_address = preferred
        # Subscribe Anne to the mailing list as a regular member.
        member = self._mlist.subscribe(anne)
        self.assertEqual(member.address, preferred)
        self.assertEqual(member.role, MemberRole.member)
        # A second subscription with the same role will fail.
        with self.assertRaises(AlreadySubscribedError) as cm:
            self._mlist.subscribe(anne)
        self.assertEqual(cm.exception.fqdn_listname, 'ant@example.com')
        self.assertEqual(cm.exception.email, 'anne@example.com')
        self.assertEqual(cm.exception.role, MemberRole.member)

    def test_subscribing_user_must_have_preferred_address(self):
        # A user object cannot be subscribed to a mailing list without a
        # preferred address.
        anne = getUtility(IUserManager).create_user('anne@example.com')
        self.assertRaises(MissingPreferredAddressError,
                          self._mlist.subscribe, anne)

    def test_pass_extensions(self):
        self._mlist.pass_extensions = ('foo', 'bar', 'baz')
        self.assertEqual(list(self._mlist.pass_extensions),
                         ['foo', 'bar', 'baz'])

    def test_get_roster_argument(self):
        self.assertRaises(ValueError, self._mlist.get_roster, 'members')

    def test_subscribe_argument(self):
        self.assertRaises(ValueError, self._mlist.subscribe, 'anne')

    def test_subscribe_by_user_admin_notification(self):
        # A notification is sent to the administrator with the user's email
        # address when a user is subscribed instead of an explicit address.
        self._mlist.send_welcome_message = False
        self._mlist.admin_notify_mchanges = True
        manager = getUtility(IUserManager)
        user = manager.make_user('anne@example.com', 'Anne Person')
        address = manager.create_address('aperson@example.com', 'A. Person')
        address.verified_on = now()
        user.preferred_address = address
        self._mlist.subscribe(user)
        # The welcome message was sent to the preferred address.
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 1)
        self.assertIn('Anne Person <aperson@example.com>',
                      items[0].msg.get_payload())



class TestListArchiver(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('ant@example.com')
        self._set = IListArchiverSet(self._mlist)

    def test_list_archivers(self):
        # Find the set of archivers registered for this mailing list.
        self.assertEqual(
            ['mail-archive', 'mhonarc', 'prototype'],
            sorted(archiver.name for archiver in self._set.archivers))

    def test_get_archiver(self):
        # Use .get() to see if a mailing list has an archiver.
        archiver = self._set.get('prototype')
        self.assertEqual(archiver.name, 'prototype')
        self.assertTrue(archiver.is_enabled)
        self.assertEqual(archiver.mailing_list, self._mlist)
        self.assertEqual(archiver.system_archiver.name, 'prototype')

    def test_get_archiver_no_such(self):
        # Using .get() on a non-existing name returns None.
        self.assertIsNone(self._set.get('no-such-archiver'))

    def test_site_disabled(self):
        # Here the system configuration enables all the archivers in time for
        # the archive set to be created with all list archivers enabled.  But
        # then the site-wide archiver gets disabled, so the list specific
        # archiver will also be disabled.
        archiver_set = IListArchiverSet(self._mlist)
        archiver = archiver_set.get('prototype')
        self.assertTrue(archiver.is_enabled)
        # Disable the site-wide archiver.
        config.push('enable prototype', """\
        [archiver.prototype]
        enable: no
        """)
        self.assertFalse(archiver.is_enabled)
        config.pop('enable prototype')



class TestDisabledListArchiver(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('ant@example.com')

    @configuration('archiver.prototype', enable='no')
    def test_enable_list_archiver(self):
        # When the system configuration file disables an archiver site-wide,
        # the list-specific mailing list will get initialized as not enabled.
        # Create the archiver set on the fly so that it doesn't get
        # initialized with a configuration that enables the prototype archiver.
        archiver_set = IListArchiverSet(self._mlist)
        archiver = archiver_set.get('prototype')
        self.assertFalse(archiver.is_enabled)
        # Enable both the list archiver and the system archiver.
        archiver.is_enabled = True
        config.push('enable prototype', """\
        [archiver.prototype]
        enable: yes
        """)
        # Get the IListArchiver again.
        archiver = archiver_set.get('prototype')
        self.assertTrue(archiver.is_enabled)
        config.pop('enable prototype')



class TestAcceptableAliases(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('ant@example.com')

    def test_delete_list_with_acceptable_aliases(self):
        # LP: #1432239 - deleting a mailing list with acceptable aliases
        # causes a SQLAlchemy error.  The aliases must be deleted first.
        with transaction():
            alias_set = IAcceptableAliasSet(self._mlist)
            alias_set.add('bee@example.com')
        self.assertEqual(['bee@example.com'], list(alias_set.aliases))
        getUtility(IListManager).delete(self._mlist)
        self.assertEqual(len(list(alias_set.aliases)), 0)



class TestHeaderMatch(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('ant@example.com')

    def test_lowercase_header(self):
        header_matches = IHeaderMatchSet(self._mlist)
        header_matches.add('Header', 'pattern')
        self.assertEqual(len(self._mlist.header_matches), 1)
        self.assertEqual(self._mlist.header_matches[0].header, 'header')

    def test_chain_defaults_to_none(self):
        header_matches = IHeaderMatchSet(self._mlist)
        header_matches.add('header', 'pattern')
        self.assertEqual(len(self._mlist.header_matches), 1)
        self.assertEqual(self._mlist.header_matches[0].chain, None)

    def test_duplicate(self):
        header_matches = IHeaderMatchSet(self._mlist)
        header_matches.add('Header', 'pattern')
        self.assertRaises(
            ValueError, header_matches.add, 'Header', 'pattern')
        self.assertEqual(len(self._mlist.header_matches), 1)

    def test_remove_non_existent(self):
        header_matches = IHeaderMatchSet(self._mlist)
        self.assertRaises(
            ValueError, header_matches.remove, 'header', 'pattern')

    def test_add_remove(self):
        header_matches = IHeaderMatchSet(self._mlist)
        header_matches.add('header', 'pattern')
        self.assertEqual(len(self._mlist.header_matches), 1)
        header_matches.remove('header', 'pattern')
        self.assertEqual(len(self._mlist.header_matches), 0)

    def test_iterator(self):
        header_matches = IHeaderMatchSet(self._mlist)
        header_matches.add('Header', 'pattern')
        header_matches.add('Subject', 'patt.*')
        header_matches.add('From', '.*@example.com', 'discard')
        header_matches.add('From', '.*@example.org', 'accept')
        matches = sorted((match.header, match.pattern, match.chain)
                         for match in IHeaderMatchSet(self._mlist))
        self.assertEqual(
            matches,
            [('from', '.*@example.com', 'discard'),
             ('from', '.*@example.org', 'accept'),
             ('header', 'pattern', None),
             ('subject', 'patt.*', None),
             ])

    def test_clear(self):
        header_matches = IHeaderMatchSet(self._mlist)
        header_matches.add('Header', 'pattern')
        self.assertEqual(len(self._mlist.header_matches), 1)
        with transaction():
            header_matches.clear()
        self.assertEqual(len(self._mlist.header_matches), 0)
