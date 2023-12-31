# Copyright (C) 1998-2023 by the Free Software Foundation, Inc.
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

"""Incoming runner.

This runner's sole purpose in life is to decide the disposition of the
message.  It can either be accepted for delivery, rejected (i.e. bounced),
held for moderator approval, or discarded.

When accepted, the message is forwarded on to the `prep queue` where it is
prepared for delivery.  Rejections, discards, and holds are processed
immediately.
"""

import logging

from contextlib import suppress
from mailman.config import config
from mailman.core.chains import process
from mailman.core.runner import Runner
from mailman.database.transaction import transaction
from mailman.interfaces.address import ExistingAddressError
from mailman.interfaces.autorespond import ResponseAction
from mailman.interfaces.usermanager import IUserManager
from public import public
from zope.component import getUtility


log = logging.getLogger('mailman.vette')


@public
class IncomingRunner(Runner):
    """The incoming runner."""

    def _dispose(self, mlist, msg, msgdata):
        """See `IRunner`."""
        if msgdata.get('envsender') is None:
            msgdata['envsender'] = mlist.no_reply_address
        # Do replybot actions for posts and -owner.
        message_id = msg.get('message-id', 'n/a')
        replybot = config.handlers['replybot']
        replybot.process(mlist, msg, msgdata)
        if (msgdata.get('to_owner') and
                mlist.autorespond_owner == ResponseAction.respond_and_discard):
            # Respond and discard.
            log.info('%s -owner message replied and discarded', message_id)
            return False
        if (msgdata.get('to_list') and
                mlist.autorespond_postings ==
                ResponseAction.respond_and_discard):
            # Respond and discard.
            log.info('%s list post replied and discarded', message_id)
            return False
        # Ensure that the email addresses of the message's senders are known
        # to Mailman.  This will be used in nonmember posting dispositions.
        user_manager = getUtility(IUserManager)
        with transaction():
            for sender in msg.senders:
                with suppress(ExistingAddressError):
                    user_manager.create_address(sender)
        # Process the message through the mailing list's start chain.
        start_chain = (mlist.owner_chain
                       if msgdata.get('to_owner', False)
                       else mlist.posting_chain)
        process(mlist, msg, msgdata, start_chain)
        # Do not keep this message queued.
        return False
