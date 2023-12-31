# Copyright (C) 2016-2023 by the Free Software Foundation, Inc.
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

"""Banned addresses rule."""

from mailman.core.i18n import _
from mailman.interfaces.bans import IBanManager
from mailman.interfaces.rules import IRule
from public import public
from zope.interface import implementer


@public
@implementer(IRule)
class BannedAddress:
    """The banned address rule."""

    name = 'banned-address'
    description = _('Match messages sent by banned addresses.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        ban_manager = IBanManager(mlist)
        for sender in msg.senders:
            if ban_manager.is_banned(sender):
                msgdata['moderation_sender'] = sender
                with _.defer_translation():
                    # This will be translated at the point of use.
                    msgdata.setdefault('moderation_reasons', []).append(
                        (_('Message sender {} is banned from this list'),
                         sender))
                return True
        return False
