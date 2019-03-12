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

"""The 'members' subcommand."""

import click

from email.utils import formataddr, parseaddr
from mailman.app.membership import add_member
from mailman.core.i18n import _
from mailman.database.transaction import transactional
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.member import (
    AlreadySubscribedError, DeliveryMode, DeliveryStatus, MemberRole)
from mailman.interfaces.subscriptions import RequestRecord
from mailman.utilities.options import I18nCommand
from operator import attrgetter
from public import public
from zope.component import getUtility
from zope.interface import implementer


def display_members(ctx, mlist, role, regular, digest, nomail, outfp):
    # Which type of digest recipients should we display?
    if digest == 'any':
        digest_types = [
            DeliveryMode.plaintext_digests,
            DeliveryMode.mime_digests,
            DeliveryMode.summary_digests,
            ]
    elif digest is not None:
        digest_types = [DeliveryMode[digest + '_digests']]
    else:
        # Don't filter on digest type.
        pass
    # Which members with delivery disabled should we display?
    if nomail is None:
        # Don't filter on delivery status.
        pass
    elif nomail == 'byadmin':
        status_types = [DeliveryStatus.by_moderator]
    elif nomail.startswith('by'):
        status_types = [DeliveryStatus['by_' + nomail[2:]]]
    elif nomail == 'enabled':
        status_types = [DeliveryStatus.enabled]
    elif nomail == 'unknown':
        status_types = [DeliveryStatus.unknown]
    elif nomail == 'any':
        status_types = [
            DeliveryStatus.by_user,
            DeliveryStatus.by_bounces,
            DeliveryStatus.by_moderator,
            DeliveryStatus.unknown,
            ]
    else:                                           # pragma: nocover
        # click should enforce a valid nomail option.
        raise AssertionError(nomail)
    # Which roles should we display?
    if role is None:
        # By default, filter on members.
        roster = mlist.members
    elif role == 'administrator':
        roster = mlist.administrators
    elif role == 'any':
        roster = mlist.subscribers
    else:
        # click should enforce a valid member role.
        roster = mlist.get_roster(MemberRole[role])
    # Print; outfp will be either the file or stdout to print to.
    addresses = list(roster.addresses)
    if len(addresses) == 0:
        print(_('$mlist.list_id has no members'), file=outfp)
        return
    for address in sorted(addresses, key=attrgetter('email')):
        if regular:
            member = roster.get_member(address.email)
            if member.delivery_mode != DeliveryMode.regular:
                continue
        if digest is not None:
            member = roster.get_member(address.email)
            if member.delivery_mode not in digest_types:
                continue
        if nomail is not None:
            member = roster.get_member(address.email)
            if member.delivery_status not in status_types:
                continue
        print(formataddr((address.display_name, address.original_email)),
              file=outfp)


@transactional
def add_members(mlist, infp):
    for line in infp:
        # Ignore blank lines and lines that start with a '#'.
        if line.startswith('#') or len(line.strip()) == 0:
            continue
        # Parse the line and ensure that the values are unicodes.
        display_name, email = parseaddr(line)
        try:
            add_member(mlist,
                       RequestRecord(email, display_name,
                                     DeliveryMode.regular,
                                     mlist.preferred_language.code))
        except AlreadySubscribedError:
            # It's okay if the address is already subscribed, just print a
            # warning and continue.
            if not display_name:
                print(_('Already subscribed (skipping): $email'))
            else:
                print(_('Already subscribed (skipping): '
                        '$display_name <$email>'))


@click.command(
    cls=I18nCommand,
    help=_("""\
    Display a mailing list's members, with filtering along various criteria.
    """))
@click.option(
    '--add', '-a', 'infp', metavar='FILENAME',
    type=click.File(encoding='utf-8'),
    help=_("""\
    Add all member addresses in FILENAME.  FILENAME can be '-' to
    indicate standard input.  Blank lines and lines That start with a
    '#' are ignored.  Without this option, this command displays
    mailing list members."""))
@click.option(
    '--output', '-o', 'outfp', metavar='FILENAME',
    type=click.File(mode='w', encoding='utf-8', atomic=True),
    help=_("""Display output to FILENAME instead of stdout.  FILENAME
    can be '-' to indicate standard output."""))
@click.option(
    '--role', '-R',
    type=click.Choice(('any', 'owner', 'moderator', 'nonmember', 'member',
                       'administrator')),
    help=_("""\
    Display only members with a given ROLE.  The role may be 'any', 'member',
    'nonmember', 'owner', 'moderator', or 'administrator' (i.e. owners and
    moderators).  If not given, then delivery members are used. """))
@click.option(
    '--regular', '-r',
    is_flag=True, default=False,
    help=_('Display only regular delivery members.'))
@click.option(
    '--digest', '-d', metavar='kind',
    # baw 2010-01-23 summary digests are not really supported yet.
    type=click.Choice(('any', 'plaintext', 'mime')),
    help=_("""\
    Display only digest members of kind.  'any' means any digest type,
    'plaintext' means only plain text (rfc 1153) type digests, 'mime' means
    mime type digests."""))
@click.option(
    '--nomail', '-n', metavar='WHY',
    type=click.Choice(('enabled', 'any', 'unknown',
                       'byadmin', 'byuser', 'bybounces')),
    help=_("""\
    Display only members with a given delivery status. 'enabled' means all
    members whose delivery is enabled, 'any' means members whose delivery is
    disabled for any reason, 'byuser' means that the member disabled their own
    delivery, 'bybounces' means that delivery was disabled by the automated
    bounce processor, 'byadmin' means delivery was disabled by the list
    administrator or moderator, and 'unknown' means that delivery was disabled
    for unknown (legacy) reasons."""))
@click.argument('listspec')
@click.pass_context
def members(ctx, infp, outfp, role, regular, digest, nomail, listspec):
    mlist = getUtility(IListManager).get(listspec)
    if mlist is None:
        ctx.fail(_('No such list: $listspec'))
    if infp is None:
        display_members(ctx, mlist, role, regular, digest, nomail, outfp)
    else:
        add_members(mlist, infp)


@public
@implementer(ICLISubCommand)
class Members:
    name = 'members'
    command = members
