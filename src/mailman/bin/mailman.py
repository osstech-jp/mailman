# Copyright (C) 2009-2017 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""The 'mailman' command dispatcher."""

import click

from contextlib import ExitStack
from mailman.config import config
from mailman.core.i18n import _
from mailman.core.initialize import initialize
from mailman.database.transaction import transaction
from mailman.interfaces.command import ICLISubCommand
from mailman.utilities.modules import add_components
from mailman.version import MAILMAN_VERSION_FULL
from public import public


class Subcommands(click.MultiCommand):
    # Handle dynamic listing and loading of `mailman` subcommands.
    def __init__(self, *args, **kws):
        super().__init__(*args, **kws)
        self._commands = {}
        # Look at all modules in the mailman.bin package and if they are
        # prepared to add a subcommand, let them do so.  I'm still undecided as
        # to whether this should be pluggable or not.  If so, then we'll
        # probably have to partially parse the arguments now, then initialize
        # the system, then find the plugins.  Punt on this for now.
        add_components('mailman.commands', ICLISubCommand, self._commands)

    def list_commands(self, ctx):
        return sorted(self._commands)               # pragma: nocover

    def get_command(self, ctx, name):
        try:
            return self._commands[name].command
        except KeyError as error:
            # Returning None here signals click to report usage information
            # and a "No such command" error message.
            return None

    # This is here to hook command parsing into the Mailman database
    # transaction system.  If the subcommand succeeds, the transaction is
    # committed, otherwise it's aborted.
    def invoke(self, ctx):
        with ExitStack() as resources:
            # If given a bogus subcommand, the database won't have been
            # initialized so there's no transaction to commit.
            if config.db is not None:
                resources.enter_context(transaction())
            return super().invoke(ctx)

    # https://github.com/pallets/click/issues/834
    #
    # Note that this only handles the case for the `mailman --help` output.
    # To handle `mailman <subcommand> --help` we create a custom click.Command
    # subclass and override this method there too.  See
    # src/mailman/utilities/options.py
    def format_options(self, ctx, formatter):
        """Writes all the options into the formatter if they exist."""
        opts = []
        for param in self.get_params(ctx):
            rv = param.get_help_record(ctx)
            if rv is not None:
                part_a, part_b = rv
                opts.append((part_a, part_b.replace('\n', ' ')))
        if opts:
            with formatter.section('Options'):
                formatter.write_dl(opts)


@click.group(
    cls=Subcommands,
    context_settings=dict(help_option_names=['-h', '--help']))
@click.pass_context
@click.option(
    '-C', '--config', 'config_file',
    envvar='MAILMAN_CONFIG_FILE',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help=_("""\
    Configuration file to use.  If not given, the environment variable
    MAILMAN_CONFIG_FILE is consulted and used if set.  If neither are given, a
    default configuration file is loaded."""))
@click.version_option(MAILMAN_VERSION_FULL, message='%(version)s')
@public
def main(ctx, config_file):
    # XXX https://github.com/pallets/click/issues/303
    """\
    The GNU Mailman mailing list management system
    Copyright 1998-2017 by the Free Software Foundation, Inc.
    http://www.list.org
    """
    # Initialize the system.  Honor the -C flag if given.
    initialize(config_file)
    # click handles dispatching to the subcommand via the Subcommands class.
