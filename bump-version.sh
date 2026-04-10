#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

usage() {
    echo "Usage: $(basename "$0") <version>"
    echo "  e.g. $(basename "$0") 0.1.2"
    exit 1
}

[[ $# -eq 1 ]] || usage
VERSION="$1"
TAG="v${VERSION}"

# Basic sanity check: version should look like X.Y.Z
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: version must be in X.Y.Z format (got '$VERSION')." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

# Repo must be clean (no staged or unstaged changes, no untracked files)
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Error: there are uncommitted changes. Please commit or stash them first." >&2
    exit 1
fi

# Tag must not already exist (locally or remotely)
if git tag | grep -qx "$TAG"; then
    echo "Error: tag '$TAG' already exists locally." >&2
    exit 1
fi
if git ls-remote --tags origin | grep -q "refs/tags/${TAG}$"; then
    echo "Error: tag '$TAG' already exists on remote." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Bump version
# ---------------------------------------------------------------------------

echo "==> Bumping version to $VERSION..."

# hub/__init__.py is the single source of truth; pyproject.toml and
# hub/main.py both read from it dynamically.
sed -i.bak -E "s/^__version__ = \"[^\"]+\"/__version__ = \"${VERSION}\"/" hub/__init__.py
rm hub/__init__.py.bak

# ---------------------------------------------------------------------------
# Commit, tag, push
# ---------------------------------------------------------------------------

git add hub/__init__.py
git commit -m "Bump version to ${VERSION}"

echo "==> Creating tag $TAG..."
git tag "$TAG"

echo "==> Pushing to origin..."
git push origin main
git push origin "$TAG"

echo "==> Done. Version bumped to $VERSION and tag $TAG pushed."
