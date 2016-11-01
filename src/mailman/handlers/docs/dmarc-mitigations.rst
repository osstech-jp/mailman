=================
DMARC Mitigations
=================

In order to mitigate the effects of DMARC on mailing list traffic, list
administrators have the ability to apply transformations to messages delivered
to list members.  These transformations are applied only to individual messages
sent to list members and not to messages in digests, archives or gated to
usenet.

The messages can be transformed by either munging the From: header and putting
original From: in Cc: or Reply-To: or by wrapping the original message in an
outer message From: the list.

Exactly what transformations are applied depends on a number of list settings.

The settings and their effects are:

 * anonymous_list: If True, no mitigations are ever applied because the message
   is already From: the list.
 * dmarc_moderation_action: The action to apply to messages From: a domain
   publishing a DMARC policy of reject and possibly quarantine or none.
 * dmarc_quarantine_moderation_action: A flag to apply dmarc_moderation_action
   to messages From: a domain publishing a DMARC policy of quarantine.
 * dmarc_none_moderation_action: A flag to apply dmarc_moderation_action to
   messages From: a domain publishing a DMARC policy of none, but only when
   dmarc_quarantine_moderation_action is also true.
 * dmarc_moderation_notice: Text to include in any rejection notice to be sent
   when dmarc_moderation_action of reject applies.
 * dmarc_wrapped_message_text: Text to be added as a separate text/plain MIME
   part preceding the original message part in the wrapped message when
   dmarc_moderation_action of wrap_message applies.
 * from_is_list: The action to be applied to all messages for which
   dmarc_moderation_action is none or not applicable.
 * reply_goes_to_list: If this is set to other than no_munging of Reply-To,
   the original From: goes in Cc: rather than Reply-To:.

The possible actions for both dmarc_moderation_action and from_is_list are:

 * none: Make no transformation to the message.
 * munge_from: Change the From: header and put the original From: in Reply-To:
   or in some cases Cc:
 * wrap_message: Wrap the message in an outer message with headers as in
   munge_from.

In addition, there are two more possible actions for dmarc_moderation_action
only:

 * reject: Bounce the message back to the sender with a default reason or one
   supplied in dmarc_moderation_notice.
 * discard: Silently discard the message.

Here's what happens when we munge the From:

    >>> from mailman.interfaces.mailinglist import (DMARCModerationAction,
    ... ReplyToMunging)
    >>> mlist = create_list('test@example.com')
    >>> mlist.dmarc_moderation_action = DMARCModerationAction.munge_from
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

    >>> mlist.dmarc_moderation_action = DMARCModerationAction.wrap_message
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

