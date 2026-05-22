"""asyncio-manager: Cliente AMI asíncrono moderno para Asterisk.

Ver https://github.com/anomalyco/asyncio-manager para documentación completa.
"""

from asyncio_manager.call_manager import Call, CallManager
from asyncio_manager.config import ManagerConfig
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
from asyncio_manager.fast_agi import FastAGIServer, Request
from asyncio_manager.logger import logger, setup_logging
from asyncio_manager.manager import Manager
from asyncio_manager.message import Message
from asyncio_manager.utils import ReconnectionConfig

__all__ = [
    # Clases principales
    "Manager",
    "Message",
    "CallManager",
    "Call",
    "FastAGIServer",
    "Request",
    # Configuración
    "ManagerConfig",
    "ReconnectionConfig",
    # Logging
    "logger",
    "setup_logging",
    # Excepciones
    "AsyncioManagerError",
    "ConnectionError",
    "AuthenticationError",
    "TimeoutError",
    "ProtocolError",
    "DisconnectedError",
    "ActionError",
    "AGIError",
    "AGIResultHangup",
    "AGINoResultError",
    "AGIUnknownError",
    "AGIAppError",
    "AGIDeadChannelError",
    "AGIInvalidCommand",
    "AGIUsageError",
]

__version__ = "1.0.0"
