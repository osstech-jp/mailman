# Copyright (C) 1998-2003 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


"""Miscellaneous essential routines.

This includes actual message transmission routines, address checking and
message and address munging, a handy-dandy routine to map a function on all
the mailing lists, and whatever else doesn't belong elsewhere.

"""

from __future__ import nested_scopes

import os
import re
import random
import urlparse
import sha
import errno
import time
import cgi
import htmlentitydefs
import email.Iterators
from types import UnicodeType
from string import whitespace, digits
try:
    # Python 2.2
    from string import ascii_letters
except ImportError:
    # Older Pythons
    _lower = 'abcdefghijklmnopqrstuvwxyz'
    ascii_letters = _lower + _lower.upper()

from Mailman import mm_cfg
from Mailman import Errors
from Mailman import Site
from Mailman.SafeDict import SafeDict

EMPTYSTRING = ''
NL = '\n'
DOT = '.'
IDENTCHARS = ascii_letters + digits + '_'

# Search for $(identifier)s strings, except that the trailing s is optional,
# since that's a common mistake
cre = re.compile(r'%\(([_a-z]\w*?)\)s?', re.IGNORECASE)
# Search for $$, $identifier, or ${identifier}
dre = re.compile(r'(\${2})|\$([_a-z]\w*)|\${([_a-z]\w*)}', re.IGNORECASE)



def list_exists(listname):
    """Return true iff list `listname' exists."""
    # The existance of any of the following file proves the list exists
    # <wink>: config.pck, config.pck.last, config.db, config.db.last
    #
    # The former two are for 2.1alpha3 and beyond, while the latter two are
    # for all earlier versions.
    basepath = Site.get_listpath(listname)
    for ext in ('.pck', '.pck.last', '.db', '.db.last'):
        dbfile = os.path.join(basepath, 'config' + ext)
        if os.path.exists(dbfile):
            return 1
    return 0


def list_names():
    """Return the names of all lists in default list directory."""
    # We don't currently support separate listings of virtual domains
    return Site.get_listnames()



# a much more naive implementation than say, Emacs's fill-paragraph!
def wrap(text, column=70, honor_leading_ws=1):
    """Wrap and fill the text to the specified column.

    Wrapping is always in effect, although if it is not possible to wrap a
    line (because some word is longer than `column' characters) the line is
    broken at the next available whitespace boundary.  Paragraphs are also
    always filled, unless honor_leading_ws is true and the line begins with
    whitespace.  This is the algorithm that the Python FAQ wizard uses, and
    seems like a good compromise.

    """
    wrapped = ''
    # first split the text into paragraphs, defined as a blank line
    paras = re.split('\n\n', text)
    for para in paras:
        # fill
        lines = []
        fillprev = 0
        for line in para.split(NL):
            if not line:
                lines.append(line)
                continue
            if honor_leading_ws and line[0] in whitespace:
                fillthis = 0
            else:
                fillthis = 1
            if fillprev and fillthis:
                # if the previous line should be filled, then just append a
                # single space, and the rest of the current line
                lines[-1] = lines[-1].rstrip() + ' ' + line
            else:
                # no fill, i.e. retain newline
                lines.append(line)
            fillprev = fillthis
        # wrap each line
        for text in lines:
            while text:
                if len(text) <= column:
                    line = text
                    text = ''
                else:
                    bol = column
                    # find the last whitespace character
                    while bol > 0 and text[bol] not in whitespace:
                        bol = bol - 1
                    # now find the last non-whitespace character
                    eol = bol
                    while eol > 0 and text[eol] in whitespace:
                        eol = eol - 1
                    # watch out for text that's longer than the column width
                    if eol == 0:
                        # break on whitespace after column
                        eol = column
                        while eol < len(text) and \
                              text[eol] not in whitespace:
                            eol = eol + 1
                        bol = eol
                        while bol < len(text) and \
                              text[bol] in whitespace:
                            bol = bol + 1
                        bol = bol - 1
                    line = text[:eol+1] + '\n'
                    # find the next non-whitespace character
                    bol = bol + 1
                    while bol < len(text) and text[bol] in whitespace:
                        bol = bol + 1
                    text = text[bol:]
                wrapped = wrapped + line
            wrapped = wrapped + '\n'
            # end while text
        wrapped = wrapped + '\n'
        # end for text in lines
    # the last two newlines are bogus
    return wrapped[:-2]



