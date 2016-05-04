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
        # The MemberModeration rule misses unconditionally if any of the
        # senders are banned.
        ban_manager = IBanManager(mlist)
        user_manager = getUtility(IUserManager)
        for sender in msg.senders:
            if ban_manager.is_banned(sender):
                return False
        # For each sender address, try to find a member associated with the
        # email address.  Start by checking the sender email directly.  If the
        # sender email is not a member, try to find the user linked to the
        # email, and then check to see if *that* user, or any of the addresses
        # linked to that user is a member.  This rule hits of we find a member
        # and their moderation action is not to defer.
        for sender in msg.senders:
            # Is the sender email itself a member?
            member = mlist.members.get_member(sender)
            if member is None:
                # Is the sender email linked to a user?
                user = user_manager.get_user(sender)
                if user is not None:
                    # Are any of the emails linked to this user a member?
                    for address in user.addresses:
                        member = mlist.members.get_member(address.email)
                        if member is not None:
                            # We found a member, so we don't need to check any
                            # of the other linked addresses.
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
                # We must stringify the moderation action so that it can be
                # stored in the pending request table.
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
        ban_manager = IBanManager(mlist)
        user_manager = getUtility(IUserManager)
        # The NonmemberModeration rule misses unconditionally if any of the
        # senders are banned.
        for sender in msg.senders:
            if ban_manager.is_banned(sender):
                return False
        # Every sender must somehow be a member or nonmember.  The sender
        # email can have one of those roles directly, or a user that the email
        # is linked to can have one of those roles indirectly, or any address
        # linked to one of those users can have one of those roles.
        #
        # If the sender is not somehow a member or nonmember, make them a
        # nonmember.  We maintain a record of which senders are members, and
        # then the ones that aren't are made nonmembers.
        found_linked_membership = set()
        for sender in msg.senders:
            member = mlist.members.get_member(sender)
            if member is None:
                user = user_manager.get_user(sender)
                if user is not None:
                    for address in user.addresses:
                        if mlist.members.get_member(address.email) is not None:
                            found_linked_membership.add(sender)
            else:
                found_linked_membership.add(sender)
            # Now we know whether the sender is somehow linked to a member or
            # not.  If not, and the email also isn't already a nonmember, make
            # them a nonmember.
            if (mlist.nonmembers.get_member(sender) is None
                    and sender not in found_linked_membership):   # noqa
                address = user_manager.get_address(sender)
                assert address is not None, (
                    'Posting address is not registered: {}'.format(sender))
                mlist.subscribe(address, MemberRole.nonmember)
        # If a membership is found, the MemberModeration rule takes precedence.
        for sender in msg.senders:
            if sender in found_linked_membership:
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
