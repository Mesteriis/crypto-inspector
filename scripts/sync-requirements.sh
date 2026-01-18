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

# Categories with their keywords
categories = [
    ("Core web framework", ["fastapi", "uvicorn"]),
    ("Database", ["sqlalchemy", "alembic", "asyncpg", "psycopg", "aiosqlite"]),
    ("Task queue (optional for HA)", ["celery", "redis"]),
    ("Data validation", ["pydantic"]),
    ("Utilities", ["dotenv", "httpx", "apscheduler"]),
    ("MCP Server", ["fastmcp", "mcp"]),
    ("Crypto & Finance", ["ccxt", "yfinance", "pandas", "numpy", "ta"]),
    ("AI & LLM", ["openai", "ollama", "langchain", "anthropic"]),
    ("HTTP & Network", ["aiohttp", "websockets", "requests"]),
]

output = []
output.append("# Auto-generated from pyproject.toml - do not edit manually")
output.append("# Run: make sync-requirements")
output.append("")

used_deps = set()

# Process categorized deps
for category, keywords in categories:
    matches = [d for d in deps if d not in used_deps and any(x in d.lower() for x in keywords)]
    if matches:
        output.append(f"# {category}")
        output.extend(matches)
        used_deps.update(matches)
        output.append("")

# Add remaining deps that weren't categorized
remaining = [d for d in deps if d not in used_deps]
if remaining:
    output.append("# Other dependencies")
    output.extend(remaining)
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
