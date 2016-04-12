# Copyright (C) 2007-2016 by the Free Software Foundation, Inc.
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

"""Membership related rules."""

import re

from mailman import public
from mailman.core.i18n import _
from mailman.interfaces.action import Action
from mailman.interfaces.bans import IBanManager
from mailman.interfaces.member import MemberRole
from mailman.interfaces.rules import IRule
from mailman.interfaces.usermanager import IUserManager
from zope.component import getUtility
from zope.interface import implementer


@public
@implementer(IRule)
class MemberModeration:
    """The member moderation rule."""

    name = 'member-moderation'
    description = _('Match messages sent by moderated members.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        user_manager = getUtility(IUserManager)
        for sender in msg.senders:
            # The member-moderation rule is not set if the address is banned,
            # even if it is linked to a subscribed addresses.
            if IBanManager(mlist).is_banned(sender):
                return False
            # Check for subscribed members linked to the address
            member = mlist.members.get_member(sender)
            if member is None:
                user = user_manager.get_user(sender)
                if user is not None:
                    for address in user.addresses:
                        if mlist.members.get_member(address.email) is not None:
                            member = mlist.members.get_member(address.email)
                            break
            if member is None:
                return False
            action = (mlist.default_member_action
                      if member.moderation_action is None
                      else member.moderation_action)
            if action is Action.defer:
                # The regular moderation rules apply.
                return False
            elif action is not None:
                # We must stringify the moderation action so that
                # it can be stored in the pending request table.
                msgdata['moderation_action'] = action.name
                msgdata['moderation_sender'] = sender
                msgdata.setdefault('moderation_reasons', []).append(
                    # This will get translated at the point of use.
                    'The message comes from a moderated member')
                return True
        # The sender is not a member so this rule does not match.
        return False


def _record_action(msgdata, action, sender, reason):
    msgdata['moderation_action'] = action
    msgdata['moderation_sender'] = sender
    msgdata.setdefault('moderation_reasons', []).append(reason)


@public
@implementer(IRule)
class NonmemberModeration:
    """The nonmember moderation rule."""

    name = 'nonmember-moderation'
    description = _('Match messages sent by nonmembers.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        user_manager = getUtility(IUserManager)
        # First ensure that all senders are already either members or
        # nonmembers.  If they are not subscribed in some role to the mailing
        # list, make them nonmembers.
        # Maintain a record of which senders have linked subscribed users
        found_linked_membership = {}
        for sender in msg.senders:
            found_linked_membership[sender] = 'False'
            # Check for linked user membership
            member = mlist.members.get_member(sender)
            if member is not None:
                found_linked_membership[sender] = 'True'
            else:
                user = user_manager.get_user(sender)
                if user is not None:
                    for address in user.addresses:
                        if mlist.members.get_member(address.email) is not None:
                            found_linked_membership[sender] = 'True'
            # If the posting addres is banned, the post is not allowed
            # to pass even if the address is linked to subscribed user.
            if IBanManager(mlist).is_banned(sender):
                found_linked_membership[sender] = 'False'
            if (mlist.nonmembers.get_member(sender) is None and
                    found_linked_membership.get(sender) == 'False'):
                # The address is neither a member nor nonmember
                # and has no linked subscribed user
                address = user_manager.get_address(sender)
                assert address is not None, (
                    'Posting address is not registered: {}'.format(sender))
                mlist.subscribe(address, MemberRole.nonmember)
        # If a member is found, the member-moderation rule takes precedence.
        for sender in msg.senders:
            if found_linked_membership.get(sender) == 'True':
                return False
        # Do nonmember moderation check.
        for sender in msg.senders:
            nonmember = mlist.nonmembers.get_member(sender)
            assert nonmember is not None, (
                'Sender not added to the nonmembers: {}'.format(sender))
            # Check the '*_these_nonmembers' properties first.  XXX These are
            # legacy attributes from MM2.1; their database type is 'pickle' and
            # they should eventually get replaced.
            for action in ('accept', 'hold', 'reject', 'discard'):
                legacy_attribute_name = '{}_these_nonmembers'.format(action)
                checklist = getattr(mlist, legacy_attribute_name)
                for addr in checklist:
                    if ((addr.startswith('^') and re.match(addr, sender))
                            or addr == sender):     # noqa
                        # The reason will get translated at the point of use.
                        reason = 'The sender is in the nonmember {} list'
                        _record_action(msgdata, action, sender,
                                       reason.format(action))
                        return True
            action = (mlist.default_nonmember_action
                      if nonmember.moderation_action is None
                      else nonmember.moderation_action)
            if action is Action.defer:
                # The regular moderation rules apply.
                return False
            elif action is not None:
                # We must stringify the moderation action so that it can be
                # stored in the pending request table.
                #
                # The reason will get translated at the point of use.
                reason = 'The message is not from a list member'
                _record_action(msgdata, action.name, sender, reason)
                return True
        # The sender must be a member, so this rule does not match.
        return False
