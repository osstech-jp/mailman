=================
 Basic operation
=================

The encoding of URI components addressing a REST endpoint is Unicode
UTF-8.  There is :ref:`more information about internationalization in
Mailman <internationalization>`.

In order to do anything with the REST API, you need to know its `Basic AUTH`_
credentials, and the version of the API you wish to speak to.


Credentials
===========

If you include the proper basic authorization credentials, the request
succeeds.

    >>> import requests
    >>> response = requests.get(
    ...     'http://localhost:9001/3.0/system/versions',
    ...     auth=('restadmin', 'restpass'))
    >>> print(response.status_code)
    200


System version information
==========================

System version information can be retrieved from the server, in the form of a
JSON encoded response.

    >>> from mailman.testing.documentation import dump_json
    >>> dump_json('http://localhost:9001/3.0/system/versions')
    api_version: 3.0
    http_etag: "..."
    mailman_version: GNU Mailman 3...
    python_version: ...
    self_link: http://localhost:9001/3.0/system/versions


API Versions
============

The REST API exposes two versions which are almost completely identical.  As
you've seen above, the ``3.0`` API is the base API.  There is also a ``3.1``
API, which can be used interchangably::

    >>> dump_json('http://localhost:9001/3.1/system/versions')
    api_version: 3.1
    http_etag: "..."
    mailman_version: GNU Mailman 3...
    python_version: ...
    self_link: http://localhost:9001/3.1/system/versions

The only difference is the way UUIDs are represented.  UUIDs are 128-bit
unique ids for objects such as users and members.  In version ``3.0`` of the
API, UUIDs are represented as 128-bit integers, but these were found to be
incompatible for some versions of JavaScript, so in API version ``3.1`` UUIDs
are represented as hex strings.

Choose whichever API version makes sense for your application.  In general, we
recommend using API ``3.1``, but most of the current documentation describes
API ``3.0``.  Just make the mental substitution as you read along.


Input Types
===========

The REST API accepts POST data in two forms, ``application/json`` and
``application/x-www-form-urlencoded``. You can send data as JSON::

     >>> response = requests.post('http://localhost:9001/3.1/domains',
     ...                          auth=('restadmin', 'restpass'),
     ...                          json={'mail_host': 'example.org',})
     >>> print(response.status_code)
     201


You can also send data as form parameters::

    >>> response = requests.post('http://localhost:9001/3.1/domains',
    ...                          auth=('restadmin', 'restpass'),
    ...                          params={'mail_host': 'example.net',})
    >>> print(response.status_code)
    201


Error Types
===========

The REST API always returns errors formatted as ``json`` with a content type of
``application/json``::

    >>> response = requests.post('http://localhost:9001/3.1/domains',
    ...                          auth=('restadmin', 'restpass'),
    ...                          json={'mail_host': 'example.org',})
    >>> print(response.status_code)
    400
    >>> print(response.headers.get('content-type', None))
    application/json; charset=UTF-8
    >>> print(response.json()['title'])
    400 Bad Request
    >>> print(response.json()['description'])
    Duplicate email host: example.org


.. _REST: https://en.wikipedia.org/wiki/REST
.. _`Basic AUTH`: https://en.wikipedia.org/wiki/Basic_auth
