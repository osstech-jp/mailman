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

"""Test the send-digests subcommand."""

__all__ = [
    'TestSendDigests',
    ]


import os
import unittest

from io import StringIO
from mailman.app.lifecycle import create_list
from mailman.commands.cli_send_digests import Send
from mailman.config import config
from mailman.interfaces.member import DeliveryMode
from mailman.runners.digest import DigestRunner
from mailman.testing.helpers import (
    get_queue_messages, make_testable_runner,
    specialized_message_from_string as mfs, subscribe)
from mailman.testing.layers import ConfigLayer
from unittest.mock import patch



class FakeArgs:
    def __init__(self):
        self.lists = []



class TestSendDigests(unittest.TestCase):
    """Test the send-digests subcommand."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('ant@example.com')
        self._mlist.digests_enabled = True
        self._mlist.digest_size_threshold = 100000
        self._mlist.send_welcome_message = False
        self._command = Send()
        self._handler = config.handlers['to-digest']
        self._runner = make_testable_runner(DigestRunner, 'digest')
        # The mailing list needs at least one digest recipient.
        member = subscribe(self._mlist, 'Anne')
        member.preferences.delivery_mode = DeliveryMode.plaintext_digests

    def test_send_one_digest_by_list_id(self):
        msg = mfs("""\
To: ant@example.com
From: anne@example.com
Subject: message 1

""")
        self._handler.process(self._mlist, msg, {})
        del msg['subject']
        msg['subject'] = 'message 2'
        self._handler.process(self._mlist, msg, {})
        # There are no digests already being sent, but the ant mailing list
        # does have a digest mbox collecting messages.
        items = get_queue_messages('digest')
        self.assertEqual(len(items), 0)
        mailbox_path = os.path.join(self._mlist.data_path, 'digest.mmdf')
        self.assertGreater(os.path.getsize(mailbox_path), 0)
        args = FakeArgs()
        args.lists.append('ant.example.com')
        self._command.process(args)
        self._runner.run()
        # Now, there's no digest mbox and there's a plaintext digest in the
        # outgoing queue.
        self.assertFalse(os.path.exists(mailbox_path))
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 1)
        digest_contents = str(items[0].msg)
        self.assertIn('Subject: message 1', digest_contents)
        self.assertIn('Subject: message 2', digest_contents)

    def test_send_one_digest_by_fqdn_listname(self):
        msg = mfs("""\
To: ant@example.com
From: anne@example.com
Subject: message 1

""")
        self._handler.process(self._mlist, msg, {})
        del msg['subject']
        msg['subject'] = 'message 2'
        self._handler.process(self._mlist, msg, {})
        # There are no digests already being sent, but the ant mailing list
        # does have a digest mbox collecting messages.
        items = get_queue_messages('digest')
        self.assertEqual(len(items), 0)
        mailbox_path = os.path.join(self._mlist.data_path, 'digest.mmdf')
        self.assertGreater(os.path.getsize(mailbox_path), 0)
        args = FakeArgs()
        args.lists.append('ant@example.com')
        self._command.process(args)
        self._runner.run()
        # Now, there's no digest mbox and there's a plaintext digest in the
        # outgoing queue.
        self.assertFalse(os.path.exists(mailbox_path))
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 1)
        digest_contents = str(items[0].msg)
        self.assertIn('Subject: message 1', digest_contents)
        self.assertIn('Subject: message 2', digest_contents)

    def test_send_one_digest_to_missing_list_id(self):
        msg = mfs("""\
To: ant@example.com
From: anne@example.com
Subject: message 1

