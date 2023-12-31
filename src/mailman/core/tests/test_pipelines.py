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

"""Test the core modification pipelines."""

import unittest

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.core.pipelines import process
from mailman.handlers.to_outgoing import ToOutgoing
from mailman.interfaces.handler import IHandler
from mailman.interfaces.member import MemberRole
from mailman.interfaces.pipeline import (
    DiscardMessage,
    IPipeline,
    RejectMessage,
)
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import (
    digest_mbox,
    get_queue_messages,
    LogFileMark,
    specialized_message_from_string as mfs,
)
from mailman.testing.layers import ConfigLayer
from operator import delitem
from zope.component import getUtility
from zope.interface import implementer


@implementer(IHandler)
class DiscardingHandler:
    name = 'discarding'

    def process(self, mlist, msg, msgdata):
        raise DiscardMessage('by test handler')


@implementer(IHandler)
class RejectHandler:
    name = 'rejecting'

    def __init__(self, message):
        self.message = message

    def process(self, mlist, msg, msgdata):
        raise RejectMessage(self.message)


@implementer(IPipeline)
class DiscardingPipeline:
    name = 'test-discarding'
    description = 'Discarding test pipeline'

    def __iter__(self):
        yield DiscardingHandler()
        yield ToOutgoing()


@implementer(IPipeline)
class RejectingPipeline:
    name = 'test-rejecting'
    description = 'Rejectinging test pipeline'

    def __init__(self):
        self.message = 'by test handler'

    def __iter__(self):
        yield RejectHandler(self.message)
        yield ToOutgoing()


class TestPostingPipeline(unittest.TestCase):
    """Test various aspects of the built-in postings pipeline."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        config.pipelines['test-discarding'] = DiscardingPipeline()
        self.addCleanup(delitem, config.pipelines, 'test-discarding')
        config.pipelines['test-rejecting'] = RejectingPipeline()
        self.addCleanup(delitem, config.pipelines, 'test-rejecting')
        self._msg = mfs("""\
From: Anne Person <anne@example.org>
To: test@example.com
Subject: a test
Message-ID: <ant>

