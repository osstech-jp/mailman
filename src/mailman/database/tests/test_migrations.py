# Copyright (C) 2013-2015 by the Free Software Foundation, Inc.
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

"""Test database schema migrations with Alembic"""

__all__ = [
    'TestMigrations',
    ]


import unittest
import alembic.command

from mailman.config import config
from mailman.database.alembic import alembic_cfg
from mailman.database.model import Model
from mailman.testing.layers import ConfigLayer
import sqlalchemy as sa



class TestMigrations(unittest.TestCase):

    layer = ConfigLayer

    def setUp(self):
        alembic.command.stamp(alembic_cfg, 'head')

    def tearDown(self):
        # Drop and restore a virgin database.
        md = sa.MetaData()
        md.reflect(bind=config.db.engine)
        for table in md.sorted_tables:
            table.drop(config.db.engine)
        Model.metadata.create_all(config.db.engine)

    def test_all_migrations(self):
        script_dir = alembic.script.ScriptDirectory.from_config(alembic_cfg)
        revisions = [sc.revision for sc in
                     script_dir.walk_revisions("base", "heads")]
        for revision in revisions:
            alembic.command.downgrade(alembic_cfg, revision)
        revisions.reverse()
        for revision in revisions:
            alembic.command.upgrade(alembic_cfg, revision)
