"""Tests para el módulo exceptions.py."""

import pytest

from asyncio_manager.exceptions import (
    AGIAppError,
    AGIDeadChannelError,
    AGIError,
    AGIInvalidCommand,
    AGINoResultError,
    AGIResultHangup,
    AGIUnknownError,
    AGIUsageError,
    ActionError,
    AsyncioManagerError,
    AuthenticationError,
    ConnectionError,
    DisconnectedError,
    ProtocolError,
    TimeoutError,
)


class TestExceptionHierarchy:
    """Tests de la jerarquía de excepciones."""

    def test_base_exception(self):
        assert issubclass(ConnectionError, AsyncioManagerError)
        assert issubclass(AuthenticationError, AsyncioManagerError)
        assert issubclass(TimeoutError, AsyncioManagerError)
        assert issubclass(ProtocolError, AsyncioManagerError)
        assert issubclass(DisconnectedError, AsyncioManagerError)
        assert issubclass(ActionError, AsyncioManagerError)

    def test_agi_exceptions(self):
        assert issubclass(AGIError, AsyncioManagerError)
        assert issubclass(AGIResultHangup, AGIError)
        assert issubclass(AGINoResultError, AGIError)
        assert issubclass(AGIUnknownError, AGIError)
        assert issubclass(AGIAppError, AGIError)
        assert issubclass(AGIDeadChannelError, AGIError)
        assert issubclass(AGIInvalidCommand, AGIError)
        assert issubclass(AGIUsageError, AGIError)

    def test_catch_base(self):
        """Capturar AsyncioManagerError captura todas."""
        with pytest.raises(AsyncioManagerError):
            raise ConnectionError("test")

        with pytest.raises(AsyncioManagerError):
            raise AuthenticationError("test")

        with pytest.raises(AsyncioManagerError):
            raise AGIError("test", {"code": 510})

    def test_exception_message(self):
        """Las excepciones almacenan mensaje."""
        exc = AuthenticationError("Invalid credentials")
        assert str(exc) == "Invalid credentials"

    def test_agi_error_items(self):
        """AGIError almacena items adicionales."""
        exc = AGIError("Command failed", {"code": 510, "line": "invalid"})
        assert exc.items["code"] == 510
        assert exc.items["line"] == "invalid"

    def test_agi_error_default_items(self):
        """AGIError sin items usa dict vacío."""
        exc = AGIError("Error")
        assert exc.items == {}
