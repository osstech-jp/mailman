=================
Cleansing headers
=================

All messages posted to a list get their headers cleansed.  Some headers are
related to additional permissions that can be granted to the message and other
headers can be used to fish for membership.

    >>> from mailman.app.lifecycle import create_list
    >>> mlist = create_list('_xtest@example.com')

Headers such as ``Approved``, ``Approve``, (as well as their ``X-`` variants)
and ``Urgent`` are used to grant special permissions to individual messages.
All may contain a password; the first two headers are used by list
administrators to pre-approve a message normal held for approval.  The latter
header is used to send a regular message to all members, regardless of whether
they get digests or not.  Because all three headers contain passwords, they
must be removed from any posted message.  ::

    >>> from mailman.testing.helpers import (specialized_message_from_string
    ...   as message_from_string)
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Approved: foobar
    ... Approve: barfoo
    ... X-Approved: bazbar
    ... X-Approve: barbaz
    ... Urgent: notreally
    ... Subject: A message of great import
    ...
    ... Blah blah blah
    ... """)

    >>> from mailman.config import config    
    >>> handler = config.handlers['cleanse']
    >>> handler.process(mlist, msg, {})
    >>> print(msg.as_string())
    From: aperson@example.com
    Subject: A message of great import
    <BLANKLINE>
    Blah blah blah
    <BLANKLINE>

Other headers can be used by list members to fish the list for membership, so
we don't let them go through.  These are a mix of standard headers and custom
headers supported by some mail readers.  For example, ``X-PMRC`` is supported
by Pegasus mail.  I don't remember what program uses ``X-Confirm-Reading-To``
though (Some Microsoft product perhaps?).

    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ... Reply-To: bperson@example.org
    ... Sender: asystem@example.net
    ... Return-Receipt-To: another@example.com
    ... Disposition-Notification-To: athird@example.com
    ... X-Confirm-Reading-To: afourth@example.com
    ... X-PMRQC: afifth@example.com
    ... Subject: a message to you
    ...
    ... How are you doing?
    ... """)
    >>> handler.process(mlist, msg, {})
    >>> print(msg.as_string())
    From: bperson@example.com
    Reply-To: bperson@example.org
    Sender: asystem@example.net
    Subject: a message to you
    <BLANKLINE>
    How are you doing?
    <BLANKLINE>


Anonymous lists
===============

Anonymous mailing lists also try to cleanse certain identifying headers from
the original posting, so that it is at least a bit more difficult to determine
who sent the message.  This isn't perfect though, for example, the body of the
messages are never scrubbed (though that might not be a bad idea).  The
``From`` and ``Reply-To`` headers in the posted message are taken from list
attributes.  ``Message-ID`` can reveal the poster's domain, so it is replaced.

Hotmail apparently sets ``X-Originating-Email``.

    >>> mlist.anonymous_list = True
    >>> mlist.description = 'A Test Mailing List'
    >>> mlist.preferred_language = 'en'
    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ... Reply-To: bperson@example.org
    ... Sender: asystem@example.net
    ... X-Originating-Email: cperson@example.com
    ... Message-ID: <99999@example.com>
    ... Subject: a message to you
    ...
    ... How are you doing?
    ... """)
    >>> handler.process(mlist, msg, {})
    >>> print(msg.as_string())
    Subject: a message to you
    Message-ID: ...
    From: A Test Mailing List <_xtest@example.com>
    Reply-To: _xtest@example.com
    <BLANKLINE>
    How are you doing?
    <BLANKLINE>

In addition to removing all the headers that we know might reveal the poster's
address or domain, we also then remove any of the remaining headers whose names
don't match a pattern in the ``anonymous_list_keep_headers setting`` in the
``[mailman]`` section of ``mailman.cfg``.  This is how that setting is
described::

  # This is a space separated list of regexps which match headers to be kept
  # in messages to anonymous lists.  Many headers are removed from posts to
  # anonymous lists before this is consulted, but of the remaining headers,
  # any that don't match one of these patterns are also removed.  The headers
  # kept by default are non X- headers, those X- headers added by Mailman
  # and any X-Spam- headers.  The match is case-insensitive.
  anonymous_list_keep_headers: ^(?!x-) ^x-mailman- ^x-content-filtered-by:
   ^x-topics: ^x-ack: ^x-beenthere: ^x-list-administrivia: ^x-spam-

So we see for a message with unknown ``X-`` headers that those headers are
also removed, but the known ``X-Mailman-Version`` header is not.

    >>> mlist.anonymous_list = True
    >>> mlist.description = 'A Test Mailing List'
    >>> mlist.preferred_language = 'en'
    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ... Reply-To: bperson@example.org
    ... Sender: asystem@example.net
    ... X-Originating-Email: cperson@example.com
    ... X-Maybe-From: bperson@example.com
    ... X-Some-Other-Unknown: What's this
    ... X-Mailman-Version: 3.3.4
    ... Message-ID: <99999@example.com>
    ... Subject: a message to you
    ...
    ... How are you doing?
    ... """)
    >>> handler.process(mlist, msg, {})
    >>> print(msg.as_string())
    X-Mailman-Version: 3.3.4
    Subject: a message to you
    Message-ID: ...
    From: A Test Mailing List <_xtest@example.com>
    Reply-To: _xtest@example.com
    <BLANKLINE>
    How are you doing?
    <BLANKLINE>
