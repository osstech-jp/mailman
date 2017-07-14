# Copyright (C) 2017 by the Free Software Foundation, Inc.
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

"""Perform origination & content authentication checks and add
an Authentication-Results header to the outgoing message"""

import logging

from authheaders import authenticate_message
from authres import AuthenticationResultsHeader
from dns.resolver import Timeout
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler
from public import public
from zope.interface import implementer

NUM_TIMEOUT_RETRIES = 2

# This value is used by the test suite to
# provide a faux DNS resolver.
dnsfunc = None

log = logging.getLogger('mailman.debug')


# Appends a group of headers to the beginning of a message.
def prepend_headers(msg, headers):
    old_headers = msg.items()

    for key in msg:
        del msg[key]

    for k, v in (headers + old_headers):
        msg[k] = v


# Retry a validation in case of a DNS timout.
def maybe_retry(msg, msgdata):
    if msgdata['retries_remaining'] > 0:
        log.debug('Authentication DNS Timout, retrying message')

        msgdata['retries_remaining'] = msgdata['retries_remaining'] - 1
        msgdata['abort_and_reprocess'] = True


# Extracts the most recent trusted Authentication-Results header from a message
def trusted_auth_res(msg):
    trusted_authserv_ids = config.ARC.trusted_authserv_ids.split(',')
    trusted_authserv_ids += [config.ARC.authserv_id]
    trusted_authserv_ids = [x.strip() for x in trusted_authserv_ids]

    if trusted_authserv_ids and 'Authentication-Results' in msg:
        prev = 'Authentication-Results: {}'.format(
            msg['Authentication-Results'])
        authserv_id = AuthenticationResultsHeader.parse(prev).authserv_id
        if authserv_id in trusted_authserv_ids:
            return prev

    return None


# ARC verify a message and update the Authentication-Results header
def authenticate(msg, msgdata):
    try:
        prev = trusted_auth_res(msg)
        authres = authenticate_message(
            msg.as_string().encode(), config.ARC.authserv_id,
            prev=prev,
            spf=False,  # cant spf check in mailman
            dkim=(config.ARC.dkim == 'yes'),
            dmarc=(config.ARC.dmarc == 'yes'),
            arc=True,
            dnsfunc=dnsfunc)
    except Timeout:
        maybe_retry(msg, msgdata)
        return

    if 'Authentication-Results' in msg:
        del msg['Authentication-Results']

    authres = authres.split(':', 1)[1].strip()
    prepend_headers(msg, [('Authentication-Results', authres)])


# Validate the ARC chain of a message and add results to a new
# Authentication-Results header
@public
@implementer(IHandler)
class ValidateAuthenticity:
    """Perform authentication checks and attach resulting headers"""

    name = 'validate-authenticity'
    description = _("""Perform auth checks and attach and AR header.""")

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        if config.ARC.enabled == 'yes':
            if 'retries_remaining' not in msgdata:
                msgdata['retries_remaining'] = NUM_TIMEOUT_RETRIES

            authenticate(msg, msgdata)
