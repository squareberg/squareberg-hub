"""Tests for CLI helper functions (_toml_value, _toml_dump, _read_manifest, _write_manifest)."""

from pathlib import Path

from hub.cli import _toml_dump, _toml_value, _read_manifest, _write_manifest


def test_toml_value_string():
    assert _toml_value("hello") == '"hello"'


def test_toml_value_int():
    assert _toml_value(42) == "42"


def test_toml_value_bool():
    assert _toml_value(True) == "true"
    assert _toml_value(False) == "false"


def test_toml_value_list():
    assert _toml_value(["a", "b"]) == '["a", "b"]'


def test_toml_dump_simple():
    data = {"key1": "value1", "key2": 42}
    lines = []
    _toml_dump(data, lines, prefix="")
    output = "\n".join(lines)
    assert 'key1 = "value1"' in output
    assert "key2 = 42" in output


def test_toml_dump_nested():
    data = {
        "top_key": "top_val",
        "section": {
            "nested_key": "nested_val",
        },
    }
    lines = []
    _toml_dump(data, lines, prefix="")
    output = "\n".join(lines)
    assert 'top_key = "top_val"' in output
    assert "[section]" in output
    assert 'nested_key = "nested_val"' in output


def test_toml_roundtrip(tmp_path):
    app_dir = tmp_path / "roundtrip-app"
    manifest_dir = app_dir / ".squareberg"
    manifest_dir.mkdir(parents=True)

    original = {
        "app": {
            "name": "roundtrip",
            "display_name": "Roundtrip App",
            "description": "Testing roundtrip",
            "version": "1.2.3",
        },
        "backend": {
            "module": "app:app",
        },
        "frontend": {
            "active": ["default"],
            "default": {
                "path": "frontend/default",
                "display_name": "Default",
            },
        },
    }

    _write_manifest(app_dir, original)
    loaded = _read_manifest(app_dir)

    assert loaded["app"]["name"] == "roundtrip"
    assert loaded["app"]["display_name"] == "Roundtrip App"
    assert loaded["app"]["description"] == "Testing roundtrip"
    assert loaded["app"]["version"] == "1.2.3"
    assert loaded["backend"]["module"] == "app:app"
    assert loaded["frontend"]["active"] == ["default"]
    assert loaded["frontend"]["default"]["path"] == "frontend/default"
