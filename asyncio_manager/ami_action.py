"""Modelo de acciones del protocolo AMI.

Define la clase ``Action`` que encapsula una acción a enviar al AMI
con su correspondiente seguimiento de respuesta. Usa composición
(vs la herencia dual problemática de panoramisk) combinando un
diccionario de headers con un ``asyncio.Future`` para la respuesta.

También provee soporte para ``EventList``: acciones que generan
múltiples eventos seguidos de un evento ``*Complete``.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from asyncio_manager.message import Message
from asyncio_manager.utils import CaseInsensitiveDict, EOL, IdGenerator


_id_generator = IdGenerator()


class Action:
    """Representa una acción a enviar al Asterisk Manager Interface.

    A diferencia de panoramisk (que usaba herencia dual de
    ``CaseInsensitiveDict`` y ``asyncio.Future``), esta clase usa
    **composición**: contiene un diccionario de headers y un Future
    interno para la respuesta.

    Args:
        headers: Diccionario con los parámetros de la acción.
                 Debe incluir al menos ``Action``.
        action_id: ID opcional. Si no se provee, se genera automáticamente.
        as_list: Si es ``True``, espera una lista de eventos (EventList).

    Example:
        >>> action = Action({"Action": "Ping"})
        >>> str(action)
        'Action: Ping\\r\\nActionID: abc-0001\\r\\n\\r\\n'
    """

    def __init__(
        self,
        headers: Dict[str, str],
        action_id: Optional[str] = None,
        as_list: bool = False,
    ) -> None:
        self._headers: CaseInsensitiveDict = CaseInsensitiveDict(headers)

        if action_id is None:
            self._action_id = _id_generator.generate()
        else:
            self._action_id = action_id

        self._headers["ActionID"] = self._action_id

        # Future para la respuesta principal
        self._future: asyncio.Future[Message] = asyncio.get_running_loop().create_future()

        # Soporte para EventList
        self._as_list: bool = as_list
        self._messages: List[Message] = []
        self._event_complete: asyncio.Event = asyncio.Event()

    @property
    def action_id(self) -> str:
        """ID único de la acción (generado automáticamente o asignado)."""
        return self._action_id

    @property
    def headers(self) -> CaseInsensitiveDict:
        """Headers de la acción (solo lectura)."""
        return self._headers

    @property
    def is_event_list(self) -> bool:
        """Indica si la acción espera una lista de eventos (EventList).

        Returns:
            ``True`` si se configuró con ``as_list=True``.
        """
        return self._as_list

    @property
    def done(self) -> bool:
        """Indica si la acción ya tiene una respuesta completa.

        Returns:
            ``True`` si el Future principal ya está resuelto.
        """
        return self._future.done()

    @property
    def messages(self) -> List[Message]:
        """Lista de mensajes recibidos para esta acción.

        Incluye tanto la respuesta principal como los eventos
        intermedios (si es EventList).
        """
        return list(self._messages)

    def add_message(self, message: Message) -> None:
        """Agrega un mensaje de respuesta a esta acción.

        Para acciones normales, completa el Future inmediatamente.
        Para EventList, acumula los eventos y espera el ``*Complete``.

        Args:
            message: Mensaje recibido desde Asterisk.
        """
        self._messages.append(message)

        if self._as_list:
            # En modo EventList, esperamos el evento Complete
            if message.is_complete_event:
                self._future.set_result(message)
                self._event_complete.set()
        else:
            # Modo normal: la primera respuesta completa la acción
            if not self._future.done():
                self._future.set_result(message)

    def set_exception(self, exception: Exception) -> None:
        """Marca la acción como fallida con una excepción.

        Args:
            exception: Excepción que causó el fallo.
        """
        if not self._future.done():
            self._future.set_exception(exception)

    async def wait(self, timeout: Optional[float] = None) -> Message:
        """Espera la respuesta principal de la acción.

        Si la acción está en modo EventList, espera hasta que
        se reciba el evento ``*Complete`` o se agote el timeout.

        Args:
            timeout: Tiempo máximo de espera en segundos.
                     ``None`` para esperar indefinidamente.

        Returns:
            Mensaje de respuesta principal.

        Raises:
            TimeoutError: Si se agota el tiempo de espera.
        """
        try:
            return await asyncio.wait_for(
                asyncio.shield(self._future),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            from asyncio_manager.exceptions import TimeoutError
            raise TimeoutError(
                f"La acción {self._action_id} no respondió en {timeout}s"
            )

    async def wait_all(self, timeout: Optional[float] = None) -> List[Message]:
        """Espera TODOS los mensajes de la acción.

        Para acciones en modo EventList, retorna la lista completa
        de eventos recibidos. Para acciones normales, retorna
        una lista con la respuesta única.

        Args:
            timeout: Tiempo máximo de espera en segundos.

        Returns:
            Lista de todos los mensajes recibidos.
        """
        await self.wait(timeout)

        if self._as_list:
            await asyncio.wait_for(
                asyncio.shield(self._event_complete.wait()),
                timeout=timeout,
            )

        return self._messages

    def cancel(self) -> None:
        """Cancela la acción pendiente."""
        if not self._future.done():
            self._future.cancel()

    def __str__(self) -> str:
        """Serializa la acción al formato wire del AMI.

        Returns:
            String con formato ``Key: Value\\r\\n`` listo para enviar.
        """
        lines: List[str] = []
        for key in self._headers:
            value = self._headers[key]
            if isinstance(value, str) and "\n" in value:
                for part in value.split("\n"):
                    lines.append(f"{key}: {part.strip()}")
            else:
                lines.append(f"{key}: {value}")
        lines.append("")
        lines.append("")
        return EOL.join(lines)

    def __repr__(self) -> str:
        return (
            f"<Action {self._headers.get('Action', 'Unknown')} "
            f"id={self._action_id} done={self._future.done()}>"
        )
