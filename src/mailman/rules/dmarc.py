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

"""DMARC mitigation rule."""

import os
import re
import logging
import dns.resolver

from dns.exception import DNSException
from email.utils import parseaddr
from lazr.config import as_timedelta
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.mailinglist import DMARCMitigateAction
from mailman.interfaces.rules import IRule
from mailman.utilities.datetime import now
from mailman.utilities.protocols import get
from mailman.utilities.string import wrap
from pkg_resources import resource_string as resource_bytes
from public import public
from requests.exceptions import HTTPError
from urllib.error import URLError
from zope.interface import implementer


elog = logging.getLogger('mailman.error')
vlog = logging.getLogger('mailman.vette')

DOT = '.'
KEEP_LOOKING = object()
LOCAL_FILE_NAME = 'public_suffix_list.dat'

# Map organizational domain suffix rules to a boolean indicating whether the
# rule is an exception or not.
suffix_cache = dict()


def ensure_current_suffix_list():
    # Read and parse the organizational domain suffix list.  First look in the
    # cached directory to see if we already have a valid copy of it.
    cached_copy_path = os.path.join(config.VAR_DIR, LOCAL_FILE_NAME)
    lifetime = as_timedelta(config.dmarc.cache_lifetime)
    download = False
    try:
        mtime = os.stat(cached_copy_path).st_mtime
    except FileNotFoundError:
        vlog.info('No cached copy of the public suffix list found')
        download = True
        cache_found = False
    else:
        cache_found = True
        # Is the cached copy out-of-date?  Note that when we write a new cache
        # version we explicitly set its mtime to the time in the future when
        # the cache will expire.
        if mtime < now().timestamp():
            download = True
            vlog.info('Cached copy of public suffix list is out of date')
    if download:
        try:
            content = get(config.dmarc.org_domain_data_url)
        except (URLError, HTTPError) as error:
            elog.error('Unable to retrieve public suffix list from %s: %s',
                       config.dmarc.org_domain_data_url,
                       getattr(error, 'reason', str(error)))
            if cache_found:
                vlog.info('Using out of date public suffix list')
                content = None
            else:
                # We couldn't access the URL and didn't even have an out of
                # date suffix list cached.  Use the shipped version.
                content = resource_bytes('mailman.rules.data', LOCAL_FILE_NAME)
        if content is not None:
            # Content is either a string or UTF-8 encoded bytes.
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            # Write the cache atomically.
            new_path = cached_copy_path + '.new'
            with open(new_path, 'w', encoding='utf-8') as fp:
                fp.write(content)
            # Set the expiry time to the future.
            mtime = (now() + lifetime).timestamp()
            os.utime(new_path, (mtime, mtime))
            # Flip the new file into the cached location.  This does not
            # modify the mtime.
            os.rename(new_path, cached_copy_path)
    return cached_copy_path


def parse_suffix_list():
    # Parse the suffix list into a per process cache.
    cached_copy_path = ensure_current_suffix_list()
    # At this point the cached copy must exist and is as valid as possible.
    # Read and return the contents as a UTF-8 string.
    with open(cached_copy_path, 'r', encoding='utf-8') as fp:
        for line in fp:
            if not line.strip() or line.startswith('//'):
                continue
            line = re.sub('\s.*', '', line)
            if not line:
                continue
            parts = line.lower().split('.')
            if parts[0].startswith('!'):
                exception = True
                parts = [parts[0][1:]] + parts[1:]
            else:
                exception = False
            parts.reverse()
            k = DOT.join(parts)
            suffix_cache[k] = exception


def _get_dom(d, l):
    # A helper to get a domain name consisting of the first l+1 labels
    # in d.
    dom = d[:min(l+1, len(d))]
    dom.reverse()
    return '.'.join(dom)


def _get_org_dom(domain):
    # Given a domain name, this returns the corresponding Organizational
    # Domain which may be the same as the input.
    if len(suffix_cache) == 0:
        parse_suffix_list()
    hits = []
    d = domain.lower().split('.')
    d.reverse()
    for k in suffix_cache:
        ks = k.split('.')
        if len(d) >= len(ks):
            for i in range(len(ks)-1):
                if d[i] != ks[i] and ks[i] != '*':
                    break
            else:
                if d[len(ks)-1] == ks[-1] or ks[-1] == '*':
                    hits.append(k)
    if not hits:
        return _get_dom(d, 1)
    l = 0
    for k in hits:
        if suffix_cache[k]:
            # It's an exception
            return _get_dom(d, len(k.split('.'))-1)
        if len(k.split('.')) > l:
            l = len(k.split('.'))
    return _get_dom(d, l)


