=======
Digests
=======

The ``digests`` rule matches when the posted message has a digest Subject:
header or quotes the digest masthead.  Generally this is used to prevent
replies to a digest with no meaningful Subject: or which quote the entire
digest from getting posted to the list.  This rule must be enabled by putting
``hold_digest: yes`` in the ``[mailman]`` section of the configuration.

    >>> from mailman.app.lifecycle import create_list
    >>> mlist = create_list('_xtest@example.com')
    >>> from mailman.config import config
    >>> rule = config.rules['digests']
    >>> print(rule.name)
    digests

If we enable the rule and post a message with a digest like Subject:, the
rule will hit.

    >>> from mailman.testing.helpers import (
    ...  configuration, specialized_message_from_string as message_from_string)
    >>> msg = message_from_string("""\
    ... From: anne@example.com
    ... To: _xtest@example.com
    ... Subject: Re: test Digest, Vol 1, Issue 1
    ... Message-ID: <ant>
    ...
    ... A message body.
    ... """)
    >>> with configuration('mailman', hold_digest='yes'):
    ...   rule.check(mlist, msg, {})
    True

Similarly, the rule will hit on a message with quotes of the digest masthead
regardless of the Subject:.

    >>> msg = message_from_string("""\
    ... From: anne@example.com
    ... To: _xtest@example.com
    ... Subject: Message Subject
    ... Message-ID: <ant>
    ...
    ... Send _xtest mailing list submissions to
    ...         _xtest@example.com
    ...
    ... To subscribe or unsubscribe via email, send a message with subject or body
    ... 'help' to
    ...         _xtest-request@example.com
    ...
    ... You can reach the person managing the list at
    ...         _xtest-owner@example.com
    ...
    ... When replying, please edit your Subject line so it is more specific than
    ... "Re: Contents of _xtest digest..."
    ... """)
    >>> with configuration('mailman', hold_digest='yes'):
    ...   rule.check(mlist, msg, {})
    True
