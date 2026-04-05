"""Tests for hub.config module."""

from pathlib import Path

from hub.config import HubConfig, get_apps_dir, get_log_dir, get_socket_dir, load_config


def test_default_config():
    cfg = HubConfig()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9100
    assert cfg.socket_mode == "xdg"
    assert cfg.log_level == "info"
    assert cfg.log_dir is None


def test_load_config_missing_file():
    cfg = load_config(Path("/nonexistent/config.toml"))
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9100
    assert cfg.socket_mode == "xdg"
    assert cfg.log_level == "info"
    assert cfg.log_dir is None


def test_load_config_from_file(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[hub]\n'
        'host = "0.0.0.0"\n'
        'port = 8080\n'
        '\n'
        '[hub.sockets]\n'
        'mode = "local"\n'
        '\n'
        '[hub.logging]\n'
        'level = "debug"\n'
        'dir = "/tmp/sqb-logs"\n'
    )
    cfg = load_config(config_file)
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 8080
    assert cfg.socket_mode == "local"
    assert cfg.log_level == "debug"
    assert cfg.log_dir == "/tmp/sqb-logs"


def test_get_socket_dir_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    cfg = HubConfig(socket_mode="xdg")
    sock_dir = get_socket_dir(cfg)
    assert sock_dir == tmp_path / "squareberg" / "sockets"
    assert sock_dir.is_dir()


def test_get_socket_dir_local():
    cfg = HubConfig(socket_mode="local")
    sock_dir = get_socket_dir(cfg)
    assert sock_dir.name == "sockets"


def test_get_log_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    cfg = HubConfig()
    log_dir = get_log_dir(cfg)
    assert log_dir == tmp_path / "squareberg" / "logs"
    assert log_dir.is_dir()


def test_get_log_dir_custom(tmp_path):
    custom_dir = str(tmp_path / "my-logs")
    cfg = HubConfig(log_dir=custom_dir)
    log_dir = get_log_dir(cfg)
    assert log_dir == Path(custom_dir)
    assert log_dir.is_dir()


def test_get_apps_dir():
    apps_dir = get_apps_dir()
    assert apps_dir.name == "apps"
    assert apps_dir.is_dir()
