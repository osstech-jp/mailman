=================
 Basic operation
=================

In order to do anything with the REST API, you need to know its `Basic AUTH`_
credentials, and the version of the API you wish to speak to.


Credentials
===========

When the `Authorization` header contains the proper credentials, the request
succeeds.

    >>> from httplib2 import Http
    >>> headers = {
    ...     'Content-Type': 'application/x-www-form-urlencode',
    ...     'Authorization': 'Basic cmVzdGFkbWluOnJlc3RwYXNz',
    ...     }
    >>> url = 'http://localhost:9001/3.0/system/versions'
    >>> response, content = Http().request(url, 'GET', None, headers)
    >>> print(response.status)
    200


System version information
==========================

System version information can be retrieved from the server, in the form of a
JSON encoded response.

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


.. _REST: http://en.wikipedia.org/wiki/REST
.. _`Basic AUTH`: https://en.wikipedia.org/wiki/Basic_auth
