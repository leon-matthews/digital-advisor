#!/bin/bash

# Run flake8 Python linter on an application.

set -o nounset
set +o errexit
set +o xtrace


if [ $# -ne 0 ]; then
    echo "Run 'flake8' Python linter on an application."
    echo "usage: $0"
    exit 1
fi


flake8 --benchmark --config .flake8 --statistics
