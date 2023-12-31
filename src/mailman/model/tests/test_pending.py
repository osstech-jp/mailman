# Copyright (C) 2015-2023 by the Free Software Foundation, Inc.
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

"""Test pendings."""

import unittest

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.pending import IPendable, IPendings
from mailman.interfaces.subscriptions import TokenOwner
from mailman.interfaces.workflow import IWorkflowStateManager
from mailman.model.pending import PendedKeyValue
from mailman.testing.layers import ConfigLayer
from zope.component import getUtility
from zope.interface import implementer


@implementer(IPendable)
class SimplePendable(dict):
    PEND_TYPE = 'simple'


class TestPendings(unittest.TestCase):
    """Test pendings."""

    layer = ConfigLayer

    def test_delete_key_values(self):
        # Deleting a pending should delete its key-values.
        pendingdb = getUtility(IPendings)
        subscription = SimplePendable(
            type='subscription',
            address='aperson@example.com',
            display_name='Anne Person',
            language='en',
            password='xyz')
        token = pendingdb.add(subscription)
        self.assertEqual(pendingdb.count(), 1)
        pendingdb.confirm(token)
        self.assertEqual(pendingdb.count(), 0)
        self.assertEqual(config.db.store.query(PendedKeyValue).count(), 0)

    def test_delete_workflow(self):
        # Deleting a pending should delete any associated workflow state.
        pendingdb = getUtility(IPendings)
        wsmanager = getUtility(IWorkflowStateManager)
        subscription = SimplePendable(
            type='subscription',
            address='aperson@example.com',
            display_name='Anne Person',
            language='en',
            password='xyz')
        token = pendingdb.add(subscription)
        wsmanager.save(token, step='step1', data='data')
        self.assertEqual(wsmanager.count, 1)
        pendingdb.confirm(token)
        self.assertEqual(wsmanager.count, 0)

    def test_find(self):
        # Test getting pendables for a mailing-list.
        mlist = create_list('list1@example.com')
        pendingdb = getUtility(IPendings)
        subscription_1 = SimplePendable(
            type='subscription',
            list_id='list1.example.com',
            token_owner='subscriber')
        subscription_2 = SimplePendable(
            type='subscription',
            list_id='list2.example.com')
        subscription_3 = SimplePendable(
            type='hold request',
            list_id='list1.example.com')
        subscription_4 = SimplePendable(
            type='hold request',
            list_id='list2.example.com')
        subscription_5 = SimplePendable(
            type='subscription',
            list_id='list2.example.com',
            token_owner='moderator')
        token_1 = pendingdb.add(subscription_1)
        pendingdb.add(subscription_2)
        token_3 = pendingdb.add(subscription_3)
        token_4 = pendingdb.add(subscription_4)
        token_5 = pendingdb.add(subscription_5)
        self.assertEqual(pendingdb.count(), 5)
        # Find the pending subscription in list1.
        pendings = list(pendingdb.find(mlist=mlist, pend_type='subscription'))
        self.assertEqual(len(pendings), 1, pendings)
        self.assertEqual(pendings[0][0], token_1)
        self.assertEqual(pendings[0][1]['list_id'], 'list1.example.com')
        self.assertEqual(pendings[0][1]['token_owner'], 'subscriber')
        # Find the pending subscription using the token_owner.
        pendings = list(pendingdb.find(token_owner=TokenOwner.moderator))
        self.assertEqual(len(pendings), 1)
        self.assertEqual(pendings[0][0], token_5)
        self.assertEqual(pendings[0][1]['list_id'], 'list2.example.com')
        self.assertEqual(pendings[0][1]['token_owner'], 'moderator')
        # Find all pending hold requests.
        pendings = list(pendingdb.find(pend_type='hold request'))
        self.assertEqual(len(pendings), 2)
        self.assertSetEqual(
            set((p[0], p[1]['list_id']) for p in pendings),
            {(token_3, 'list1.example.com'), (token_4, 'list2.example.com')}
            )
        # Find all pendings for list1.
        pendings = list(pendingdb.find(mlist=mlist))
        self.assertEqual(len(pendings), 2)
        self.assertSetEqual(
            set((p[0], p[1]['list_id'], p[1]['type']) for p in pendings),
            {(token_1, 'list1.example.com', 'subscription'),
             (token_3, 'list1.example.com', 'hold request')}
            )

        # Run count queries.
        self.assertEqual(
            pendingdb.count(mlist=mlist, pend_type='subscription'), 1)
        self.assertEqual(
            pendingdb.count(token_owner=TokenOwner.moderator), 1)
        self.assertEqual(
            pendingdb.count(token_owner=TokenOwner.subscriber), 1)
        self.assertEqual(
            pendingdb.count(mlist=mlist, token_owner=TokenOwner.subscriber), 1)
