"""Tests for CLI commands using Typer's CliRunner (offline-capable commands only)."""

from __future__ import annotations

from typer.testing import CliRunner

from hub.cli import app

runner = CliRunner()


# -----------------------------------------------------------------
# Hub status (offline)
# -----------------------------------------------------------------


def test_status_offline():
    """'sqb status' reports the hub as stopped and lists the hello app."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "stopped" in result.output.lower()
    assert "hello" in result.output.lower()


# -----------------------------------------------------------------
# App commands (offline)
# -----------------------------------------------------------------


def test_app_list_offline():
    """'sqb app list' lists the hello app."""
    result = runner.invoke(app, ["app", "list"])
    assert result.exit_code == 0
    assert "hello" in result.output.lower()


def test_app_remove_nonexistent():
    """'sqb app remove nonexistent_app_xyz' fails gracefully."""
    result = runner.invoke(app, ["app", "remove", "nonexistent_app_xyz"])
    # Should exit with code 1 or show an error message
    assert result.exit_code != 0 or "not found" in result.output.lower()


# -----------------------------------------------------------------
# Frontend commands
# -----------------------------------------------------------------


def test_frontend_list():
    """'sqb frontend list hello' shows the default frontend as active."""
    result = runner.invoke(app, ["frontend", "list", "hello"])
    assert result.exit_code == 0
    assert "default" in result.output.lower()
    assert "yes" in result.output.lower()


# -----------------------------------------------------------------
# Help
# -----------------------------------------------------------------


def test_help():
    """'sqb --help' shows Squareberg in the output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "squareberg" in result.output.lower()


def test_app_help():
    """'sqb app --help' lists expected subcommands."""
    result = runner.invoke(app, ["app", "--help"])
    assert result.exit_code == 0
    output_lower = result.output.lower()
    assert "list" in output_lower
    assert "add" in output_lower
    assert "remove" in output_lower