def _DMARCProhibited(mlist, email, dmarc_domain, org=False):
    resolver = dns.resolver.Resolver()
    resolver.timeout = as_timedelta(
        config.dmarc.resolver_timeout).total_seconds()
    resolver.lifetime = as_timedelta(
        config.dmarc.resolver_lifetime).total_seconds()
    try:
        txt_recs = resolver.query(dmarc_domain, dns.rdatatype.TXT)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return KEEP_LOOKING
    except DNSException as e:
        elog.error(
            'DNSException: Unable to query DMARC policy for %s (%s). %s',
            email, dmarc_domain, e.__doc__)
        return KEEP_LOOKING
    # Be as robust as possible in parsing the result.
    results_by_name = {}
    cnames = {}
    want_names = set([dmarc_domain + '.'])
    for txt_rec in txt_recs.response.answer:
        if txt_rec.rdtype == dns.rdatatype.CNAME:
            cnames[txt_rec.name.to_text()] = (
                txt_rec.items[0].target.to_text())
        if txt_rec.rdtype != dns.rdatatype.TXT:
            continue
        results_by_name.setdefault(
            txt_rec.name.to_text(), []).append(
                "".join(
                   [str(x, encoding='utf-8')
                       for x in txt_rec.items[0].strings]))
    expands = list(want_names)
    seen = set(expands)
    while expands:
        item = expands.pop(0)
        if item in cnames:
            if cnames[item] in seen:
                continue  # cname loop
            expands.append(cnames[item])
            seen.add(cnames[item])
            want_names.add(cnames[item])
            want_names.discard(item)
    if len(want_names) != 1:
        elog.error(
            """multiple DMARC entries in results for %s,
            processing each to be strict""",
            dmarc_domain)
    for name in want_names:
        if name not in results_by_name:
            continue
        dmarcs = [x for x in results_by_name[name]
                  if x.startswith('v=DMARC1;')]
        if len(dmarcs) == 0:
            return KEEP_LOOKING
        if len(dmarcs) > 1:
            elog.error(
                """RRset of TXT records for %s has %d v=DMARC1 entries;
                testing them all""",
                dmarc_domain, len(dmarcs))
        for entry in dmarcs:
            mo = re.search(r'\bsp=(\w*)\b', entry, re.IGNORECASE)
            if org and mo:
                policy = mo.group(1).lower()
            else:
                mo = re.search(r'\bp=(\w*)\b', entry, re.IGNORECASE)
                if mo:
                    policy = mo.group(1).lower()
                else:
                    continue
            if policy in ('reject', 'quarantine'):
                vlog.info(
                    """%s: DMARC lookup for %s (%s)
                    found p=%s in %s = %s""",
                    mlist.list_name,
                    email,
                    dmarc_domain,
                    policy,
                    name,
                    entry)
                return True
    return False


def _IsDMARCProhibited(mlist, email):
    # This takes an email address, and returns True if DMARC policy is
    # p=reject or quarantine.
    email = email.lower()
    # Scan from the right in case quoted local part has an '@'.
    local, at, from_domain = email.rpartition('@')
    if at != '@':
        return False
    x = _DMARCProhibited(mlist, email, '_dmarc.{}'.format(from_domain))
    if x is not KEEP_LOOKING:
        return x
    org_dom = _get_org_dom(from_domain)
    if org_dom != from_domain:
        x = _DMARCProhibited(
            mlist, email, '_dmarc.{}'.format(org_dom), org=True)
        if x is not KEEP_LOOKING:
            return x
    return False


@public
@implementer(IRule)
class DMARCMitigation:
    """The DMARC mitigation rule."""

    name = 'dmarc-mitigation'
    description = _('Find DMARC policy of From: domain.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        if mlist.dmarc_mitigate_action is DMARCMitigateAction.no_mitigation:
            # Don't bother to check if we're not going to do anything.
            return False
        dn, addr = parseaddr(msg.get('from'))
        if _IsDMARCProhibited(mlist, addr):
            # If dmarc_mitigate_action is discard or reject, this rule fires
            # and jumps to the 'moderation' chain to do the actual discard.
            # Otherwise, the rule misses but sets a flag for the dmarc handler
            # to do the appropriate action.
            msgdata['dmarc'] = True
            if mlist.dmarc_mitigate_action is DMARCMitigateAction.discard:
                msgdata['moderation_action'] = 'discard'
                msgdata['moderation_reasons'] = [_('DMARC moderation')]
            elif mlist.dmarc_mitigate_action is DMARCMitigateAction.reject:
                listowner = mlist.owner_address       # noqa F841
                reason = (mlist.dmarc_moderation_notice or
                          _('You are not allowed to post to this mailing '
                            'list From: a domain which publishes a DMARC '
                            'policy of reject or quarantine, and your message'
                            ' has been automatically rejected.  If you think '
                            'that your messages are being rejected in error, '
                            'contact the mailing list owner at ${listowner}.'))
                msgdata['moderation_reasons'] = [wrap(reason)]
                msgdata['moderation_action'] = 'reject'
            else:
                return False
            msgdata['moderation_sender'] = addr
            return True
        return False
