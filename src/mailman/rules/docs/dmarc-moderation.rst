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

    >>> mlist.dmarc_moderation_action = DMARCModerationAction.discard
    >>> msg = message_from_string("""\
    ... From: aperson@yahoo.com
    ... To: _xtest@example.com
    ... Subject: A posted message
    ... Message-ID: <xxx_message_id@yahoo.com>
    ...
    ... """)
    >>> msgdata = {}
    >>> rule.check(mlist, msg, msgdata)
    True
    >>> msgdata['dmarc']
    True
    >>> msgdata['moderation_action']
    'discard'

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
    >>> rule.check(mlist, msg, msgdata)
    True
    >>> msgdata['dmarc']
    True
    >>> msgdata['moderation_action']
    'reject'
    >>> msgdata['moderation_reasons']
    ['You are not allowed to post to this mailing list From: a domain ...

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
    >>> rule.check(mlist, msg, msgdata)
    True
    >>> msgdata['dmarc']
    True
    >>> msgdata['moderation_action']
    'reject'
    >>> msgdata['moderation_reasons']
    ['A silly reason']