def QuotePeriods(text):
    JOINER = '\n .\n'
    SEP = '\n.\n'
    return JOINER.join(text.split(SEP))


# This takes an email address, and returns a tuple containing (user,host)
def ParseEmail(email):
    user = None
    domain = None
    email = email.lower()
    at_sign = email.find('@')
    if at_sign < 1:
        return email, None
    user = email[:at_sign]
    rest = email[at_sign+1:]
    domain = rest.split('.')
    return user, domain


def LCDomain(addr):
    "returns the address with the domain part lowercased"
    atind = addr.find('@')
    if atind == -1: # no domain part
        return addr
    return addr[:atind] + '@' + addr[atind+1:].lower()


# TBD: what other characters should be disallowed?
_badchars = re.compile(r'[][()<>|;^,/\200-\377]')

def ValidateEmail(s):
    """Verify that the an email address isn't grossly evil."""
    # Pretty minimal, cheesy check.  We could do better...
    if not s or s.count(' ') > 0:
        raise Errors.MMBadEmailError
    if _badchars.search(s) or s[0] == '-':
        raise Errors.MMHostileAddress, s
    user, domain_parts = ParseEmail(s)
    # This means local, unqualified addresses, are no allowed
    if not domain_parts:
        raise Errors.MMBadEmailError, s
    if len(domain_parts) < 2:
        raise Errors.MMBadEmailError, s



def GetPathPieces(envar='PATH_INFO'):
    path = os.environ.get(envar)
    if path:
        return [p for p in path.split('/') if p]
    return None



def ScriptURL(target, web_page_url=None, absolute=0):
    """target - scriptname only, nothing extra
    web_page_url - the list's configvar of the same name
    absolute - a flag which if set, generates an absolute url
    """
    if web_page_url is None:
        web_page_url = mm_cfg.DEFAULT_URL_PATTERN % get_domain()
        if web_page_url[-1] <> '/':
            web_page_url = web_page_url + '/'
    fullpath = os.environ.get('REQUEST_URI')
    if fullpath is None:
        fullpath = os.environ.get('SCRIPT_NAME', '') + \
                   os.environ.get('PATH_INFO', '')
    baseurl = urlparse.urlparse(web_page_url)[2]
    if not absolute and fullpath.endswith(baseurl):
        # Use relative addressing
        fullpath = fullpath[len(baseurl):]
        i = fullpath.find('?')
        if i > 0:
            count = fullpath.count('/', 0, i)
        else:
            count = fullpath.count('/')
        path = ('../' * count) + target
    else:
        path = web_page_url + target
    return path + mm_cfg.CGIEXT



def GetPossibleMatchingAddrs(name):
    """returns a sorted list of addresses that could possibly match
    a given name.

    For Example, given scott@pobox.com, return ['scott@pobox.com'],
    given scott@blackbox.pobox.com return ['scott@blackbox.pobox.com',
                                           'scott@pobox.com']"""

    name = name.lower()
    user, domain = ParseEmail(name)
    res = [name]
    if domain:
        domain = domain[1:]
        while len(domain) >= 2:
            res.append("%s@%s" % (user, DOT.join(domain)))
            domain = domain[1:]
    return res



def List2Dict(list, foldcase=0):
    """Return a dict keyed by the entries in the list passed to it."""
    d = {}
    if foldcase:
        for i in list:
            d[i.lower()] = 1
    else:
        for i in list:
            d[i] = 1
    return d



_vowels = ('a', 'e', 'i', 'o', 'u')
_consonants = ('b', 'c', 'd', 'f', 'g', 'h', 'k', 'm', 'n',
               'p', 'r', 's', 't', 'v', 'w', 'x', 'z')
_syllables = []

