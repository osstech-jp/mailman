# Copyright (C) 2006-2016 by the Free Software Foundation, Inc.
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

"""Model for preferences."""

from mailman import public
from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.database.transaction import dbconnection
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.member import DeliveryMode, DeliveryStatus
from mailman.interfaces.preferences import IPreferences
from sqlalchemy import Boolean, Column, Integer, Unicode
from zope.component import getUtility
from zope.interface import implementer


@public
@implementer(IPreferences)
class Preferences(Model):
    """See `IPreferences`."""

    __tablename__ = 'preferences'

    id = Column(Integer, primary_key=True)
    acknowledge_posts = Column(Boolean)
    hide_address = Column(Boolean)
    _preferred_language = Column('preferred_language', Unicode)
    receive_list_copy = Column(Boolean)
    receive_own_postings = Column(Boolean)
    delivery_mode = Column(Enum(DeliveryMode))
    delivery_status = Column(Enum(DeliveryStatus))
    # When adding new columns, also add them to
    # mailman.model.tests.test_preferences.TestPreferences.test_absorb_all_attributes()

    def __repr__(self):
        return '<Preferences object at {:#x}>'.format(id(self))

    @property
    def preferred_language(self):
        if self._preferred_language is None:
            return None
        return getUtility(ILanguageManager)[self._preferred_language]

    @preferred_language.setter
    def preferred_language(self, language):
        if language is None:
            self._preferred_language = None
        # Accept both a language code and a `Language` instance.
        try:
            self._preferred_language = language.code
        except AttributeError:
            self._preferred_language = language

    @dbconnection
    def absorb(self, store, preferences):
        """See `IPreferences`."""
        column_names = [ c.name for c in self.__table__.columns
                         if not c.primary_key ]
        for cname in column_names:
            if (getattr(self, cname) is None and
                getattr(preferences, cname) is not None):
                setattr(self, cname, getattr(preferences, cname))
        store.delete(preferences)
