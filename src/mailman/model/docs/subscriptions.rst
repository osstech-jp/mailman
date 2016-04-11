=====================
Subscription services
=====================

The ``ISubscriptionService`` utility provides higher level convenience methods
useful for searching, retrieving, iterating, and removing memberships across
all mailing lists on th esystem.  Adding new users is handled by the
``IRegistrar`` interface.

    >>> from mailman.interfaces.subscriptions import ISubscriptionService
    >>> from zope.component import getUtility
    >>> service = getUtility(ISubscriptionService)

You can use the service to get all members of all mailing lists, for any
membership role.  At first, there are no memberships.

    >>> service.get_members()
    []
    >>> sum(1 for member in service)
    0
    >>> from uuid import UUID
    >>> print(service.get_member(UUID(int=801)))
    None


Listing members
===============

When there are some members, of any role on any mailing list, they can be
retrieved through the subscription service.

    >>> from mailman.app.lifecycle import create_list
    >>> ant = create_list('ant@example.com')
    >>> bee = create_list('bee@example.com')
    >>> cat = create_list('cat@example.com')

Some people become members.

    >>> from mailman.interfaces.member import MemberRole
    >>> from mailman.testing.helpers import subscribe
    >>> anne_1 = subscribe(ant, 'Anne')
    >>> anne_2 = subscribe(ant, 'Anne', MemberRole.owner)
    >>> bart_1 = subscribe(ant, 'Bart', MemberRole.moderator)
    >>> bart_2 = subscribe(bee, 'Bart', MemberRole.owner)
    >>> anne_3 = subscribe(cat, 'Anne', email='anne@example.com')
    >>> cris_1 = subscribe(cat, 'Cris')

The service can be used to iterate over them.

    >>> for member in service.get_members():
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.moderator>
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Bart Person <bperson@example.com>
        on bee@example.com as MemberRole.owner>
    <Member: Anne Person <anne@example.com>
        on cat@example.com as MemberRole.member>
    <Member: Cris Person <cperson@example.com>
        on cat@example.com as MemberRole.member>

The service can also be used to get the information about a single member.

    >>> print(service.get_member(bart_2.member_id))
    <Member: Bart Person <bperson@example.com>
        on bee@example.com as MemberRole.owner>

There is an iteration shorthand for getting all the members.

    >>> for member in service:
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.moderator>
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Bart Person <bperson@example.com>
        on bee@example.com as MemberRole.owner>
    <Member: Anne Person <anne@example.com>
        on cat@example.com as MemberRole.member>
    <Member: Cris Person <cperson@example.com>
        on cat@example.com as MemberRole.member>


Searching for members
=====================

The subscription service can be used to find memberships based on specific
search criteria.  For example, we can find all the mailing lists that Anne is
a member of with her ``aperson@example.com`` address.

    >>> for member in service.find_members('aperson@example.com'):
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>

There may be no matching memberships.

    >>> list(service.find_members('dave@example.com'))
    []

The address may contain asterisks, which will be interpreted as a wildcard in
the search pattern.

    >>> for member in service.find_members('*person*'):
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.moderator>
    <Member: Bart Person <bperson@example.com>
        on bee@example.com as MemberRole.owner>
    <Member: Cris Person <cperson@example.com>
        on cat@example.com as MemberRole.member>

Memberships can also be searched for by user id.

    >>> for member in service.find_members(anne_1.user.user_id):
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>

You can find all the memberships for a specific mailing list.

    >>> for member in service.find_members(list_id='ant.example.com'):
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.moderator>

You can find all the memberships for an address on a specific mailing list,
but you have to give it the list id, not the fqdn listname since the former is
stable but the latter could change if the list is moved.

    >>> for member in service.find_members(
    ...         'bperson@example.com', 'ant.example.com'):
    ...     print(member)
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.moderator>

You can find all the memberships for an address with a specific role.

    >>> for member in service.find_members(
    ...         list_id='ant.example.com', role=MemberRole.owner):
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>

You can also find a specific membership by all three criteria.

    >>> for member in service.find_members(
    ...         'bperson@example.com', 'bee.example.com', MemberRole.owner):
    ...     print(member)
    <Member: Bart Person <bperson@example.com>
        on bee@example.com as MemberRole.owner>


Finding a single member
=======================

If you expect only zero or one member to match your criteria, you can use a
the more efficient ``find_member()`` method.  This takes exactly the same
criteria as ``find_members()``.

There may be no matching members.

    >>> print(service.find_member('dave@example.com'))
    None

But if there is exactly one membership, it is returned.

    >>> service.find_member('bperson@example.com', 'ant.example.com')
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.moderator>


Removing members
================

Members can be removed via this service.

    >>> len(service.get_members())
    6
    >>> service.leave('cat.example.com', 'cperson@example.com')
    >>> len(service.get_members())
    5
    >>> for member in service:
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.moderator>
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Bart Person <bperson@example.com>
        on bee@example.com as MemberRole.owner>
    <Member: Anne Person <anne@example.com>
        on cat@example.com as MemberRole.member>


Mass Removal
============

The subscription service can be used to perform mass removals. You are
required to pass the list id of the respective mailing list and a list
of email addresses to be removed.

    >>> bart_2 = subscribe(ant, 'Bart')
    >>> cris_2 = subscribe(ant, 'Cris')
    >>> for member in service:
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.moderator>
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Cris Person <cperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Bart Person <bperson@example.com>
        on bee@example.com as MemberRole.owner>
    <Member: Anne Person <anne@example.com>
        on cat@example.com as MemberRole.member>
    >>> len(service.get_members())
    7
    >>> print(service.find_member('bogus@example.com'))
    None
    >>> success, fail = service.unsubscribe_members(
    ...         'ant.example.com', ['aperson@example.com',
    ...                             'cperson@example.com',
    ...                             'bogus@example.com',
    ...                            ])
    >>> dump_list(success)
    aperson@example.com
    cperson@example.com
    >>> dump_list(fail)
    bogus@example.com
    >>> for member in service:
    ...     print(member)
    <Member: Anne Person <aperson@example.com>
        on ant@example.com as MemberRole.owner>
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.moderator>
    <Member: Bart Person <bperson@example.com>
        on ant@example.com as MemberRole.member>
    <Member: Bart Person <bperson@example.com>
        on bee@example.com as MemberRole.owner>
    <Member: Anne Person <anne@example.com>
        on cat@example.com as MemberRole.member>
    >>> len(service.get_members())
    5