""")
        self._handler.process(self._mlist, msg, {})
        del msg['subject']
        msg['subject'] = 'message 2'
        self._handler.process(self._mlist, msg, {})
        # There are no digests already being sent, but the ant mailing list
        # does have a digest mbox collecting messages.
        items = get_queue_messages('digest')
        self.assertEqual(len(items), 0)
        mailbox_path = os.path.join(self._mlist.data_path, 'digest.mmdf')
        self.assertGreater(os.path.getsize(mailbox_path), 0)
        args = FakeArgs()
        args.lists.append('bee.example.com')
        stderr = StringIO()
        with patch('mailman.commands.cli_send_digests.sys.stderr', stderr):
            self._command.process(args)
        self._runner.run()
        # The warning was printed to stderr.
        self.assertEqual(stderr.getvalue(),
                         'No such list found: bee.example.com\n')
        # And no digest was prepared.
        self.assertGreater(os.path.getsize(mailbox_path), 0)
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 0)

    def test_send_one_digest_to_missing_fqdn_listname(self):
        msg = mfs("""\
To: ant@example.com
From: anne@example.com
Subject: message 1

""")
        self._handler.process(self._mlist, msg, {})
        del msg['subject']
        msg['subject'] = 'message 2'
        self._handler.process(self._mlist, msg, {})
        # There are no digests already being sent, but the ant mailing list
        # does have a digest mbox collecting messages.
        items = get_queue_messages('digest')
        self.assertEqual(len(items), 0)
        mailbox_path = os.path.join(self._mlist.data_path, 'digest.mmdf')
        self.assertGreater(os.path.getsize(mailbox_path), 0)
        args = FakeArgs()
        args.lists.append('bee@example.com')
        stderr = StringIO()
        with patch('mailman.commands.cli_send_digests.sys.stderr', stderr):
            self._command.process(args)
        self._runner.run()
        # The warning was printed to stderr.
        self.assertEqual(stderr.getvalue(),
                         'No such list found: bee@example.com\n')
        # And no digest was prepared.
        self.assertGreater(os.path.getsize(mailbox_path), 0)
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 0)

    def test_send_digest_to_one_missing_and_one_existing_list(self):
        msg = mfs("""\
To: ant@example.com
From: anne@example.com
Subject: message 1

""")
        self._handler.process(self._mlist, msg, {})
        del msg['subject']
        msg['subject'] = 'message 2'
        self._handler.process(self._mlist, msg, {})
        # There are no digests already being sent, but the ant mailing list
        # does have a digest mbox collecting messages.
        items = get_queue_messages('digest')
        self.assertEqual(len(items), 0)
        mailbox_path = os.path.join(self._mlist.data_path, 'digest.mmdf')
        self.assertGreater(os.path.getsize(mailbox_path), 0)
        args = FakeArgs()
        args.lists.extend(('ant.example.com', 'bee.example.com'))
        stderr = StringIO()
        with patch('mailman.commands.cli_send_digests.sys.stderr', stderr):
            self._command.process(args)
        self._runner.run()
        # The warning was printed to stderr.
        self.assertEqual(stderr.getvalue(),
                         'No such list found: bee.example.com\n')
        # But ant's digest was still prepared.
        self.assertFalse(os.path.exists(mailbox_path))
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 1)
        digest_contents = str(items[0].msg)
        self.assertIn('Subject: message 1', digest_contents)
        self.assertIn('Subject: message 2', digest_contents)

    def test_send_digests_for_two_lists(self):
        # Populate ant's digest.
        msg = mfs("""\
To: ant@example.com
From: anne@example.com
Subject: message 1

""")
        self._handler.process(self._mlist, msg, {})
        del msg['subject']
        msg['subject'] = 'message 2'
        self._handler.process(self._mlist, msg, {})
        # Create the second list.
        bee = create_list('bee@example.com')
        bee.digests_enabled = True
        bee.digest_size_threshold = 100000
        bee.send_welcome_message = False
        member = subscribe(bee, 'Bart')
        member.preferences.delivery_mode = DeliveryMode.plaintext_digests
        # Populate bee's digest.
        msg = mfs("""\
To: bee@example.com
From: bart@example.com
Subject: message 3

