# Copyright (C) 2015-2018 by the Free Software Foundation, Inc.
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

"""Experimental Gunicorn based REST server.

To use this do the following:

* Install gunicorn as a Python 3 application (in a venv if necessary).
* Copy this file into your Python's site-packages under the name mmgunicorn.py
* Create a mailman.cfg with at least the following in it:

  [runner.rest]
  start: no

* Start Mailman as normal: `mailman start`
* Set the MAILMAN_CONFIG_FILE environment variable to the location of your
  mailman.cfg file from above.
* Run: gunicorn mmgunicorn:run
"""

from public import public


_initialized = False


@public
def run(environ, start_response):
    """Create the WSGI application.

    Use this if you want to integrate Mailman's REST server with an external
    WSGI server, such as gunicorn.  Be sure to set the $MAILMAN_CONFIG_FILE
    environment variable.
    """
    # Imports are here to evaluate them lazily, prevent circular imports, and
    # make flake8 happy.
    global _initialized
    if not _initialized:
        from mailman.core.initialize import initialize
        # First things first, initialize the system before any other imports or
        # other operations.  It must only be initialized once though.
        initialize(propagate_logs=True)
        _initialized = True
    # Hook things up to WSGI.
    from mailman.rest.wsgiapp import make_application
    app = make_application()
    return app(environ, start_response)
