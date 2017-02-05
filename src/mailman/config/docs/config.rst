.. _configuration:

=====================
 Configuring Mailman
=====================

This is Mailman's default configuration, directly included from the source
code.  The format is standard "ini"-style.

You can override these in your configuration to modify the behavior of Mailman
Core.  To override these settings, these file system paths are search in
order:

* The file system path specified by the environment variable
  ``$MAILMAN_CONFIG_FILE``;
* ``mailman.cfg`` in the current working directory;
* ``var/etc/mailman.cfg`` relative to the current working directory;
* ``$HOME/.mailman.cfg``
* ``/etc/mailman.cfg``
* ``../../etc/mailman.cfg`` relative to the working directory of ``argv[0]``

You only need to include the settings you want to override.  They must be
specified inside the appropriate section.  For example, to override the "no
reply address" only, put this in your ``mailman.cfg`` file::

    [mailman]
    noreply_address: ignore@example.com

You will need to restart Mailman for any changes to take effect.


schema.cfg
==========

``schema.cfg`` defines the ini-file schema and contains documentation for
every section and configuration variable.  Sections that are named with a
suffix of ``.master`` or ``.template`` (e.g. ``paths.master``) are "template"
sections which must be defined in the ``mailman.cfg`` file [#]_.

.. literalinclude:: ../schema.cfg


mailman.cfg
===========

Configuration options provided in the source code's ``mailman.cfg`` override
those provided in ``schema.cfg``.  Your own ``mailman.cfg`` file overrides
these.

.. literalinclude:: ../mailman.cfg


.. [#] The technical differences are described in the `lazr.config
       <http://pythonhosted.org/lazr.config/>`_ package, upon which Mailman's
       configuration system is based.
