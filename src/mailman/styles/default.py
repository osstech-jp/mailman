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

"""Application of list styles to new and existing lists."""

from mailman.core.i18n import _
from mailman.interfaces.styles import IStyle
from mailman.styles.base import (
    Announcement,
    BasicOperation,
    Bounces,
    Discussion,
    Identity,
    Moderation,
    Private,
    Public,
)
from public import public
from zope.interface import implementer


@public
@implementer(IStyle)
class LegacyDefaultStyle(
        Identity, BasicOperation, Bounces, Public, Discussion, Moderation):

    """The legacy default style."""

    name = 'legacy-default'
    description = _('Ordinary discussion mailing list style.')

    def apply(self, mailing_list):
        """See `IStyle`."""
        Identity.apply(self, mailing_list)
        BasicOperation.apply(self, mailing_list)
        Bounces.apply(self, mailing_list)
        Public.apply(self, mailing_list)
        Discussion.apply(self, mailing_list)
        Moderation.apply(self, mailing_list)


@public
@implementer(IStyle)
class LegacyAnnounceOnly(
        Identity, BasicOperation, Bounces, Public, Announcement, Moderation):

    """Similar to the legacy-default style, but for announce-only lists."""

    name = 'legacy-announce'
    description = _('Announce only mailing list style.')

    def apply(self, mailing_list):
        """See `IStyle`."""
        Identity.apply(self, mailing_list)
        BasicOperation.apply(self, mailing_list)
        Bounces.apply(self, mailing_list)
        Public.apply(self, mailing_list)
        Announcement.apply(self, mailing_list)
        Moderation.apply(self, mailing_list)


@public
@implementer(IStyle)
class PrivateDefaultStyle(
        Identity, BasicOperation, Bounces, Private, Discussion, Moderation):

    """Style for mailing-lists with private archives."""

    name = 'private-default'
    description = _('Discussion mailing list style with private archives.')

    def apply(self, mailing_list):
        """See `IStyle`."""
        Identity.apply(self, mailing_list)
        BasicOperation.apply(self, mailing_list)
        Bounces.apply(self, mailing_list)
        Private.apply(self, mailing_list)
        Discussion.apply(self, mailing_list)
        Moderation.apply(self, mailing_list)
