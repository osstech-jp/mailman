# Copyright (C) 2016 by the Free Software Foundation, Inc.
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

"""Some helpers for queries."""

__all__ = [
    'QuerySequence',
    ]


from collections.abc import Sequence


class QuerySequence(Sequence):
    def __init__(self, query=None):
        super().__init__()
        self._query = query
        self._cached_results = None

    def __len__(self):
        return (0 if self._query is None else self._query.count())

    def __getitem__(self, index):
        if self._query is None:
            raise IndexError('index out of range')
        if self._cached_results is None:
            self._cached_results = list(self._query)
        return self._cached_results[index]
