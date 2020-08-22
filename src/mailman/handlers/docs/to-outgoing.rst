====================
The outgoing handler
====================

Mailman's outgoing queue is used as the wrapper around SMTP delivery to the
upstream mail server.  The to-outgoing handler does little more than drop the
message into the outgoing queue.

    >>> from mailman.app.lifecycle import create_list
    >>> mlist = create_list('test@example.com')

Craft a message destined for the outgoing queue.  Include some random metadata
as if this message had passed through some other handlers.
::

    >>> from mailman.testing.helpers import (specialized_message_from_string
    ...   as message_from_string)   
    >>> msg = message_from_string("""\
    ... Subject: Here is a message
    ...
    ... Something of great import.
    ... """)

    >>> msgdata = dict(foo=1, bar=2, verp=True)
    >>> from mailman.config import config   
    >>> handler = config.handlers['to-outgoing']
    >>> handler.process(mlist, msg, msgdata)

While the queued message will not be changed, the queued metadata will have an
additional key set: the mailing list name.

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('out')
    >>> len(messages)
    1
    >>> print(messages[0].msg.as_string())
    Subject: Here is a message
    <BLANKLINE>
    Something of great import.
    >>> from mailman.testing.documentation import dump_msgdata    
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg: False
    bar      : 2
    foo      : 1
    listid   : test.example.com
    verp     : True
    version  : 3
