==================
Changing addresses
==================

The ``mailman changeaddress`` command is used to change an email address for
a user.

    >>> from mailman.testing.documentation import cli
    >>> command = cli('mailman.commands.cli_changeaddress.changeaddress')

Usage
-----

Here is the complete usage for the command.
::

    >>> command('mailman changeaddress --help')
    Usage: changeaddress [OPTIONS] OLD_ADDRESS NEW_ADDRESS
    <BLANKLINE>
      Change a user's email address from old_address to possibly case-preserved
      new_address.
    <BLANKLINE>
    Options:
      --help  Show this message and exit.

Examples
--------

First we create an address.
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)
    >>> user_manager.create_address('anne@example.com', 'Anne Person')
    <Address: Anne Person <anne@example.com> [not verified] at ...

Now we can change the email address.
::

    >>> command('mailman changeaddress anne@example.com anne@example.net')
    Address changed from anne@example.com to anne@example.net.
    >>> print(user_manager.get_address('anne@example.com'))
    None
    >>> user_manager.get_address('anne@example.net')
    <Address: Anne Person <anne@example.net> [not verified] at ...

We can also change only the case of an address
::

    >>> command('mailman changeaddress anne@example.net Anne@example.net')
    Address changed from anne@example.net to Anne@example.net.
    >>> user_manager.get_address('anne@example.net')
    <Address: Anne Person <Anne@example.net> [not verified] key: anne@example.net at ...

