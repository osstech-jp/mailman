# Copyright (C) 2007-2023 by the Free Software Foundation, Inc.
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

"""Implementations of the IPendable and IPending interfaces."""

import json

from lazr.config import as_timedelta
from mailman.config import config
from mailman.database.model import Model
from mailman.database.transaction import dbconnection
from mailman.database.types import SAUnicode, SAUnicodeXL
from mailman.interfaces.pending import (
    IPendable,
    IPended,
    IPendedKeyValue,
    IPendings,
)
from mailman.interfaces.workflow import IWorkflowStateManager
from mailman.utilities.datetime import now
from mailman.utilities.uid import TokenFactory
from public import public
from sqlalchemy import and_, Column, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import aliased, relationship
from zope.component import getUtility
from zope.interface import implementer
from zope.interface.verify import verifyObject


token_factory = TokenFactory()


@public
@implementer(IPendedKeyValue)
class PendedKeyValue(Model):
    """A pended key/value pair, tied to a token."""

    __tablename__ = 'pendedkeyvalue'
    __table_args__ = (Index('ix_pendedkeyvalue_value', 'value',
                            mysql_length=100), )

    id = Column(Integer, primary_key=True)
    key = Column(SAUnicode, index=True)
    value = Column(SAUnicodeXL)
    pended_id = Column(Integer, ForeignKey('pended.id'), index=True)

    def __init__(self, key, value):
        self.key = key
        self.value = value


@public
@implementer(IPended)
class Pended(Model):
    """A pended event, tied to a token."""

    __tablename__ = 'pended'

    id = Column(Integer, primary_key=True)
    token = Column(SAUnicode, index=True)
    expiration_date = Column(DateTime, index=True)
    key_values = relationship('PendedKeyValue', cascade='all, delete-orphan')


@public
@implementer(IPendable)
class UnpendedPendable(dict):
    PEND_TYPE = 'unpended'


@public
@implementer(IPendings)
class Pendings:
    """Implementation of the IPending interface."""

    @dbconnection
    def add(self, store, pendable, lifetime=None):
        verifyObject(IPendable, pendable)
        # Calculate the token and the lifetime.
        if lifetime is None:
            if pendable.get('token_owner', None) == 'moderator':
                lifetime = as_timedelta(config.mailman.moderator_request_life)
            else:
                lifetime = as_timedelta(config.mailman.pending_request_life)
        for attempts in range(3):
            token = token_factory.new()
            # In practice, we'll never get a duplicate, but we'll be anal
            # about checking anyway.
            if store.query(Pended).filter_by(token=token).count() == 0:
                break
        else:
            raise RuntimeError('Could not find a valid pendings token')
        # Create the record, and then the individual key/value pairs.
        pending = Pended(
            token=token,
            expiration_date=now() + lifetime)
        pendable_type = pendable.get('type', pendable.PEND_TYPE)
        pending.key_values.append(
            PendedKeyValue(key='type', value=pendable_type))
        for key, value in pendable.items():
            # The type has been handled above.
            if key == 'type':
                continue
            # Both keys and values must be strings.
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                # Make sure we can turn this back into a bytes.
                value = dict(__encoding__='utf-8',
                             value=value.decode('utf-8'))
            keyval = PendedKeyValue(key=key, value=json.dumps(value))
            pending.key_values.append(keyval)
        store.add(pending)
        return token

    @dbconnection
    def confirm(self, store, token, *, expunge=True):
        # Token can come in as a unicode, but it's stored in the database as
        # bytes.  They must be ascii.
        pendings = store.query(Pended).filter_by(token=str(token))
        pendings_count = pendings.count()
        if pendings_count == 0:
            return None
        assert pendings_count == 1, (
            'Unexpected token count: {}'.format(pendings_count))
        pending = pendings[0]
        pendable = UnpendedPendable()
        # Iterate on PendedKeyValue entries that are associated with the
        # pending object's ID.  Watch out for type conversions.
        for keyvalue in pending.key_values:
            # The `type` key is special and reserved.  It is not JSONified.
            # See the IPendable interface for details.
            if keyvalue.key == 'type':
                value = keyvalue.value
            else:
                value = json.loads(keyvalue.value)
            if isinstance(value, dict) and '__encoding__' in value:
                value = value['value'].encode(value['__encoding__'])
            pendable[keyvalue.key] = value
        if expunge:
            store.delete(pending)
            # Discard associated workflow if any.
            getUtility(IWorkflowStateManager).discard(token)
        return pendable

    @dbconnection
    def evict(self, store):
        right_now = now()
        for pending in store.query(Pended).all():
            if pending.expiration_date < right_now:
                store.delete(pending)

    @dbconnection
    def _query(
        self, store, mlist, pend_type, token_owner, held_msgid
    ):
        query = store.query(Pended)
        if mlist is not None:
            pkv_alias_mlist = aliased(PendedKeyValue)
            query = query.join(pkv_alias_mlist).filter(and_(
                pkv_alias_mlist.key == 'list_id',
                pkv_alias_mlist.value == json.dumps(mlist.list_id)
                ))
        if held_msgid is not None:
            pkv_alias_held_msg = aliased(PendedKeyValue)
            query = query.join(pkv_alias_held_msg).filter(and_(
                pkv_alias_held_msg.key == '_mod_message_id',
                pkv_alias_held_msg.value == json.dumps(held_msgid)
                ))
        if pend_type is not None:
            pkv_alias_type = aliased(PendedKeyValue)
            query = query.join(pkv_alias_type).filter(and_(
                pkv_alias_type.key == 'type',
                pkv_alias_type.value == pend_type
                ))
        if token_owner is not None:
            pkv_alias_type = aliased(PendedKeyValue)
            query = query.join(pkv_alias_type).filter(and_(
                pkv_alias_type.key == 'token_owner',
                pkv_alias_type.value == json.dumps(token_owner.name)
                ))
        return query

    def find(
        self,
        mlist=None,
        pend_type=None,
        confirm=True,
        token_owner=None,
        held_msgid=None,
    ):
        query = self._query(mlist, pend_type, token_owner, held_msgid)
        for pending in query:
            pendable = (self.confirm(pending.token, expunge=False)
                        if confirm else None)
            yield pending.token, pendable

    @dbconnection
    def __iter__(self, store):
        for pending in store.query(Pended).all():
            yield pending.token, self.confirm(pending.token, expunge=False)

    def count(
        self, mlist=None, pend_type=None, token_owner=None, held_msgid=None
    ):
        query = self._query(mlist, pend_type, token_owner, held_msgid)
        return query.count()
