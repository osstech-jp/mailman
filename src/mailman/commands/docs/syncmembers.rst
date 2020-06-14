===============
Syncing members
===============

The ``mailman syncmembers`` command allows a site administrator to sync the
membership of a mailing list with an input file.

    >>> command = cli('mailman.commands.cli_syncmembers.syncmembers')

You can synchronize all member addresses of a mailing list with the
member addresses found in a file from the command line.  To do so, you
need a file containing email addresses and optional display names that can be
parsed by ``email.utils.parseaddr()``.  All mail addresses *not contained* in
the file will be *deleted* from the mailing list. Every address *found* in the
specified file will be added to the specified mailing list.

First we create a list and add a few members.
::

    >>> bee = create_list('bee@example.com')
    >>> from mailman.testing.helpers import subscribe
    >>> subscribe(bee, 'Fred')
    <Member: Fred Person <fperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Greg')
    <Member: Greg Person <gperson@example.com> on bee@example.com
             as MemberRole.member>
    >>> subscribe(bee, 'Jeff')
    <Member: Jeff Person <jperson@example.com> on bee@example.com
             as MemberRole.member>

*Note* that only changes of the mailing list will be written to output so in
the first example, Fred is a member who remains on the list and isn't reported.
::

    >>> from tempfile import NamedTemporaryFile
    >>> filename = cleanups.enter_context(NamedTemporaryFile()).name
    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... aperson@example.com
    ... cperson@example.com (Cate Person)
    ... Fred Person <fperson@example.com>
    ... """, file=fp)

    >>> command('mailman syncmembers ' + filename + ' bee.example.com')
    [ADD] aperson@example.com
    [ADD] Cate Person <cperson@example.com>
    [DEL] Greg Person <gperson@example.com>
    [DEL] Jeff Person <jperson@example.com>

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
    >>> command('mailman syncmembers - bee.example.com', input=stdin)
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

    >>> command('mailman syncmembers ' + filename + ' bee.example.com')
    [ADD] bperson@example.com
    [DEL] dperson@example.com

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    bperson@example.com
    Elly Person <eperson@example.com>

If there is nothing to do, it will output just that.
::

    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... bperson@example.com
    ... eperson@example.com
    ... """, file=fp)

    >>> command('mailman syncmembers ' + filename + ' bee.example.com')
    Nothing to do

    >>> dump_list(bee.members.addresses, key=attrgetter('email'))
    bperson@example.com
    Elly Person <eperson@example.com>