for v in _vowels:
    for c in _consonants:
        _syllables.append(c+v)
        _syllables.append(v+c)
del c, v

def MakeRandomPassword(length=6):
    syls = []
    while len(syls)*2 < length:
        syls.append(random.choice(_syllables))
    return EMPTYSTRING.join(syls)[:length]

def GetRandomSeed():
    chr1 = int(random.random() * 52)
    chr2 = int(random.random() * 52)
    def mkletter(c):
        if 0 <= c < 26:
            c = c + 65
        if 26 <= c < 52:
            c = c - 26 + 97
        return c
    return "%c%c" % tuple(map(mkletter, (chr1, chr2)))



def set_global_password(pw, siteadmin=1):
    if siteadmin:
        filename = mm_cfg.SITE_PW_FILE
    else:
        filename = mm_cfg.LISTCREATOR_PW_FILE
    omask = os.umask(026)                         # rw-r-----
    try:
        fp = open(filename, 'w')
        fp.write(sha.new(pw).hexdigest() + '\n')
        fp.close()
    finally:
        os.umask(omask)


def get_global_password(siteadmin=1):
    if siteadmin:
        filename = mm_cfg.SITE_PW_FILE
    else:
        filename = mm_cfg.LISTCREATOR_PW_FILE
    try:
        fp = open(filename)
        challenge = fp.read()[:-1]                # strip off trailing nl
        fp.close()
    except IOError, e:
        if e.errno <> errno.ENOENT: raise
        # It's okay not to have a site admin password, just return false
        return None
    return challenge


def check_global_password(response, siteadmin=1):
    challenge = get_global_password(siteadmin)
    if challenge is None:
        return None
    return challenge == sha.new(response).hexdigest()



def websafe(s):
    return cgi.escape(s, quote=1)



# Just changing these two functions should be enough to control the way
# that email address obscuring is handled.
def ObscureEmail(addr, for_text=0):
    """Make email address unrecognizable to web spiders, but invertable.

    When for_text option is set (not default), make a sentence fragment
    instead of a token."""
    if for_text:
        return addr.replace('@', ' at ')
    else:
        return addr.replace('@', '--at--')

def UnobscureEmail(addr):
    """Invert ObscureEmail() conversion."""
    # Contrived to act as an identity operation on already-unobscured
    # emails, so routines expecting obscured ones will accept both.
    return addr.replace('--at--', '@')



