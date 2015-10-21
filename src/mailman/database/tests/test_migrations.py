# Copyright (C) 2015 by the Free Software Foundation, Inc.
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
import sqlalchemy as sa

from mailman.config import config
from mailman.database.alembic import alembic_cfg
from mailman.database.helpers import exists_in_db
from mailman.database.model import Model
from mailman.testing.layers import ConfigLayer



class TestMigrations(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        alembic.command.stamp(alembic_cfg, 'head')

    def tearDown(self):
        # Drop and restore a virgin database.
        config.db.store.rollback()
        md = sa.MetaData(bind=config.db.engine)
        md.reflect()
        # We have circular dependencies between user and address, thus we can't
        # use drop_all() without getting a warning.  Setting use_alter to True
        # on the foreign keys helps SQLAlchemy mark those loops as known.
        for tablename in ('user', 'address'):
            if tablename not in md.tables:
                continue
            for fk in md.tables[tablename].foreign_keys:
                fk.constraint.use_alter = True
        md.drop_all()
        Model.metadata.create_all(config.db.engine)

    def test_all_migrations(self):
        script_dir = alembic.script.ScriptDirectory.from_config(alembic_cfg)
        revisions = [sc.revision for sc in script_dir.walk_revisions()]
        for revision in revisions:
            alembic.command.downgrade(alembic_cfg, revision)
        revisions.reverse()
        for revision in revisions:
            alembic.command.upgrade(alembic_cfg, revision)

    def test_42756496720_header_matches(self):
        test_header_matches = [
            ('test-header-1', 'test-pattern-1'),
            ('test-header-2', 'test-pattern-2'),
            ('test-header-3', 'test-pattern-3'),
            ]
        mlist_table = sa.sql.table(
            'mailinglist',
            sa.sql.column('id', sa.Integer),
            sa.sql.column('header_matches', sa.PickleType)
            )
        header_match_table = sa.sql.table(
            'headermatch',
            sa.sql.column('mailing_list_id', sa.Integer),
            sa.sql.column('header', sa.Unicode),
            sa.sql.column('pattern', sa.Unicode),
            )
        # Downgrading.
        config.db.store.execute(mlist_table.insert().values(id=1))
        config.db.store.execute(header_match_table.insert().values(
            [{'mailing_list_id': 1, 'header': hm[0], 'pattern': hm[1]}
             for hm in test_header_matches]))
        config.db.store.commit()
        alembic.command.downgrade(alembic_cfg, '2bb9b382198')
        results = config.db.store.execute(
            mlist_table.select()).fetchall()
        self.assertEqual(results[0].header_matches, test_header_matches)
        self.assertFalse(exists_in_db(config.db.engine, 'headermatch'))
        config.db.store.commit()
        # Upgrading.
        alembic.command.upgrade(alembic_cfg, '42756496720')
        results = config.db.store.execute(
            header_match_table.select()).fetchall()
        self.assertEqual(results,
            [(1, hm[0], hm[1]) for hm in test_header_matches])
