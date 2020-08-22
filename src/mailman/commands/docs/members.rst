================
Managing members
================

The ``mailman members`` command allows a site administrator to display, add,
and delete members from a mailing list.

    >>> from mailman.testing.documentation import cli
    >>> command = cli('mailman.commands.cli_members.members')


Listing members
===============

You can list all the members of a mailing list by calling the command with no
options.  To start with, there are no members of the mailing list.

    >>> from mailman.app.lifecycle import create_list
    >>> ant = create_list('ant@example.com')
    >>> command('mailman members ant.example.com')
    ant.example.com has no members

Once the mailing list add some members, they will be displayed.
::

    >>> from mailman.testing.helpers import subscribe
    >>> subscribe(ant, 'Anne', email='anne@example.com')
    <Member: Anne Person <anne@example.com> on ant@example.com
             as MemberRole.member>
    >>> subscribe(ant, 'Bart', email='bart@example.com')
    <Member: Bart Person <bart@example.com> on ant@example.com
             as MemberRole.member>

    >>> command('mailman members ant.example.com')
    Anne Person <anne@example.com>
    Bart Person <bart@example.com>

Members are displayed in alphabetical order based on their address.
::

    >>> subscribe(ant, 'Anne', email='anne@aaaxample.com')
    <Member: Anne Person <anne@aaaxample.com> on ant@example.com
             as MemberRole.member>

    >>> command('mailman members ant.example.com')
    Anne Person <anne@aaaxample.com>
    Anne Person <anne@example.com>
    Bart Person <bart@example.com>

You can also output this list to a file.
::

    >>> from tempfile import NamedTemporaryFile
    >>> filename = cleanups.enter_context(NamedTemporaryFile()).name

    >>> command('mailman members -o ' + filename + ' ant.example.com')
    >>> with open(filename, 'r', encoding='utf-8') as fp:
    ...     print(fp.read())
    Anne Person <anne@aaaxample.com>
    Anne Person <anne@example.com>
    Bart Person <bart@example.com>

The output file can also be standard out.

    >>> command('mailman members -o - ant.example.com')
    Anne Person <anne@aaaxample.com>
    Anne Person <anne@example.com>
    Bart Person <bart@example.com>


Filtering on delivery mode
--------------------------

You can limit output to just the regular non-digest members...
::

    >>> member = ant.members.get_member('anne@example.com')
    >>> from mailman.interfaces.member import DeliveryMode
    >>> member.preferences.delivery_mode = DeliveryMode.plaintext_digests

    >>> command('mailman members --regular ant.example.com')
    Anne Person <anne@aaaxample.com>
    Bart Person <bart@example.com>

...or just the digest members.  Furthermore, you can either display all digest
members...
::

    >>> member = ant.members.get_member('anne@aaaxample.com')
    >>> member.preferences.delivery_mode = DeliveryMode.mime_digests

    >>> command('mailman members --digest any ant.example.com')
    Anne Person <anne@aaaxample.com>
    Anne Person <anne@example.com>

...just plain text digest members...

    >>> command('mailman members --digest plaintext ant.example.com')
    Anne Person <anne@example.com>

...or just MIME digest members.
::

    >>> command('mailman members --digest mime ant.example.com')
    Anne Person <anne@aaaxample.com>


Filtering on delivery status
----------------------------

You can also filter the display on the member's delivery status.  By default,
all members are displayed, but you can filter out only those whose delivery
status is enabled...
::

    >>> from mailman.interfaces.member import DeliveryStatus

    >>> member = ant.members.get_member('anne@aaaxample.com')
    >>> member.preferences.delivery_status = DeliveryStatus.by_moderator
    >>> member = ant.members.get_member('bart@example.com')
    >>> member.preferences.delivery_status = DeliveryStatus.by_user

    >>> member = subscribe(ant, 'Cris', email='cris@example.com')
    >>> member.preferences.delivery_status = DeliveryStatus.unknown
    >>> member = subscribe(ant, 'Dave', email='dave@example.com')
    >>> member.preferences.delivery_status = DeliveryStatus.enabled
    >>> member = subscribe(ant, 'Elle', email='elle@example.com')
    >>> member.preferences.delivery_status = DeliveryStatus.by_bounces

    >>> command('mailman members --nomail enabled ant.example.com')
    Anne Person <anne@example.com>
    Dave Person <dave@example.com>

