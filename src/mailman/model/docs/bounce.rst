=======
Bounces
=======

When a message to an email address bounces, Mailman's bounce runner will
register a bounce event.  This registration is done through a utility.

    >>> from zope.component import getUtility
    >>> from zope.interface.verify import verifyObject
    >>> from mailman.interfaces.bounce import IBounceProcessor
    >>> processor = getUtility(IBounceProcessor)
    >>> verifyObject(IBounceProcessor, processor)
    True


Registration
============

When a bounce occurs, it's always within the context of a specific mailing
list.

    >>> from mailman.app.lifecycle import create_list
    >>> mlist = create_list('test@example.com')
    >>> mlist.send_welcome_message = False

The bouncing email contains useful information that will be registered as
well.  In particular, the Message-ID is a key piece of data that needs to be
recorded.

    >>> from mailman.testing.helpers import (specialized_message_from_string
    ...   as message_from_string)
    >>> msg = message_from_string("""\
    ... From: mail-daemon@example.org
    ... To: test-bounces@example.com
    ... Message-ID: <first>
    ...
    ... """)

There is a suite of bounce detectors that are used to heuristically extract
the bouncing email addresses.  Various techniques are employed including VERP,
DSN, and magic.  It is the bounce runner's responsibility to extract the set
of bouncing email addresses.  These are passed one-by-one to the registration
interface.

    >>> event = processor.register(mlist, 'anne@example.com', msg)
    >>> print(event.list_id)
    test.example.com
    >>> print(event.email)
    anne@example.com
    >>> print(event.message_id)
    <first>

Bounce events have a timestamp.

    >>> print(event.timestamp)
    2005-08-01 07:49:23

Bounce events have a flag indicating whether they've been processed or not.

    >>> event.processed
    False

When a bounce is registered, you can indicate the bounce context.

    >>> msg = message_from_string("""\
    ... From: mail-daemon@example.org
    ... To: test-bounces@example.com
    ... Message-ID: <second>
    ...
    ... """)

If no context is given, then a default one is used.

    >>> event = processor.register(mlist, 'bart@example.com', msg)
    >>> print(event.message_id)
    <second>
    >>> print(event.context)
    BounceContext.normal

A probe bounce carries more weight than just a normal bounce.

    >>> from mailman.interfaces.bounce import BounceContext
    >>> event = processor.register(
    ...     mlist, 'bart@example.com', msg, BounceContext.probe)
    >>> print(event.message_id)
    <second>
    >>> print(event.context)
    BounceContext.probe


Processing
==========

Bounce events are periodically processed via Bounce Runner to take actions for
email addresses that bounce often. The first bounce in a day for an email
address, in the context of a Mailinglist, increases the bounce score of their
membership resource.

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> user_manager = getUtility(IUserManager)
    >>> bart = user_manager.create_address('bart@example.com')
    >>> bart_member = mlist.subscribe(bart)

Initially, every member's ``bounce_score`` is equal to 0.

    >>> print(bart_member.bounce_score)
    0

Once a ``normal`` bounce event is processed belonging to that member, the bounce
score is increased by ``1``:

    >>> event = processor.register(
    ...     mlist, 'bart@example.com', msg, BounceContext.normal)
    >>> print(event.message_id)
    <second>
    >>> processor.process_event(event)
    >>> print(event.processed)
    True
    >>> print(bart_member.bounce_score)
    1
    >>> print(bart_member.last_bounce_received)
    2005-08-01 07:49:23

However, ``bounce_score`` is bumped only once for a day, any other bounces for the
same day have no effect on the score:

    >>> event = processor.register(
    ...     mlist, 'bart@example.com', msg, BounceContext.normal)
    >>> print(event.message_id)
    <second>
    >>> processor.process_event(event)
    >>> print(event.processed)
    True
    >>> print(bart_member.bounce_score)
    1

Bounce score that is older than Mailinglist's configured
``bounce_info_stale_after`` number of days older is considered stale. It is
reset to 1.0 if a bounce event is received after that many number of days.

We pretend last bounce was received 10 days ago, more than MailingList's
``bounce_info_stale_after`` days

    >>> print(mlist.bounce_info_stale_after)
    7 days, 0:00:00
    >>> from mailman.utilities.datetime import now
    >>> from datetime import timedelta
    >>> bart_member.last_bounce_received = now() - timedelta(days=10)
    >>> bart_member.bounce_score = 5

Now, another event after 10 days will reset the score:

    >>> event = processor.register(
    ...     mlist, 'bart@example.com', msg, BounceContext.normal)
    >>> processor.process_event(event)
    >>> print(bart_member.bounce_score)
    1


DeliveryStatus
==============

If the ``bounce_score`` reaches the Mailinglist's configured
``bounce_score_threshold``, bouncing Member's delivery is suspended:

    >>> print(mlist.bounce_score_threshold)
    5
    >>> bart_member.last_bounce_received = now() - timedelta(days=1)
    >>> bart_member.bounce_score = 4
    >>> event = processor.register(
    ...     mlist, 'bart@example.com', msg, BounceContext.normal)
    >>> processor.process_event(event)
    >>> # Disabling delivery resets the score.
    >>> print(bart_member.bounce_score)
    0
    >>> print(bart_member.preferences.delivery_status)
    DeliveryStatus.by_bounces

If Mailinglist is configured to do so, a notice is sent out the owners when a
Member's delivery is disabled:

    >>> print(mlist.bounce_notify_owner_on_disable)
    True
    >>> from mailman.testing.helpers import get_queue_messages
    >>> items = get_queue_messages('virgin', expected_count=1)
    >>> print(items[0].msg['Subject'])
    bart@example.com's subscription disabled on Test


VERP Probes
===========