def maketext(templatefile, dict=None, raw=0, lang=None, mlist=None):
    # Make some text from a template file.  The order of searches depends on
    # whether mlist and lang are provided.  Once the templatefile is found,
    # string substitution is performed by interpolation in `dict'.  If `raw'
    # is false, the resulting text is wrapped/filled by calling wrap().
    #
    # When looking for a template in a specific language, there are 4 places
    # that are searched, in this order:
    #
    # 1. the list-specific language directory
    #    lists/<listname>/<language>
    #
    # 2. the domain-specific language directory
    #    templates/<list.host_name>/<language>
    #
    # 3. the site-wide language directory
    #    templates/site/<language>
    #
    # 4. the global default language directory
    #    templates/<language>
    #
    # The first match found stops the search.  In this way, you can specialize
    # templates at the desired level, or, if you use only the default
    # templates, you don't need to change anything.  You should never modify
    # files in the templates/<language> subdirectory, since Mailman will
    # overwrite these when you upgrade.  That's what the templates/site
    # language directories are for.
    #
    # A further complication is that the language to search for is determined
    # by both the `lang' and `mlist' arguments.  The search order there is
    # that if lang is given, then the 4 locations above are searched,
    # substituting lang for <language>.  If no match is found, and mlist is
    # given, then the 4 locations are searched using the list's preferred
    # language.  After that, the server default language is used for
    # <language>.  If that still doesn't yield a template, then the standard
    # distribution's English language template is used as an ultimate
    # fallback.  If that's missing you've got big problems. ;)
    #
    # A word on backwards compatibility: Mailman versions prior to 2.1 stored
    # templates in templates/*.{html,txt} and lists/<listname>/*.{html,txt}.
    # Those directories are no longer searched so if you've got customizations
    # in those files, you should move them to the appropriate directory based
    # on the above description.  Mailman's upgrade script cannot do this for
    # you.
    #
    # Calculate the languages to scan
    languages = []
    if lang is not None:
        languages.append(lang)
    if mlist is not None:
        languages.append(mlist.preferred_language)
    languages.append(mm_cfg.DEFAULT_SERVER_LANGUAGE)
    # Calculate the locations to scan
    searchdirs = []
    if mlist is not None:
        searchdirs.append(mlist.fullpath())
        searchdirs.append(os.path.join(mm_cfg.TEMPLATE_DIR, mlist.host_name))
    searchdirs.append(os.path.join(mm_cfg.TEMPLATE_DIR, 'site'))
    searchdirs.append(mm_cfg.TEMPLATE_DIR)
    # Start scanning
    quickexit = 'quickexit'
    fp = None
    try:
        for lang in languages:
            for dir in searchdirs:
                filename = os.path.join(dir, lang, templatefile)
                try:
                    fp = open(filename)
                    raise quickexit
                except IOError, e:
                    if e.errno <> errno.ENOENT: raise
                    # Okay, it doesn't exist, keep looping
                    fp = None
    except quickexit:
        pass
    if fp is None:
        # Try one last time with the distro English template, which, unless
        # you've got a really broken installation, must be there.
        try:
            fp = open(os.path.join(mm_cfg.TEMPLATE_DIR, 'en', templatefile))
        except IOError, e:
            if e.errno <> errno.ENOENT: raise
            # We never found the template.  BAD!
            raise IOError(errno.ENOENT, 'No template file found', templatefile)
    template = fp.read()
    fp.close()
    text = template
    if dict is not None:
        try:
            sdict = SafeDict(dict)
            try:
                text = sdict.interpolate(template)
            except UnicodeError:
                # Try again after coercing the template to unicode
                utemplate = unicode(template, GetCharSet(lang), 'replace')
                text = sdict.interpolate(utemplate)
        except (TypeError, ValueError), e:
            # The template is really screwed up
            from Mailman.Logging.Syslog import syslog
            syslog('error', 'broken template: %s\n%s', filename, e)
            pass
    if raw:
        return text
    return wrap(text)



ADMINDATA = {
    # admin keyword: (minimum #args, maximum #args)
    'confirm':     (1, 1),
    'help':        (0, 0),
    'info':        (0, 0),
    'lists':       (0, 0),
    'options':     (0, 0),
    'password':    (2, 2),
    'remove':      (0, 0),
    'set':         (3, 3),
    'subscribe':   (0, 3),
    'unsubscribe': (0, 1),
    'who':         (0, 0),
    }

# Given a Message.Message object, test for administrivia (eg subscribe,
# unsubscribe, etc).  The test must be a good guess -- messages that return
# true get sent to the list admin instead of the entire list.
def is_administrivia(msg):
    linecnt = 0
    lines = []
    for line in email.Iterators.body_line_iterator(msg):
        # Strip out any signatures
        if line == '-- ':
            break
        if line.strip():
            linecnt += 1
        if linecnt > mm_cfg.DEFAULT_MAIL_COMMANDS_MAX_LINES:
            return 0
        lines.append(line)
    bodytext = NL.join(lines)
    # See if the body text has only one word, and that word is administrivia
    if ADMINDATA.has_key(bodytext.strip().lower()):
        return 1
    # Look at the first N lines and see if there is any administrivia on the
    # line.  BAW: N is currently hardcoded to 5.  str-ify the Subject: header
    # because it may be an email.Header.Header instance rather than a string.
    bodylines = lines[:5]
    subject = str(msg.get('subject', ''))
    bodylines.append(subject)
    for line in bodylines:
        if not line.strip():
            continue
        words = [word.lower() for word in line.split()]
        minargs, maxargs = ADMINDATA.get(words[0], (None, None))
        if minargs is None and maxargs is None:
            continue
        if minargs <= len(words[1:]) <= maxargs:
            # Special case the `set' keyword.  BAW: I don't know why this is
            # here.
            if words[0] == 'set' and words[2] not in ('on', 'off'):
                continue
            return 1
    return 0