...or disabled by the user...

    >>> command('mailman members --nomail byuser ant.example.com')
    Bart Person <bart@example.com>

...or disabled by the list administrator (or moderator)...

    >>> command('mailman members --nomail byadmin ant.example.com')
    Anne Person <anne@aaaxample.com>

...or by the bounce processor...

    >>> command('mailman members --nomail bybounces ant.example.com')
    Elle Person <elle@example.com>

...or for unknown (legacy) reasons.

    >>> command('mailman members --nomail unknown ant.example.com')
    Cris Person <cris@example.com>

You can also display all members who have delivery disabled for any reason.
::

    >>> command('mailman members --nomail any ant.example.com')
    Anne Person <anne@aaaxample.com>
    Bart Person <bart@example.com>
    Cris Person <cris@example.com>
    Elle Person <elle@example.com>


Adding members
==============

You can add members to a mailing list from the command line.  To do so, you
need a file containing email addresses and full names that can be parsed by
``email.utils.parseaddr()``.
::

    >>> bee = create_list('bee@example.com')
    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... aperson@example.com
    ... Bart Person <bperson@example.com>
    ... cperson@example.com (Cate Person)
    ... """, file=fp)

    >>> command('mailman members --add ' + filename + ' bee.example.com')
    Warning: The --add option is deprecated. Use `mailman addmembers` instead.

    >>> from operator import attrgetter
    >>> from mailman.testing.documentation import dump_list    
    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    aperson@example.com
    Bart Person <bperson@example.com>
    Cate Person <cperson@example.com>

You can also specify ``-`` as the filename, in which case the addresses are
taken from standard input.
::

    >>> stdin = """\
    ... dperson@example.com
    ... Elly Person <eperson@example.com>
    ... fperson@example.com (Fred Person)
    ... """
    >>> command('mailman members --add - bee.example.com', input=stdin)
    Warning: The --add option is deprecated. Use `mailman addmembers` instead.

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    aperson@example.com
    Bart Person <bperson@example.com>
    Cate Person <cperson@example.com>
    dperson@example.com
    Elly Person <eperson@example.com>
    Fred Person <fperson@example.com>

Blank lines and lines that begin with '#' are ignored.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... gperson@example.com
    ... # hperson@example.com
    ...
    ... iperson@example.com
    ... """, file=fp)

    >>> command('mailman members --add ' + filename + ' bee.example.com')
    Warning: The --add option is deprecated. Use `mailman addmembers` instead.

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    aperson@example.com
    Bart Person <bperson@example.com>
    Cate Person <cperson@example.com>
    dperson@example.com
    Elly Person <eperson@example.com>
    Fred Person <fperson@example.com>
    gperson@example.com
    iperson@example.com

Addresses which are already subscribed are ignored, although a warning is
printed.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... gperson@example.com
    ... aperson@example.com
    ... jperson@example.com
    ... """, file=fp)

    >>> command('mailman members --add ' + filename + ' bee.example.com')
    Warning: The --add option is deprecated. Use `mailman addmembers` instead.
    Already subscribed (skipping): gperson@example.com
    Already subscribed (skipping): aperson@example.com

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    aperson@example.com
    Bart Person <bperson@example.com>
    Cate Person <cperson@example.com>
    dperson@example.com
    Elly Person <eperson@example.com>
    Fred Person <fperson@example.com>
    gperson@example.com
    iperson@example.com
    jperson@example.com


Deleting members
================

You can delete members from a mailing list from the command line.  To do so, you
need a file containing email addresses and full names that can be parsed by
``email.utils.parseaddr()``.  All mail addresses in the file will be deleted
from the mailing list.

Assuming you have populated a mailing list with the code examples from above,
use these code snippets to delete subscriptions from the list again.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... aperson@example.com
    ... cperson@example.com (Cate Person)
    ... """, file=fp)

    >>> command('mailman members --delete ' + filename + ' bee.example.com')
    Warning: The --delete option is deprecated. Use `mailman delmembers` instead.

    >>> from operator import attrgetter
    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Bart Person <bperson@example.com>
    dperson@example.com
    Elly Person <eperson@example.com>
    Fred Person <fperson@example.com>
    gperson@example.com
    iperson@example.com
    jperson@example.com

