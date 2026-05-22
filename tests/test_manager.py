"""Tests para el módulo manager.py.

Usa mocking para simular el protocolo sin conexión real a Asterisk.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asyncio_manager.exceptions import ConnectionError
from asyncio_manager.manager import Manager, EventCallbackItem
from asyncio_manager.message import Message


class TestEventCallbackItem:
    """Tests de EventCallbackItem."""

    @pytest.mark.asyncio
    async def test_wildcard_match(self):
        """Patrón * coincide con todo."""
        callback = AsyncMock()
        item = EventCallbackItem("*", callback)
        msg = Message({"Event": "NewChannel"})
        assert item.match(msg)

    @pytest.mark.asyncio
    async def test_exact_match(self):
        """Patrón exacto coincide."""
        callback = AsyncMock()
        item = EventCallbackItem("NewChannel", callback)
        assert item.match(Message({"Event": "NewChannel"}))
        assert not item.match(Message({"Event": "Hangup"}))

    @pytest.mark.asyncio
    async def test_prefix_match(self):
        """Patrón con wildcard coincide por prefijo."""
        callback = AsyncMock()
        item = EventCallbackItem("Queue*", callback)
        assert item.match(Message({"Event": "QueueStatusComplete"}))
        assert item.match(Message({"Event": "QueueParams"}))
        assert not item.match(Message({"Event": "NewChannel"}))

    @pytest.mark.asyncio
    async def test_no_event_type(self):
        """Mensaje sin Event no coincide."""
        callback = AsyncMock()
        item = EventCallbackItem("*", callback)
        assert not item.match(Message({"Response": "Success"}))


class TestManagerCreation:
    """Tests de creación de Manager."""

    def test_default_values(self):
        manager = Manager()
        assert manager._config.host == "127.0.0.1"
        assert manager._config.port == 5038
        assert not manager.is_connected

    def test_custom_values(self):
        manager = Manager(
            host="10.0.0.1",
            port=5040,
            username="test",
            secret="pass",
            timeout=15.0,
        )
        assert manager._config.host == "10.0.0.1"
        assert manager._config.port == 5040
        assert manager._config.username == "test"
        assert manager._config.timeout == 15.0

    def test_config_object(self):
        from asyncio_manager.config import ManagerConfig
        config = ManagerConfig(host="192.168.1.1", port=5039)
        manager = Manager(config=config)
        assert manager._config.host == "192.168.1.1"
        assert manager._config.port == 5039


class TestManagerConnect:
    """Tests de conexión (con mocking)."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Conexión exitosa (mockeando protocolo)."""
        manager = Manager(username="admin", secret="pass")

        with patch("asyncio_manager.manager.AMIProtocol") as mock_proto_class:
            mock_instance = MagicMock()
            mock_instance.connect = AsyncMock()
            mock_instance.send_action = AsyncMock()
            mock_instance.send_action.return_value = Message({
                "Response": "Success",
                "Message": "Authentication accepted",
            })
            mock_proto_class.return_value = mock_instance

            await manager.connect()

            assert manager._connected
            assert manager._authenticated

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Fallo de conexión."""
        manager = Manager(username="admin", secret="pass")

        with patch("asyncio_manager.manager.AMIProtocol") as mock_proto_class:
            mock_instance = MagicMock()
            mock_instance.connect = AsyncMock(
                side_effect=ConnectionError("Connection refused")
            )
            mock_proto_class.return_value = mock_instance

            with pytest.raises(ConnectionError):
                await manager.connect()


class TestManagerSendAction:
    """Tests de send_action."""

    @pytest.mark.asyncio
    async def test_send_action_not_connected(self):
        """send_action lanza error si no conectado."""
        manager = Manager()

        with pytest.raises(ConnectionError):
            await manager.send_action({"Action": "Ping"})

    @pytest.mark.asyncio
    async def test_register_event(self):
        """Registrar evento no lanza error (se registra al conectar)."""
        manager = Manager()

        @manager.register_event("NewChannel")
        async def handler(msg):
            pass

        # No debería lanzar error
        assert handler is not None
