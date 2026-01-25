#!/bin/bash
# Check that versions in pyproject.toml and config.yaml are synchronized

set -e

PYPROJECT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
CONFIG_VERSION=$(grep '^version: ' config.yaml | sed 's/version: "\(.*\)"/\1/')

if [ "$PYPROJECT_VERSION" != "$CONFIG_VERSION" ]; then
    echo "❌ Version mismatch!"
    echo "   pyproject.toml: $PYPROJECT_VERSION"
    echo "   config.yaml:    $CONFIG_VERSION"
    echo ""
    echo "Please ensure both files have the same version."
    exit 1
fi

echo "✓ Versions synchronized: $PYPROJECT_VERSION"
exit 0
