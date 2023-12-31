# Copyright (C) 2012-2023 by the Free Software Foundation, Inc.
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

"""Test the incoming queue runner."""

import unittest

from mailman.app.lifecycle import create_list
from mailman.chains.base import TerminalChainBase
from mailman.config import config
from mailman.interfaces.autorespond import ResponseAction
from mailman.runners.incoming import IncomingRunner
from mailman.testing.helpers import (
    get_queue_messages,
    make_testable_runner,
    specialized_message_from_string as mfs,
)
from mailman.testing.layers import ConfigLayer


class Chain(TerminalChainBase):
    name = 'test'
    description = 'a test chain'

    def __init__(self, marker):
        self._marker = marker

    def _process(self, mlist, msg, msgdata):
        msgdata['marker'] = self._marker
        config.switchboards['out'].enqueue(msg, msgdata)


class TestIncoming(unittest.TestCase):
    """Test the incoming queue runner."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.posting_chain = 'test posting'
        self._mlist.owner_chain = 'test owner'
        config.chains['test posting'] = Chain('posting')
        self.addCleanup(config.chains.pop, 'test posting')
        config.chains['test owner'] = Chain('owner')
        self.addCleanup(config.chains.pop, 'test owner')
        self._in = make_testable_runner(IncomingRunner, 'in')
        self._msg = mfs("""\
From: anne@example.com
To: test@example.com

""")

    def test_posting(self):
        # A message posted to the list goes through the posting chain.
        msgdata = dict(listid='test.example.com')
        config.switchboards['in'].enqueue(self._msg, msgdata)
        self._in.run()
        items = get_queue_messages('out', expected_count=1)
        self.assertEqual(items[0].msgdata.get('marker'), 'posting')

    def test_posting_from_invalid(self):
        # A message posted to the list goes through the posting chain even if
        # From: is invalid.
        del self._msg['from']
        self._msg['From'] = 'anne@example.com.'
        msgdata = dict(listid='test.example.com')
        config.switchboards['in'].enqueue(self._msg, msgdata)
        self._in.run()
        items = get_queue_messages('out', expected_count=1)
        self.assertEqual(items[0].msgdata.get('marker'), 'posting')

    def test_respond_and_continue_post(self):
        # A post gets an autoresponse and continues processing.
        msgdata = dict(listid='test.example.com', to_list=True)
        self._mlist.autorespond_postings = ResponseAction.respond_and_continue
        self._mlist.autoresponse_postings_text = 'Autoresponse'
        config.switchboards['in'].enqueue(self._msg, msgdata)
        self._in.run()
        items = get_queue_messages('out', expected_count=1)
        self.assertEqual(items[0].msgdata.get('marker'), 'posting')
        items = get_queue_messages('virgin', expected_count=1)
        self.assertEqual(items[0].msg.get_payload(), 'Autoresponse')

    def test_respond_and_discard_post(self):
        # A post gets an autoresponse and is discarded.
        msgdata = dict(listid='test.example.com', to_list=True)
        self._mlist.autorespond_postings = ResponseAction.respond_and_discard
        self._mlist.autoresponse_postings_text = 'Autoresponse'
        config.switchboards['in'].enqueue(self._msg, msgdata)
        self._in.run()
        items = get_queue_messages('out', expected_count=0)
        items = get_queue_messages('virgin', expected_count=1)
        self.assertEqual(items[0].msg.get_payload(), 'Autoresponse')

    def test_owner(self):
        # A message posted to the list goes through the posting chain.
        msgdata = dict(listid='test.example.com',
                       to_owner=True)
        config.switchboards['in'].enqueue(self._msg, msgdata)
        self._in.run()
        items = get_queue_messages('out', expected_count=1)
        self.assertEqual(items[0].msgdata.get('marker'), 'owner')

    def test_respond_and_continue_owner(self):
        # A -owner message gets an autoresponse and continues processing.
        msgdata = dict(listid='test.example.com', to_owner=True)
        self._mlist.autorespond_owner = ResponseAction.respond_and_continue
        self._mlist.autoresponse_owner_text = 'Autoresponse'
        config.switchboards['in'].enqueue(self._msg, msgdata)
        self._in.run()
        items = get_queue_messages('out', expected_count=1)
        self.assertEqual(items[0].msgdata.get('marker'), 'owner')
        items = get_queue_messages('virgin', expected_count=1)
        self.assertEqual(items[0].msg.get_payload(), 'Autoresponse')

    def test_respond_and_discard_owner(self):
        # A -owner message gets an autoresponse and is discarded.
        msgdata = dict(listid='test.example.com', to_owner=True)
        self._mlist.autorespond_owner = ResponseAction.respond_and_discard
        self._mlist.autoresponse_owner_text = 'Autoresponse'
        config.switchboards['in'].enqueue(self._msg, msgdata)
        self._in.run()
        items = get_queue_messages('out', expected_count=0)
        items = get_queue_messages('virgin', expected_count=1)
        self.assertEqual(items[0].msg.get_payload(), 'Autoresponse')
