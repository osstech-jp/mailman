=================================
Notify Admins Of Pending Requests
=================================

The ``mailman notify`` command is normally run periodically, usually daily, by
cron to send a notice summarizing pending subscriptions, unsubscriptions and
held messages waiting moderator approval to a list's owners and moderators.

There are options for doing selected lists and reporting but not actually
sending the notices.  Complete information about command options may be
obtained by running ``mailman notify --help``.
::

    >>> from mailman.testing.documentation import cli
    >>> command = cli('mailman.commands.cli_notify.notify')

    >>> command('mailman notify --help')
    Usage: notify [OPTIONS]
    <BLANKLINE>
      Notify list owners/moderators of pending requests.
    <BLANKLINE>
    Options:
      -l, --list list  Operate on this mailing list.  Multiple --list options can be
                       given.  The argument can either be a List-ID or a fully
                       qualified list name.  Without this option, operate on the
                       requests for all mailing lists.
      -n, --dry-run    Don't actually do anything, but in conjunction with
                       --verbose, show what would happen.
      -v, --verbose    Print some additional status.
      --help           Show this message and exit.
