# Copyright (C) 2012-2016 by the Free Software Foundation, Inc.
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

"""Test the header chain."""

__all__ = [
    'TestHeaderChain',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.chains.headers import HeaderMatchRule, make_link
from mailman.config import config
from mailman.core.chains import process
from mailman.email.message import Message
from mailman.interfaces.chain import LinkAction, HoldEvent
from mailman.interfaces.mailinglist import IHeaderMatchSet
from mailman.testing.helpers import (
    LogFileMark, configuration, event_subscribers,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestHeaderChain(unittest.TestCase):
    """Test the header chain code."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')

    def test_make_link(self):
        # Test that make_link() with no given chain creates a Link with a
        # deferred link action.
        link = make_link('Subject', '[tT]esting')
        self.assertEqual(link.rule.header, 'Subject')
        self.assertEqual(link.rule.pattern, '[tT]esting')
        self.assertEqual(link.action, LinkAction.defer)
        self.assertIsNone(link.chain)

    def test_make_link_with_chain(self):
        # Test that make_link() with a given chain creates a Link with a jump
        # action to the chain.
        link = make_link('Subject', '[tT]esting', 'accept')
        self.assertEqual(link.rule.header, 'Subject')
        self.assertEqual(link.rule.pattern, '[tT]esting')
        self.assertEqual(link.action, LinkAction.jump)
        self.assertEqual(link.chain, config.chains['accept'])

    @configuration('antispam', header_checks="""
    Foo: a+
    Bar: bb?
    """)
    def test_config_checks(self):
        # Test that the header-match chain has the header checks from the
        # configuration file.
        chain = config.chains['header-match']
        # The links are created dynamically; the rule names will all start
        # with the same prefix, but have a variable suffix.  The actions will
        # all be to jump to the named chain.  Do these checks now, while we
        # collect other useful information.
        post_checks = []
        saw_any_rule = False
        for link in chain.get_links(self._mlist, Message(), {}):
            if link.rule.name == 'any':
                saw_any_rule = True
                self.assertEqual(link.action, LinkAction.jump)
            elif saw_any_rule:
                raise AssertionError("'any' rule was not last")
            else:
                self.assertEqual(link.rule.name[:13], 'header-match-')
                self.assertEqual(link.action, LinkAction.defer)
                post_checks.append((link.rule.header, link.rule.pattern))
        self.assertListEqual(post_checks, [
            ('Foo', 'a+'),
            ('Bar', 'bb?'),
            ])

    @configuration('antispam', header_checks="""
    Foo: foo
    A-bad-line
    Bar: bar
    """)
    def test_bad_configuration_line(self):
        # Take a mark on the error log file.
        mark = LogFileMark('mailman.error')
        # A bad value in [antispam]header_checks should just get ignored, but
        # with an error message logged.
        chain = config.chains['header-match']
        # The links are created dynamically; the rule names will all start
        # with the same prefix, but have a variable suffix.  The actions will
        # all be to jump to the named chain.  Do these checks now, while we
        # collect other useful information.
        post_checks = []
        saw_any_rule = False
        for link in chain.get_links(self._mlist, Message(), {}):
            if link.rule.name == 'any':
                saw_any_rule = True
                self.assertEqual(link.action, LinkAction.jump)
            elif saw_any_rule:
                raise AssertionError("'any' rule was not last")
            else:
                self.assertEqual(link.rule.name[:13], 'header-match-')
                self.assertEqual(link.action, LinkAction.defer)
                post_checks.append((link.rule.header, link.rule.pattern))
        self.assertListEqual(post_checks, [
            ('Foo', 'foo'),
            ('Bar', 'bar'),
            ])
        # Check the error log.
        self.assertEqual(mark.readline()[-77:-1],
                         'Configuration error: [antispam]header_checks '
                         'contains bogus line: A-bad-line')

    def test_duplicate_header_match_rule(self):
        # 100% coverage: test an assertion in a corner case.
        #
        # Save the existing rules so they can be restored later.
        saved_rules = config.rules.copy()
        next_rule_name = 'header-match-{0:02}'.format(HeaderMatchRule._count)
        config.rules[next_rule_name] = object()
        try:
            self.assertRaises(AssertionError,
                              HeaderMatchRule, 'x-spam-score', '.*')
        finally:
            config.rules = saved_rules

    def test_list_rule(self):
        # Test that the header-match chain has the header checks from the
        # mailing-list configuration.
        chain = config.chains['header-match']
        header_matches = IHeaderMatchSet(self._mlist)
        header_matches.add('Foo', 'a+')
        links = [link for link in chain.get_links(self._mlist, Message(), {})
                 if link.rule.name != 'any']
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].action, LinkAction.defer)
        self.assertEqual(links[0].rule.header, 'foo')
        self.assertEqual(links[0].rule.pattern, 'a+')

    def test_list_complex_rule(self):
        # Test that the mailing-list header-match complex rules are read
        # properly.
        chain = config.chains['header-match']
        header_matches = IHeaderMatchSet(self._mlist)
        header_matches.add('Foo', 'a+', 'reject')
        header_matches.add('Bar', 'b+', 'discard')
        header_matches.add('Baz', 'z+', 'accept')
        links = [link for link in chain.get_links(self._mlist, Message(), {})
                 if link.rule.name != 'any']
        self.assertEqual(len(links), 3)
        self.assertEqual([
            (link.rule.header, link.rule.pattern, link.action, link.chain.name)
            for link in links
            ],
            [('foo', 'a+', LinkAction.jump, 'reject'),
             ('bar', 'b+', LinkAction.jump, 'discard'),
             ('baz', 'z+', LinkAction.jump, 'accept'),
            ])

    @configuration('antispam', header_checks="""
    Foo: foo
    """, jump_chain='hold')
    def test_priority_site_over_list(self):
        # Test that the site-wide checks take precedence over the list-specific
        # checks.
        msg = mfs("""\
From: anne@example.com
To: test@example.com
Subject: A message
Message-ID: <ant>
Foo: foo
MIME-Version: 1.0

A message body.
""")
        msgdata = {}
        header_matches = IHeaderMatchSet(self._mlist)
        header_matches.add('Foo', 'foo', 'accept')
        # This event subscriber records the event that occurs when the message
        # is processed by the owner chain.
        events = []
        with event_subscribers(events.append):
            process(self._mlist, msg, msgdata, start_chain='header-match')
        self.assertEqual(len(events), 1)
        event = events[0]
        # Site-wide wants to hold the message, the list wants to accept it.
        self.assertTrue(isinstance(event, HoldEvent))
        self.assertEqual(event.chain, config.chains['hold'])
