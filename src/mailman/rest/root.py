# Copyright (C) 2010-2016 by the Free Software Foundation, Inc.
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

"""The root of the REST API."""

import falcon

from base64 import b64decode
from mailman import public
from mailman.config import config
from mailman.core.api import API30, API31
from mailman.core.constants import system_preferences
from mailman.core.system import system
from mailman.interfaces.listmanager import IListManager
from mailman.model.uid import UID
from mailman.rest.addresses import AllAddresses, AnAddress
from mailman.rest.bans import BannedEmail, BannedEmails
from mailman.rest.domains import ADomain, AllDomains
from mailman.rest.helpers import (
    BadRequest, NotFound, child, etag, no_content, not_found, okay)
from mailman.rest.lists import AList, AllLists, Styles
from mailman.rest.members import AMember, AllMembers, FindMembers
from mailman.rest.preferences import ReadOnlyPreferences
from mailman.rest.queues import AQueue, AQueueFile, AllQueues
from mailman.rest.templates import TemplateFinder
from mailman.rest.users import AUser, AllUsers, ServerOwners
from zope.component import getUtility


SLASH = '/'


@public
class Root:
    """The RESTful root resource.

    At the root of the tree are the API version numbers.  Everything else
    lives underneath those.  Currently there is only one API version number,
    and we start at 3.0 to match the Mailman version number.  That may not
    always be the case though.
    """

    @child('3.0')
    def api_version_30(self, request, segments):
        # API version 3.0 was introduced in Mailman 3.0.
        request.context['api'] = API30
        return self._check_authorization(request, segments)

    @child('3.1')
    def api_version_31(self, request, segments):
        # API version 3.1 was introduced in Mailman 3.1.  Primary backward
        # incompatible difference is that uuids are represented as hex strings
        # instead of 128 bit integers.  The latter is not compatible with all
        # versions of JavaScript.
        request.context['api'] = API31
        return self._check_authorization(request, segments)

    def _check_authorization(self, request, segments):
        # We have to do this here instead of in a @falcon.before() handler
        # because those handlers are not compatible with our custom traversal
        # logic.  Specifically, falcon's before/after handlers will call the
        # responder, but the method we're wrapping isn't a responder, it's a
        # child traversal method.  There's no way to cause the thing that
        # calls the before hook to follow through with the child traversal in
        # the case where no error is raised.
        if request.auth is None:
            raise falcon.HTTPUnauthorized(
                '401 Unauthorized',
                'The REST API requires authentication')
        if request.auth.startswith('Basic '):
            # b64decode() returns bytes, but we require a str.
            credentials = b64decode(request.auth[6:]).decode('utf-8')
            username, password = credentials.split(':', 1)
            if (username != config.webservice.admin_user or
                    password != config.webservice.admin_pass):
                # Not authorized.
                raise falcon.HTTPUnauthorized(
                    '401 Unauthorized',
                    'User is not authorized for the REST API')
        return TopLevel()


@public
class Versions:
    def on_get(self, request, response):
        """/<api>/system/versions"""
        resource = dict(
            mailman_version=system.mailman_version,
            python_version=system.python_version,
            api_version=self.api.version,
            self_link=self.api.path_to('system/versions'),
            )
        okay(response, etag(resource))


@public
class SystemConfiguration:
    def __init__(self, section=None):
        self._section = section

    def on_get(self, request, response):
        if self._section is None:
            resource = dict(
                sections=sorted(section.name for section in config))
            okay(response, etag(resource))
            return
        missing = object()
        section = getattr(config, self._section, missing)
        if section is missing:
            not_found(response)
            return
        # Sections don't have .keys(), .values(), or .items() but we can
        # iterate over them.
        resource = {key: section[key] for key in section}
        okay(response, etag(resource))


@public
class Pipelines:
    def on_get(self, request, response):
        resource = dict(pipelines=list(config.pipelines.keys()))
        okay(response, etag(resource))


@public
class Reserved:
    """Top level API for reserved operations.

    Nothing under this resource should be considered part of the stable API.
    The resources that appear here are purely for the support of external
    non-production systems, such as testing infrastructures for cooperating
    components.  Use at your own risk.
    """
    def __init__(self, segments):
        self._resource_path = SLASH.join(segments)

    def on_delete(self, request, response):
        if self._resource_path != 'uids/orphans':
            not_found(response)
            return
        UID.cull_orphans()
        no_content(response)