testing
""")

    def test_rfc2369_headers(self):
        # Ensure that RFC 2369 List-* headers are added.
        msgdata = {}
        process(self._mlist, self._msg, msgdata,
                pipeline_name='default-posting-pipeline')
        self.assertEqual(self._msg['list-id'], '<test.example.com>')
        self.assertEqual(self._msg['list-post'], '<mailto:test@example.com>')

    def test_rfc2369_headers_virgin(self):
        # Internally crafted messages should get reduced List-* headers.
        msgdata = {'reduced_list_headers': True}
        process(self._mlist, self._msg, msgdata,
                pipeline_name='virgin')
        self.assertEqual(self._msg['list-id'], '<test.example.com>')
        self.assertIsNone(self._msg['list-post'])

    def test_discarding_pipeline(self):
        # If a handler in the pipeline raises DiscardMessage, the message will
        # be thrown away, but with a log message.
        mark = LogFileMark('mailman.vette')
        process(self._mlist, self._msg, {}, 'test-discarding')
        line = mark.readline()[:-1]
        self.assertTrue(line.endswith(
            '<ant> discarded by "test-discarding" pipeline handler '
            '"discarding": by test handler'))
        # There should be no outgoing message.
        get_queue_messages('out', expected_count=0)

    def test_rejecting_pipeline(self):
        # If a handler in the pipeline raises RejectMessage, the post will
        # be bounced with a log message.
        mark = LogFileMark('mailman.vette')
        process(self._mlist, self._msg, {}, 'test-rejecting')
        line = mark.readline()[:-1]
        self.assertEqual(
            line[-80:],
            '<ant> rejected by "test-rejecting" pipeline handler '
            '"rejecting": by test handler',
            line)
        # In the rejection case, the original message will also be in the
        # virgin queue.
        items = get_queue_messages('virgin', expected_count=1)
        self.assertEqual(
            str(items[0].msg.get_payload(1).get_payload(0)['subject']),
            'a test')
        # The first payload contains the rejection reason.
        payload = items[0].msg.get_payload(0).get_payload()
        self.assertEqual(payload, 'by test handler')
        # There should be no outgoing message.
        get_queue_messages('out', expected_count=0)

    def test_rejecting_pipeline_without_message(self):
        # Similar to above, but without a rejection message.
        pipeline = config.pipelines['test-rejecting']
        message = pipeline.message
        self.addCleanup(setattr, pipeline, 'message', message)
        pipeline.message = None
        mark = LogFileMark('mailman.vette')
        process(self._mlist, self._msg, {}, 'test-rejecting')
        line = mark.readline()[:-1]
        self.assertEqual(
            line[-91:],
            '<ant> rejected by "test-rejecting" pipeline handler '
            '"rejecting": [No details are available]',
            line)
        # In the rejection case, the original message will also be in the
        # virgin queue.
        items = get_queue_messages('virgin', expected_count=1)
        self.assertEqual(
            str(items[0].msg.get_payload(1).get_payload(0)['subject']),
            'a test')
        # The first payload contains the rejection reason.
        payload = items[0].msg.get_payload(0).get_payload()
        self.assertEqual(payload, '[No details are available]')
        # There should be no outgoing message.
        get_queue_messages('out', expected_count=0)

    def test_decorate_bulk(self):
        # Ensure that bulk postings get decorated with the footer.
        # Decorate is no longer in the pipeline.  This is now tested in
        # mailman/mta/tests/test_delivery.py.
        pass

    def test_nodecorate_verp(self):
        # Ensure that verp postings don't get decorated twice.
        # This test was always wrong as verp decoration wasn't done in
        # the pipeline.
        pass

    def test_only_decorate_output(self):
        # Ensure that decoration is not done on the archive, digest, or
        # usenet copy of the message.
        # This test is moot now that decorate isn't in the posting pipeline
        # but let it remain.
        self.assertTrue(self._mlist.digests_enabled)
        # Set up NNTP.
        self._mlist.gateway_to_news = True
        self._mlist.linked_newsgroup = 'testing'
        # Process the email.
        process(self._mlist, self._msg, {},
                pipeline_name='default-posting-pipeline')
        for queue in ('archive', 'nntp'):
            items = get_queue_messages(queue, expected_count=1)
            payload = items[0].msg.get_payload()
            self.assertNotIn('Test mailing list', payload)
        self.assertEqual(len(digest_mbox(self._mlist)), 1)
        payload = digest_mbox(self._mlist)[0].get_payload()
        self.assertNotIn('Test mailing list', payload)


class TestOwnerPipeline(unittest.TestCase):
    """Test various aspects of the built-in owner pipeline."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        user_manager = getUtility(IUserManager)
        anne = user_manager.create_address('anne@example.com')
        bart = user_manager.create_address('bart@example.com')
        self._mlist.subscribe(anne, MemberRole.owner)
        self._mlist.subscribe(bart, MemberRole.moderator)
        self._msg = mfs("""\
From: Anne Person <anne@example.org>
To: test-owner@example.com

""")

    def test_calculate_recipients(self):
        # Recipients are the administrators of the mailing list.
        msgdata = dict(listname='test@example.com',
                       to_owner=True)
        process(self._mlist, self._msg, msgdata,
                pipeline_name='default-owner-pipeline')
        self.assertEqual(msgdata['recipients'], set(('anne@example.com',
                                                     'bart@example.com')))

    def test_to_outgoing(self):
        # The message, with the calculated recipients, gets put in the
        # outgoing queue.
        process(self._mlist, self._msg, {},
                pipeline_name='default-owner-pipeline')
        items = get_queue_messages('out', sort_on='to', expected_count=1)
        self.assertEqual(items[0].msgdata['recipients'],
                         set(('anne@example.com', 'bart@example.com')))
