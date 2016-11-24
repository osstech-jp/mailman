# Copyright (C) 2009-2016 by the Free Software Foundation, Inc.
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

"""Fake MTA for testing purposes."""

import asyncio
import logging
import smtplib

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message as MessageHandler
from aiosmtpd.smtp import SMTP
from mailman import public
from mailman.interfaces.mta import IMailTransportAgentLifecycle
from queue import Empty, Queue
from zope.interface import implementer


log = logging.getLogger('lazr.smtptest')


@public
@implementer(IMailTransportAgentLifecycle)
class FakeMTA:
    """Fake MTA for testing purposes."""

    def create(self, mlist):
        pass

    def delete(self, mlist):
        pass

    def regenerate(self, output=None):
        pass


class ConnectionCountingHandler(MessageHandler):
    def __init__(self, msg_queue):
        super().__init__()
        self._msg_queue = msg_queue

    def handle_message(self, message):
        self._msg_queue.put(message)


class ConnectionCountingSMTP(SMTP):
    def __init__(self, handler, oob_queue, err_queue, *args, **kws):
        super().__init__(handler, *args, **kws)
        self._auth_response = None
        self._waiting_for_auth_response = False
        self._connection_count = 0
        self._oob_queue = oob_queue
        self._err_queue = err_queue
        self._last_error = None

    @asyncio.coroutine
    def smtp_AUTH(self, arg):
        """Record that the AUTH occurred."""
        args = arg.split()
        if args[0].lower() == 'plain':
            if len(args) == 2:
                response = args[1]
                # The second argument is the AUTH PLAIN <initial-response>
                # which must be equal to the base 64 equivalent of the
                # expected login string "testuser:testpass".
                if response == 'AHRlc3R1c2VyAHRlc3RwYXNz':
                    yield from self.push('235 Ok')
                    self._oob_queue.put(response)
                else:
                    yield from self.push('571 Bad authentication')
            else:
                assert len(args) == 1, args
                # Send a challenge and set us up to wait for the response.
                yield from self.push('334 ')
                self._waiting_for_auth_response = True
        else:
            yield from self.push('571 Bad authentication')

    @asyncio.coroutine
    def smtp_EHLO(self, arg):
        yield from super().smtp_EHLO(arg)
        # If the upcall succeeded, this flag will be set.  In that case, also
        # push an AUTH PLAIN response, which the superclass doesn't do.
        ## if self.extended_smtp:
        ##     yield from self.push('250 AUTH PLAIN')

    @asyncio.coroutine
    def smtp_STAT(self, arg):
        """Cause the server to send statistics to its controller."""
        # Do not count the connection caused by the STAT connect.
        self._connection_count -= 1
        self._oob_queue.put(self._connection_count)
        yield from self.push('250 Ok')

    def _next_error(self, command):
        """Return the next error for the SMTP command, if there is one.

        :param command: The SMTP command for which an error might be
            expected.  If the next error matches the given command, the
            expected error code is returned.
        :type command: string, lower-cased
        :return: An SMTP error code
        :rtype: integer
        """
        # If the last error we pulled from the queue didn't match, then we're
        # caching it, and it might match this expected error.  If there is no
        # last error in the cache, get one from the queue now.
        if self._last_error is None:
            try:
                self._last_error = self._err_queue.get_nowait()
            except Empty:
                # No error is expected
                return None
        if self._last_error[0] == command:
            code = self._last_error[1]
            self._last_error = None
            return code
        return None

    @asyncio.coroutine
    def smtp_RCPT(self, arg):
        """For testing, sometimes cause a non-25x response."""
        code = self._next_error('rcpt')
        if code is None:
            # Everything's cool.
            yield from super().smtp_RCPT(arg)
        else:
            # The test suite wants this to fail.  The message corresponds to
            # the exception we expect smtplib.SMTP to raise.
            yield from self.push('%d Error: SMTPRecipientsRefused' % code)

    @asyncio.coroutine
    def smtp_MAIL(self, arg):
        """For testing, sometimes cause a non-25x response."""
        code = self._next_error('mail')
        if code is None:
            # Everything's cool.
            yield from super().smtp_MAIL(arg)
        else:
            # The test suite wants this to fail.  The message corresponds to
            # the exception we expect smtplib.SMTP to raise.
            yield from self.push('%d Error: SMTPResponseException' % code)

    def found_terminator(self):
        # Are we're waiting for the AUTH challenge response?
        if self._waiting_for_auth_response:
            line = self._emptystring.join(self.received_lines)
            self._auth_response = line
            self._waiting_for_auth_response = False
            self.received_lines = []
            # Now check to see if they authenticated correctly.
            self._check_auth(line)
        else:
            super().found_terminator()


import socket
import asyncio


class ConnectionCountingController(Controller):
    """Count the number of SMTP connections opened."""

    def __init__(self, host, port):
        self._msg_queue = Queue()
        self._oob_queue = Queue()
        self.err_queue = Queue()
        handler = ConnectionCountingHandler(self._msg_queue)
        super().__init__(handler, hostname=host, port=port)

    def factory(self):
        return ConnectionCountingSMTP(
            self.handler, self._oob_queue, self.err_queue)

    def _run(self, ready_event):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        sock.bind((self.hostname, self.port))
        asyncio.set_event_loop(self.loop)
        server = self.loop.run_until_complete(
            self.loop.create_server(self.factory, sock=sock))
        self.loop.call_soon(ready_event.set)
        self.loop.run_forever()
        server.close()
        self.loop.run_until_complete(server.wait_closed())
        self.loop.close()

    def start(self):
        super().start()
        # Reset the connection statistics, since the base class's start()
        # method causes a connection to occur.
        self.reset()

    def _connect(self):
        client = smtplib.SMTP()
        client.connect(self.hostname, self.port)
        return client

    def get_connection_count(self):
        """Retrieve the number of connections.

        :return: The number of connections to the server that have been made.
        :rtype: integer
        """
        client = self._connect()
        client.docmd('STAT')
        # An Empty exception will occur if the data isn't available in 10
        # seconds.  Let that propagate.
        return self._oob_queue.get(block=True, timeout=10)

    def get_authentication_credentials(self):
        """Retrieve the last authentication credentials."""
        return self._oob_queue.get(block=True, timeout=10)

    def __iter__(self):
        while True:
            try:
                yield self._msg_queue.get_nowait()
            except Empty:
                raise StopIteration

    @property
    def messages(self):
        """Return all the messages received by the SMTP server."""
        yield from self

    def clear(self):
        """Clear all the messages from the queue."""
        list(self)

    def reset(self):
        client = self._connect()
        client.docmd('RSET')
