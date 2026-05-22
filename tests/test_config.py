"""Tests para el módulo config.py."""

import os
import tempfile

import pytest

from asyncio_manager.config import ManagerConfig


class TestManagerConfig:
    """Tests de ManagerConfig."""

    def test_default_values(self):
        config = ManagerConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 5038
        assert config.username == ""
        assert config.secret == ""
        assert config.timeout == 5.0
        assert config.ssl is False

    def test_custom_values(self):
        config = ManagerConfig(
            host="10.0.0.1",
            port=5039,
            username="testuser",
            secret="testpass",
            timeout=10.0,
        )
        assert config.host == "10.0.0.1"
        assert config.port == 5039
        assert config.username == "testuser"
        assert config.secret == "testpass"

    def test_from_file(self):
        """Carga configuración desde archivo INI."""
        ini_content = """
[asterisk]
host = 192.168.1.100
port = 5038
username = admin
secret = s3cret
timeout = 15.0
ssl = true
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ini", delete=False
        ) as f:
            f.write(ini_content)
            f.flush()
            config_path = f.name

        try:
            config = ManagerConfig.from_file(config_path)
            assert config.host == "192.168.1.100"
            assert config.port == 5038
            assert config.username == "admin"
            assert config.secret == "s3cret"
            assert config.timeout == 15.0
            assert config.ssl is True
        finally:
            os.unlink(config_path)

    def test_from_env(self):
        """Carga configuración desde variables de entorno."""
        os.environ["ASTERISK_HOST"] = "10.0.0.50"
        os.environ["ASTERISK_PORT"] = "5040"
        os.environ["ASTERISK_USERNAME"] = "envuser"
        os.environ["ASTERISK_SECRET"] = "envpass"
        os.environ["ASTERISK_SSL"] = "true"
        os.environ["ASTERISK_TIMEOUT"] = "20.0"

        try:
            config = ManagerConfig.from_env()
            assert config.host == "10.0.0.50"
            assert config.port == 5040
            assert config.username == "envuser"
            assert config.secret == "envpass"
            assert config.ssl is True
            assert config.timeout == 20.0
        finally:
            del os.environ["ASTERISK_HOST"]
            del os.environ["ASTERISK_PORT"]
            del os.environ["ASTERISK_USERNAME"]
            del os.environ["ASTERISK_SECRET"]
            del os.environ["ASTERISK_SSL"]
            del os.environ["ASTERISK_TIMEOUT"]

    def test_from_env_partial(self):
        """Variables parciales usan defaults."""
        os.environ["ASTERISK_HOST"] = "10.0.0.50"

        try:
            config = ManagerConfig.from_env()
            assert config.host == "10.0.0.50"
            assert config.port == 5038  # default
        finally:
            del os.environ["ASTERISK_HOST"]

    def test_to_dict_excludes_secret(self):
        """to_dict no incluye secret."""
        config = ManagerConfig(username="user", secret="mypassword")
        d = config.to_dict()
        assert "secret" not in d
        assert d["username"] == "user"

    def test_encoding_default(self):
        config = ManagerConfig()
        assert config.encoding == "utf-8"
