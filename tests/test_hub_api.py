"""Tests for the hub's FastAPI endpoints using TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from hub.main import app


@pytest.fixture(scope="module")
def client():
    """Module-scoped TestClient — triggers the app lifespan once."""
    with TestClient(app) as c:
        yield c


# -----------------------------------------------------------------
# Registry endpoints
# -----------------------------------------------------------------


def test_registry_list(client: TestClient):
    """GET /registry returns 200 with the hello app in the list."""
    resp = client.get("/registry")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = [app_info["name"] for app_info in data]
    assert "hello" in names


def test_registry_get_existing(client: TestClient):
    """GET /registry/hello returns correct metadata."""
    resp = client.get("/registry/hello")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "hello"
    assert "display_name" in data
    assert "version" in data
    assert "status" in data


def test_registry_get_nonexistent(client: TestClient):
    """GET /registry/nonexistent returns 404."""
    resp = client.get("/registry/nonexistent")
    assert resp.status_code == 404


def test_registry_spec_not_running(client: TestClient):
    """GET /registry/hello/spec returns 503 when the app is stopped."""
    resp = client.get("/registry/hello/spec")
    assert resp.status_code == 503


# -----------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------


def test_dashboard_placeholder(client: TestClient):
    """GET / returns 200 with 'Squareberg' in the HTML."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Squareberg" in resp.text


# -----------------------------------------------------------------
# Proxy endpoints
# -----------------------------------------------------------------


def test_proxy_app_not_running(client: TestClient):
    """GET /apps/hello/api/hello returns 503 when the app is stopped."""
    resp = client.get("/apps/hello/api/hello")
    assert resp.status_code == 503


def test_proxy_app_not_found(client: TestClient):
    """GET /apps/nonexistent/api/hello returns 404."""
    resp = client.get("/apps/nonexistent/api/hello")
    assert resp.status_code == 404
