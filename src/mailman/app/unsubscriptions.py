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

"""Handle un-subscriptions."""

import uuid
import logging

from datetime import timedelta
from email.utils import formataddr
from mailman import public
from mailman.app.membership import delete_member
from mailman.app.subscriptions import WhichSubscriber
from mailman.app.workflow import Workflow
from mailman.core.i18n import _
from mailman.email.message import UserNotification
from mailman.interfaces.address import IAddress
from mailman.interfaces.mailinglist import SubscriptionPolicy
from mailman.interfaces.workflowmanager import ConfirmationNeededEvent
from mailman.interfaces.user import IUser
from mailman.interfaces.pending import IPendings, IPendable
from mailman.interfaces.subscriptions import TokenOwner
from mailman.interfaces.usermanager import IUserManager
from mailman.interfaces.workflow import IWorkflowStateManager
from mailman.utilities.datetime import now
from mailman.utilities.i18n import make
from zope.component import getUtility
from zope.event import notify
from zope.interface import implementer


log = logging.getLogger('mailman.subscribe')


@implementer(IPendable)
class Pendable(dict):
    PEND_TYPE = 'unsubscription'


class UnSubscriptionWorkflow(Workflow):
    """Workflow of a un-subscription request
    """

    INITIAL_STATE = 'subscription_checks'
    SAVE_ATTRIBUTES = (
        'pre_approved',
        'pre_confirmed',
        'address_key',
        'user_key',
        'subscriber_key',
        'token_owner_key',
    )

    def __init__(self, mlist, subscriber=None, *,
                 pre_approved=False, pre_confirmed = False):
        super().__init__()
        self.mlist = mlist
        self.address = None
        self.user = None
        self.which = None
        self._set_token(TokenOwner.no_one)
        # `subscriber` should be an implementer of IAddress.
        if IAddress.providedBy(subscriber):
            self.address = subscriber
            self.user = self.address.user
            self.which = WhichSubscriber.address
            self.member = self.mlist.regular_members.get_member(
                              self.address.email)            
        elif IUser.providedBy(subscriber):
            self.address = subscriber.preferred_address
            self.user = subscriber
            self.which = WhichSubscriber.address
            self.member = self.mlist.regular_members.get_member(
                              self.address.email)
        self.subscriber = subscriber
        self.pre_confirmed = pre_confirmed
        self.pre_approved = pre_approved

    @property
    def user_key(self):
        # For save.
        return self.user.user_id.hex

    @user_key.setter
    def user_key(self, hex_key):
        # For restore.
        uid = uuid.UUID(hex_key)
        self.user = getUtility(IUserManager).get_user_by_id(uid)
        assert self.user is not None

    @property
    def address_key(self):
        # For save.
        return self.address.email

    @address_key.setter
    def address_key(self, email):
        # For restore.
        self.address = getUtility(IUserManager).get_address(email)
        assert self.address is not None

    @property
    def subscriber_key(self):
        return self.which.value

    @subscriber_key.setter
    def subscriber_key(self, key):
        self.which = WhichSubscriber(key)

    @property
    def token_owner_key(self):
        return self.token_owner.value

    @token_owner_key.setter
    def token_owner_key(self, value):
        self.token_owner = TokenOwner(value)

    def _set_token(self, token_owner):
        assert isinstance(token_owner, TokenOwner)
        pendings = getUtility(IPendings)
        # Clear out the previous pending token if there is one.
        if self.token is not None:
            pendings.confirm(self.token)
        # Create a new token to prevent replay attacks.  It seems like this
        # would produce the same token, but it won't because the pending adds a
        # bit of randomization.
        self.token_owner = token_owner
        if token_owner is TokenOwner.no_one:
            self.token = None
            return
        pendable = Pendable(
            list_id=self.mlist.list_id,
            email=self.address.email,
            display_name=self.address.display_name,
            when=now().replace(microsecond=0).isoformat(),
            token_owner=token_owner.name,
        )
        self.token = pendings.add(pendable, timedelta(days=3650))

    def _step_subscription_checks(self):
        assert self.mlist.is_subscribed(self.subscriber)
        self.push('confirmation_checks')

    def _step_confirmation_checks(self):
        # If list's unsubscription policy is open, the user can unsubscribe
        # right now.
        if self.mlist.unsubscription_policy is SubscriptionPolicy.open:
            self.push('do_unsubscription')
            return
        # If we don't need the user's confirmation, then skip to the moderation
        # checks
        if self.mlist.unsubscription_policy is SubscriptionPolicy.moderate:
            self.push('moderation_checks')
            return

        if self.pre_confirmed:
            next_step = ('moderation_checks'
                         if self.mlist.subscription_policy is
                             SubscriptionPolicy.confirm_then_moderate   # noqa
                         else 'do_subscription')
            self.push(next_step)
            return
        # The user must confirm their un-subsbcription.
        self.push('send_confirmation')

    def _step_send_confirmation(self):
        self._set_token(TokenOwner.subscriber)
        self.push('do_confirm_verify')
        self.save()
        notify(ConfirmationNeededEvent(
            self.mlist, self.token, self.address.email))
        raise StopIteration

    def _step_moderation_checks(self):
        # Does the moderator need to approve the unsubscription request.
        assert self.mlist.unsubscription_policy in (
            SubscriptionPolicy.moderate,
            SubscriptionPolicy.confirm_then_moderate,
        ), self.mlist.unsubscription_policy
        if self.pre_approved:
            self.push('do_unsubscription')
        else:
            self.push('get_moderator_approval')

    def _step_get_moderator_approval(self):
        self._set_token(TokenOwner.moderator)
        self.push('unsubscribe_from_restored')
        self.save()
        log.info('{}: held unsubscription request from {}'.format(
            self.mlist.fqdn_listname, self.address.email))
        if self.mlist.admin_immed_notify:
            subject = _(
                'New unsubscription request to $self.mlist.display_name '
                'from $self.address.email')
            username = formataddr(
                (self.subscriber.display_name, self.address.email))
            text = make('unsubauth.txt',
                        mailing_list=self.mlist,
                        username=username,
                        listname=self.mlist.fqdn_listname,
                        )
            # This message should appear to come from the <list>-owner so as
            # to avoid any useless bounce processing.
            msg = UserNotification(
                self.mlist.owner_address, self.mlist.owner_address,
                subject, text, self.mlist.preferred_language)
            msg.send(self.mlist, tomoderators=True)
        # The workflow must stop running here
        raise StopIteration

    def _step_do_confirm_verify(self):
        if self.which is WhichSubscriber.address:
            self.subscriber = self.address
        else:
            assert self.which is WhichSubscriber.user
            self.subscriber = self.user
            # Reset the token so it can't be used in a replay attack.
        self._set_token(TokenOwner.no_one)
        next_step = ('moderation_checks'
                     if self.mlist.unsubscription_policy in (
                          SubscriptionPolicy.moderate,
                          SubscriptionPolicy.confirm_then_moderate,
                          )
                     else 'do_unsubscription')
        self.push('do_unsubscription')

    def _step_do_unsubscription(self):
        delete_member(self.mlist, self.address.email)
        self.member = None
        # This workflow is done so throw away any associated state.
        getUtility(IWorkflowStateManager).restore(self.name, self.token)    

    def _step_unsubscribe_from_restored(self):
        # Prevent replay attacks.
        self._set_token(TokenOwner.no_one)
        if self.which is WhichSubscriber.address:
            self.subscriber = self.address
        else:
            assert self.which is WhichSubsriber.user
            self.subscriber = self.user
        self.push('do_unsubscription')
