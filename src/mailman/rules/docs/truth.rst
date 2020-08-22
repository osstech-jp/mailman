=====
Truth
=====

This rule always matches.  This makes it useful as a terminus rule for
unconditionally jumping to another chain.

    >>> from mailman.config import config
    >>> rule = config.rules['truth']
    >>> rule.check(False, False, False)
    True
