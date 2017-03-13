# Copyright (C) 2009-2019 by the Free Software Foundation, Inc.
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

"""MTA connections."""

import ssl
import logging
import smtplib

from contextlib import suppress
from lazr.config import as_boolean
from mailman.config import config
from mailman.interfaces.smtp import ISMTPConnection
from public import public
from zope.interface import implementer

log = logging.getLogger('mailman.smtp')


@implementer(ISMTPConnection)
class Connection:

    def __init__(self, host, port, sessions_per_connection,
                 smtp_user=None, smtp_pass=None):
        """Create a connection manager.

        :param host: The host name of the SMTP server to connect to.
        :type host: string
        :param port: The port number of the SMTP server to connect to.
        :type port: integer
        :param sessions_per_connection: The number of SMTP sessions per
            connection to the SMTP server.  After this number of sessions
            has been reached, the connection is closed and a new one is
            opened.  Set to zero for an unlimited number of sessions per
            connection (i.e. your MTA has no limit).
        :type sessions_per_connection: integer
        :param smtp_user: Optional SMTP authentication user name.  If given,
            `smtp_pass` must also be given.
        :type smtp_user: str
        :param smtp_pass: Optional SMTP authentication password.  If given,
            `smtp_user` must also be given.
        """
        self._host = host
        self._port = port
        self._sessions_per_connection = sessions_per_connection
        self._username = smtp_user
        self._password = smtp_pass
        self._session_count = None
        self._connection = None

    def _login(self):
        """Send login if both username and password are specified."""
        if self._username is not None and self._password is not None:
            log.debug('Logging in')
            self._connection.login(self._username, self._password)

    def sendmail(self, envsender, recipients, msgtext):
        if as_boolean(config.devmode.enabled):
            # Force the recipients to the specified address, but still deliver
            # to the same number of recipients.
            recipients = [config.devmode.recipient] * len(recipients)
        if self._connection is None:
            self._connect()
            self._login()
        # smtplib.SMTP.sendmail requires the message string to be pure ascii.
        # We have seen malformed messages with non-ascii unicodes, so ensure
        # we have pure ascii.
        msgtext = msgtext.encode('ascii', 'replace').decode('ascii')
        try:
            log.debug('envsender: %s, recipients: %s, size(msgtext): %s',
                      envsender, recipients, len(msgtext))
            results = self._connection.sendmail(envsender, recipients, msgtext)
        except smtplib.SMTPException:
            # For safety, close this connection.  The next send attempt will
            # automatically re-open it.  Pass the exception on up.
            self.quit()
            raise
        # This session has been successfully completed.
        self._session_count -= 1
        # By testing exactly for equality to 0, we automatically handle the
        # case for SMTP_MAX_SESSIONS_PER_CONNECTION <= 0 meaning never close
        # the connection.  We won't worry about wraparound <wink>.
        if self._session_count == 0:
            self.quit()
        return results

    def quit(self):
        if self._connection is None:
            return
        with suppress(smtplib.SMTPException):
            self._connection.quit()
        self._connection = None


@public
class SMTPConnection(Connection):
    """Manage a clear connection to the SMTP server."""

    def _connect(self):
        """Open a new connection."""
        log.debug('Connecting to %s:%s', self._host, self._port)
        self._connection = smtplib.SMTP(self._host, self._port)
        self._session_count = self._sessions_per_connection


class _SSLConnection(Connection):
    """Manage a SMTP connection with a SSL context(either SMTPS or STARTTLS)"""

    def __init__(self, host, port, sessions_per_connection,
                 verify_cert=False, verify_hostname=False,
                 smtp_user=None, smtp_pass=None):
        """
        Create a connection manager with and SSL context.

        :param host: The host name of the SMTP server to connect to.
        :type host: string
        :param port: The port number of the SMTP server to connect to.
        :type port: integer
        :param sessions_per_connection: The number of SMTP sessions per
            connection to the SMTP server.  After this number of sessions
            has been reached, the connection is closed and a new one is
            opened.  Set to zero for an unlimited number of sessions per
            connection (i.e. your MTA has no limit).
        :type sessions_per_connection: integer
        :param verify_cert: Whether to require a server cert and verify it.
            Verification in this context means that the server needs to supply
            a valid certificate signed by a CA from a set of the system's
            default CA certs.
        :type verify_cert: bool
        :param verify_hostname: Whether to check that the server certificate
            specifies the hostname as passed to this constructor.
            RFC 2818 and RFC 6125 rules are followed.
        :type verify_hostname: bool
        :param smtp_user: Optional SMTP authentication user name.  If given,
            `smtp_pass` must also be given.
        :type smtp_user: str
        :param smtp_pass: Optional SMTP authentication password.  If given,
            `smtp_user` must also be given.
        """
        super().__init__(host, port, sessions_per_connection,
                         smtp_user, smtp_pass)
        self._tls_context = self._get_context(verify_cert, verify_hostname)

    def _get_context(self, verify_cert, verify_hostname):
        """Create and return a new SSLContext."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = verify_hostname
        if verify_cert:
            ssl_context.verify_mode = ssl.CERT_REQUIRED
        else:
            ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context


@public
class SMTPSConnection(_SSLConnection):
    """Manage a SMTPS connection."""

    def _connect(self):
        log.debug('Connecting to %s:%s', self._host, self._port)
        self._connection = smtplib.SMTP_SSL(self._host, self._port,
                                            context=self._tls_context)
        self._session_count = self._sessions_per_connection


@public
class STARTTLSConnection(_SSLConnection, SMTPConnection):
    """Manage a plain connection with STARTTLS."""

    def _connect(self):
        super()._connect()
        log.debug('Starttls')
        try:
            self._connection.starttls(context=self._tls_context)
        except smtplib.SMTPNotSupportedError as notls:
            log.error('Starttls failed: ' + str(notls))