@public
class TopLevel:
    """Top level collections and entries."""

    @child()
    def system(self, request, segments):
        """/<api>/system"""
        if len(segments) == 0:
            # This provides backward compatibility; see /system/versions.
            return Versions()
        elif segments[0] == 'preferences':
            if len(segments) > 1:
                return BadRequest(), []
            return ReadOnlyPreferences(system_preferences, 'system'), []
        elif segments[0] == 'versions':
            if len(segments) > 1:
                return BadRequest(), []
            return Versions(), []
        elif segments[0] == 'configuration':
            if len(segments) <= 2:
                return SystemConfiguration(*segments[1:]), []
            return BadRequest(), []
        elif segments[0] == 'pipelines':
            if len(segments) > 1:
                return BadRequest(), []
            return Pipelines(), []
        else:
            return NotFound(), []

    @child()
    def addresses(self, request, segments):
        """/<api>/addresses
           /<api>/addresses/<email>
        """
        if len(segments) == 0:
            resource = AllAddresses()
            resource.api = request.context['api']
            return resource
        else:
            email = segments.pop(0)
            resource = AnAddress(email)
            resource.api = request.context['api']
            return resource, segments

    @child()
    def domains(self, request, segments):
        """/<api>/domains
           /<api>/domains/<domain>
        """
        if len(segments) == 0:
            return AllDomains()
        else:
            domain = segments.pop(0)
            return ADomain(domain), segments

    @child()
    def lists(self, request, segments):
        """/<api>/lists
           /<api>/lists/styles
           /<api>/lists/<list>
           /<api>/lists/<list>/...
        """
        if len(segments) == 0:
            return AllLists()
        elif len(segments) == 1 and segments[0] == 'styles':
            return Styles(), []
        else:
            # list-id is preferred, but for backward compatibility,
            # fqdn_listname is also accepted.
            list_identifier = segments.pop(0)
            return AList(list_identifier), segments

    @child()
    def members(self, request, segments):
        """/<api>/members"""
        api = request.context['api']
        if len(segments) == 0:
            resource = AllMembers()
            resource.api = api
            return resource
        # Either the next segment is the string "find" or a member id.  They
        # cannot collide.
        segment = segments.pop(0)
        if segment == 'find':
            resource = FindMembers()
            resource.api = api
        else:
            resource = AMember(api, segment)
        return resource, segments

    @child()
    def users(self, request, segments):
        """/<api>/users"""
        api = request.context['api']
        if len(segments) == 0:
            resource = AllUsers()
            resource.api = api
            return resource
        else:
            user_id = segments.pop(0)
            return AUser(api, user_id), segments

    @child()
    def owners(self, request, segments):
        """/<api>/owners"""
        if len(segments) != 0:
            return BadRequest(), []
        else:
            resource = ServerOwners()
            resource.api = request.context['api']
            return resource, segments

    @child()
    def templates(self, request, segments):
        """/<api>/templates/<fqdn_listname>/<template>/[<language>]

        Use content negotiation to request language and suffix (content-type).
        """
        if len(segments) == 3:
            fqdn_listname, template, language = segments
        elif len(segments) == 2:
            fqdn_listname, template = segments
            language = 'en'
        else:
            return BadRequest(), []
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            return NotFound(), []
        # XXX dig out content-type from request
        content_type = None
        return TemplateFinder(
            fqdn_listname, template, language, content_type)

    @child()
    def queues(self, request, segments):
        """/<api>/queues[/<name>[/file]]"""
        if len(segments) == 0:
            return AllQueues()
        elif len(segments) == 1:
            return AQueue(segments[0]), []
        elif len(segments) == 2:
            return AQueueFile(segments[0], segments[1]), []
        else:
            return BadRequest(), []

    @child()
    def bans(self, request, segments):
        """/<api>/bans
           /<api>/bans/<email>
        """
        if len(segments) == 0:
            return BannedEmails(None)
        else:
            email = segments.pop(0)
            return BannedEmail(None, email), segments

    @child()
    def reserved(self, request, segments):
        """/<api>/reserved/[...]"""
        return Reserved(segments), []
