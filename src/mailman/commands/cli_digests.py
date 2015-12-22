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
    'Digests',
    ]


import sys

from mailman.app.digests import maybe_send_digest_now
from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.listmanager import IListManager
from zope.component import getUtility
from zope.interface import implementer



@implementer(ICLISubCommand)
class Digests:
    """Operate on digests."""

    name = 'digests'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""

        command_parser.add_argument(
            '-l', '--list',
            default=[], dest='lists', metavar='list', action='append',
            help=_("""Operate on this mailing list.  Multiple --list
                   options can be given.  The argument can either be a List-ID
                   or a fully qualified list name.  Without this option,
                   operate on the digests for all mailing lists."""))
        command_parser.add_argument(
            '-s', '--send',
            default=False, action='store_true',
            help=_("""Send any collected digests right now, even if the size
                   threshold has not yet been met."""))
        command_parser.add_argument(
            '-b', '--bump',
            default=False, action='store_true',
            help=_("""Increment the digest volume number and reset the digest
                   number to one.  If given with --send, the volume number is
                   incremented after any current digests are sent."""))

    def process(self, args):
        """See `ICLISubCommand`."""
        list_manager = getUtility(IListManager)
        if args.send:
            if not args.lists:
                # Send the digests for every list.
                for mlist in list_manager.mailing_lists:
                    maybe_send_digest_now(mlist, force=True)
                return
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
        if args.bump:
            if not args.lists:
                mlists = list(list_manager.mailing_lists)
            else:
                # We'll accept list-ids or fqdn list names.
                if '@' in list_spec:
                    mlist = list_manager.get(list_spec)
                else:
                    mlist = list_manager.get_by_list_id(list_spec)
