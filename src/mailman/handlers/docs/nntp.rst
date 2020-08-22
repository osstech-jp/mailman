============
NNTP Gateway
============

Mailman has an NNTP gateway, whereby messages posted to the mailing list can
be forwarded onto an NNTP newsgroup.

    >>> from mailman.app.lifecycle import create_list
    >>> mlist = create_list('test@example.com')

Gatewaying from the mailing list to the newsgroup happens through a separate
``nntp`` queue and happen immediately when the message is posted through to
the list.  Note that gatewaying from the newsgroup to the list happens via a
separate process.

There are several situations which prevent a message from being gatewayed to
the newsgroup.  The feature could be disabled, as is the default.
::

    >>> mlist.gateway_to_news = False
    >>> from mailman.testing.helpers import (specialized_message_from_string
    ...   as message_from_string)    
    >>> msg = message_from_string("""\
    ... Subject: An important message
    ...
    ... Something of great import.
    ... """)

    >>> from mailman.config import config    
    >>> handler = config.handlers['to-usenet']
    >>> handler.process(mlist, msg, {})
    >>> from mailman.testing.helpers import get_queue_messages
    >>> get_queue_messages('nntp')
    []

Even if enabled, messages that came from the newsgroup are never gated back to
the newsgroup.

    >>> mlist.gateway_to_news = True
    >>> handler.process(mlist, msg, dict(fromusenet=True))
    >>> get_queue_messages('nntp')
    []

Neither are digests ever gated to the newsgroup.

    >>> handler.process(mlist, msg, dict(isdigest=True))
    >>> get_queue_messages('nntp')
    []

However, other posted messages get gated to the newsgroup via the nntp queue.
The list owner can set the linked newsgroup.  The nntp host that messages are
gated to is a global configuration.
::

    >>> mlist.linked_newsgroup = 'comp.lang.thing'
    >>> handler.process(mlist, msg, {})
    >>> messages = get_queue_messages('nntp')
    >>> len(messages)
    1

    >>> print(messages[0].msg.as_string())
    Subject: An important message
    <BLANKLINE>
    Something of great import.
    <BLANKLINE>

    >>> from mailman.testing.documentation import dump_msgdata    
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg: False
    listid   : test.example.com
    version  : 3
