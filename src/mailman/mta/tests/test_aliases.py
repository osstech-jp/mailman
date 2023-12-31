# Copyright (C) 2011-2023 by the Free Software Foundation, Inc.
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

"""Test the MTA file generating utility."""

import os
import shutil
import tempfile
import unittest

from mailman.app.lifecycle import create_list
from mailman.interfaces.domain import IDomainManager
from mailman.interfaces.mta import IMailTransportAgentAliases
from mailman.mta.postfix import LMTP
from mailman.testing.layers import ConfigLayer
from zope.component import getUtility


NL = '\n'


def _strip_header(contents):
    lines = contents.splitlines()
    return NL.join(lines[7:])


class TestAliases(unittest.TestCase):

    layer = ConfigLayer

    def setUp(self):
        self.utility = getUtility(IMailTransportAgentAliases)
        self.mlist = create_list('test@example.com')

    def test_posting_address_first(self):
        # The posting address is always first.
        aliases = list(self.utility.aliases(self.mlist))
        self.assertEqual(aliases[0], self.mlist.posting_address)

    def test_aliases(self):
        # The aliases are the fully qualified email addresses.
        aliases = list(self.utility.aliases(self.mlist))
        self.assertEqual(aliases, [
            'test@example.com',
            'test-bounces@example.com',
            'test-confirm@example.com',
            'test-join@example.com',
            'test-leave@example.com',
            'test-owner@example.com',
            'test-request@example.com',
            'test-subscribe@example.com',
            'test-unsubscribe@example.com',
            ])

    def test_destinations(self):
        # The destinations are just the local part.
        destinations = list(self.utility.destinations(self.mlist))
        self.assertEqual(destinations, [
            'test',
            'test-bounces',
            'test-confirm',
            'test-join',
            'test-leave',
            'test-owner',
            'test-request',
            'test-subscribe',
            'test-unsubscribe',
            ])

    def test_duck_typed_aliases(self):
        # Test the .aliases() method with duck typed arguments.
        class Duck:
            def __init__(self, list_name, mail_host):
                self.list_name = list_name
                self.mail_host = mail_host
                self.posting_address = '{}@{}'.format(list_name, mail_host)
        duck_list = Duck('sample', 'example.net')
        aliases = list(self.utility.aliases(duck_list))
        self.assertEqual(aliases, [
            'sample@example.net',
            'sample-bounces@example.net',
            'sample-confirm@example.net',
            'sample-join@example.net',
            'sample-leave@example.net',
            'sample-owner@example.net',
            'sample-request@example.net',
            'sample-subscribe@example.net',
            'sample-unsubscribe@example.net',
            ])

    def test_duck_typed_destinations(self):
        # Test the .destinations() method with duck typed arguments.
        class Duck:
            def __init__(self, list_name):
                self.list_name = list_name
        duck_list = Duck('sample')
        destinations = list(self.utility.destinations(duck_list))
        self.assertEqual(destinations, [
            'sample',
            'sample-bounces',
            'sample-confirm',
            'sample-join',
            'sample-leave',
            'sample-owner',
            'sample-request',
            'sample-subscribe',
            'sample-unsubscribe',
            ])


