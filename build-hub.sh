#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "==> Reinstalling hub Python package..."
uv pip install -e .

echo "==> Rebuilding dashboard..."
cd hub/dashboard
npm install
npm run build

echo "==> Done."
