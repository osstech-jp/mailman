#!/bin/bash
MAILMAN_EXTRA_TESTING_CFG=mysql.cfg tox -e py38-nocov-mysql -- $@