class TestPostfix(unittest.TestCase):
    """Test the Postfix LMTP alias generator."""

    layer = ConfigLayer

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)
        self.utility = getUtility(IMailTransportAgentAliases)
        self.mlist = create_list('test@example.com')
        self.postfix = LMTP()
        # Let assertMultiLineEqual work without bounds.
        self.maxDiff = None

    def test_aliases(self):
        # Test the format of the Postfix alias generator.
        self.postfix.regenerate(self.tempdir)
        # There are two files in this directory.
        self.assertEqual(sorted(os.listdir(self.tempdir)),
                         ['postfix_domains', 'postfix_lmtp'])
        # The domains file, just contains the example.com domain.  We have to
        # ignore the file header.
        with open(os.path.join(self.tempdir, 'postfix_domains')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
example.com example.com
""")
        # The lmtp file contains transport mappings to the lmtp server.
        with open(os.path.join(self.tempdir, 'postfix_lmtp')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Aliases which are visible only in the @example.com domain.
test@example.com                       lmtp:[127.0.0.1]:9024
test-bounces@example.com               lmtp:[127.0.0.1]:9024
test-confirm@example.com               lmtp:[127.0.0.1]:9024
test-join@example.com                  lmtp:[127.0.0.1]:9024
test-leave@example.com                 lmtp:[127.0.0.1]:9024
test-owner@example.com                 lmtp:[127.0.0.1]:9024
test-request@example.com               lmtp:[127.0.0.1]:9024
test-subscribe@example.com             lmtp:[127.0.0.1]:9024
test-unsubscribe@example.com           lmtp:[127.0.0.1]:9024
""")

    def test_two_lists(self):
        # Both lists need to show up in the aliases file.  LP: #874929.
        # Create a second list.
        create_list('other@example.com')
        self.postfix.regenerate(self.tempdir)
        # There are two files in this directory.
        self.assertEqual(sorted(os.listdir(self.tempdir)),
                         ['postfix_domains', 'postfix_lmtp'])
        # Because both lists are in the same domain, there should be only one
        # entry in the relays file.
        with open(os.path.join(self.tempdir, 'postfix_domains')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
example.com example.com
""")
        # The transport file contains entries for both lists.
        with open(os.path.join(self.tempdir, 'postfix_lmtp')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Aliases which are visible only in the @example.com domain.
other@example.com                       lmtp:[127.0.0.1]:9024
other-bounces@example.com               lmtp:[127.0.0.1]:9024
other-confirm@example.com               lmtp:[127.0.0.1]:9024
other-join@example.com                  lmtp:[127.0.0.1]:9024
other-leave@example.com                 lmtp:[127.0.0.1]:9024
other-owner@example.com                 lmtp:[127.0.0.1]:9024
other-request@example.com               lmtp:[127.0.0.1]:9024
other-subscribe@example.com             lmtp:[127.0.0.1]:9024
other-unsubscribe@example.com           lmtp:[127.0.0.1]:9024

test@example.com                       lmtp:[127.0.0.1]:9024
test-bounces@example.com               lmtp:[127.0.0.1]:9024
test-confirm@example.com               lmtp:[127.0.0.1]:9024
test-join@example.com                  lmtp:[127.0.0.1]:9024
test-leave@example.com                 lmtp:[127.0.0.1]:9024
test-owner@example.com                 lmtp:[127.0.0.1]:9024
test-request@example.com               lmtp:[127.0.0.1]:9024
test-subscribe@example.com             lmtp:[127.0.0.1]:9024
test-unsubscribe@example.com           lmtp:[127.0.0.1]:9024
""")

    def test_two_lists_two_domains(self):
        # Now we have two lists in two different domains.  Both lists will
        # show up in the postfix_lmtp file, and both domains will show up in
        # the postfix_domains file.
        getUtility(IDomainManager).add('example.net')
        create_list('other@example.net')
        self.postfix.regenerate(self.tempdir)
        # There are two files in this directory.
        self.assertEqual(sorted(os.listdir(self.tempdir)),
                         ['postfix_domains', 'postfix_lmtp'])
        # Because the lists are in different domains, there should be two
        # entries in the relays file.
        with open(os.path.join(self.tempdir, 'postfix_domains')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
example.com example.com
example.net example.net
""")
        # The transport file contains entries for both lists.
        with open(os.path.join(self.tempdir, 'postfix_lmtp')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Aliases which are visible only in the @example.com domain.
test@example.com                       lmtp:[127.0.0.1]:9024
test-bounces@example.com               lmtp:[127.0.0.1]:9024
test-confirm@example.com               lmtp:[127.0.0.1]:9024
test-join@example.com                  lmtp:[127.0.0.1]:9024
test-leave@example.com                 lmtp:[127.0.0.1]:9024
test-owner@example.com                 lmtp:[127.0.0.1]:9024
test-request@example.com               lmtp:[127.0.0.1]:9024
test-subscribe@example.com             lmtp:[127.0.0.1]:9024
test-unsubscribe@example.com           lmtp:[127.0.0.1]:9024

# Aliases which are visible only in the @example.net domain.
other@example.net                       lmtp:[127.0.0.1]:9024
other-bounces@example.net               lmtp:[127.0.0.1]:9024
other-confirm@example.net               lmtp:[127.0.0.1]:9024
other-join@example.net                  lmtp:[127.0.0.1]:9024
other-leave@example.net                 lmtp:[127.0.0.1]:9024
other-owner@example.net                 lmtp:[127.0.0.1]:9024
other-request@example.net               lmtp:[127.0.0.1]:9024
other-subscribe@example.net             lmtp:[127.0.0.1]:9024
other-unsubscribe@example.net           lmtp:[127.0.0.1]:9024
""")

    def test_missing_postmap_command_raises_runtime_errorr(self):
        # Changing the postmap command to false will always
        # return a non-zero exit code.
        self.postfix.postmap_command = 'false'
        # Generating postmap hash files will raise a runtimerror.
        with self.assertRaises(RuntimeError):
            self.postfix.regenerate(self.tempdir)
        # Now change the command back to true will make the
        # command run normally.
        self.postfix.postmap_command = 'true'
        self.postfix.regenerate(self.tempdir)
        # There should be two files in the tempdir.
        self.assertEqual(sorted(os.listdir(self.tempdir)),
                         ['postfix_domains', 'postfix_lmtp'])

    def test_aliases_regex(self):
        # Test aliases generation for regex maps for postfix.
        # Set the transport map type to regex.
        self.postfix.transport_file_type = 'regex'
        self.postfix.regenerate(self.tempdir)
        # The domains file just contains the example.com domain.
        with open(os.path.join(self.tempdir, 'postfix_domains')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
/^example\\.com$/ example.com
""")
        # the    lmtp file contains transport mapping to the lmtp server.
        with open(os.path.join(self.tempdir, 'postfix_lmtp')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Aliases which are visible only in the @example.com domain.
/^test@example\\.com$/                  lmtp:[127.0.0.1]:9024
/^test-bounces(\\+.*)?@example\\.com$/   lmtp:[127.0.0.1]:9024
/^test-confirm(\\+.*)?@example\\.com$/   lmtp:[127.0.0.1]:9024
/^test-join@example\\.com$/             lmtp:[127.0.0.1]:9024
/^test-leave@example\\.com$/            lmtp:[127.0.0.1]:9024
/^test-owner@example\\.com$/            lmtp:[127.0.0.1]:9024
/^test-request@example\\.com$/          lmtp:[127.0.0.1]:9024
/^test-subscribe@example\\.com$/        lmtp:[127.0.0.1]:9024
/^test-unsubscribe@example\\.com$/      lmtp:[127.0.0.1]:9024
""")

    def test_aliases_regex_with_dots(self):
        # Test regex is generated for listnames with multiple dots.
        self.postfix.transport_file_type = 'regex'
        create_list('test.list.name.dots@example.com')
        self.postfix.regenerate(self.tempdir)
        with open(os.path.join(self.tempdir, 'postfix_domains')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
/^example\\.com$/ example.com
""")
        with open(os.path.join(self.tempdir, 'postfix_lmtp')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Aliases which are visible only in the @example.com domain.
/^test@example\\.com$/                  lmtp:[127.0.0.1]:9024
/^test-bounces(\\+.*)?@example\\.com$/   lmtp:[127.0.0.1]:9024
/^test-confirm(\\+.*)?@example\\.com$/   lmtp:[127.0.0.1]:9024
/^test-join@example\\.com$/             lmtp:[127.0.0.1]:9024
/^test-leave@example\\.com$/            lmtp:[127.0.0.1]:9024
/^test-owner@example\\.com$/            lmtp:[127.0.0.1]:9024
/^test-request@example\\.com$/          lmtp:[127.0.0.1]:9024
/^test-subscribe@example\\.com$/        lmtp:[127.0.0.1]:9024
/^test-unsubscribe@example\\.com$/      lmtp:[127.0.0.1]:9024

/^test\\.list\\.name\\.dots@example\\.com$/\
                  lmtp:[127.0.0.1]:9024
/^test\\.list\\.name\\.dots-bounces(\\+.*)?@example\\.com$/\
   lmtp:[127.0.0.1]:9024
/^test\\.list\\.name\\.dots-confirm(\\+.*)?@example\\.com$/\
   lmtp:[127.0.0.1]:9024
/^test\\.list\\.name\\.dots-join@example\\.com$/\
             lmtp:[127.0.0.1]:9024
/^test\\.list\\.name\\.dots-leave@example\\.com$/\
            lmtp:[127.0.0.1]:9024
/^test\\.list\\.name\\.dots-owner@example\\.com$/\
            lmtp:[127.0.0.1]:9024
/^test\\.list\\.name\\.dots-request@example\\.com$/\
          lmtp:[127.0.0.1]:9024
/^test\\.list\\.name\\.dots-subscribe@example\\.com$/\
        lmtp:[127.0.0.1]:9024
/^test\\.list\\.name\\.dots-unsubscribe@example\\.com$/\
      lmtp:[127.0.0.1]:9024
""")

    def test_three_lists_three_domains_with_one_alias_domain(self):
        # Now we have three lists in three different domains.  All lists will
        # show up in the postfix_lmtp file, and both domains will show up in
        # the postfix_domains file.  One domain has an alias_domain so there
        # will also be a postfix_vmap file with mappings from the email_domain
        # to the alias_domain for the list in that domain and entries for the
        # alias_domain in the other files.
        getUtility(IDomainManager).add('example.net')
        create_list('other@example.net')
        getUtility(IDomainManager).add(
            'example.org', alias_domain='x.example.org')
        create_list('third@example.org')
        self.postfix.regenerate(self.tempdir)
        # There are three files in this directory.
        self.assertEqual(sorted(os.listdir(self.tempdir)),
                         ['postfix_domains', 'postfix_lmtp', 'postfix_vmap'])
        # Because the lists are in different domains, there should be three
        # entries in the relays file.
        with open(os.path.join(self.tempdir, 'postfix_domains')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
example.com example.com
example.net example.net
x.example.org example.org
""")
        # The transport file contains entries for all three lists.
        with open(os.path.join(self.tempdir, 'postfix_lmtp')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Aliases which are visible only in the @example.com domain.
test@example.com                       lmtp:[127.0.0.1]:9024
test-bounces@example.com               lmtp:[127.0.0.1]:9024
test-confirm@example.com               lmtp:[127.0.0.1]:9024
test-join@example.com                  lmtp:[127.0.0.1]:9024
test-leave@example.com                 lmtp:[127.0.0.1]:9024
test-owner@example.com                 lmtp:[127.0.0.1]:9024
test-request@example.com               lmtp:[127.0.0.1]:9024
test-subscribe@example.com             lmtp:[127.0.0.1]:9024
test-unsubscribe@example.com           lmtp:[127.0.0.1]:9024

# Aliases which are visible only in the @example.net domain.
other@example.net                       lmtp:[127.0.0.1]:9024
other-bounces@example.net               lmtp:[127.0.0.1]:9024
other-confirm@example.net               lmtp:[127.0.0.1]:9024
other-join@example.net                  lmtp:[127.0.0.1]:9024
other-leave@example.net                 lmtp:[127.0.0.1]:9024
other-owner@example.net                 lmtp:[127.0.0.1]:9024
other-request@example.net               lmtp:[127.0.0.1]:9024
other-subscribe@example.net             lmtp:[127.0.0.1]:9024
other-unsubscribe@example.net           lmtp:[127.0.0.1]:9024

# Aliases which are visible only in the @x.example.org domain.
third@x.example.org                        lmtp:[127.0.0.1]:9024
third-bounces@x.example.org                lmtp:[127.0.0.1]:9024
third-confirm@x.example.org                lmtp:[127.0.0.1]:9024
third-join@x.example.org                   lmtp:[127.0.0.1]:9024
third-leave@x.example.org                  lmtp:[127.0.0.1]:9024
third-owner@x.example.org                  lmtp:[127.0.0.1]:9024
third-request@x.example.org                lmtp:[127.0.0.1]:9024
third-subscribe@x.example.org              lmtp:[127.0.0.1]:9024
third-unsubscribe@x.example.org            lmtp:[127.0.0.1]:9024
""")
        # The virtual mapping contains only entries for the list with an
        # alias_domain.
        with open(os.path.join(self.tempdir, 'postfix_vmap')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Virtual mappings for the @example.org domain.
third@example.org                         third@x.example.org
third-bounces@example.org                 third-bounces@x.example.org
third-confirm@example.org                 third-confirm@x.example.org
third-join@example.org                    third-join@x.example.org
third-leave@example.org                   third-leave@x.example.org
third-owner@example.org                   third-owner@x.example.org
third-request@example.org                 third-request@x.example.org
third-subscribe@example.org               third-subscribe@x.example.org
third-unsubscribe@example.org             third-unsubscribe@x.example.org
""")

    def test_vmap_regex(self):
        # Test alias domain virtual mapping with regex.
        self.postfix.transport_file_type = 'regex'
        getUtility(IDomainManager).add(
            'example.org', alias_domain='x.example.org')
        create_list('other@example.org')
        self.postfix.regenerate(self.tempdir)
        # There are three files in this directory.
        self.assertEqual(sorted(os.listdir(self.tempdir)),
                         ['postfix_domains', 'postfix_lmtp', 'postfix_vmap'])
        # Because the lists are in different domains, there should be two
        # entries in the relays file.
        with open(os.path.join(self.tempdir, 'postfix_domains')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
/^example\\.com$/ example.com
/^x\\.example\\.org$/ example.org
""")
        # The transport file contains entries for both lists.
        with open(os.path.join(self.tempdir, 'postfix_lmtp')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Aliases which are visible only in the @example.com domain.
/^test@example\\.com$/                  lmtp:[127.0.0.1]:9024
/^test-bounces(\\+.*)?@example\\.com$/   lmtp:[127.0.0.1]:9024
/^test-confirm(\\+.*)?@example\\.com$/   lmtp:[127.0.0.1]:9024
/^test-join@example\\.com$/             lmtp:[127.0.0.1]:9024
/^test-leave@example\\.com$/            lmtp:[127.0.0.1]:9024
/^test-owner@example\\.com$/            lmtp:[127.0.0.1]:9024
/^test-request@example\\.com$/          lmtp:[127.0.0.1]:9024
/^test-subscribe@example\\.com$/        lmtp:[127.0.0.1]:9024
/^test-unsubscribe@example\\.com$/      lmtp:[127.0.0.1]:9024

# Aliases which are visible only in the @x.example.org domain.
/^other@x\\.example\\.org$/                  lmtp:[127.0.0.1]:9024
/^other-bounces(\\+.*)?@x\\.example\\.org$/   lmtp:[127.0.0.1]:9024
/^other-confirm(\\+.*)?@x\\.example\\.org$/   lmtp:[127.0.0.1]:9024
/^other-join@x\\.example\\.org$/             lmtp:[127.0.0.1]:9024
/^other-leave@x\\.example\\.org$/            lmtp:[127.0.0.1]:9024
/^other-owner@x\\.example\\.org$/            lmtp:[127.0.0.1]:9024
/^other-request@x\\.example\\.org$/          lmtp:[127.0.0.1]:9024
/^other-subscribe@x\\.example\\.org$/        lmtp:[127.0.0.1]:9024
/^other-unsubscribe@x\\.example\\.org$/      lmtp:[127.0.0.1]:9024
""")
        # The virtual mapping contains only entries for the list with an
        # alias_domain.
        with open(os.path.join(self.tempdir, 'postfix_vmap')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Virtual mappings for the @example.org domain.
/^other@example\\.org$/                    other@x.example.org
/^other-bounces(\\+.*)?@example\\.org$/     other-bounces@x.example.org
/^other-confirm(\\+.*)?@example\\.org$/     other-confirm@x.example.org
/^other-join@example\\.org$/               other-join@x.example.org
/^other-leave@example\\.org$/              other-leave@x.example.org
/^other-owner@example\\.org$/              other-owner@x.example.org
/^other-request@example\\.org$/            other-request@x.example.org
/^other-subscribe@example\\.org$/          other-subscribe@x.example.org
/^other-unsubscribe@example\\.org$/        other-unsubscribe@x.example.org
""")

    def test_long_list_names(self):
        getUtility(IDomainManager).add('grups.mailsandbox.xxxxxx.org',
                                       alias_domain='mail-ng.xxxxxx.org')
        create_list('llista1@grups.mailsandbox.xxxxxx.org')
        self.postfix.regenerate(self.tempdir)
        # There are three files in this directory.
        self.assertEqual(sorted(os.listdir(self.tempdir)),
                         ['postfix_domains', 'postfix_lmtp', 'postfix_vmap'])
        # Make sure vmap files has two columns instead of one overflowing and
        # merging to other.
        with open(os.path.join(self.tempdir, 'postfix_vmap')) as fp:
            contents = _strip_header(fp.read())
        self.assertMultiLineEqual(contents, """\
# Virtual mappings for the @grups.mailsandbox.xxxxxx.org domain.
llista1@grups.mailsandbox.xxxxxx.org                         llista1@mail-ng.xxxxxx.org
llista1-bounces@grups.mailsandbox.xxxxxx.org                 llista1-bounces@mail-ng.xxxxxx.org
llista1-confirm@grups.mailsandbox.xxxxxx.org                 llista1-confirm@mail-ng.xxxxxx.org
llista1-join@grups.mailsandbox.xxxxxx.org                    llista1-join@mail-ng.xxxxxx.org
llista1-leave@grups.mailsandbox.xxxxxx.org                   llista1-leave@mail-ng.xxxxxx.org
llista1-owner@grups.mailsandbox.xxxxxx.org                   llista1-owner@mail-ng.xxxxxx.org
llista1-request@grups.mailsandbox.xxxxxx.org                 llista1-request@mail-ng.xxxxxx.org
llista1-subscribe@grups.mailsandbox.xxxxxx.org               llista1-subscribe@mail-ng.xxxxxx.org
llista1-unsubscribe@grups.mailsandbox.xxxxxx.org             llista1-unsubscribe@mail-ng.xxxxxx.org
""")   # noqa: E501
