====================
Printing the version
====================

You can print the Mailman version number by invoking the ``version`` command.

    >>> from mailman.testing.documentation import cli
    >>> command = cli('mailman.commands.cli_version.version')
    >>> command('mailman version')
    GNU Mailman 3...