You can also specify ``-`` as the filename, in which case the addresses are
taken from standard input.
::

    >>> stdin = """\
    ... dperson@example.com
    ... Elly Person <eperson@example.com>
    ... """
    >>> command('mailman members --delete - bee.example.com', input=stdin)
    Warning: The --delete option is deprecated. Use `mailman delmembers` instead.

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Bart Person <bperson@example.com>
    Fred Person <fperson@example.com>
    gperson@example.com
    iperson@example.com
    jperson@example.com

Blank lines and lines that begin with '#' are ignored.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... # cperson@example.com
    ...
    ... bperson@example.com
    ... """, file=fp)

    >>> command('mailman members --delete ' + filename + ' bee.example.com')
    Warning: The --delete option is deprecated. Use `mailman delmembers` instead.

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Fred Person <fperson@example.com>
    gperson@example.com
    iperson@example.com
    jperson@example.com

Addresses which are not subscribed are ignored, although a warning is
printed.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... kperson@example.com
    ... iperson@example.com
    ... """, file=fp)

    >>> command('mailman members --delete ' + filename + ' bee.example.com')
    Warning: The --delete option is deprecated. Use `mailman delmembers` instead.
    Member not subscribed (skipping): kperson@example.com

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Fred Person <fperson@example.com>
    gperson@example.com
    jperson@example.com


Synchronizing members
=====================

You can synchronize all member addresses of a mailing list with the
member addresses found in a file from the command line.  To do so, you
need a file containing email addresses and full names that can be parsed by
``email.utils.parseaddr()``.  All mail addresses *not contained* in the file
will be *deleted* from the mailing list. Every address *found* in the specified
file will be added to the specified mailing list.

Assuming you have populated a mailing list with the code examples from above,
use these code snippets to synchronize mail addresses with subscriptions of the
mailing list.  *Note* that only changes of the mailing list will be
written to output.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... aperson@example.com
    ... cperson@example.com (Cate Person)
    ... Fred Person <fperson@example.com>
    ... """, file=fp)

    >>> command('mailman members --sync ' + filename + ' bee.example.com')
    Warning: The --sync option is deprecated. Use `mailman syncmembers` instead.
    [ADD] aperson@example.com
    [ADD] Cate Person <cperson@example.com>
    [DEL] gperson@example.com
    [DEL] jperson@example.com

    >>> from operator import attrgetter
    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    aperson@example.com
    Cate Person <cperson@example.com>
    Fred Person <fperson@example.com>

You can also specify ``-`` as the filename, in which case the addresses are
taken from standard input.
::

    >>> stdin = """\
    ... dperson@example.com
    ... Elly Person <eperson@example.com>
    ... """
    >>> command('mailman members --sync - bee.example.com', input=stdin)
    Warning: The --sync option is deprecated. Use `mailman syncmembers` instead.
    [ADD] dperson@example.com
    [ADD] Elly Person <eperson@example.com>
    [DEL] aperson@example.com
    [DEL] Cate Person <cperson@example.com>
    [DEL] Fred Person <fperson@example.com>

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    dperson@example.com
    Elly Person <eperson@example.com>

Blank lines and lines that begin with '#' are ignored.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... #cperson@example.com
    ... eperson@example.com
    ...
    ... bperson@example.com
    ... """, file=fp)

    >>> command('mailman members --sync ' + filename + ' bee.example.com')
    Warning: The --sync option is deprecated. Use `mailman syncmembers` instead.
    [ADD] bperson@example.com
    [DEL] dperson@example.com

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Bart Person <bperson@example.com>
    Elly Person <eperson@example.com>

If there is nothing to do, it will output just that.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... bperson@example.com
    ... eperson@example.com
    ... """, file=fp)

    >>> command('mailman members --sync ' + filename + ' bee.example.com')
    Warning: The --sync option is deprecated. Use `mailman syncmembers` instead.
    Nothing to do

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Bart Person <bperson@example.com>
    Elly Person <eperson@example.com>


Displaying members
==================

With no arguments, the command displays all members of the list.

    >>> command('mailman members bee.example.com')
    Bart Person <bperson@example.com>
    Elly Person <eperson@example.com>
