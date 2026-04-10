#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> Upgrading npm dependencies..."
npx npm-check-updates -u
npm install

echo "==> Done."
