# Copyright (C) 2015-2016 by the Free Software Foundation, Inc.
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

import os
import unittest
import alembic.command
import sqlalchemy as sa

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.database.alembic import alembic_cfg
from mailman.database.helpers import exists_in_db
from mailman.database.model import Model
from mailman.database.transaction import transaction
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
        # Bring the DB to the revision that is being tested.
        alembic.command.downgrade(alembic_cfg, '42756496720')
        # Test downgrading.
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
        # Test upgrading.
        alembic.command.upgrade(alembic_cfg, '42756496720')
        results = config.db.store.execute(
            header_match_table.select()).fetchall()
        self.assertEqual(
            results,
            [(1, hm[0], hm[1]) for hm in test_header_matches])

    def test_47294d3a604_pendable_keyvalues(self):
        # We have 5 pended items:
        # - one is a probe request
        # - one is a subscription request
        # - one is a moderation request
        # - one is a held message
        # - one is a registration request in the new format
        #
        # The first three used to have no 'type' key and must be properly
        # typed, the held message used to have a type key, but in JSON, and
        # must be converted.
        pended_table = sa.sql.table(
            'pended',
            sa.sql.column('id', sa.Integer),
            )
        keyvalue_table = sa.sql.table(
            'pendedkeyvalue',
            sa.sql.column('id', sa.Integer),
            sa.sql.column('key', sa.Unicode),
            sa.sql.column('value', sa.Unicode),
            sa.sql.column('pended_id', sa.Integer),
            )
        def get_from_db():                          # flake8: noqa
            results = {}
            for i in range(1, 6):
                query = sa.sql.select(
                    [keyvalue_table.c.key, keyvalue_table.c.value]
                ).where(
                    keyvalue_table.c.pended_id == i
                )
                results[i] = dict([
                    (r['key'], r['value']) for r in
                    config.db.store.execute(query).fetchall()
                    ])
            return results
        # Start at the previous revision
        with transaction():
            alembic.command.downgrade(alembic_cfg, '33bc0099223')
            for i in range(1, 6):
                config.db.store.execute(pended_table.insert().values(id=i))
            config.db.store.execute(keyvalue_table.insert().values([
                {'pended_id': 1, 'key': 'member_id', 'value': 'test-value'},
                {'pended_id': 2, 'key': 'token_owner', 'value': 'test-value'},
                {'pended_id': 3, 'key': '_mod_message_id',
                                 'value': 'test-value'},
                {'pended_id': 4, 'key': 'type', 'value': '"held message"'},
                {'pended_id': 5, 'key': 'type', 'value': 'registration'},
                ]))
        # Upgrading.
        with transaction():
            alembic.command.upgrade(alembic_cfg, '47294d3a604')
            results = get_from_db()
        for i in range(1, 5):
            self.assertIn('type', results[i])
        self.assertEqual(results[1]['type'], 'probe')
        self.assertEqual(results[2]['type'], 'subscription')
        self.assertEqual(results[3]['type'], 'data')
        self.assertEqual(results[4]['type'], 'held message')
        self.assertEqual(results[5]['type'], 'registration')
        # Downgrading.
        with transaction():
            alembic.command.downgrade(alembic_cfg, '33bc0099223')
            results = get_from_db()
        for i in range(1, 4):
            self.assertNotIn('type', results[i])
        self.assertEqual(results[4]['type'], '"held message"')
        self.assertEqual(results[5]['type'], '"registration"')

    def test_70af5a4e5790_digests(self):
        IDS_TO_DIGESTABLE = [
            (1, True),
            (2, False),
            (3, False),
            (4, True),
            ]
        mlist_table = sa.sql.table(
            'mailinglist',
            sa.sql.column('id', sa.Integer),
            sa.sql.column('digests_enabled', sa.Boolean)
            )
        # Downgrading.
        with transaction():
            for table_id, enabled in IDS_TO_DIGESTABLE:
                config.db.store.execute(mlist_table.insert().values(
                    id=table_id, digests_enabled=enabled))
        with transaction():
            alembic.command.downgrade(alembic_cfg, '47294d3a604')
            results = config.db.store.execute(
                'SELECT id, digestable FROM mailinglist').fetchall()
        self.assertEqual(results, IDS_TO_DIGESTABLE)
        # Upgrading.
        with transaction():
            alembic.command.upgrade(alembic_cfg, '70af5a4e5790')
        results = config.db.store.execute(
            'SELECT id, digests_enabled FROM mailinglist').fetchall()
        self.assertEqual(results, IDS_TO_DIGESTABLE)

    def test_70af5a4e5790_data_paths(self):
        # Create a couple of mailing lists through the standard API.
        with transaction():
            ant = create_list('ant@example.com')
            bee = create_list('bee@example.com')
        # Downgrade and verify that the old data paths exist.
        alembic.command.downgrade(alembic_cfg, '47294d3a604')
        self.assertTrue(os.path.exists(
            os.path.join(config.LIST_DATA_DIR, 'ant@example.com')))
        self.assertTrue(os.path.exists(
            os.path.join(config.LIST_DATA_DIR, 'ant@example.com')))
        # Upgrade and verify that the new data paths exists and the old ones
        # no longer do.
        alembic.command.upgrade(alembic_cfg, '70af5a4e5790')
        self.assertFalse(os.path.exists(
            os.path.join(config.LIST_DATA_DIR, 'ant@example.com')))
        self.assertFalse(os.path.exists(
            os.path.join(config.LIST_DATA_DIR, 'ant@example.com')))
        self.assertTrue(os.path.exists(ant.data_path))
        self.assertTrue(os.path.exists(bee.data_path))
