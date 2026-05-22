"""Type aliases y helpers de tipos para asyncio-manager.

Centraliza las definiciones de tipos utilizadas en toda la librería,
facilitando el mantenimiento y garantizando consistencia en los type hints.
"""

from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from asyncio_manager.message import Message

# Diccionario que representa una acción AMI a enviar
# Ejemplo: {"Action": "Ping", "ActionID": "abc123"}
ActionDict = Dict[str, str]

# Headers de una respuesta o evento AMI
HeadersDict = Dict[str, str]

# Callback para eventos registrados
# Recibe el mensaje del evento y retorna una corrutina
EventCallback = Callable[[Message], Awaitable[None]]

# Callback para eventos de reconexión
ReconnectCallback = Callable[[int], Awaitable[None]]

# Resultado de una acción: un mensaje simple o una lista (modo EventList)
ActionResult = Union[Message, List[Message]]

# Callback para acciones asíncronas (originate con Async: True)
AsyncActionCallback = Callable[[Message], Awaitable[None]]

# ID único de acción o de llamada
IDType = str

# Nivel de logging aceptado por setup_logging
LogLevel = int
