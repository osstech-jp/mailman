==============
Adding members
==============

The ``mailman addmembers`` command allows a site administrator to add members
to a mailing list.

    >>> command = cli('mailman.commands.cli_addmembers.addmembers')

You can add members to a mailing list from the command line.  To do so, you
need a file containing email addresses and optional display names that can be
parsed by ``email.utils.parseaddr()``.
::

    >>> from tempfile import NamedTemporaryFile
    >>> filename = cleanups.enter_context(NamedTemporaryFile()).name
    >>> bee = create_list('bee@example.com')
    >>> with open(filename, 'w', encoding='utf-8') as fp:
    ...     print("""\
    ... aperson@example.com
    ... Bart Person <bperson@example.com>
    ... cperson@example.com (Cate Person)
    ... """, file=fp)

    >>> command('mailman addmembers ' + filename + ' bee.example.com')

    >>> from operator import attrgetter
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
    >>> command('mailman addmembers - bee.example.com', input=stdin)

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

    >>> command('mailman addmembers ' + filename + ' bee.example.com')

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

    >>> command('mailman addmembers ' + filename + ' bee.example.com')
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
