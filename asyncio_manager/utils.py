"""Utilidades para asyncio-manager.

Contiene:
- ``CaseInsensitiveDict``: diccionario case-insensitive para headers AMI.
- ``IdGenerator``: generador único de IDs para acciones.
- ``parse_agi_result``: parser de respuestas del protocolo AGI.
- ``calculate_delay``: cálculo de backoff exponencial con jitter.
"""

import math
import random
import re
import uuid
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from asyncio_manager.exceptions import (
    AGIAppError,
    AGIDeadChannelError,
    AGIInvalidCommand,
    AGINoResultError,
    AGIResultHangup,
    AGIUnknownError,
    AGIUsageError,
)

# Separador de líneas del protocolo AMI
EOL = "\r\n"

# Expresiones regulares para parsear resultados AGI
re_code = re.compile(r"^(?P<code>\d+)\s*(?P<result>.*)")
re_kv = re.compile(r"^(?P<key>\w+)=(?P<value>.*)")


class CaseInsensitiveDict(MutableMapping):
    """Diccionario con claves case-insensitive.

    Implementa ``collections.abc.MutableMapping`` y normaliza todas
    las claves a minúsculas internamente, pero preserva el primer
    caso usado al insertar cada clave para la representación.

    Útil para manejar headers AMI donde las claves pueden variar
    en mayúsculas/minúsculas.

    Args:
        other: Diccionario o iterable inicial para poblar el mapa.
        **kwargs: Pares clave-valor adicionales.

    Example:
        >>> d = CaseInsensitiveDict({"Content-Type": "text/plain"})
        >>> d["content-type"]
        'text/plain'
        >>> d["CONTENT-TYPE"]
        'text/plain'
    """

    def __init__(
        self,
        other: Optional[dict] = None,
        **kwargs: Any,
    ) -> None:
        self._store: dict[str, tuple[str, Any]] = {}
        if other is not None:
            self.update(other)
        self.update(kwargs)

    def __setitem__(self, key: str, value: Any) -> None:
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key: str) -> Any:
        return self._store[key.lower()][1]

    def __delitem__(self, key: str) -> None:
        del self._store[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return (cased_key for cased_key, _ in self._store.values())

    def __len__(self) -> int:
        return len(self._store)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CaseInsensitiveDict):
            return dict(self.items()) == dict(other.items())
        if isinstance(other, dict):
            return dict(self.items()) == other
        return NotImplemented

    def __repr__(self) -> str:
        items = ", ".join(f"{k!r}: {v!r}" for k, v in self.items())
        return f"{self.__class__.__name__}({{{items}}})"

    def copy(self) -> "CaseInsensitiveDict":
        """Retorna una copia superficial del diccionario."""
        return CaseInsensitiveDict(self._store.values())

    @classmethod
    def from_keys(
        cls,
        iterable: Any,
        value: Any = None,
    ) -> "CaseInsensitiveDict":
        """Crea un CaseInsensitiveDict desde un iterable de claves.

        Args:
            iterable: Iterable con las claves.
            value: Valor por defecto para cada clave.

        Returns:
            Nuevo CaseInsensitiveDict.
        """
        d = cls()
        for key in iterable:
            d[key] = value
        return d


class IdGenerator:
    """Generador de identificadores únicos para acciones AMI.

    Usa UUIDs combinados con un contador interno para garantizar
    unicidad incluso en alta concurrencia.

    Example:
        >>> gen = IdGenerator()
        >>> gen.generate()
        'a1b2c3d4-0001'
        >>> gen.generate()
        'a1b2c3d4-0002'
    """

    def __init__(self) -> None:
        self._base: str = uuid.uuid4().hex[:8]
        self._counter: int = 0

    def generate(self) -> str:
        """Genera un nuevo ID único.

        Returns:
            String con formato ``<base>-<contador>``.
        """
        self._counter += 1
        return f"{self._base}-{self._counter:04d}"


