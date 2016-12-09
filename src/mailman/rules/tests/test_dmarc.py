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

"""Support for mocking dnspython calls from dmarc rules."""

from dns.rdatatype import TXT
from dns.resolver import NXDOMAIN, NoAnswer
from public import public
from unittest import mock


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
    patcher = mock.patch('dns.resolver.Resolver', Resolver)
    return patcher
