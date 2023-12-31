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

"""REST for users."""

from functools import lru_cache
from lazr.config import as_boolean
from mailman.config import config
from mailman.interfaces.address import (
    ExistingAddressError,
    InvalidEmailAddressError,
)
from mailman.interfaces.usermanager import IUserManager
from mailman.rest.addresses import PreferredAddress, UserAddresses
from mailman.rest.helpers import (
    bad_request,
    BadRequest,
    child,
    CollectionMixin,
    conflict,
    created,
    etag,
    forbidden,
    GetterSetter,
    no_content,
    not_found,
    NotFound,
    okay,
)
from mailman.rest.preferences import Preferences
from mailman.rest.validator import (
    list_of_strings_validator,
    PatchValidator,
    ReadOnlyPATCHRequestError,
    UnknownPATCHRequestError,
    Validator,
)
from passlib.utils import generate_password as generate
from public import public
from zope.component import getUtility


# Attributes of a user which can be changed via the REST API.
@public
class PasswordEncrypterGetterSetter(GetterSetter):
    def __init__(self):
        super().__init__(config.password_context.encrypt)

    def get(self, obj, attribute):
        assert attribute == 'cleartext_password'
        super().get(obj, 'password')

    def put(self, obj, attribute, value):
        assert attribute == 'cleartext_password'
        super().put(obj, 'password', value)


@public
class ListOfDomainOwners(GetterSetter):
    def get(self, domain, attribute):
        assert attribute == 'owner', (
            'Unexpected attribute: {}'.format(attribute))
        def sort_key(owner):                                      # noqa: E306
            return owner.addresses[0].email
        return sorted(domain.owners, key=sort_key)

    def put(self, domain, attribute, value):
        assert attribute == 'owner', (
            'Unexpected attribute: {}'.format(attribute))
        domain.add_owners(value)


ATTRIBUTES = dict(
    cleartext_password=PasswordEncrypterGetterSetter(),
    display_name=GetterSetter(str),
    is_server_owner=GetterSetter(as_boolean),
    )


CREATION_FIELDS = dict(
    display_name=str,
    email=str,
    is_server_owner=as_boolean,
    password=str,
    _optional=('display_name', 'password', 'is_server_owner'),
    )


def create_user(api, arguments, response):
    """Create a new user."""
    # We can't pass the 'password' argument to the user creation method, so
    # strip that out (if it exists), then create the user, adding the password
    # after the fact if successful.
    password = arguments.pop('password', None)
    is_server_owner = arguments.pop('is_server_owner', False)
    user_manager = getUtility(IUserManager)
    try:
        user = user_manager.create_user(**arguments)
    except ExistingAddressError as error:
        # The address already exists.  If the address already has a user
        # linked to it, raise an error, otherwise create a new user and link
        # it to this address.
        email = arguments.pop('email')
        user = user_manager.get_user(email)
        if user is None:
            address = user_manager.get_address(email)
            user = user_manager.create_user(**arguments)
            user.link(address)
        else:
            bad_request(
                response,
                'User already exists: {}'.format(error.address).encode())
            return None
    if password is None:
        # This will have to be reset since it cannot be retrieved.
        password = generate(int(config.passwords.password_length))
    user.password = config.password_context.encrypt(password)
    user.is_server_owner = is_server_owner
    user_id = api.from_uuid(user.user_id)
    location = api.path_to('users/{}'.format(user_id))
    created(response, location)
    return user


class _UserBase(CollectionMixin):
    """Shared base class for user representations."""

    def _resource_as_dict(self, user):
        """See `CollectionMixin`."""
        # The canonical URL for a user is their unique user id, although we
        # can always look up a user based on any registered and validated
        # email address associated with their account.  The user id is a UUID,
        # but we serialize its integer equivalent.
        user_id = self.api.from_uuid(user.user_id)
        resource = dict(
            created_on=user.created_on,
            is_server_owner=user.is_server_owner,
            self_link=self.api.path_to('users/{}'.format(user_id)),
            user_id=user_id,
            )
        # Add the password attribute, only if the user has a password.  Same
        # with the real name.  These could be None or the empty string.
        if user.password:
            resource['password'] = user.password
        if user.display_name:
            resource['display_name'] = user.display_name
        return resource

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return getUtility(IUserManager).users


@public
class AllUsers(_UserBase):
    """The users."""

    def on_get(self, request, response):
        """/users"""
        resource = self._make_collection(request)
        okay(response, etag(resource))

    def on_post(self, request, response):
        """Create a new user."""
        try:
            validator = Validator(**CREATION_FIELDS)
            arguments = validator(request)
            create_user(self.api, arguments, response)
        except (ValueError, InvalidEmailAddressError) as error:
            error_message = 'Invalid email address {}'.format(error)
            bad_request(response, error_message)
            return


