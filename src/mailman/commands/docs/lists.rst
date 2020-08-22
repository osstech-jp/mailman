=========================
Command line list display
=========================

A system administrator can display all the mailing lists via the command
line.  When there are no mailing lists, a helpful message is displayed.
::

    >>> from mailman.testing.documentation import cli
    >>> command = cli('mailman.commands.cli_lists.lists')
    >>> command('mailman lists')
    No matching mailing lists found

When there are a few mailing lists, they are shown in alphabetical order by
their fully qualified list names, with a description.
::

    >>> from mailman.interfaces.domain import IDomainManager
    >>> from zope.component import getUtility
    >>> getUtility(IDomainManager).add('example.net')
    <Domain example.net...>

    >>> from mailman.app.lifecycle import create_list    
    >>> mlist_1 = create_list('list-one@example.com')
    >>> mlist_1.description = 'List One'

    >>> mlist_2 = create_list('list-two@example.com')
    >>> mlist_2.description = 'List Two'

    >>> mlist_3 = create_list('list-one@example.net')
    >>> mlist_3.description = 'List One in Example.Net'

    >>> command('mailman lists')
    3 matching mailing lists found:
    list-one@example.com
    list-one@example.net
    list-two@example.com


Names
=====

You can display the mailing list names with their posting addresses, using the
``--names/-n`` switch.

    >>> command('mailman lists --names')
    3 matching mailing lists found:
    list-one@example.com [List-one]
    list-one@example.net [List-one]
    list-two@example.com [List-two]


Descriptions
============

You can also display the mailing list descriptions, using the
``--descriptions/-d`` option.

    >>> command('mailman lists --descriptions --names')
    3 matching mailing lists found:
    list-one@example.com [List-one] - List One
    list-one@example.net [List-one] - List One in Example.Net
    list-two@example.com [List-two] - List Two

Maybe you want the descriptions but not the names.

    >>> command('mailman lists --descriptions --no-names')
    3 matching mailing lists found:
    list-one@example.com - List One
    list-one@example.net - List One in Example.Net
    list-two@example.com - List Two


Less verbosity
==============

There's also a ``--quiet/-q`` switch which reduces the verbosity a bit.

    >>> command('mailman lists --quiet')
    list-one@example.com
    list-one@example.net
    list-two@example.com


Specific domain
===============

You can narrow the search down to a specific domain with the --domain option.
A helpful message is displayed if no matching domains are given.

    >>> command('mailman lists --domain example.org')
    No matching mailing lists found

But if a matching domain is given, only mailing lists in that domain are
shown.

    >>> command('mailman lists --domain example.net')
    1 matching mailing lists found:
    list-one@example.net

More than one ``--domain`` argument can be given; then all mailing lists in
matching domains are shown.

    >>> command('mailman lists --domain example.com --domain example.net')
    3 matching mailing lists found:
    list-one@example.com
    list-one@example.net
    list-two@example.com


Advertised lists
================

Mailing lists can be "advertised" meaning their existence is public knowledge.
Non-advertised lists are considered private.  Display through the command line
can select on this attribute.
::

    >>> mlist_1.advertised = False
    >>> command('mailman lists --advertised')
    2 matching mailing lists found:
    list-one@example.net
    list-two@example.com
