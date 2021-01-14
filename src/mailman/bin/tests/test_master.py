# Copyright (C) 2010-2021 by the Free Software Foundation, Inc.
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

"""Test master watcher utilities."""

import os
import tempfile
import unittest

from click.testing import CliRunner
from contextlib import ExitStack, suppress
from datetime import timedelta
from flufl.lock import Lock, TimeOutError
from importlib_resources import path
from io import StringIO
from mailman.bin import master
from mailman.config import config
from mailman.testing.layers import ConfigLayer
from unittest.mock import patch


class FakeLock:
    details = ('host.example.com', 9999, '/tmp/whatever')

    def unlock(self):
        pass


class TestMaster(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        fd, self.lock_file = tempfile.mkstemp()
        os.close(fd)
        # The lock file should not exist before we try to acquire it.
        os.remove(self.lock_file)

    def tearDown(self):
        # Unlocking removes the lock file, but just to be safe (i.e. in case
        # of errors).
        with suppress(FileNotFoundError):
            os.remove(self.lock_file)

    def test_acquire_lock_1(self):
        lock = master.acquire_lock_1(False, self.lock_file)
        is_locked = lock.is_locked
        lock.unlock()
        self.assertTrue(is_locked)

    def test_acquire_lock_1_force(self):
        # Create the lock and lock it.
        my_lock = Lock(self.lock_file)
        my_lock.lock(timedelta(seconds=60))
        # Try to aquire it again with force.
        lock = master.acquire_lock_1(True, self.lock_file)
        self.assertTrue(lock.is_locked)
        lock.unlock()

    def test_master_state(self):
        my_lock = Lock(self.lock_file)
        # Mailman is not running.
        state, lock = master.master_state(self.lock_file)
        self.assertEqual(state, master.WatcherState.none)
        # Acquire the lock as if another process had already started the
        # master.  Use a timeout to avoid this test deadlocking.
        my_lock.lock(timedelta(seconds=60))
        try:
            state, lock = master.master_state(self.lock_file)
        finally:
            my_lock.unlock()
        self.assertEqual(state, master.WatcherState.conflict)

    def test_acquire_lock_timeout_reason_unknown(self):
        stderr = StringIO()
        with ExitStack() as resources:
            resources.enter_context(patch(
                'mailman.bin.master.acquire_lock_1',
                side_effect=TimeOutError))
            resources.enter_context(patch(
                'mailman.bin.master.master_state',
                return_value=(master.WatcherState.none, FakeLock())))
            resources.enter_context(patch(
                'mailman.bin.master.sys.stderr', stderr))
            with self.assertRaises(SystemExit) as cm:
                master.acquire_lock(False)
            self.assertEqual(cm.exception.code, 1)
            self.assertEqual(stderr.getvalue(), """\
For unknown reasons, the master lock could not be acquired.

Lock file: {}
Lock host: host.example.com

Exiting.
""".format(config.LOCK_FILE))

    def test_main_cli(self):
        command = CliRunner()
        fake_lock = FakeLock()
        with ExitStack() as resources:
            config_file = str(resources.enter_context(
                path('mailman.testing', 'testing.cfg')))
            init_mock = resources.enter_context(patch(
                'mailman.bin.master.initialize'))
            lock_mock = resources.enter_context(patch(
                'mailman.bin.master.acquire_lock',
                return_value=fake_lock))
            start_mock = resources.enter_context(patch.object(
                master.Loop, 'start_runners'))
            loop_mock = resources.enter_context(patch.object(
                master.Loop, 'loop'))
            command.invoke(
                master.main,
                ('-C', config_file,
                 '--no-restart', '--force',
                 '-r', 'in:1:1', '--verbose'))
            # We got initialized with the custom configuration file and the
            # verbose flag.
            init_mock.assert_called_once_with(config_file, True)
            # We returned a lock that was force-acquired.
            lock_mock.assert_called_once_with(True)
            # We created a non-restartable loop.
            start_mock.assert_called_once_with([('in', 1, 1)])
            loop_mock.assert_called_once_with()
