.. _rest-api:

========================
 Mailman 3 Core REST API
========================

Here is extensive documentation on the Mailman Core administrative REST API.


The REST server
===============

Mailman exposes a REST HTTP server for administrative control.

The server listens for connections on a configurable host name and port.

It is always protected by HTTP basic authentication using a single global
user name and password. The credentials are set in the `[webservice]` section
of the configuration using the `admin_user` and `admin_pass` properties.

Because the REST server has full administrative access, it should never be
exposed to the public internet.  By default it only listens to connections on
``localhost``.  Don't change this unless you really know what you're doing.
In addition you should set the user name and password to secure values and
distribute them to any REST clients with reasonable precautions.

The Mailman major and minor version numbers are in the URL.

You can write your own HTTP clients to speak this API, or you can use the
`official Python bindings`_.


Root URL
========

In this documentation, we mainly use ``http://localhost:9001/3.0/``   
as the REST root url. Port ``9001`` is used for unit tests, but 
for a running system, the port is ``8001`` unless changed in config. 

In the documentation we use ``3.0`` as the primary API version, but 
the latest version of the API might be different. You may check the 
difference of versions in `Basic Operation`_.

The ``hostname`` and ``port`` where Mailman's REST API will be 
listening can be found by running `mailman info`_ command. 
You can configure that in ``mailman.cfg`` configuration file.::

    >>> command = cli('mailman.commands.cli_info.info')

    >>> command('mailman info')
    GNU Mailman 3...
    Python ...
    ...
    config file: .../test.cfg
    db url: ...
    REST root url: http://localhost:9001/3.1/
    REST credentials: restadmin:restpass


REST API Documentation
======================

.. toctree::
   :glob:
   :maxdepth: 1

   ./basic
   ./collections
   ./helpers
   ./systemconf
   ./domains
   ./lists
   ./listconf
   ./addresses
   ./users
   ./membership
   ./queues
   ./*


.. _`official Python bindings`: https://mailmanclient.readthedocs.io/en/latest/
.. _`mailman info`: https://mailman.readthedocs.io/en/latest/src/mailman/config/docs/config.html#which-configuration-file-is-in-use
.. _`Basic Operation`: https://mailman.readthedocs.io/en/latest/src/mailman/rest/docs/basic.html#api-versions