def GetRequestURI(fallback=None, escape=1):
    """Return the full virtual path this CGI script was invoked with.

    Newer web servers seems to supply this info in the REQUEST_URI
    environment variable -- which isn't part of the CGI/1.1 spec.
    Thus, if REQUEST_URI isn't available, we concatenate SCRIPT_NAME
    and PATH_INFO, both of which are part of CGI/1.1.

    Optional argument `fallback' (default `None') is returned if both of
    the above methods fail.

    The url will be cgi escaped to prevent cross-site scripting attacks,
    unless `escape' is set to 0.
    """
    url = fallback
    if os.environ.has_key('REQUEST_URI'):
        url = os.environ['REQUEST_URI']
    elif os.environ.has_key('SCRIPT_NAME') and os.environ.has_key('PATH_INFO'):
        url = os.environ['SCRIPT_NAME'] + os.environ['PATH_INFO']
    if escape:
        return websafe(url)
    return url



# Wait on a dictionary of child pids
def reap(kids, func=None, once=0):
    while kids:
        if func:
            func()
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except OSError, e:
            # If the child procs had a bug we might have no children
            if e.errno <> errno.ECHILD:
                raise
            kids.clear()
            break
        if pid <> 0:
            try:
                del kids[pid]
            except KeyError:
                # Huh?  How can this happen?
                pass
        if once:
            break


def GetLanguageDescr(lang):
    return mm_cfg.LC_DESCRIPTIONS[lang][0]


def GetCharSet(lang):
    return mm_cfg.LC_DESCRIPTIONS[lang][1]

def IsLanguage(lang):
    return mm_cfg.LC_DESCRIPTIONS.has_key(lang)



def get_domain():
    host = os.environ.get('HTTP_HOST', os.environ.get('SERVER_NAME'))
    port = os.environ.get('SERVER_PORT')
    # Strip off the port if there is one
    if port and host.endswith(':' + port):
        host = host[:-len(port)-1]
    if mm_cfg.VIRTUAL_HOST_OVERVIEW and host:
        return host.lower()
    else:
        # See the note in Defaults.py concerning DEFAULT_HOST_NAME
        # vs. DEFAULT_EMAIL_HOST.
        hostname = mm_cfg.DEFAULT_HOST_NAME or mm_cfg.DEFAULT_EMAIL_HOST
        return hostname.lower()


def get_site_email(hostname=None, extra=None):
    if hostname is None:
        hostname = mm_cfg.VIRTUAL_HOSTS.get(get_domain(), get_domain())
    if extra is None:
        return '%s@%s' % (mm_cfg.MAILMAN_SITE_LIST, hostname)
    return '%s-%s@%s' % (mm_cfg.MAILMAN_SITE_LIST, extra, hostname)



# This algorithm crafts a guaranteed unique message-id.  The theory here is
# that pid+listname+host will distinguish the message-id for every process on
# the system, except when process ids wrap around.  To further distinguish
# message-ids, we prepend the integral time in seconds since the epoch.  It's
# still possible that we'll vend out more than one such message-id per second,
# so we prepend a monotonically incrementing serial number.  It's highly
# unlikely that within a single second, there'll be a pid wraparound.
_serial = 0
def unique_message_id(mlist):
    global _serial
    msgid = '<mailman.%d.%d.%d.%s@%s>' % (
        _serial, time.time(), os.getpid(),
        mlist.internal_name(), mlist.host_name)
    _serial += 1
    return msgid


# Figure out epoch seconds of midnight at the start of today (or the given
# 3-tuple date of (year, month, day).
def midnight(date=None):
    if date is None:
        date = time.localtime()[:3]
    # -1 for dst flag tells the library to figure it out
    return time.mktime(date + (0,)*5 + (-1,))



