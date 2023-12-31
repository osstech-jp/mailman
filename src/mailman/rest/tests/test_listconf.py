# Copyright (C) 2014-2023 by the Free Software Foundation, Inc.
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

"""Test list configuration via the REST API."""

import unittest

from mailman.app.lifecycle import create_list
from mailman.database.transaction import transaction
from mailman.interfaces.digests import DigestFrequency
from mailman.interfaces.mailinglist import (
    IAcceptableAliasSet,
    SubscriptionPolicy,
)
from mailman.interfaces.template import ITemplateManager
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer
from urllib.error import HTTPError
from zope.component import getUtility


# The representation of the listconf resource as a dictionary.  This is used
# when PUTting to the list's configuration resource.
RESOURCE = dict(
    acceptable_aliases=[
        'ant@example.com',
        'bee@example.com',
        'cat@example.com',
        ],
    accept_these_nonmembers=[
        r'ant_*@example.com',
        ],
    admin_immed_notify=False,
    admin_notify_mchanges=True,
    administrivia=False,
    advertised=False,
    allow_list_posts=False,
    anonymous_list=True,
    archive_policy='never',
    archive_rendering_mode='text',
    autorespond_owner='respond_and_discard',
    autorespond_postings='respond_and_continue',
    autorespond_requests='respond_and_discard',
    autoresponse_grace_period='45d',
    autoresponse_owner_text='the owner',
    autoresponse_postings_text='the mailing list',
    autoresponse_request_text='the robot',
    bounce_info_stale_after='7d',
    bounce_notify_owner_on_bounce_increment=False,
    bounce_notify_owner_on_disable=False,
    bounce_notify_owner_on_removal=True,
    bounce_score_threshold=5,
    bounce_you_are_disabled_warnings=3,
    bounce_you_are_disabled_warnings_interval='2d',
    collapse_alternatives=False,
    convert_html_to_plaintext=True,
    default_member_action='hold',
    default_nonmember_action='discard',
    description='This is my mailing list',
    digest_send_periodic=True,
    digest_size_threshold=10.5,
    digest_volume_frequency='monthly',
    digests_enabled=True,
    discard_these_nonmembers=[
       'aperson@example.com',
       ],
    display_name='Fnords',
    dmarc_mitigate_action='munge_from',
    dmarc_mitigate_unconditionally=False,
    dmarc_addresses='',
    dmarc_moderation_notice='Some moderation notice',
    dmarc_wrapped_message_text='some message text',
    emergency=False,
    filter_action='discard',
    filter_extensions=['.exe'],
    filter_content=True,
    filter_types=['application/zip'],
    first_strip_reply_to=True,
    forward_unrecognized_bounces_to='administrators',
    gateway_to_mail=False,
    gateway_to_news=False,
    goodbye_message_uri='mailman:///goodbye.txt',
    hold_these_nonmembers=[
        r'*@example.com',
        ],
    include_rfc2369_headers=False,
    info='This is the mailing list info',
    linked_newsgroup='',
    moderator_password='password',
    max_message_size='150',
    newsgroup_moderation='none',
    nntp_prefix_subject_too=False,
    pass_extensions=['.pdf'],
    pass_types=['image/jpeg'],
    personalize='none',
    posting_pipeline='virgin',
    preferred_language='en',
    process_bounces=True,
    reject_these_nonmembers=[
       'bperson@example.com',
       ],
    reply_goes_to_list='point_to_list',
    reply_to_address='bee@example.com',
    require_explicit_destination=True,
    member_roster_visibility='public',
    send_goodbye_message=False,
    send_welcome_message=False,
    subject_prefix='[ant]',
    subscription_policy='confirm_then_moderate',
    unsubscription_policy='confirm',
    welcome_message_uri='mailman:///welcome.txt',
    respond_to_post_requests=True,
    max_num_recipients=150,
    max_days_to_hold=20,
    )


