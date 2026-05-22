"""Modelo de mensajes del protocolo AMI.

Provee la clase ``Message`` que encapsula tanto eventos como respuestas
del Asterisk Manager Interface. Soporta acceso case-insensitive a los
headers y propiedades de conveniencia para determinar el tipo de mensaje.
"""

from typing import Any, List, Optional

from asyncio_manager.utils import CaseInsensitiveDict


class Message(CaseInsensitiveDict):
    """Representa un mensaje del protocolo AMI (evento o respuesta).

    Hereda de ``CaseInsensitiveDict`` para acceso case-insensitive
    a los campos del mensaje. Agrega propiedades de conveniencia
    para identificar el tipo de mensaje y extraer información común.

    Args:
        headers: Diccionario con los headers del mensaje.
        content: Contenido multilínea opcional (ej: salida de ``Command``).

    Example:
        >>> msg = Message({"Event": "NewChannel", "Channel": "SIP/100"})
        >>> msg.is_event
        True
        >>> msg.event_type
        'NewChannel'
        >>> msg["channel"]
        'SIP/100'
    """

    def __init__(
        self,
        headers: Optional[dict] = None,
        content: Optional[List[str]] = None,
    ) -> None:
        super().__init__(headers or {})
        self._content: List[str] = content or []

    @property
    def is_response(self) -> bool:
        """Indica si el mensaje es una respuesta a una acción.

        Returns:
            ``True`` si el mensaje contiene la clave ``Response``.
        """
        return "Response" in self._store

    @property
    def is_event(self) -> bool:
        """Indica si el mensaje es un evento generado por Asterisk.

        Returns:
            ``True`` si el mensaje contiene la clave ``Event``.
        """
        return "Event" in self._store

    @property
    def is_success(self) -> bool:
        """Indica si la acción fue exitosa.

        Returns:
            ``True`` si es un evento, o si ``Response`` está en
            (``Success``, ``Follows``, ``Goodbye``).
        """
        if self.is_event:
            return True
        response = self.get("Response", "")
        return response in ("Success", "Follows", "Goodbye")

    @property
    def action_id(self) -> Optional[str]:
        """ID de la acción asociada a este mensaje.

        Busca las claves ``ActionID`` o ``CommandID`` (case-insensitive)
        en los headers del mensaje.

        Returns:
            El ID de la acción, o ``None`` si no tiene.
        """
        return self.get("ActionID") or self.get("CommandID")

    @property
    def event_type(self) -> Optional[str]:
        """Tipo de evento.

        Retorna el valor de la clave ``Event`` si el mensaje es un evento.

        Returns:
            El tipo de evento (ej: ``NewChannel``), o ``None``.
        """
        return self.get("Event")

    @property
    def message(self) -> Optional[str]:
        """Mensaje de texto asociado (usado en respuestas).

        Returns:
            El valor de la clave ``Message``, o ``None``.
        """
        return self.get("Message")

    @property
    def content(self) -> List[str]:
        """Contenido multilínea del mensaje.

        Algunas respuestas como ``Command`` o ``QueueStatus`` incluyen
        contenido adicional después de los headers. Esta propiedad
        retorna ese contenido como lista de líneas.

        Returns:
            Lista de líneas del contenido, o lista vacía.
        """
        return self._content

    @property
    def is_complete_event(self) -> bool:
        """Indica si este evento marca el final de una lista de eventos.

        Detecta eventos ``*Complete`` como ``QueueStatusComplete``,
        ``DBGetResponseComplete``, etc.

        Returns:
            ``True`` si el tipo de evento termina en ``Complete``.
        """
        event = self.event_type
        if event is None:
            return False
        return event.endswith("Complete")

    def get_multiline(self, key: str) -> List[str]:
        """Obtiene un valor que contiene múltiples líneas.

        Útil para headers que pueden tener valores multilínea
        (ej: ``Variable`` en eventos ``VarSet``).

        Args:
            key: Nombre del header a buscar.

        Returns:
            Lista de líneas del valor, o lista vacía si no existe.
        """
        value = self.get(key)
        if value is None:
            return []
        return value.split("\n")

    @classmethod
    def from_line(cls, data: str) -> "Message":
        """Parsea una cadena de texto del protocolo AMI.

        Convierte el formato wire de AMI (``Key: Value\\r\\n``) en un
        objeto ``Message``. Maneja valores multilínea (continuación
        con espacio o tabulación) y contenido después de respuesta.

        Args:
            data: Cadena de texto del wire AMI, incluyendo headers
                  y contenido opcional separados por ``\\r\\n\\r\\n``.

        Returns:
            Objeto Message con los headers parseados.
            Siempre retorna un Message válido (nunca ``None``).

        Example:
            >>> msg = Message.from_line("Event: NewChannel\\r\\nChannel: SIP/100\\r\\n\\r\\n")
            >>> msg.event_type
            'NewChannel'
        """
        headers: dict = {}
        content: List[str] = []
        last_key: Optional[str] = None

        # Dividir headers y contenido
        parts = data.split("\r\n\r\n", 1)
        header_lines = parts[0].split("\r\n")

        for line in header_lines:
            if not line:
                continue

            # Línea de continuación (empieza con espacio o tab)
            if line[0] in (" ", "\t") and last_key:
                headers[last_key] += "\n" + line.strip()
                continue

            # Línea normal: "Key: Value"
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key] = value.strip()
                last_key = key

        # Contenido posterior (si existe)
        if len(parts) > 1 and parts[1].strip():
            content = [
                l for l in parts[1].split("\r\n") if l.strip()
            ]

        return cls(headers, content)

    def __repr__(self) -> str:
        event = self.event_type or "Response"
        return f"<Message {event}: {dict(self)}>"
