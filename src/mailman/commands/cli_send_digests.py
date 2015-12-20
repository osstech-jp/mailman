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

"""The `send_digests` subcommand."""

__all__ = [
    'Send',
    ]


import sys

from mailman.core.i18n import _
from mailman.handlers.to_digest import maybe_send_digest_now
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.listmanager import IListManager
from zope.component import getUtility
from zope.interface import implementer



@implementer(ICLISubCommand)
class Send:
    """Send some mailing list digests right now."""

    name = 'send-digests'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""

        command_parser.add_argument(
            '-l', '--list',
            default=[], dest='lists', metavar='list', action='append',
            help=_("""Send the digests for this mailing list.  Multiple --list
                   options can be given.  The argument can either be a List-ID
                   or a fully qualified list name.  Without this option, the
                   digests for all mailing lists will be sent if possible."""))

    def process(self, args):
        """See `ICLISubCommand`."""
        if not args.lists:
            # Send the digests for every list.
            maybe_send_digest_now(force=True)
            return
        list_manager = getUtility(IListManager)
        for list_spec in args.lists:
            # We'll accept list-ids or fqdn list names.
            if '@' in list_spec:
                mlist = list_manager.get(list_spec)
            else:
                mlist = list_manager.get_by_list_id(list_spec)
            if mlist is None:
                print(_('No such list found: $list_spec'), file=sys.stderr)
                continue
            maybe_send_digest_now(mlist, force=True)
