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

"""Interface for a SMTP connection."""

from public import public
from zope.interface import Interface


@public
class ISMTPConnection(Interface):
    """A SMTP connection. Like smtplib.SMTP."""

    def sendmail(self, envsender, recipients, msgtext):
        """Mimic `smtplib.SMTP.sendmail`."""

    def quit(self):
        """Mimic `smtplib.SMTP.quit`."""