""")
        self._handler.process(bee, msg, {})
        del msg['subject']
        msg['subject'] = 'message 4'
        self._handler.process(bee, msg, {})
        # There are no digests for either list already being sent, but the
        # mailing lists do have a digest mbox collecting messages.
        ant_mailbox_path = os.path.join(self._mlist.data_path, 'digest.mmdf')
        self.assertGreater(os.path.getsize(ant_mailbox_path), 0)
        # Check bee's digest.
        bee_mailbox_path = os.path.join(bee.data_path, 'digest.mmdf')
        self.assertGreater(os.path.getsize(bee_mailbox_path), 0)
        # Both.
        items = get_queue_messages('digest')
        self.assertEqual(len(items), 0)
        # Process both list's digests.
        args = FakeArgs()
        args.lists.extend(('ant.example.com', 'bee@example.com'))
        self._command.process(args)
        self._runner.run()
        # Now, neither list has a digest mbox and but there are plaintext
        # digest in the outgoing queue for both.
        self.assertFalse(os.path.exists(ant_mailbox_path))
        self.assertFalse(os.path.exists(bee_mailbox_path))
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 2)
        # Figure out which digest is going to ant and which to bee.
        if items[0].msg['to'] == 'ant@example.com':
            ant = items[0].msg
            bee = items[1].msg
        else:
            assert items[0].msg['to'] == 'bee@example.com'
            ant = items[1].msg
            bee = items[0].msg
        # Check ant's digest.
        digest_contents = str(ant)
        self.assertIn('Subject: message 1', digest_contents)
        self.assertIn('Subject: message 2', digest_contents)
        # Check bee's digest.
        digest_contents = str(bee)
        self.assertIn('Subject: message 3', digest_contents)
        self.assertIn('Subject: message 4', digest_contents)

    def test_send_digests_for_all_lists(self):
        # Populate ant's digest.
        msg = mfs("""\
To: ant@example.com
From: anne@example.com
Subject: message 1

""")
        self._handler.process(self._mlist, msg, {})
        del msg['subject']
        msg['subject'] = 'message 2'
        self._handler.process(self._mlist, msg, {})
        # Create the second list.
        bee = create_list('bee@example.com')
        bee.digests_enabled = True
        bee.digest_size_threshold = 100000
        bee.send_welcome_message = False
        member = subscribe(bee, 'Bart')
        member.preferences.delivery_mode = DeliveryMode.plaintext_digests
        # Populate bee's digest.
        msg = mfs("""\
To: bee@example.com
From: bart@example.com
Subject: message 3

""")
        self._handler.process(bee, msg, {})
        del msg['subject']
        msg['subject'] = 'message 4'
        self._handler.process(bee, msg, {})
        # There are no digests for either list already being sent, but the
        # mailing lists do have a digest mbox collecting messages.
        ant_mailbox_path = os.path.join(self._mlist.data_path, 'digest.mmdf')
        self.assertGreater(os.path.getsize(ant_mailbox_path), 0)
        # Check bee's digest.
        bee_mailbox_path = os.path.join(bee.data_path, 'digest.mmdf')
        self.assertGreater(os.path.getsize(bee_mailbox_path), 0)
        # Both.
        items = get_queue_messages('digest')
        self.assertEqual(len(items), 0)
        # Process all mailing list digests by not setting any arguments.
        self._command.process(FakeArgs())
        self._runner.run()
        # Now, neither list has a digest mbox and but there are plaintext
        # digest in the outgoing queue for both.
        self.assertFalse(os.path.exists(ant_mailbox_path))
        self.assertFalse(os.path.exists(bee_mailbox_path))
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 2)
        # Figure out which digest is going to ant and which to bee.
        if items[0].msg['to'] == 'ant@example.com':
            ant = items[0].msg
            bee = items[1].msg
        else:
            assert items[0].msg['to'] == 'bee@example.com'
            ant = items[1].msg
            bee = items[0].msg
        # Check ant's digest.
        digest_contents = str(ant)
        self.assertIn('Subject: message 1', digest_contents)
        self.assertIn('Subject: message 2', digest_contents)
        # Check bee's digest.
        digest_contents = str(bee)
        self.assertIn('Subject: message 3', digest_contents)
        self.assertIn('Subject: message 4', digest_contents)
