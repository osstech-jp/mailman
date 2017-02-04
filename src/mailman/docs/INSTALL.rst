====================
Installing Mailman 3
====================

Copyright (C) 2008-2017 by the Free Software Foundation, Inc.


Requirements
============

For the Core, Python 3.4 or newer is required.  It can either be the default
'python3' on your ``$PATH`` or it can be accessible via the ``python3.4``,
``python3.5``, or ``python3.6`` binary.  If your operating system does not
include Python 3, see http://www.python.org for information about downloading
installers (where available) and installing it from source (when necessary or
preferred).  Python 2 is not supported by the Core.

You may need some additional dependencies, which are either available from
your OS vendor, or can be downloaded automatically from the `Python
Cheeseshop`_.


Documentation
=============

The documentation for Mailman 3 is distributed throughout the sources.  The
core documentation (such as this file) is found in the ``src/mailman/docs``
directory, but much of the documentation is in module-specific places.  Online
versions of the `Mailman 3 Core documentation`_ is available online.


Get the sources
===============

The Mailman 3 source code is version controlled using Git. You can get a
local copy by running this command::

    $ git clone https://gitlab.com/mailman/mailman.git

or if you have a GitLab account and prefer ssh::

    $ git clone git@gitlab.com:mailman/mailman.git


Running Mailman 3
=================

You will need to set up a configuration file to override the defaults and set
things up for your environment.  Mailman is configured using an "ini"-style
configuration system.

``src/mailman/config/schema.cfg`` defines the ini-file schema and contains
documentation for every section and configuration variable.  Sections that end
in ``.template`` or ``.master`` are templates that must be overridden in
actual configuration files.  There is a default configuration file that
defines these basic overrides in ``src/mailman/config/mailman.cfg``.  Your own
configuration file will override those.

By default, all runtime files are put under a ``var`` directory in the current
working directory.

Mailman searches for its configuration file using the following search path.
The first existing file found wins.

* ``-C config`` command line option
* ``$MAILMAN_CONFIG_FILE`` environment variable
* ``./mailman.cfg``
* ``~/.mailman.cfg``
* ``/etc/mailman.cfg``
* ``argv[0]/../../etc/mailman.cfg``

Run the ``mailman info`` command to see which configuration file Mailman will
use, and where it will put its database file.  The first time you run this,
Mailman will also create any necessary run-time directories and log files.

Try ``mailman --help`` for more details.  You can use the commands
``mailman start`` to start the runner subprocess daemons, and of course
``mailman stop`` to stop them.

Postorius_, a web UI for administration and subscriber settings, is being
developed as a separate, Django-based project.  For now, the most flexible
means of configuration is via the command line and REST API.

Note that you can also "run" Mailman from one of the virtual environments
created by tox, e.g.::

    $ .tox/py35-nocov/bin/mailman info


Mailman Shell
=============

This documentation has examples which use the Mailman shell to interact with
Mailman.  To start the shell type ``mailman shell`` in your terminal.

There are some testings functions which need to be imported first before you
use them. They can be imported from the modules available in
``mailman.testing``.  For example, to use ``dump_list`` you first need to
import it from the ``mailman.testing.documentation`` module.

.. Of course, *this* doctest doesn't have these preloaded...
   >>> from zope.component import getUtility
   >>> from mailman.interfaces.listmanager import IListManager

The shell automatically initializes the Mailman system, loads all the
available interfaces, and configures the `Zope Component Architecture`_ (ZCA)
which is used to access all the software components in Mailman.  So for
example, if you wanted to get access to the list manager component, you could
do::

    $ mailman shell
    Welcome to the GNU Mailman shell

    >>> list_manager = getUtility(IListManager)


.. _`Postorius`: https://gitlab.com/mailman/postorius
.. _`Python Cheeseshop`: http://pypi.python.org/pypi
.. _`Mailman 3 Core documentation`: https://mailman.readthedocs.io
.. _`Zope Component Architecture`: https://pypi.python.org/pypi/zope.component
