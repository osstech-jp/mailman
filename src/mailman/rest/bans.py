# Copyright (C) 2015 by the Free Software Foundation, Inc.
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

"""REST for banned emails."""

__all__ = [
    'BannedEmail',
    'BannedEmails',
    ]


from mailman.interfaces.bans import IBanManager
from mailman.rest.helpers import (
    CollectionMixin, bad_request, child, created, etag, no_content, not_found,
    okay, path_to)
from mailman.rest.validator import Validator



class _BannedBase:
    """Common base class."""

    def __init__(self, mailing_list):
        self._mlist = mailing_list
        self.ban_manager = IBanManager(self._mlist)

    def _location(self, email):
        if self._mlist is None:
            base_location = ''
        else:
            base_location = 'lists/{}/'.format(self._mlist.list_id)
        return path_to(
            '{}bans/{}'.format(base_location, email), self.api_version)


class BannedEmail(_BannedBase):
    """A banned email."""

    def __init__(self, mailing_list, email):
        super().__init__(mailing_list)
        self._email = email

    def on_get(self, request, response):
        """Get a banned email."""
        if self._email is None:
            bad_request(response, 'Invalid email')
        elif not self.ban_manager.is_banned(self._email):
            not_found(
                response, 'Email {} is not banned'.format(self._email))
        else:
            resource = dict(
                email=self._email,
                list_id=self._mlist.list_id if self._mlist else None,
                self_link=self._location(self._email),
                )
            okay(response, etag(resource))

    def on_delete(self, request, response):
        """Remove an email from the ban list."""
        if self._email is None:
            bad_request(response, 'Invalid email')
        elif not self.ban_manager.is_banned(self._email):
            bad_request(
                response, 'Email {} is not banned'.format(self._email))
        else:
            self.ban_manager.unban(self._email)
            no_content(response)


class BannedEmails(_BannedBase, CollectionMixin):
    """The list of all banned emails."""

    def _resource_as_dict(self, ban):
        """See `CollectionMixin`."""
        return dict(
            email=ban.email,
            list_id=ban.list_id,
            self_link=self._location(ban.email),
            )

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(self.ban_manager)

    def on_get(self, request, response):
        """/bans"""
        resource = self._make_collection(request)
        okay(response, etag(resource))

    def on_post(self, request, response):
        """Ban some email from subscribing."""
        validator = Validator(email=str)
        try:
            email = validator(request)['email']
        except ValueError as error:
            bad_request(response, str(error))
            return
        if self.ban_manager.is_banned(email):
            bad_request(response, b'Address is already banned')
        else:
            self.ban_manager.ban(email)
            created(response, self._location(email))

    @child(r'^(?P<email>[^/]+)')
    def email(self, request, segments, **kw):
        return BannedEmail(self._mlist, kw['email'])
