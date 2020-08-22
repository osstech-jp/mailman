=======
Unshunt
=======

When errors occur while processing email messages, the messages will end up in
the ``shunt`` queue.  The ``unshunt`` command allows system administrators to
manage the shunt queue.
::

    >>> from mailman.testing.documentation import cli   
    >>> command = cli('mailman.commands.cli_unshunt.unshunt')

Let's say there is a message in the shunt queue.
::

    >>> from mailman.testing.helpers import (specialized_message_from_string
    ...   as message_from_string)   
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: A broken message
    ... Message-ID: <aardvark>
    ...
    ... """)

    >>> from mailman.config import config    
    >>> shuntq = config.switchboards['shunt']
    >>> len(list(shuntq.files))
    0
    >>> base_name = shuntq.enqueue(msg, {})
    >>> len(list(shuntq.files))
    1

The ``unshunt`` command by default moves the message back to the incoming
queue.
::

    >>> inq = config.switchboards['in']
    >>> len(list(inq.files))
    0

    >>> command('mailman unshunt')

    >>> from mailman.testing.helpers import get_queue_messages
    >>> items = get_queue_messages('in')
    >>> len(items)
    1
    >>> print(items[0].msg.as_string())
    From: aperson@example.com
    To: test@example.com
    Subject: A broken message
    Message-ID: <aardvark>
    <BLANKLINE>
    <BLANKLINE>

``unshunt`` moves all shunt queue messages.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: A broken message
    ... Message-ID: <badgers>
    ...
    ... """)
    >>> base_name = shuntq.enqueue(msg, {})

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: A broken message
    ... Message-ID: <crow>
    ...
    ... """)
    >>> base_name = shuntq.enqueue(msg, {})

    >>> len(list(shuntq.files))
    2

    >>> command('mailman unshunt')
    >>> items = get_queue_messages('in')
    >>> len(items)
    2

    >>> sorted(item.msg['message-id'] for item in items)
    ['<badgers>', '<crow>']


Return to the original queue
============================

While the messages in the shunt queue are generally returned to the incoming
queue, if the error occurred while the message was being processed from a
different queue, it will be returned to the queue it came from.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: A broken message
    ... Message-ID: <dingo>
    ...
    ... """)

The queue that the message comes from is in message metadata.
::

    >>> base_name = shuntq.enqueue(msg, {}, whichq='bounces')

    >>> len(list(shuntq.files))
    1
    >>> len(list(config.switchboards['bounces'].files))
    0

The message is automatically re-queued to the bounces queue.
::

    >>> command('mailman unshunt')
    >>> len(list(shuntq.files))
    0
    >>> items = get_queue_messages('bounces')
    >>> len(items)
    1

    >>> print(items[0].msg.as_string())
    From: aperson@example.com
    To: test@example.com
    Subject: A broken message
    Message-ID: <dingo>
    <BLANKLINE>
    <BLANKLINE>


Discarding all shunted messages
===============================

If you don't care about the shunted messages, just discard them.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: A broken message
    ... Message-ID: <elephant>
    ...
    ... """)
    >>> base_name = shuntq.enqueue(msg, {})

    >>> command('mailman unshunt --discard')

The messages are now gone.

    >>> items = get_queue_messages('in')
    >>> len(items)
    0
