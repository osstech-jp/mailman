================
DMARC mitigation
================

This rule only matches in order to jump to the moderation chain to reject
or discard the message.  The rule looks at the list's dmarc_mitigate_action
and if it is other than 'no_mitigation', it checks the domain of the From:
address for a DMARC policy and depending on settings may reject or discard
the message or just flag it for the dmarc handler to apply DMARC mitigations
to the message.

    >>> mlist = create_list('_xtest@example.com')
    >>> rule = config.rules['dmarc-mitigation']
    >>> print(rule.name)
    dmarc-mitigation

First we set up a mock patcher to return predictable responses to DNS lookups.
This returns p=reject for the example.biz domain and not for any others.

    >>> from mailman.rules.tests.test_dmarc import get_dns_resolver
    >>> patcher = get_dns_resolver()

And we do a similar thing to mock the organizational domain data.

    >>> from mailman.rules.tests.test_dmarc import get_org_data
    >>> patcher2 = get_org_data()


A message From: a domain without a DMARC policy does not set any flags.

    >>> from mailman.interfaces.mailinglist import DMARCMitigateAction
    >>> mlist.dmarc_mitigate_action = DMARCMitigateAction.munge_from
    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: _xtest@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> msgdata = {}
    >>> with patcher as Resolver, patcher2 as urlopen:
    ...     rule.check(mlist, msg, msgdata)
    False
    >>> msgdata == {}
    True

Even if the From: domain publishes p=reject, no flags are set if the list's
action is no_mitigation.

    >>> mlist.dmarc_mitigate_action = DMARCMitigateAction.no_mitigation
    >>> msg = message_from_string("""\
    ... From: aperson@example.biz
    ... To: _xtest@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> msgdata = {}
    >>> with patcher as Resolver, patcher2 as urlopen:
    ...     rule.check(mlist, msg, msgdata)
    False
    >>> msgdata == {}
    True

But with a different list setting, the message is flagged.

    >>> mlist.dmarc_mitigate_action = DMARCMitigateAction.munge_from
    >>> msg = message_from_string("""\
    ... From: aperson@example.biz
    ... To: _xtest@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> msgdata = {}
    >>> with patcher as Resolver, patcher2 as urlopen:
    ...     rule.check(mlist, msg, msgdata)
    False
    >>> msgdata['dmarc']
    True

Subdomains which don't have a policy will check the organizational domain.

    >>> msg = message_from_string("""\
    ... From: aperson@sub.domain.example.biz
    ... To: _xtest@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> msgdata = {}
    >>> with patcher as Resolver, patcher2 as urlopen:
    ...     rule.check(mlist, msg, msgdata)
    False
    >>> msgdata['dmarc']
    True

The list's action can also be set to immediately discard or reject the
message.

    >>> mlist.dmarc_mitigate_action = DMARCMitigateAction.discard
    >>> msg = message_from_string("""\
    ... From: aperson@example.biz
    ... To: _xtest@example.com
    ... Subject: A posted message
    ... Message-ID: <xxx_message_id@example.biz>
    ...
    ... """)
    >>> msgdata = {}
    >>> with patcher as Resolver, patcher2 as urlopen:
    ...     rule.check(mlist, msg, msgdata)
    True
    >>> msgdata['dmarc']
    True
    >>> msgdata['moderation_action']
    'discard'

We can reject the message with a default reason.

    >>> mlist.dmarc_mitigate_action = DMARCMitigateAction.reject
    >>> msg = message_from_string("""\
    ... From: aperson@example.biz
    ... To: _xtest@example.com
    ... Subject: A posted message
    ... Message-ID: <xxx_message_id@example.biz>
    ...
    ... """)
    >>> msgdata = {}
    >>> with patcher as Resolver, patcher2 as urlopen:
    ...     rule.check(mlist, msg, msgdata)
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
    ... From: aperson@example.biz
    ... To: _xtest@example.com
    ... Subject: A posted message
    ... Message-ID: <xxx_message_id@example.biz>
    ...
    ... """)
    >>> msgdata = {}
    >>> with patcher as Resolver, patcher2 as urlopen:
    ...     rule.check(mlist, msg, msgdata)
    True
    >>> msgdata['dmarc']
    True
    >>> msgdata['moderation_action']
    'reject'
    >>> msgdata['moderation_reasons']
    ['A silly reason']
