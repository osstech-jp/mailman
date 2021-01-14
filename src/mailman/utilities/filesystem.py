# Copyright (C) 2009-2021 by the Free Software Foundation, Inc.
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
# GNU Mailman.  If not, see <https://www.gnu.org/licenses/>.

"""Filesystem utilities."""

import os
import sys

from contextlib import suppress
from public import public


@public
class umask:
    """Manage the umask for the with statement."""

    def __init__(self, umask):
        self._umask = umask
        self._old_umask = None

    def __enter__(self):
        assert self._old_umask is None, 'Unexpected existing umask'
        self._old_umask = os.umask(self._umask)

    def __exit__(self, *exc_info):
        assert self._old_umask is not None, 'No previous umask'
        os.umask(self._old_umask)
        # Do not suppress exceptions.
        return False


@public
def makedirs(path, mode=0o0755):
    """Create a directory hierarchy, ensuring permissions.

    Other than just calling os.makedirs(), this ensures that the umask is
    reset so that the makedirs mode will be honored.

    :param path: The directory path to create.
    :type path: string
    :param mode: The numeric permission mode to use.
    :type mode: int
    """
    with umask(0):
        # In order for os.walk to set permissions appropriately if required,
        # the FIRST NON EXISTENT parent directory of the one we wanted to
        # create has to be provided.
        upwards = first_inexistent_directory(path)

        # The directory exists, nothing to do.
        if upwards is None:
            return

        try:
            os.makedirs(path, mode)
        except FileExistsError:
            if not os.path.isdir(path):
                raise FileExistsError((
                   "A race condition might have happened. {} actually "
                   "exists and is not a directory.").format(path))

    # Some systems such as FreeBSD ignore mkdir's mode, so walk the just
    # created directories and try to set the mode, ignoring any OSErrors that
    # occur here.
    for dirpath, dirnames, filenames in os.walk(upwards):
        with suppress(OSError):
            os.chmod(dirpath, mode)


@public
def safe_remove(path):
    with suppress(FileNotFoundError):
        os.remove(path)


@public
def first_inexistent_directory(path):
    """Splits iteratively a path until it gives the first non-existent
    directory in the tree.

    That is, if /home/user/foo/bar/baz is given to the function, and
    /home/user/foo/bar doesn't exist but /home/user/foo exists, returns
    /home/user/foo/bar.
    """
    directory = path
    rhs = None

    while True:
        if os.path.isdir(directory):
            if rhs is None:
                return None
            else:
                return os.path.join(directory, rhs)
        elif os.path.exists(directory):
            raise FileExistsError(
                "The path %s exists but is not a directory.",
                directory)
        directory, rhs = os.path.split(directory)


@public
def path(package, module, *args, **kw):
    """Wrap around importlib.resources.path.

    importlib_resources.path (PyPI package we use for compatibility in Python <
    3.7) has now diverged in behavior from importlib.resources.path (in Python
    >= 3.7), especially in terms of supporting directories. Even though we can
    just jump to the new version of the library, many distributions packaging
    Mailman do not package importlib_resources at all and instead patch the
    source code to simply replace importlib_resources with importlib.resources.

    This utility method is meant to keep that patching ability without any
    complicated patches to make Mailman work with standard library
    importlib.resources. This is only supposed to be used where the divergent
    behavior causes problems for us.
    """
    # Note to packaging teams: This function will handle both standard library
    # and 3rd party importlib_resources package. Please do not patch it.
    if module:
        module_package = '{}.{}'.format(package, module)
    else:
        module_package = package

    try:
        if sys.version_info < (3, 9):
            from importlib.resources import path
            return path(package, module, *args, **kw)
        else:
            from importlib.resources import files             # pragma: nocover
            return files(module_package, *args, **kw)         # pragma: nocover
    except ImportError:                                       # pragma: nocover
        from importlib_resources import files                 # pragma: nocover
        return files(module_package, *args, **kw)             # pragma: nocover