class TestConfiguration(unittest.TestCase):
    """Test list configuration via the REST API."""

    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('ant@example.com')

    def test_get_missing_attribute(self):
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config/bogus')
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.reason, 'Unknown attribute: bogus')

    def test_put_configuration(self):
        # When using PUT, all writable attributes must be included.
        json, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config',
            RESOURCE,
            'PUT')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self._mlist.display_name, 'Fnords')
        # All three acceptable aliases were set.
        self.assertEqual(set(IAcceptableAliasSet(self._mlist).aliases),
                         set(RESOURCE['acceptable_aliases']))

    def test_put_attribute(self):
        json, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com'
            '/config/reply_to_address')
        self.assertEqual(json['reply_to_address'], '')
        json, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com'
            '/config/reply_to_address',
            dict(reply_to_address='bar@ant.example.com'),
            'PUT')
        self.assertEqual(response.status_code, 204)
        json, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com'
            '/config/reply_to_address')
        self.assertEqual(json['reply_to_address'], 'bar@ant.example.com')

    def test_put_extra_attribute(self):
        bogus_resource = RESOURCE.copy()
        bogus_resource['bogus'] = 'yes'
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config',
                bogus_resource,
                'PUT')
        self.assertEqual(cm.exception.code, 400)
        self.assertTrue('Unexpected parameters: bogus' in cm.exception.reason)

    def test_put_attribute_mismatch(self):
        json, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com'
            '/config/reply_to_address')
        self.assertEqual(json['reply_to_address'], '')
        with self.assertRaises(HTTPError) as cm:
            json, response = call_api(
                'http://localhost:9001/3.0/lists/ant.example.com'
                '/config/reply_to_address',
                dict(display_name='bar@ant.example.com'),
                'PUT')
        self.assertEqual(cm.exception.code, 400)
        self.assertTrue(
            'Unexpected parameters: display_name' in cm.exception.reason)

    def test_put_attribute_double(self):
        with self.assertRaises(HTTPError) as cm:
            resource, response = call_api(
                'http://localhost:9001/3.0/lists/ant.example.com'
                '/config/reply_to_address',
                dict(display_name='bar@ant.example.com',
                     reply_to_address='foo@example.com'),
                'PUT')
        self.assertEqual(cm.exception.code, 400)
        self.assertTrue(
            'Unexpected parameters: display_name' in cm.exception.reason)

    def test_put_read_only_attribute(self):
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/ant.example.com'
                     '/config/mail_host',
                     dict(mail_host='foo.example.com'),
                     'PUT')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason, 'Read-only attribute: mail_host')

    def test_put_missing_attribute(self):
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config/bogus',
                dict(bogus='no matter'),
                'PUT')
        self.assertEqual(cm.exception.code, 404)
        self.assertTrue('Unknown attribute: bogus' in cm.exception.reason)

    def test_patch_subscription_policy(self):
        # The new subscription_policy value can be patched.
        #
        # To start with, the subscription policy is confirm by default.
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config')
        self.assertEqual(resource['subscription_policy'], 'confirm')
        # Let's patch it to do some moderation.
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config', dict(
                subscription_policy='confirm_then_moderate'),
            method='PATCH')
        self.assertEqual(response.status_code, 204)
        # And now we verify that it has the requested setting.
        self.assertEqual(self._mlist.subscription_policy,
                         SubscriptionPolicy.confirm_then_moderate)

    def test_patch_attribute_double(self):
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com'
                '/config/reply_to_address',
                dict(display_name='bar@ant.example.com',
                     reply_to_address='foo'),
                'PATCH')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason, 'Expected 1 attribute, got 2')

    def test_unknown_patch_attribute(self):
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/ant.example.com/config',
                     dict(bogus=1),
                     'PATCH')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason, 'Unknown attribute: bogus')

    def test_read_only_patch_attribute(self):
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/ant.example.com'
                     '/config/mail_host',
                     dict(mail_host='foo.example.com'),
                     'PATCH')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason, 'Read-only attribute: mail_host')

    def test_patch_missing_attribute(self):
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config/bogus',
                dict(bogus='no matter'),
                'PATCH')
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.reason, 'Unknown attribute: bogus')

    def test_patch_bad_value(self):
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config'
                '/archive_policy',
                dict(archive_policy='not a valid archive policy'),
                'PATCH')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(
            cm.exception.reason,
            'Invalid Parameter "archive_policy": Accepted Values are:'
            ' never, private, public.')

    def test_patch_with_json_boolean(self):
        # Ensure we can patch with JSON boolean value.
        with transaction():
            self._mlist.gateway_to_mail = False
        response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config',
            method='PATCH', headers={'Content-Type': 'application/json'},
            json={'gateway_to_mail': True})
        self.assertEqual(response[1].status_code, 204)
        self.assertTrue(self._mlist.gateway_to_mail)

    def test_bad_pipeline_name(self):
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config'
                '/posting_pipeline',
                dict(posting_pipeline='not a valid pipeline'),
                'PATCH')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(
            cm.exception.reason,
            'Invalid Parameter "posting_pipeline": Unknown pipeline: not a valid pipeline.')  # noqa: E501

    def test_get_digest_send_periodic(self):
        with transaction():
            self._mlist.digest_send_periodic = False
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/digest_send_periodic')
        self.assertFalse(resource['digest_send_periodic'])

    def test_patch_digest_send_periodic(self):
        with transaction():
            self._mlist.digest_send_periodic = False
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/digest_send_periodic',
            dict(digest_send_periodic=True),
            'PATCH')
        self.assertEqual(response.status_code, 204)
        self.assertTrue(self._mlist.digest_send_periodic)

    def test_put_digest_send_periodic(self):
        with transaction():
            self._mlist.digest_send_periodic = False
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/digest_send_periodic',
            dict(digest_send_periodic=True),
            'PUT')
        self.assertEqual(response.status_code, 204)
        self.assertTrue(self._mlist.digest_send_periodic)

    def test_get_digest_volume_frequency(self):
        with transaction():
            self._mlist.digest_volume_frequency = DigestFrequency.yearly
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/digest_volume_frequency')
        self.assertEqual(resource['digest_volume_frequency'], 'yearly')

    def test_patch_digest_volume_frequency(self):
        with transaction():
            self._mlist.digest_volume_frequency = DigestFrequency.yearly
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/digest_volume_frequency',
            dict(digest_volume_frequency='monthly'),
            'PATCH')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self._mlist.digest_volume_frequency,
                         DigestFrequency.monthly)

    def test_put_digest_volume_frequency(self):
        with transaction():
            self._mlist.digest_volume_frequency = DigestFrequency.yearly
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/digest_volume_frequency',
            dict(digest_volume_frequency='monthly'),
            'PUT')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self._mlist.digest_volume_frequency,
                         DigestFrequency.monthly)

    def test_bad_patch_digest_volume_frequency(self):
        with transaction():
            self._mlist.digest_volume_frequency = DigestFrequency.yearly
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config'
                '/digest_volume_frequency',
                dict(digest_volume_frequency='once in a while'),
                'PATCH')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(
            cm.exception.reason,
            'Invalid Parameter "digest_volume_frequency": Accepted Values are:'
            ' yearly, monthly, quarterly, weekly, daily.')

    def test_bad_put_digest_volume_frequency(self):
        with transaction():
            self._mlist.digest_volume_frequency = DigestFrequency.yearly
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config'
                '/digest_volume_frequency',
                dict(digest_volume_frequency='once in a while'),
                'PUT')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(
            cm.exception.reason,
            'Invalid Parameter "digest_volume_frequency": Accepted Values are:'
            ' yearly, monthly, quarterly, weekly, daily.')

    def test_get_digests_enabled(self):
        with transaction():
            self._mlist.digests_enabled = False
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/digests_enabled')
        self.assertFalse(resource['digests_enabled'])

    def test_patch_digests_enabled(self):
        with transaction():
            self._mlist.digests_enabled = False
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/digests_enabled',
            dict(digests_enabled=True),
            'PATCH')
        self.assertEqual(response.status_code, 204)
        self.assertTrue(self._mlist.digests_enabled)

    def test_put_digests_enabled(self):
        with transaction():
            self._mlist.digests_enabled = False
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/digests_enabled',
            dict(digests_enabled=True),
            'PUT')
        self.assertEqual(response.status_code, 204)
        self.assertTrue(self._mlist.digests_enabled)

    def test_get_goodbye_message_uri(self):
        with transaction():
            getUtility(ITemplateManager).set(
                'list:user:notice:goodbye', self._mlist.list_id,
                'mailman:///goodbye.txt')
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/goodbye_message_uri')
        self.assertEqual(
            resource['goodbye_message_uri'], 'mailman:///goodbye.txt')

    def test_patch_goodbye_message_uri_parent(self):
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config',
            dict(goodbye_message_uri='mailman:///salutation.txt'),
            'PATCH')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            getUtility(ITemplateManager).raw(
                'list:user:notice:goodbye', self._mlist.list_id).uri,
            'mailman:///salutation.txt')

    def test_patch_goodbye_message_uri(self):
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/goodbye_message_uri',
            dict(goodbye_message_uri='mailman:///salutation.txt'),
            'PATCH')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            getUtility(ITemplateManager).raw(
                'list:user:notice:goodbye', self._mlist.list_id).uri,
            'mailman:///salutation.txt')

    def test_put_goodbye_message_uri(self):
        manager = getUtility(ITemplateManager)
        with transaction():
            manager.set(
                'list:user:notice:goodbye',
                self._mlist.list_id,
                'mailman:///somefile.txt')
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/goodbye_message_uri',
            dict(goodbye_message_uri='mailman:///salutation.txt'),
            'PUT')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            manager.raw('list:user:notice:goodbye', self._mlist.list_id).uri,
            'mailman:///salutation.txt')

    def test_advertised(self):
        # GL issue #220 claimed advertised was read-only.
        with transaction():
            self._mlist.advertised = False
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/advertised')
        self.assertFalse(resource['advertised'])
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config',
            dict(advertised=True),
            'PATCH')
        self.assertTrue(self._mlist.advertised)

    def test_patch_bad_description_value(self):
        # Do not accept multiline descriptions.  GL#273
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config'
                '/description',
                dict(description='This\ncontains\nnewlines.'),
                'PATCH')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(
            cm.exception.reason,
            'Invalid Parameter "description":'
            ' This value must be a single line: This\ncontains\nnewlines..')

    def test_patch_info(self):
        with transaction():
            resource, response = call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config',
                dict(info='multiline\ntest\nvalue'),
                'PATCH')
            self.assertEqual(self._mlist.info, 'multiline\ntest\nvalue')
        # Now empty it
        with transaction():
            resource, response = call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/config',
                dict(info=''),
                'PATCH')
            self.assertEqual(self._mlist.info, '')

    def test_patch_send_welcome_message(self):
        with transaction():
            self._mlist.send_welcome_message = False
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/send_welcome_message',
            dict(send_welcome_message=True),
            'PATCH')
        self.assertEqual(response.status_code, 204)
        self.assertTrue(self._mlist.send_welcome_message)

    def test_patch_send_goodbye_message(self):
        with transaction():
            self._mlist.send_goodbye_message = False
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/ant.example.com/config'
            '/send_goodbye_message',
            dict(send_goodbye_message=True),
            'PATCH')
        self.assertEqual(response.status_code, 204)
        self.assertTrue(self._mlist.send_goodbye_message)

    def test_delete_top_level_listconf(self):
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/ant.example.com/config',
                     method='DELETE')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason,
                         'Cannot delete the list configuration itself')

    def test_delete_read_only_attribute(self):
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/'
                'config/post_id',
                method='DELETE')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason,
                         'Read-only attribute: post_id')

    def test_delete_undeletable_attribute(self):
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant.example.com/'
                'config/administrivia',
                method='DELETE')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason,
                         'Attribute cannot be DELETEd: administrivia')