class _FoundUsers(_UserBase):
    def __init__(self, users, api):
        super().__init__()
        self._users = users
        self.api = api

    def _get_collection(self, request):
        return self._users


class FindUsers(_UserBase):

    def on_get(self, request, response):
        validator = Validator(q=str,
                              # Allow pagination.
                              page=int,
                              count=int,
                              _optional=('page', 'count'))
        try:
            data = validator(request)
        except ValueError as error:
            bad_request(response, str(error))
            return

        user_manager = getUtility(IUserManager)
        users = list(user_manager.find_users(data.get('q')))
        resource = _FoundUsers(users, self.api)
        try:
            collection = resource._make_collection(request)
        except ValueError as ex:
            bad_request(response, str(ex))
        else:
            okay(response, etag(collection))


@public
class AUser(_UserBase):
    """A user."""

    def __init__(self, user_identifier):
        """Get a user by various type of identifiers.

        :param user_identifier: The identifier used to retrieve the user.  The
            identifier may either be an email address controlled by the user
            or the UUID of the user.  The type of identifier is auto-detected
            by looking for an `@` symbol, in which case it's taken as an email
            address, otherwise it's assumed to be a UUID.  However, UUIDs in
            API 3.0 are integers, while in 3.1 are hex.
        :type user_identifier: string
        """
        self._user_identifier = user_identifier
        # Defer calculation of the user until the API object is set, since
        # that will determine how to interpret the user identifier.  For ease
        # of code migration, use an _user caching property (see below).

    @property
    @lru_cache(1)
    def _user(self):
        user_manager = getUtility(IUserManager)
        if '@' in self._user_identifier:
            return user_manager.get_user(self._user_identifier)
        else:
            # The identifier is the string representation of a UUID, either an
            # int in API 3.0 or a hex in API 3.1.
            try:
                user_id = self.api.to_uuid(self._user_identifier)
            except ValueError:
                return None
            else:
                return user_manager.get_user_by_id(user_id)

    def on_get(self, request, response):
        """Return a single user end-point."""
        if self._user is None:
            not_found(response)
        else:
            okay(response, self._resource_as_json(self._user))

    @child()
    def addresses(self, context, segments):
        """/users/<uid>/addresses"""
        if self._user is None:
            return NotFound(), []
        return UserAddresses(self._user)

    @child()
    def preferred_address(self, context, segements):
        """Return a user's preferred address."""
        if self._user is None:
            return NotFound(), []
        return PreferredAddress(self._user)

    def on_delete(self, request, response):
        """Delete the named user and all associated resources."""
        if self._user is None:
            not_found(response)
            return
        for member in self._user.memberships.members:
            member.unsubscribe()
        user_manager = getUtility(IUserManager)
        user_manager.delete_user(self._user)
        no_content(response)

    @child()
    def preferences(self, context, segments):
        """/users/<id>/preferences"""
        if len(segments) != 0:
            return BadRequest(), []
        if self._user is None:
            return NotFound(), []
        child = Preferences(
            self._user.preferences,
            'users/{}'.format(self.api.from_uuid(self._user.user_id)))
        return child, []

    def on_patch(self, request, response):
        """Patch the user's configuration (i.e. partial update)."""
        if self._user is None:
            not_found(response)
            return
        try:
            validator = PatchValidator(request, ATTRIBUTES)
        except UnknownPATCHRequestError as error:
            bad_request(
                response,
                'Unknown attribute: {0}'.format(error.attribute).encode())
        except ReadOnlyPATCHRequestError as error:
            bad_request(
                response,
                'Read-only attribute: {0}'.format(error.attribute).encode())
        else:
            validator.update(self._user, request)
            no_content(response)

    def on_put(self, request, response):
        """Put the user's configuration (i.e. full update)."""
        if self._user is None:
            not_found(response)
            return
        validator = Validator(**ATTRIBUTES)
        try:
            validator.update(self._user, request)
        except UnknownPATCHRequestError as error:
            bad_request(
                response,
                'Unknown attribute: {0}'.format(error.attribute).encode())
        except ReadOnlyPATCHRequestError as error:
            bad_request(
                response,
                'Read-only attribute: {0}'.format(error.attribute).encode())
        except ValueError as error:
            bad_request(response, str(error))
        else:
            no_content(response)

    @child()
    def login(self, context, segments):
        """Log the user in, sort of, by verifying a given password."""
        if self._user is None:
            return NotFound(), []
        return Login(self._user)


