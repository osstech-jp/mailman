# Copyright (C) 2014-2015 by the Free Software Foundation, Inc.
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

"""Test list configuration via the REST API."""

__all__ = [
    'TestConfiguration',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.database.transaction import transaction
from mailman.interfaces.mailinglist import (
    IAcceptableAliasSet, SubscriptionPolicy)
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer



class TestConfiguration(unittest.TestCase):
    """Test list configuration via the REST API."""

    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('test@example.com')

    def test_put_configuration(self):
        aliases = [
            'ant@example.com',
            'bee@example.com',
            'cat@example.com',
            ]
        # When using PUT, all writable attributes must be included.
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/test@example.com/config',
            dict(
                acceptable_aliases=aliases,
                admin_immed_notify=False,
                admin_notify_mchanges=True,
                administrivia=False,
                advertised=False,
                anonymous_list=True,
                archive_policy='never',
                autorespond_owner='respond_and_discard',
                autorespond_postings='respond_and_continue',
                autorespond_requests='respond_and_discard',
                autoresponse_grace_period='45d',
                autoresponse_owner_text='the owner',
                autoresponse_postings_text='the mailing list',
                autoresponse_request_text='the robot',
                display_name='Fnords',
                description='This is my mailing list',
                include_rfc2369_headers=False,
                allow_list_posts=False,
                digest_send_periodic='yes',
                digest_size_threshold=10.5,
                digest_volume_frequency=1,
                posting_pipeline='virgin',
                filter_content=True,
                first_strip_reply_to=True,
                convert_html_to_plaintext=True,
                collapse_alternatives=False,
                reply_goes_to_list='point_to_list',
                reply_to_address='bee@example.com',
                send_welcome_message=False,
                subject_prefix='[ant]',
                subscription_policy='confirm_then_moderate',
                welcome_message_uri='mailman:///welcome.txt',
                default_member_action='hold',
                default_nonmember_action='discard',
                ),
            'PUT')
        self.assertEqual(response.status, 204)
        self.assertEqual(self._mlist.display_name, 'Fnords')
        # All three acceptable aliases were set.
        self.assertEqual(set(IAcceptableAliasSet(self._mlist).aliases),
                         set(aliases))

    def test_patch_subscription_policy(self):
        # The new subscription_policy value can be patched.
        #
        # To start with, the subscription policy is confirm by default.
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/test@example.com/config')
        self.assertEqual(resource['subscription_policy'], 'confirm')
        # Let's patch it to do some moderation.
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/test@example.com/config', dict(
                subscription_policy='confirm_then_moderate'),
            method='PATCH')
        self.assertEqual(response.status, 204)
        # And now we verify that it has the requested setting.
        self.assertEqual(self._mlist.subscription_policy,
                         SubscriptionPolicy.confirm_then_moderate)
