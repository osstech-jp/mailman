=========================
 Subscription moderation
=========================

Subscription (and sometimes unsubscription) requests can similarly be
accepted, discarded, rejected, or deferred by the list moderators.


Viewing subscription requests
=============================

A mailing list starts with no pending subscription or unsubscription requests.

    >>> from mailman.app.lifecycle import create_list
    >>> ant = create_list('ant@example.com')
    >>> ant.admin_immed_notify = False
    >>> from mailman.interfaces.mailinglist import SubscriptionPolicy
    >>> ant.subscription_policy = SubscriptionPolicy.moderate
    >>> from mailman.config import config
    >>> transaction = config.db    
    >>> transaction.commit()
    >>> from mailman.testing.documentation import dump_json    
    >>> dump_json('http://localhost:9001/3.0/lists/ant.example.com/requests')
    http_etag: "..."
    start: 0
    total_size: 0

When Anne tries to subscribe to the Ant list, her subscription is held for
moderator approval.  Her email address is pre-verified and her subscription
request is pre-confirmed, but because the mailing list is moderated, a token
is returned to track her subscription request.

    >>> dump_json('http://localhost:9001/3.0/members', {
    ...           'list_id': 'ant.example.com',
    ...           'subscriber': 'anne@example.com',
    ...           'display_name': 'Anne Person',
    ...           'pre_verified': True,
    ...           'pre_confirmed': True,
    ...           })
    http_etag: ...
    token: 0000000000000000000000000000000000000001
    token_owner: moderator

The subscription request can be viewed in the REST API.

    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/lists/ant.example.com/requests')
    entry 0:
        display_name: Anne Person
        email: anne@example.com
        http_etag: "..."
        list_id: ant.example.com
        token: 0000000000000000000000000000000000000001
        token_owner: moderator
        type: subscription
        when: 2005-08-01T07:49:23
    http_etag: "..."
    start: 0
    total_size: 1


Viewing individual requests
===========================

You can view an individual membership change request by providing the token
(a.k.a. request id).  Anne's subscription request looks like this.

    >>> dump_json('http://localhost:9001/3.0/lists/ant.example.com/'
    ...           'requests/0000000000000000000000000000000000000001')
    display_name: Anne Person
    email: anne@example.com
    http_etag: "..."
    list_id: ant.example.com
    token: 0000000000000000000000000000000000000001
    token_owner: moderator
    type: subscription
    when: 2005-08-01T07:49:23


Disposing of subscription requests
==================================

Moderators can dispose of held subscription requests by POSTing back to the
request's resource.  The POST data requires an action of one of the following:

 * discard - throw the request away.
 * reject - the request is denied and a notification is sent to the email
   address requesting the membership change.
 * defer - defer any action on this membership change (continue to hold it).
 * accept - accept the membership change.

Anne's subscription request is accepted.

    >>> dump_json('http://localhost:9001/3.0/lists/ant.example.com/requests'
    ...           '/0000000000000000000000000000000000000001',
    ...           {'action': 'accept'})
    date: ...
    server: ...
    status: 204

Anne is now a member of the mailing list.

    >>> ant.members.get_member('anne@example.com')
    <Member: Anne Person <anne@example.com> on ant@example.com
             as MemberRole.member>

There are no more membership change requests.

    >>> dump_json('http://localhost:9001/3.0/lists/ant.example.com/requests')
    http_etag: "..."
    start: 0
    total_size: 0


..  >>> # Clear the virgin queue.
    >>> from mailman.testing.helpers import get_queue_messages
	  >>> items = get_queue_messages('virgin')

When rejecting subscription requests, an optional reason can be specified. When
Bart tries to subscribe to Ant mailing list, the request is held for moderator
approval::

    >>> dump_json('http://localhost:9001/3.0/members', {
    ...           'list_id': 'ant.example.com',
    ...           'subscriber': 'bperson@example.com',
    ...           'display_name': 'Bart Person',
    ...           'pre_verified': True,
    ...           'pre_confirmed': True,
    ...           })
    http_etag: ...
    token: 0000000000000000000000000000000000000002
    token_owner: moderator


The moderator can then reject the request stating the reason for rejection::

    >>> dump_json('http://localhost:9001/3.0/lists/ant.example.com/requests'
    ...           '/0000000000000000000000000000000000000002',
    ...           {'action': 'reject', 'reason': 'This is a private list'})
    date: ...
    server: ...
    status: 204

This will send an email to Bart with the rejection reason::

    >>> from mailman.testing.helpers import get_queue_messages
	  >>> items = get_queue_messages('virgin')
    >>> message = items[0].msg
    >>> print(message.as_string())
    MIME-Version: 1.0
		...
    <BLANKLINE>
    Your request to the ant@example.com mailing list
    <BLANKLINE>
        Subscription request
    <BLANKLINE>
    has been rejected by the list moderator.  The moderator gave the
    following reason for rejecting your request:
    <BLANKLINE>
    "This is a private list"
    <BLANKLINE>
    Any questions or comments should be directed to the list administrator
    at:
    <BLANKLINE>
        ant-owner@example.com
    <BLANKLINE>
