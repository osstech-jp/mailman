#!/bin/bash
MAILMAN_EXTRA_TESTING_CFG=./dev/mysql.cfg tox -e py38-nocov-mysql -- $@