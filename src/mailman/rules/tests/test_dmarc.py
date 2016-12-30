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

"""Provides support for mocking dnspython calls from dmarc rules and some
organizational domain tests."""

from contextlib import ExitStack
from dns.rdatatype import TXT
from dns.resolver import NXDOMAIN, NoAnswer
from mailman.app.lifecycle import create_list
from mailman.interfaces.mailinglist import DMARCMitigateAction
from mailman.rules import dmarc
from mailman.testing.helpers import (
    LogFileMark, specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer
from public import public
from unittest import TestCase
from unittest.mock import patch
from urllib.error import URLError


@public
def get_dns_resolver():
    """Create a dns.resolver.Resolver mock.

    This is used to return a predictable response to a _dmarc query.  It
    returns p=reject for the example.biz domain and raises either NXDOMAIN
    or NoAnswer for any other.

    It only implements those classes and attributes used by the dmarc rule.
    """
    class Name:
        # mock answer.name
        def __init__(self):
            pass

        def to_text(self):
            return '_dmarc.example.biz.'

    class Item:
        # mock answer.items
        def __init__(self):
            self.strings = [b'v=DMARC1; p=reject;']

    class Ans_e:
        # mock answer element
        def __init__(self):
            self.rdtype = TXT
            self.items = [Item()]
            self.name = Name()

    class Answer:
        # mock answer
        def __init__(self):
            self.answer = [Ans_e()]

    class Resolver:
        # mock dns.resolver.Resolver class.
        def __init__(self):
            pass

        def query(self, domain, data_type):
            if data_type != TXT:
                raise NoAnswer
            dparts = domain.split('.')
            if len(dparts) < 3:
                raise NXDOMAIN
            if len(dparts) > 3:
                raise NoAnswer
            if dparts[0] != '_dmarc':
                raise NoAnswer
            if dparts[1] != 'example' or dparts[2] != 'biz':
                raise NXDOMAIN
            self.response = Answer()
            return self
    patcher = patch('dns.resolver.Resolver', Resolver)
    return patcher


class TestDMARCRules(TestCase):
    """Test organizational domain determination."""

    layer = ConfigLayer

    def setUp(self):
        self.resources = ExitStack()
        self.addCleanup(self.resources.close)
        # Make sure every test has a clean cache.
        self.cache = {}
        self.resources.enter_context(
            patch('mailman.rules.dmarc.s_dict', self.cache))

    def test_no_url(self):
        dmarc._get_suffixes(None)
        self.assertEqual(len(self.cache), 0)

    def test_no_data_for_domain(self):
        self.assertEqual(
            dmarc._get_org_dom('sub.dom.example.nxtld'),
            'example.nxtld')

    def test_domain_with_wild_card(self):
        self.assertEqual(
            dmarc._get_org_dom('ssub.sub.foo.kobe.jp'),
            'sub.foo.kobe.jp')

    def test_exception_to_wild_card(self):
        self.assertEqual(
            dmarc._get_org_dom('ssub.sub.city.kobe.jp'),
            'city.kobe.jp')

    def test_no_publicsuffix_dot_org(self):
        mark = LogFileMark('mailman.error')
        with patch('mailman.rules.dmarc.request.urlopen',
                   side_effect=URLError('no internet')):
            domain = dmarc._get_org_dom('ssub.sub.city.kobe.jp')
        line = mark.readline()
        self.assertEqual(
            line[-95:],
            'Unable to retrieve data from '
            'https://publicsuffix.org/list/public_suffix_list.dat: '
            'no internet\n')
        self.assertEqual(domain, 'kobe.jp')

    def test_no_at_sign_in_from_address(self):
        # If there's no @ sign in the From: address, the rule can't hit.
        mlist = create_list('ant@example.com')
        mlist.dmarc_mitigate_action = DMARCMitigateAction.munge_from
        msg = mfs("""\
From: anne
To: ant@example.com

""")
        rule = dmarc.DMARCMitigation()
        self.assertFalse(rule.check(mlist, msg, {}))
