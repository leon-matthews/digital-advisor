#!/bin/bash

# Run 'mypy' optional static type checking on application.

set -o nounset
set +o errexit
set +o xtrace


if [ $# -ne 0 ]; then
    echo "Produce a type-checker report for an application."
    echo "usage: $0"
    exit 1
fi


mypy --config-file .mypy.ini --sqlite-cache .
