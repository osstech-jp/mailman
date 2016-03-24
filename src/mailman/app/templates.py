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

"""Template loader."""

from contextlib import closing
from mailman import public
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.templates import ITemplateLoader
from mailman.utilities.i18n import TemplateNotFoundError, find
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import BaseHandler, build_opener, install_opener, urlopen
from urllib.response import addinfourl
from zope.component import getUtility
from zope.interface import implementer


class MailmanHandler(BaseHandler):
    # Handle internal mailman: URLs.
    def mailman_open(self, req):
        list_manager = getUtility(IListManager)
        # Parse urls of the form:
        #
        # mailman:///<fqdn_listname|list_id>/<language>/<template_name>
        #
        # where only the template name is required.
        mlist = code = template = None
        # Parse the full requested URL and be sure it's something we handle.
        original_url = req.get_full_url()
        parsed = urlparse(original_url)
        assert parsed.scheme == 'mailman'
        # The path can contain one, two, or three components.  Since no empty
        # path components are legal, filter them out.
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) == 0:
            raise URLError('No template specified')
        elif len(parts) == 1:
            template = parts[0]
        elif len(parts) == 2:
            part0, template = parts
            # Is part0 a language code or a mailing list?  This is rather
            # tricky because if it's a mailing list, it could be a list-id and
            # that will contain dots, as could the language code.
            language = getUtility(ILanguageManager).get(part0)
            if language is None:
                # part0 must be a fqdn-listname or list-id.
                mlist = (list_manager.get(part0)
                         if '@' in part0 else
                         list_manager.get_by_list_id(part0))
                if mlist is None:
                    raise URLError('Bad language or list name')
            else:
                code = language.code
        elif len(parts) == 3:
            part0, code, template = parts
            # part0 could be an fqdn-listname or a list-id.
            mlist = (getUtility(IListManager).get(part0)
                     if '@' in part0 else
                     getUtility(IListManager).get_by_list_id(part0))
            if mlist is None:
                raise URLError('Missing list')
            language = getUtility(ILanguageManager).get(code)
            if language is None:
                raise URLError('No such language')
            code = language.code
        else:
            raise URLError('No such file')
        # Find the template, mutating any missing template exception.
        try:
            path, fp = find(template, mlist, code)
        except TemplateNotFoundError:
            raise URLError('No such file')
        return addinfourl(fp, {}, original_url)


@public
@implementer(ITemplateLoader)
class TemplateLoader:
    """Loader of templates, with caching and support for mailman:// URIs."""

    def __init__(self):
        opener = build_opener(MailmanHandler())
        install_opener(opener)

    def get(self, uri):
        """See `ITemplateLoader`."""
        with closing(urlopen(uri)) as fp:
            return fp.read()
