==============
After delivery
==============

After a message is delivered, or more correctly, after it has been processed
by the rest of the handlers in the incoming queue pipeline, a couple of
bookkeeping pieces of information are updated.

    >>> from datetime import timedelta
    >>> from mailman.utilities.datetime import now
    >>> from mailman.app.lifecycle import create_list    
    >>> mlist = create_list('_xtest@example.com')
    >>> post_time = now() - timedelta(minutes=10)
    >>> mlist.last_post_at = post_time
    >>> mlist.post_id = 10

Processing a message with this handler updates the last_post_at and post_id
attributes.
::
   
    >>> from mailman.testing.helpers import (specialized_message_from_string
    ...   as message_from_string)
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... Something interesting.
    ... """)

    >>> from mailman.config import config    
    >>> handler = config.handlers['after-delivery']
    >>> handler.process(mlist, msg, {})
    >>> mlist.last_post_at > post_time
    True
    >>> mlist.post_id
    11