def parse_agi_result(line: str) -> str:
    """Analiza una línea de resultado del protocolo AGI.

    Procesa la línea de respuesta de un comando AGI y retorna
    el resultado. Lanza excepciones específicas según el código
    de estado retornado por Asterisk.

    Args:
        line: Línea de respuesta del servidor AGI.

    Returns:
        El resultado del comando (sin el código numérico).

    Raises:
        AGIResultHangup: Si el canal fue colgado.
        AGINoResultError: Si no hay resultado.
        AGIUnknownError: Si el código es desconocido.
    """
    match = re_code.match(line.strip())
    if not match:
        raise AGINoResultError(f"Could not parse result: {line!r}")

    code = int(match.group("code"))
    result = match.group("result").strip()

    return agi_code_check(code, result, line)


def agi_code_check(code: int, result: str, line: str) -> str:
    """Verifica el código de estado de una respuesta AGI.

    Dispara la excepción AGI correspondiente según el código:

    - ``100``: Trying (intermedio, continuar leyendo)
    - ``200``: Success (retorna el resultado)
    - ``510``: Invalid command
    - ``511``: Dead channel
    - ``520``: Usage error
    - Otros: Dependiendo del resultado, puede ser AppError o Hangup

    Args:
        code: Código numérico de la respuesta.
        result: Texto del resultado (sin código).
        line: Línea completa de respuesta (para el mensaje de error).

    Returns:
        El resultado si el código indica éxito.

    Raises:
        AGIInvalidCommand: Si el código es 510.
        AGIDeadChannelError: Si el código es 511.
        AGIUsageError: Si el código es 520.
        AGIAppError: Si el código indica error de aplicación.
        AGIResultHangup: Si el canal fue colgado.
        AGIUnknownError: Si el código es desconocido.
    """
    if code == 100:
        return result
    elif code == 200:
        return result
    elif code == 510:
        raise AGIInvalidCommand(f"Invalid command: {line}")
    elif code == 511:
        raise AGIDeadChannelError(f"Channel is dead: {line}")
    elif code == 520:
        raise AGIUsageError(f"Usage error: {line}")
    else:
        if result.startswith("-"):
            raise AGIAppError(f"App error: {line}")
        if result == "hangup":
            raise AGIResultHangup(f"Channel hangup: {line}")
        raise AGIUnknownError(f"Unknown AGI result: {line}")


@dataclass
class ReconnectionConfig:
    """Configuración para la reconexión automática con backoff exponencial.

    Controla cómo y cuándo el Manager intenta reconectarse
    después de una pérdida de conexión.

    Attributes:
        max_attempts: Número máximo de intentos de reconexión (default: 10).
                       Usar ``-1`` para intentos ilimitados.
        initial_delay: Delay inicial en segundos (default: 1.0).
        max_delay: Delay máximo en segundos (default: 60.0).
        exponential_base: Base para el crecimiento exponencial (default: 2.0).
        jitter: Si es ``True``, agrega variación aleatoria ±20% al delay.
    """

    max_attempts: int = 10
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


def calculate_delay(attempt: int, config: ReconnectionConfig) -> float:
    """Calcula el delay para un intento de reconexión.

    Implementa backoff exponencial con jitter opcional::

        delay = min(initial_delay * (base ** (attempt - 1)), max_delay)

    Si ``jitter`` está activado, se agrega una variación aleatoria
    de ±20% para evitar el efecto ``thundering herd``.

    Args:
        attempt: Número de intento (1-indexed).
        config: Configuración de reconexión.

    Returns:
        Delay en segundos para esperar antes del siguiente intento.
    """
    delay = min(
        config.initial_delay * (config.exponential_base ** (attempt - 1)),
        config.max_delay,
    )

    if config.jitter:
        jitter = delay * 0.2 * (random.random() * 2 - 1)
        delay = max(0.1, delay + jitter)

    return delay
