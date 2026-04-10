#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "==> Installing docs dependencies..."
uv pip install -e ".[docs]"

echo "==> Serving docs (http://127.0.0.1:8000)..."
export NO_MKDOCS_2_WARNING=1
mkdocs serve -w docs -w mkdocs.yml --livereload
