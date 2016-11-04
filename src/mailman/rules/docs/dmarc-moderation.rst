================
DMARC moderation
================

This rule is different from others in that it never matches bucause a match
would cause the message to be held.  The rule looks at the list's
dmarc_moderation_policy and if it is other than 'none', it checks the domain
of the From: address for a DMARC policy and depending on settings may reject
or discard the message or just flag in for the dmarc handler to apply DMARC
mitigations to the message.

    >>> mlist = create_list('_xtest@example.com')
    >>> rule = config.rules['dmarc-moderation']
    >>> print(rule.name)
    dmarc-moderation

A message From: a domain without a DMARC policy does not set any flags.

    >>> from mailman.interfaces.mailinglist import DMARCModerationAction
    >>> mlist.dmarc_moderation_action = DMARCModerationAction.munge_from
    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: _xtest@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> msgdata = {}
    >>> rule.check(mlist, msg, msgdata)
    False
    >>> msgdata == {}
    True

Even if the From: domain publishes p=reject, no flags are set if the list's
action is none.

    >>> mlist.dmarc_moderation_action = DMARCModerationAction.none
    >>> msg = message_from_string("""\
    ... From: aperson@yahoo.com
    ... To: _xtest@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> msgdata = {}
    >>> rule.check(mlist, msg, msgdata)
    False
    >>> msgdata == {}
    True

But with a different list setting, the message is flagged.

    >>> mlist.dmarc_moderation_action = DMARCModerationAction.munge_from
    >>> msg = message_from_string("""\
    ... From: aperson@yahoo.com
    ... To: _xtest@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> msgdata = {}
    >>> rule.check(mlist, msg, msgdata)
    False
    >>> msgdata['dmarc']
    True

Subdomains which don't have a policy will check the organizational domain.

    >>> msg = message_from_string("""\
    ... From: aperson@sub.domain.yahoo.com
    ... To: _xtest@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> msgdata = {}
    >>> rule.check(mlist, msg, msgdata)
    False
    >>> msgdata['dmarc']
    True

The list's action can also be set to immediately discard or reject the
message.

    >>> from mailman.interfaces.chain import ChainEvent
    >>> from mailman.testing.helpers import event_subscribers
    >>> def handler(event):
    ...     if isinstance(event, ChainEvent):
    ...         print(event.__class__.__name__,
    ...               event.chain.name, event.msg['message-id'])
    >>> mlist.dmarc_moderation_action = DMARCModerationAction.discard
    >>> msg = message_from_string("""\
    ... From: aperson@yahoo.com
    ... To: _xtest@example.com
    ... Subject: A posted message
    ... Message-ID: <xxx_message_id@yahoo.com>
    ...
    ... """)
    >>> msgdata = {}
    >>> with event_subscribers(handler):
    ...     rule.check(mlist, msg, msgdata)
    DiscardEvent discard <xxx_message_id@yahoo.com>
    False
    >>> msgdata['dmarc']
    True

We can reject the message with a default reason.

    >>> mlist.dmarc_moderation_action = DMARCModerationAction.reject
    >>> msg = message_from_string("""\
    ... From: aperson@yahoo.com
    ... To: _xtest@example.com
    ... Subject: A posted message
    ... Message-ID: <xxx_message_id@yahoo.com>
    ...
    ... """)
    >>> msgdata = {}
    >>> with event_subscribers(handler):
    ...     rule.check(mlist, msg, msgdata)
    RejectEvent reject <xxx_message_id@yahoo.com>
    False
    >>> msgdata['dmarc']
    True

There is now a reject message in the virgin queue.

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1
    >>> print(messages[0].msg.as_string())
    Subject: A posted message
    From: _xtest-owner@example.com
    To: aperson@yahoo.com
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="..."
    Message-ID: <...>
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    --...
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    <BLANKLINE>
    Your message to the _xtest mailing-list was rejected for the following
    reasons:
    <BLANKLINE>
    You are not allowed to post to this mailing list From: a domain which
    publishes a DMARC policy of reject or quarantine, and your message has
    been automatically rejected.  If you think that your messages are
    being rejected in error, contact the mailing list owner at
    _xtest-owner@example.com.
    <BLANKLINE>
    The original message as received by Mailman is attached.
    <BLANKLINE>
    --...
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    From: aperson@yahoo.com
    To: _xtest@example.com
    Subject: A posted message
    Message-ID: <xxx_message_id@yahoo.com>
    X-Mailman-Rule-Hits: dmarc-moderation
    <BLANKLINE>
    <BLANKLINE>
    --...--
    <BLANKLINE>

And, we can reject with a custom message.

    >>> mlist.dmarc_moderation_notice = 'A silly reason'
    >>> msg = message_from_string("""\
    ... From: aperson@yahoo.com
    ... To: _xtest@example.com
    ... Subject: A posted message
    ... Message-ID: <xxx_message_id@yahoo.com>
    ...
    ... """)
    >>> msgdata = {}
    >>> with event_subscribers(handler):
    ...     rule.check(mlist, msg, msgdata)
    RejectEvent reject <xxx_message_id@yahoo.com>
    False
    >>> msgdata['dmarc']
    True

Check the the virgin queue.

    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1
    >>> print(messages[0].msg.as_string())
    Subject: A posted message
    From: _xtest-owner@example.com
    To: aperson@yahoo.com
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="..."
    Message-ID: <...>
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    --...
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    <BLANKLINE>
    Your message to the _xtest mailing-list was rejected for the following
    reasons:
    <BLANKLINE>
    A silly reason
    <BLANKLINE>
    The original message as received by Mailman is attached.
    <BLANKLINE>
    --...
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    From: aperson@yahoo.com
    To: _xtest@example.com
    Subject: A posted message
    Message-ID: <xxx_message_id@yahoo.com>
    X-Mailman-Rule-Hits: dmarc-moderation
    <BLANKLINE>
    <BLANKLINE>
    --...--
    <BLANKLINE>
