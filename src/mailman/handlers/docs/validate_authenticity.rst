=====================
Validate Authenticity
=====================

Incoming messages have the ability to be authenticated via the DKIM and DMARC
protocols, which are used for ARC signing of messages.  The results of these
authentication checks are added to an Authentication-Results header which is
added to the top of the message.  If the most recent Authentication-Results
header is from a trusted domain, as specified in the configuration file, the
results of both sets of authentication checks are merged. ARC authentication is
enable and configured via the ``[ARC]`` section of ``mailman.cfg``.  Further
documentation is included there.
