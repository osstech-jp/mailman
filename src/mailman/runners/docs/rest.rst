===========
REST server
===========

Mailman is controllable through an administrative `REST`_ HTTP server.

    >>> from mailman.testing import helpers
    >>> master = helpers.TestableMaster(helpers.wait_for_webservice)
    >>> master.start('rest')

The RESTful server can be used to access basic version information.

    >>> from mailman.testing.documentation import dump_json
    >>> dump_json('http://localhost:9001/3.1/system')
    api_version: 3.1
    http_etag: "..."
    mailman_version: GNU Mailman 3...
    python_version: ...
    self_link: http://localhost:9001/3.1/system/versions

Previous versions of the REST API can also be accessed.

    >>> dump_json('http://localhost:9001/3.0/system')
    api_version: 3.0
    http_etag: "..."
    mailman_version: GNU Mailman 3...
    python_version: ...
    self_link: http://localhost:9001/3.0/system/versions


Configuration
=============

Mailman uses `Gunicorn`_ as `WSGI`_ server. Some parts of it can be configured
by setting up options in ``[webservice]`` in configuration::

    # mailman.cfg
    [webservice]
    workers: 4

This will start up 4 workers instead of the default 2, if you need to scale
the REST API.

Additional Gunicorn configuration can be added by creating a configuration file
::

    # mailman.cfg
    [webservice]
    configuration: /etc/mailman3/gunicorn.cfg

    # /etc/mailman3/gunicorn.cfg
    [gunicorn]
    keyfile:
    certfile:


Clean up
========

    >>> master.stop()

.. _REST: https://en.wikipedia.org/wiki/REST
.. _Gunicorn: https://gunicorn.org/
.. _WSGI: https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface
