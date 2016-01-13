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

"""REST web service API context."""

__all__ = [
    'IAPI',
    ]


from zope.interface import Attribute, Interface


class IAPI(Interface):
    """The REST web service context."""

    version = Attribute("""The REST API version.""")

    def from_uuid(uuid):
        """Return the string representation of a UUID."""

    def to_uuid(uuid_repr):
        """Return the UUID from the string representation."""
