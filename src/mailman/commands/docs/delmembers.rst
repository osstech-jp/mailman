================
Managing members
================

The ``mailman members`` command allows a site administrator to display, add,
and delete members from a mailing list.

    >>> command = cli('mailman.commands.cli_delmembers.delmembers')

You can delete members from a mailing list from the command line.  To do so, you
need a file containing email addresses and optional display names that can be
parsed by ``email.utils.parseaddr()``.  All mail addresses in the file will be
deleted from the mailing list.  You can also specify members with command
options on the command line.

First we need a list with some members.
::

    >>> bee = create_list('bee@example.com')
    >>> from mailman.testing.helpers import subscribe
    >>> subscribe(bee, 'Anne')
    <Member: Anne Person <aperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Bart')
    <Member: Bart Person <bperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Cate')
    <Member: Cate Person <cperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Doug')
    <Member: Doug Person <dperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Elly')
    <Member: Elly Person <eperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Fred')
    <Member: Fred Person <fperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Greg')
    <Member: Greg Person <gperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Irma')
    <Member: Irma Person <iperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Jeff')
    <Member: Jeff Person <jperson@example.com> on bee@example.com
             as MemberRole.member>

Now we can delete some members.
::

    >>> from tempfile import NamedTemporaryFile
    >>> filename = cleanups.enter_context(NamedTemporaryFile()).name
    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... aperson@example.com
    ... cperson@example.com (Cate Person)
    ... """, file=fp)

    >>> command('mailman delmembers -f ' + filename + ' -l  bee.example.com')

    >>> from operator import attrgetter
    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Bart Person <bperson@example.com>
    Doug Person <dperson@example.com>
    Elly Person <eperson@example.com>
    Fred Person <fperson@example.com>
    Greg Person <gperson@example.com>
    Irma Person <iperson@example.com>
    Jeff Person <jperson@example.com>

You can also specify ``-`` as the filename, in which case the addresses are
taken from standard input.
::

    >>> stdin = """\
    ... dperson@example.com
    ... Elly Person <eperson@example.com>
    ... """
    >>> command('mailman delmembers -f - -l bee.example.com', input=stdin)

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Bart Person <bperson@example.com>
    Fred Person <fperson@example.com>
    Greg Person <gperson@example.com>
    Irma Person <iperson@example.com>
    Jeff Person <jperson@example.com>

Blank lines and lines that begin with '#' are ignored.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... # cperson@example.com
    ...
    ... bperson@example.com
    ... """, file=fp)

    >>> command('mailman delmembers -f ' + filename + ' -l bee.example.com')

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Fred Person <fperson@example.com>
    Greg Person <gperson@example.com>
    Irma Person <iperson@example.com>
    Jeff Person <jperson@example.com>

Addresses which are not subscribed are ignored, although a warning is
printed.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... kperson@example.com
    ... iperson@example.com
    ... """, file=fp)

    >>> command('mailman delmembers -f ' + filename + ' -l bee.example.com')
    Member not subscribed (skipping): kperson@example.com

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Fred Person <fperson@example.com>
    Greg Person <gperson@example.com>
    Jeff Person <jperson@example.com>

Addresses to delete can be specified on the command line.
::

    >>> command('mailman delmembers -m gperson@example.com -l bee.example.com')

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    Fred Person <fperson@example.com>
    Jeff Person <jperson@example.com>

All members can be deleted as well.
::

    >>> command('mailman delmembers --all -l bee.example.com')

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    *Empty*
