#!/usr/bin/env bash
# Sync requirements.txt from pyproject.toml
# This script is called by pre-commit when pyproject.toml changes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Syncing requirements.txt from pyproject.toml..."

# Use Python to parse pyproject.toml and generate clean requirements.txt
python3 << 'EOF'
import tomllib

# Read pyproject.toml
with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)

# Get dependencies
deps = data.get("project", {}).get("dependencies", [])

# Group dependencies by category
output = []
output.append("# Auto-generated from pyproject.toml - do not edit manually")
output.append("# Run: make sync-requirements")
output.append("")
output.append("# Core web framework")
output.extend([d for d in deps if any(x in d.lower() for x in ["fastapi", "uvicorn"])])
output.append("")
output.append("# Database")
output.extend([d for d in deps if any(x in d.lower() for x in ["sqlalchemy", "alembic", "asyncpg", "psycopg", "aiosqlite"])])
output.append("")
output.append("# Task queue (optional for HA)")
output.extend([d for d in deps if any(x in d.lower() for x in ["celery", "redis"])])
output.append("")
output.append("# Data validation")
output.extend([d for d in deps if "pydantic" in d.lower()])
output.append("")
output.append("# Utilities")
output.extend([d for d in deps if any(x in d.lower() for x in ["dotenv", "httpx", "apscheduler"])])
output.append("")

# Write requirements.txt
with open("requirements.txt.tmp", "w") as f:
    f.write("\n".join(output))

print("Generated requirements.txt from pyproject.toml")
EOF

# Check if requirements.txt changed
if [[ -f requirements.txt.tmp ]]; then
    if ! diff -q requirements.txt requirements.txt.tmp > /dev/null 2>&1; then
        mv requirements.txt.tmp requirements.txt
        echo "requirements.txt updated"
        # Stage the updated file
        git add requirements.txt
    else
        rm -f requirements.txt.tmp
        echo "requirements.txt is up to date"
    fi
fi

exit 0
