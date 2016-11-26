# Copyright (C) 2016 by the Free Software Foundation, Inc.
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

"""Do DMARC Munge From and Wrap Message actions."""

import re
import copy
import logging

from email.header import Header, decode_header
from email.mime.message import MIMEMessage
from email.mime.text import MIMEText
from email.utils import formataddr, getaddresses, make_msgid
from mailman import public
from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler
from mailman.interfaces.mailinglist import (
    DMARCModerationAction, FromIsList, ReplyToMunging)
from mailman.utilities.string import wrap
from zope.interface import implementer


log = logging.getLogger('mailman.error')

COMMASPACE = ', '
MAXLINELEN = 78
NONASCII = re.compile('[^\s!-~]')
# Headers from the original that we want to keep in the wrapper.  These are
# actually regexps matched with re.match so they match anything that starts
# with the given string unless they end with '$'.
KEEPERS = ('archived-at',
           'date',
           'in-reply-to',
           'list-',
           'precedence',
           'references',
           'subject',
           'to',
           'x-mailman-',
           )


def munged_headers(mlist, msg, msgdata):
    # Be as robust as possible here.
    faddrs = getaddresses(msg.get_all('from', []))
    # Strip the nulls and bad emails.
    faddrs = [x for x in faddrs if x[1].find('@') > 0]
    if len(faddrs) == 1:
        realname, email = o_from = faddrs[0]
    else:
        # No From: or multiple addresses.  Just punt and take
        # the get_sender result.
        realname = ''
        email = msgdata['original_sender']
        o_from = (realname, email)
    if not realname:
        member = mlist.members.get_member(email)
        if member:
            realname = member.display_name or email
        else:
            realname = email
    # Remove domain from realname if it looks like an email address
    realname = re.sub(r'@([^ .]+\.)+[^ .]+$', '---', realname)
    # Make a display name and RFC 2047 encode it if necessary.  This is
    # difficult and kludgy. If the realname came from From: it should be
    # ascii or RFC 2047 encoded. If it came from the list, it should be
    # a string.  If it's from the email address, it should be an ascii string.
    # In any case, ensure it's an unencoded string.
    srn = ''
    for frag, cs in decode_header(realname):
        if not cs:
            # Character set should be ascii, but use iso-8859-1 anyway.
            cs = 'iso-8859-1'
        if not isinstance(frag, str):
            srn += str(frag, cs, errors='replace')
        else:
            srn += frag
    # The list's real_name is a string.
    slrn = mlist.display_name
    # get translated 'via' with dummy replacements
    realname = '$realname'
    lrn = '$lrn'                 # noqa  F841
    # Ensure the i18n context is the list's preferred_language.
    with _.using(mlist.preferred_language.code):
        via = _('$realname via $lrn')
    # Replace the dummy replacements.
    via = re.sub('\$lrn', slrn, re.sub('\$realname', srn, via))
    # And get an RFC 2047 encoded header string.
    dn = str(Header(via, mlist.preferred_language.charset))
    retn = [('From', formataddr((dn, mlist.posting_address)))]
    # We've made the munged From:.  Now put the original in Reply-To: or Cc:
    if mlist.reply_goes_to_list == ReplyToMunging.no_munging:
        # Add original from to Reply-To:
        add_to = 'Reply-To'
    else:
        # Add original from to Cc:
        add_to = 'Cc'
    orig = getaddresses(msg.get_all(add_to, []))
    if o_from[1] not in [x[1] for x in orig]:
        orig.append(o_from)
    retn.append((add_to, COMMASPACE.join([formataddr(x) for x in orig])))
    return retn


def munge_from(mlist, msg, msgdata):
    for k, v in munged_headers(mlist, msg, msgdata):
        del msg[k]
        msg[k] = v
    return


def wrap_message(mlist, msg, msgdata, dmarc_wrap=False):
    # Create a wrapper message around the original.
    # There are various headers in msg that we don't want, so we basically
    # make a copy of the msg, then delete almost everything and set/copy
    # what we want.
    omsg = copy.deepcopy(msg)
    for key in msg.keys():
        keep = False
        for keeper in KEEPERS:
            if re.match(keeper, key, re.I):
                keep = True
                break
        if not keep:
            del msg[key]
    msg['MIME-Version'] = '1.0'
    msg['Message-ID'] = make_msgid()
    for k, v in munged_headers(mlist, omsg, msgdata):
        msg[k] = v
    # Are we including dmarc_wrapped_message_text?  I.e., do we have text and
    # are we wrapping because of dmarc_moderation_action?
    if mlist.dmarc_wrapped_message_text and dmarc_wrap:
        part1 = MIMEText(wrap(mlist.dmarc_wrapped_message_text),
                         'plain',
                         mlist.preferred_language.charset)
        part1['Content-Disposition'] = 'inline'
        part2 = MIMEMessage(omsg)
        part2['Content-Disposition'] = 'inline'
        msg['Content-Type'] = 'multipart/mixed'
        msg.set_payload([part1, part2])
    else:
        msg['Content-Type'] = 'message/rfc822'
        msg['Content-Disposition'] = 'inline'
        msg.set_payload([omsg])
    return


def process(mlist, msg, msgdata):
    """Process DMARC actions."""
    if ((not msgdata.get('dmarc') or
            mlist.dmarc_moderation_action == DMARCModerationAction.none) and
            mlist.from_is_list == FromIsList.none):
        return
    if mlist.anonymous_list:
        # DMARC mitigation is not required for anonymous lists.
        return
    if (mlist.dmarc_moderation_action != DMARCModerationAction.none and
            msgdata.get('dmarc')):
        if mlist.dmarc_moderation_action == DMARCModerationAction.munge_from:
            munge_from(mlist, msg, msgdata)
        elif (mlist.dmarc_moderation_action ==
                DMARCModerationAction.wrap_message):
            wrap_message(mlist, msg, msgdata, dmarc_wrap=True)
        else:
            assert False, (
                'handlers/dmarc.py: dmarc_moderation_action = {0}'.format(
                    mlist.dmarc_moderation_action))
    else:
        if mlist.from_is_list == FromIsList.munge_from:
            munge_from(mlist, msg, msgdata)
        elif mlist.from_is_list == FromIsList.wrap_message:
            wrap_message(mlist, msg, msgdata)
        else:
            assert False, (
                'handlers/dmarc.py: from_is_list = {0}'.format(
                    mlist.from_is_list))


@public
@implementer(IHandler)
class DMARC:
    """Apply DMARC mitigations."""

    name = 'dmarc'
    description = _('Apply DMARC mitigations.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        process(mlist, msg, msgdata)