Instead of immediately suspending the delivery of a Member, Mailman can be
configured to send VERP probes to the sender after their bounce score has
reached the Mailinglist's threshold.

    >>> anne = user_manager.create_address('anne@example.com')
    >>> anne_member = mlist.subscribe(anne)
    >>> anne_member.bounce_score = 4
    >>> anne_member.last_bounce_received = now() - timedelta(days=1)

Next bounce event for anne should trigger a probe which resets bounce_score:

    >>> event = processor.register(
    ...    mlist, 'anne@example.com', msg, BounceContext.normal)
    >>> from mailman.testing.helpers import configuration
    >>> with configuration('mta', verp_probes='yes'):
    ...     processor.process_event(event)
    >>> print(anne_member.bounce_score)
    0
    >>> print(anne_member.preferences.delivery_status)
    None
    >>> items = get_queue_messages('virgin', expected_count=1)
    >>> msg = items[0].msg
    >>> print(msg.as_string())
    Subject: Test mailing list probe message
    From: test-bounces+...@example.com
    To: anne@example.com
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="..."
    Message-ID: ...
    Date: ...
    <BLANKLINE>
    ...
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    This is a probe message.  You can ignore this message.
    <BLANKLINE>
    The test@example.com mailing list has received a number of bounces
    from you, indicating that there may be a problem delivering messages
    to anne@example.com.  A sample is attached below.  Please examine this
    message to make sure there are no problems with your email address.
    You may want to check with your mail administrator for more help.
    <BLANKLINE>
    You don't need to do anything to remain an enabled member of the
    mailing list.
    <BLANKLINE>
    If you have any questions or problems, you can contact the mailing
    list owner at
    <BLANKLINE>
        test-owner@example.com
    <BLANKLINE>
    ...
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    From: mail-daemon@example.org
    To: test-bounces@example.com
    Message-ID: <second>
    ...

When such a probe bounces, their delivery is then suspended immediately:

    >>> event = processor.register(
    ...     mlist, 'anne@example.com', msg, BounceContext.probe)
    >>> processor.process_event(event)
    >>> print(anne_member.preferences.delivery_status)
    DeliveryStatus.by_bounces


Warnings and Unsubscription
===========================

When a Member's delivery is disabled, they will received a configured number of
warnings before they are removed as a subscriber of the mailing list.

    >>> print(mlist.bounce_you_are_disabled_warnings)
    3
    >>> # The warnings are sent after a configured interval.
    >>> print(mlist.bounce_you_are_disabled_warnings_interval)
    7 days, 0:00:00

For now, ``anne`` hasn't received any warnings:

    >>> print(anne_member.total_warnings_sent)
    0

..  >>> #flush the queue.
    >>> _ = get_queue_messages('virgin', expected_count=1)

Bounce Runner invokes BounceProcessor to sends these warnings periodically and
removes members when max number of warnings are sent.

    >>> processor.send_warnings_and_remove()
    >>> print(anne_member.total_warnings_sent)
    1
    >>> print(anne_member.last_warning_sent)
    2005-08-01 07:49:23
    >>> print(bart_member.total_warnings_sent)
    1
    >>> items = get_queue_messages('virgin', expected_count=2)
    >>> for item in sorted(items, key=lambda x: str(x.msg['to'])):
    ...     print('To: {}\nSubject: {}\n{}\n'.format(
    ...           item.msg['to'], item.msg['subject'], item.msg.get_payload()))
    To: anne@example.com
    Subject: Your subscription for Test mailing list has been disabled
    Your subscription has been disabled on the test@example.com mailing list
    because it has received a number of bounces indicating that there may
    be a problem delivering messages to anne@example.com.  You may want to
    check with your mail administrator for more help.
    <BLANKLINE>
    If you have any questions or problems, you can contact the mailing
    list owner at
    <BLANKLINE>
        test-owner@example.com
    <BLANKLINE>
    <BLANKLINE>
    To: bart@example.com
    Subject: Your subscription for Test mailing list has been disabled
    Your subscription has been disabled on the test@example.com mailing list
    because it has received a number of bounces indicating that there may
    be a problem delivering messages to bart@example.com.  You may want to
    check with your mail administrator for more help.
    <BLANKLINE>
    If you have any questions or problems, you can contact the mailing
    list owner at
    <BLANKLINE>
        test-owner@example.com
    <BLANKLINE>
    <BLANKLINE>


After Mailinglist's configured ``bounce_you_are_disabled_warnings`` have been
sent and another ``bounce_you_are_disabled_warnings_interval`` has elapsed:

    >>> print(mlist.bounce_you_are_disabled_warnings)
    3
    >>> anne_member.total_warnings_sent = 3
    >>> print(mlist.bounce_you_are_disabled_warnings_interval)
    7 days, 0:00:00
    >>> anne_member.last_warning_sent = (
    ...    now() - mlist.bounce_you_are_disabled_warnings_interval)

Now, the processor will unsubscribe ``anne``:

    >>> processor.send_warnings_and_remove()
    >>> print(mlist.members.get_member('anne@example.com'))
    None

If Mailinglist's ``bounce_notify_owner_on_removal`` is ``True``, owners will
receive a notification about the removal. ``anne`` will also be notified about
about the un-subscription, depending on how the list's ``send_goodby_message``
is configured to ``True``:

    >>> print(mlist.bounce_notify_owner_on_removal)
    True
    >>> print(mlist.send_goodbye_message)
    True
    >>> items = get_queue_messages('virgin', expected_count=2)
    >>> for item in sorted(items, key=lambda x: str(x.msg['to'])):
    ...     print(item.msg['to'], item.msg['subject'])   
    anne@example.com You have been unsubscribed from the Test mailing list
    test-owner@example.com anne@example.com unsubscribed from Test mailing list due to bounces
