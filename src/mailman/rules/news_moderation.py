# Copyright (C) 2007-2023 by the Free Software Foundation, Inc.
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

"""The news moderation rule."""

from mailman.core.i18n import _
from mailman.interfaces.nntp import NewsgroupModeration
from mailman.interfaces.rules import IRule
from public import public
from zope.interface import implementer


@public
@implementer(IRule)
class ModeratedNewsgroup:
    """The news moderation rule."""

    name = 'news-moderation'
    description = _(
        """Match all messages posted to a mailing list that gateways to a
        moderated newsgroup.
        """)
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        if mlist.newsgroup_moderation is NewsgroupModeration.moderated:
            msgdata['moderation_sender'] = msg.sender
            with _.defer_translation():
                # This will be translated at the point of use.
                msgdata.setdefault('moderation_reasons', []).append(
                    _('Post to a moderated newsgroup gateway'))
            return True
        return False
