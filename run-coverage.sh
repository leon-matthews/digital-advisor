#!/bin/bash

# Run unit tests and show code coverage of same, if all tests pass.

set -o nounset
set -o errexit
set +o xtrace

if [ $# -ne 0 ]; then
    echo "Produce a test coverage report."
    echo "usage: $0"
    exit 1
fi

command="python3 -m unittest discover $@"
echo "$command"
coverage run --branch "$command"
coverage report --omit="$MODULE/migrations/*" --show-missing --skip-covered
coverage erase