@public
class AddressUser(_UserBase):
    """The user linked to an address."""

    def __init__(self, address):
        self._address = address
        self._user = address.user

    def on_get(self, request, response):
        """Return a single user end-point."""
        if self._user is None:
            not_found(response)
        else:
            okay(response, self._resource_as_json(self._user))

    def on_delete(self, request, response):
        """Delete the named user, all her memberships, and addresses."""
        if self._user is None:
            not_found(response)
            return
        self._user.unlink(self._address)
        no_content(response)

    def on_post(self, request, response):
        """Link a user to the address, and create it if needed."""
        if self._user:
            conflict(response)
            return
        # When creating a linked user by POSTing, the user either must already
        # exist, or it can be automatically created, if the auto_create flag
        # is given and true (if missing, it defaults to true).  However, in
        # this case we do not accept 'email' as a POST field.
        fields = CREATION_FIELDS.copy()
        del fields['email']
        fields['user_id'] = self.api.to_uuid
        fields['auto_create'] = as_boolean
        fields['_optional'] = fields['_optional'] + (
            'user_id', 'auto_create', 'is_server_owner')
        try:
            validator = Validator(**fields)
            arguments = validator(request)
        except ValueError as error:
            bad_request(response, str(error))
            return
        user_manager = getUtility(IUserManager)
        if 'user_id' in arguments:
            user_id = arguments['user_id']
            user = user_manager.get_user_by_id(user_id)
            if user is None:
                bad_request(response, 'No user with ID {}'.format(
                    self.api.from_uuid(user_id)).encode())
                return
            okay(response)
        else:
            auto_create = arguments.pop('auto_create', True)
            if auto_create:
                # This sets the 201 or 400 status.
                user = create_user(self.api, arguments, response)
                if user is None:
                    return
            else:
                forbidden(response)
                return
        user.link(self._address)

    def on_put(self, request, response):
        """Set or replace the addresses's user."""
        if self._user:
            self._user.unlink(self._address)
        # Process post data and check for an existing user.
        fields = CREATION_FIELDS.copy()
        fields['user_id'] = self.api.to_uuid
        fields['_optional'] = fields['_optional'] + (
            'user_id', 'email', 'is_server_owner')
        try:
            validator = Validator(**fields)
            arguments = validator(request)
        except ValueError as error:
            bad_request(response, str(error))
            return
        user_manager = getUtility(IUserManager)
        if 'user_id' in arguments:
            user_id = arguments['user_id']
            user = user_manager.get_user_by_id(user_id)
            if user is None:
                not_found(response,
                          'No user with ID {}'.format(user_id).encode())
                return
            okay(response)
        else:
            user = create_user(self.api, arguments, response)
            if user is None:
                return
        user.link(self._address)


@public
class Login:
    """<api>/users/<uid>/login"""

    def __init__(self, user):
        assert user is not None
        self._user = user

    def on_post(self, request, response):
        # We do not want to encrypt the plaintext password given in the POST
        # data.  That would hash the password, but we need to have the
        # plaintext in order to pass into passlib.
        validator = Validator(cleartext_password=GetterSetter(str))
        try:
            values = validator(request)
        except ValueError as error:
            bad_request(response, str(error))
            return
        is_valid, new_hash = config.password_context.verify(
            values['cleartext_password'], self._user.password)
        if is_valid:
            if new_hash is not None:
                self._user.password = new_hash
            no_content(response)
        else:
            forbidden(response)


@public
class OwnersForDomain(_UserBase):
    """Owners for a particular domain."""

    def __init__(self, domain):
        self._domain = domain

    def on_get(self, request, response):
        """/domains/<domain>/owners"""
        if self._domain is None:
            not_found(response)
            return
        resource = self._make_collection(request)
        okay(response, etag(resource))

    def on_post(self, request, response):
        """POST to /domains/<domain>/owners """
        if self._domain is None:
            not_found(response)
            return
        validator = Validator(
            owner=ListOfDomainOwners(list_of_strings_validator))
        try:
            validator.update(self._domain, request)
        except ValueError as error:
            bad_request(response, str(error))
            return
        return no_content(response)

    def on_delete(self, request, response):
        """DELETE to /domains/<domain>/owners"""
        if self._domain is None:
            not_found(response)
        try:
            # No arguments.
            Validator()(request)
        except ValueError as error:
            bad_request(response, str(error))
            return
        owner_email = [
            owner.addresses[0].email
            for owner in self._domain.owners
            ]
        for email in owner_email:
            self._domain.remove_owner(email)
        return no_content(response)

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(self._domain.owners)


@public
class ServerOwners(_UserBase):
    """All server owners."""

    def on_get(self, request, response):
        """/owners"""
        resource = self._make_collection(request)
        okay(response, etag(resource))

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(IUserManager).server_owners)
