# Contributing

This page covers everything you need to develop, test, and release Squareberg.

## Development Setup

```bash
git clone https://github.com/squareberg/squareberg-hub
cd squareberg-hub
uv venv --prompt sqb --python 3.12
uv pip install -e ".[docs,dev]"
```

Verify the installation:

```bash
sqb --help
.venv/bin/pytest tests/
```

!!! tip "Requirements"
    You need Python 3.10+, Node.js 18+, `uv`, and Git installed on your system.

## Dashboard Build

The hub dashboard is a Preact + daisyUI + Tailwind SPA located under `hub/dashboard/`.

To rebuild it use the bash script at the root of the repo:

```bash
./build-hub.sh
```

The built `hub/dashboard/dist/` directory is committed to the repo so the Python package works without requiring Node.js at install time.

!!! warning "Commit the build output"
    You **must** rebuild and commit `dist/` whenever you change dashboard source files (`hub/dashboard/src/`, `hub/dashboard/index.html`, etc.). Forgetting this means the installed package will serve stale assets.

## Running Tests

Run the full test suite (42 tests, unit + functional):

```bash
pytest tests/
```

Functional tests in `test_process_lifecycle.py` require the hello app venv to exist. Set it up once:

```bash
uv venv examples/hello/.venv
uv pip install fastapi uvicorn --python examples/hello/.venv/bin/python
```

!!! tip "Unix socket paths"
    Tests use short `/tmp/sqb-*` paths for Unix sockets to avoid the macOS 104-character socket path limit.

## Building for PyPI

Make sure the dashboard is built first (see above), then:

```bash
uv pip install build
python -m build
```

This produces:

- `dist/squareberg_hub-{version}-py3-none-any.whl`
- `dist/squareberg_hub-{version}.tar.gz`

The wheel includes the pre-built dashboard artifacts but **not** the dashboard source or `node_modules`.

Verify the wheel contents:

```bash
python -c "import zipfile; z = zipfile.ZipFile('dist/squareberg_hub-*.whl'); print('\n'.join(sorted(z.namelist())))"
```

## Release Checklist

1. Update `version` in `pyproject.toml`
2. Rebuild dashboard: `cd hub/dashboard && npm run build`
3. Run tests: `pytest tests/`
4. Build docs: `mkdocs build --strict`
5. Build package: `python -m build`
6. Inspect wheel and sdist contents
7. Commit all changes (including `hub/dashboard/dist/`)
8. Tag: `git tag v{version}`
9. Push: `git push && git push --tags`
10. Publish: `twine upload dist/*` (or `uv publish`)

## Documentation

Docs are built with mkdocs-material. To preview locally use the bash script at the root of the repo:

```bash
./serve-docs.sh
```

Build with strict mode to catch broken links:

```bash
mkdocs build --strict
```

Docs are deployed to GitHub Pages automatically when a `v*` tag is pushed.

## Project Structure

| Directory | Description |
|-----------|-------------|
| `hub/` | Hub backend: FastAPI server, reverse proxy, app registry, and process manager |
| `hub/dashboard/` | Hub dashboard SPA (Preact + daisyUI + Tailwind) |
| `examples/` | Example apps (e.g. `hello/` minimal demo) |
| `tests/` | pytest unit and functional tests |
| `docs/` | mkdocs-material documentation source |
| `blueprints/` | Design documents and architecture notes |
