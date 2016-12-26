=================
DMARC Mitigations
=================

In order to mitigate the effects of DMARC_ on mailing list traffic, list
administrators have the ability to apply transformations to messages delivered
to list members.  These transformations are applied only to individual messages
sent to list members and not to messages in digests, archives, or gated to
USENET.

The messages can be transformed by either munging the From: header and putting
original From: in Cc: or Reply-To: or by wrapping the original message in an
outer message From: the list.

Exactly what transformations are applied depends on a number of list settings.

The settings and their effects are:

``anonymous_list``
   If True, no mitigations are ever applied because the message
   is already From: the list.
``dmarc_mitigate_action``
   The action to apply to messages From: a domain
   publishing a DMARC policy of reject or quarantine or to all messages
   depending on the next setting.
``dmarc_mitigate_unconditionally``
   A Flag to apply dmarc_mitigate_action to all messages, but only if
   dmarc_mitigate_action is neither reject or discard.
``dmarc_moderation_notice``
   Text to include in any rejection notice to be sent
   when dmarc_policy_mitigation of reject applies.  This overrides the bult-in
   default text.
``dmarc_wrapped_message_text``
   Text to be added as a separate text/plain MIME
   part preceding the original message part in the wrapped message when a
   wrap_message mitigation applies.  If this is not provided the separate
   text/plain MIME part is not added.
``reply_goes_to_list``
   If this is set to other than no_munging of Reply-To,
   the original From: goes in Cc: rather than Reply-To:.  This is intended to
   make MUA functions of reply and reply-all have the same effect with
   messages to which mitigations have been applied as they do with other
   messages.

The possible actions for dmarc_mitigate_action are:

``no_mitigation``
   Make no transformation to the message.
``munge_from``
   Change the From: header and put the original From: in Reply-To:
   or in some cases Cc:
``wrap_message``
   Wrap the message in an outer message with headers as in
   munge_from.
``reject``
   Bounce the message back to the sender with a default reason or one
   supplied in dmarc_moderation_notice.
``discard``
   Silently discard the message.

Here's what happens when we munge the From.

    >>> from mailman.interfaces.mailinglist import (DMARCMitigateAction,
    ... ReplyToMunging)
    >>> mlist = create_list('test@example.com')
    >>> mlist.dmarc_mitigate_action = DMARCMitigateAction.munge_from
    >>> mlist.reply_goes_to_list = ReplyToMunging.no_munging
    >>> msg = message_from_string("""\
    ... From: A Person <aperson@example.com>
    ... To: test@example.com
    ...
    ... A message of great import.
    ... """)
    >>> msgdata = dict(dmarc=True, original_sender='aperson@example.com')
    >>> from mailman.handlers.dmarc import process
    >>> process(mlist, msg, msgdata)
    >>> print(msg.as_string())
    To: test@example.com
    From: A Person via Test <test@example.com>
    Reply-To: A Person <aperson@example.com>
    <BLANKLINE>
    A message of great import.
    <BLANKLINE>
    
Here we wrap the message without adding a text part.

    >>> mlist.dmarc_mitigate_action = DMARCMitigateAction.wrap_message
    >>> mlist.dmarc_wrapped_message_text = ''
    >>> msg = message_from_string("""\
    ... From: A Person <aperson@example.com>
    ... To: test@example.com
    ...
    ... A message of great import.
    ... """)
    >>> msgdata = dict(dmarc=True, original_sender='aperson@example.com')
    >>> process(mlist, msg, msgdata)
    >>> print(msg.as_string())
    To: test@example.com
    MIME-Version: 1.0
    Message-ID: <...>
    From: A Person via Test <test@example.com>
    Reply-To: A Person <aperson@example.com>
    Content-Type: message/rfc822
    Content-Disposition: inline
    <BLANKLINE>
    From: A Person <aperson@example.com>
    To: test@example.com
    <BLANKLINE>
    A message of great import.
    <BLANKLINE>

And here's a wrapped message with an added text part.

    >>> mlist.dmarc_wrapped_message_text = 'The original message is attached.'
    >>> msg = message_from_string("""\
    ... From: A Person <aperson@example.com>
    ... To: test@example.com
    ...
    ... A message of great import.
    ... """)
    >>> msgdata = dict(dmarc=True, original_sender='aperson@example.com')
    >>> process(mlist, msg, msgdata)
    >>> print(msg.as_string())
    To: test@example.com
    MIME-Version: 1.0
    Message-ID: <...>
    From: A Person via Test <test@example.com>
    Reply-To: A Person <aperson@example.com>
    Content-Type: multipart/mixed; boundary="..."
    <BLANKLINE>
    --...
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    Content-Disposition: inline
    <BLANKLINE>
    The original message is attached.
    --...
    Content-Type: message/rfc822
    MIME-Version: 1.0
    Content-Disposition: inline
    <BLANKLINE>
    From: A Person <aperson@example.com>
    To: test@example.com
    <BLANKLINE>
    A message of great import.
    <BLANKLINE>
    --...--
    <BLANKLINE>

.. _DMARC: https://wikipedia.org/wiki/DMARC
