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

"""Perform authentication checks and adds headers to outgoing message"""

import logging

from authheaders import sign_message
from dkim import DKIMException
from mailman.config import config
from mailman.core.i18n import _
from mailman.handlers.validate_authenticity import prepend_headers
from mailman.interfaces.handler import IHandler
from public import public
from zope.interface import implementer

# a manual override used by the test suite
timestamp = None

config_log = logging.getLogger('mailman.config')
error_log = logging.getLogger('mailman.error')


# ARC sign a message, and prepend the signature headers to the message
def sign(msg, msgdata):
    split_headers = config.ARC.sig_headers.encode().split(b',')
    sig_headers = [x.strip() for x in split_headers]

    try:
        with open(config.ARC.privkey, encoding='ascii') as fp:
            privkey = fp.read()
    except OSError:
        config_log.error('Private key file is unreadable: {}'.format(
            config.ARC.privkey))
        return
    except UnicodeDecodeError:
        config_log.error('Private key file contains non-ASCII: {}'.format(
            config.ARC.privkey))
        return

    try:
        sig = sign_message(msg.as_string().encode(),
                           config.ARC.selector.encode(),
                           config.ARC.domain.encode(),
                           privkey.encode(), sig_headers,
                           'ARC', config.ARC.authserv_id,
                           timestamp=timestamp,
                           standardize=('ARC-Standardize' in msgdata))
    except DKIMException as e:
        error_log.exception('Failed to sign message')
        return

    headers = [x.decode('utf-8').split(': ', 1) for x in sig]
    prepend_headers(msg, headers)


@public
@implementer(IHandler)
class ArcSign:
    """Sign message and attach result headers."""

    name = 'arc-sign'
    description = _('Perform ARC auth checks and attach resulting headers')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""

        if config.ARC.enabled == 'yes':
            sign(msg, msgdata)