# Utilities to convert from simplified $identifier substitutions to/from
# standard Python $(identifier)s substititions.  The "Guido rules" for the
# former are:
#    $$ -> $
#    $identifier -> $(identifier)s
#    ${identifier} -> $(identifier)s

def to_dollar(s):
    """Convert from %-strings to $-strings."""
    s = s.replace('$', '$$').replace('%%', '%')
    parts = cre.split(s)
    for i in range(1, len(parts), 2):
        if parts[i+1] and parts[i+1][0] in IDENTCHARS:
            parts[i] = '${' + parts[i] + '}'
        else:
            parts[i] = '$' + parts[i]
    return EMPTYSTRING.join(parts)


def to_percent(s):
    """Convert from $-strings to %-strings."""
    s = s.replace('%', '%%').replace('$$', '$')
    parts = dre.split(s)
    for i in range(1, len(parts), 4):
        if parts[i] is not None:
            parts[i] = '$'
        elif parts[i+1] is not None:
            parts[i+1] = '%(' + parts[i+1] + ')s'
        else:
            parts[i+2] = '%(' + parts[i+2] + ')s'
    return EMPTYSTRING.join(filter(None, parts))


def dollar_identifiers(s):
    """Return the set (dictionary) of identifiers found in a $-string."""
    d = {}
    for name in filter(None, [b or c or None for a, b, c in dre.findall(s)]):
        d[name] = 1
    return d


def percent_identifiers(s):
    """Return the set (dictionary) of identifiers found in a %-string."""
    d = {}
    for name in cre.findall(s):
        d[name] = 1
    return d



# Utilities to canonicalize a string, which means un-HTML-ifying the string to
# produce a Unicode string or an 8-bit string if all the characters are ASCII.
def canonstr(s, lang=None):
    newparts = []
    parts = re.split(r'&(?P<ref>[^;]+);', s)
    def appchr(i):
        if i < 256:
            newparts.append(chr(i))
        else:
            newparts.append(unichr(i))
    while 1:
        newparts.append(parts.pop(0))
        if not parts:
            break
        ref = parts.pop(0)
        if ref.startswith('#'):
            try:
                appchr(int(ref[1:]))
            except ValueError:
                # Non-convertable, stick with what we got
                newparts.append('&'+ref+';')
        else:
            c = htmlentitydefs.entitydefs.get(ref, '?')
            if c.startswith('#') and c.endswith(';'):
                appchr(int(ref[1:-1]))
            else:
                newparts.append(c)
    newstr = EMPTYSTRING.join(newparts)
    if isinstance(newstr, UnicodeType):
        return newstr
    # We want the default fallback to be iso-8859-1 even if the language is
    # English (us-ascii).  This seems like a practical compromise so that
    # non-ASCII characters in names can be used in English lists w/o having to
    # change the global charset for English from us-ascii (which I
    # superstitiously think my have unintended consequences).
    if lang is None:
        charset = 'iso-8859-1'
    else:
        charset = GetCharSet(lang)
        if charset == 'us-ascii':
            charset = 'iso-8859-1'
    return unicode(newstr, charset, 'replace')


# The opposite of canonstr() -- sorta.  I.e. it attempts to encode s in the
# charset of the given language, which is the character set that the page will
# be rendered in, and failing that, replaces non-ASCII characters with their
# html references.  It always returns a byte string.
def uncanonstr(s, lang=None):
    if s is None:
        s = u''
    if lang is None:
        charset = 'us-ascii'
    else:
        charset = GetCharSet(lang)
    # See if the string contains characters only in the desired character
    # set.  If so, return it unchanged, except for coercing it to a byte
    # string.
    try:
        if isinstance(s, UnicodeType):
            return s.encode(charset)
        else:
            u = unicode(s, charset)
            return s
    except UnicodeError:
        # Nope, it contains funny characters, so html-ref it
        return uquote(s)

def uquote(s):
    a = []
    for c in s:
        o = ord(c)
        if o > 127:
            a.append('&#%3d;' % o)
        else:
            a.append(c)
    # Join characters together and coerce to byte string
    return str(EMPTYSTRING.join(a))
