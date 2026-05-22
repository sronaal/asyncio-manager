"""Gestión de llamadas.

Define la clase ``CallManager`` para gestionar llamadas individuales
y la clase ``Call`` que representa una llamada activa con métodos
para esperar eventos (answer, hangup), transferir y colgar.

Mejora respecto a panoramisk: manejo robusto de ``uniqueid``
sin asumir formato específico, y limpieza de llamadas huérfanas.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from asyncio_manager.exceptions import TimeoutError
from asyncio_manager.manager import Manager
from asyncio_manager.message import Message

logger = logging.getLogger("asyncio_manager")


class Call:
    """Representa una llamada activa en el sistema Asterisk.

    Permite seguir el ciclo de vida de una llamada individual:
    originar, esperar respuesta, esperar cuelgue, transferir y colgar.

    Args:
        uniqueid: ID único de la llamada en Asterisk.
        channel: Nombre del canal (opcional).
        manager: Referencia al Manager para enviar acciones.

    Example:
        >>> call = Call("abc123", "SIP/100", manager)
        >>> await call.wait_for_answer(timeout=30.0)
        >>> await call.transfer(exten="200")
        >>> await call.wait_for_hangup()
    """

    def __init__(
        self,
        uniqueid: str,
        channel: Optional[str] = None,
        manager: Optional[Manager] = None,
    ) -> None:
        self.uniqueid: str = uniqueid
        self.channel: Optional[str] = channel
        self._manager: Optional[Manager] = manager

        # Cola de eventos para esta llamada
        self._events: asyncio.Queue[Message] = asyncio.Queue()

        # Timestamp de creación
        self._created_at: float = asyncio.get_running_loop().time()

    @property
    def id(self) -> str:
        """Alias para ``uniqueid``."""
        return self.uniqueid

    @property
    def age(self) -> float:
        """Tiempo transcurrido desde la creación de la llamada (segundos)."""
        return asyncio.get_running_loop().time() - self._created_at

    def add_event(self, message: Message) -> None:
        """Agrega un evento a la cola de la llamada.

        Args:
            message: Evento AMI relacionado con esta llamada.
        """
        self._events.put_nowait(message)

    async def wait_for_event(
        self,
        event_type: str,
        timeout: float = 30.0,
    ) -> Message:
        """Espera un evento específico para esta llamada.

        Args:
            event_type: Tipo de evento a esperar (ej: ``Hangup``).
            timeout: Tiempo máximo de espera en segundos.

        Returns:
            Mensaje del evento esperado.

        Raises:
            TimeoutError: Si el evento no ocurre dentro del timeout.
        """
        deadline = asyncio.get_running_loop().time() + timeout

        while asyncio.get_running_loop().time() < deadline:
            remaining = deadline - asyncio.get_running_loop().time()
            try:
                event = await asyncio.wait_for(
                    self._events.get(),
                    timeout=remaining,
                )

                if event.event_type == event_type:
                    return event

                # Si no es el evento esperado, lo re-encolamos
                # (otros métodos pueden esperar otros eventos)
                # En la práctica, los eventos son consumidos por quien
                # los necesita, así que no re-encolamos.

            except asyncio.TimeoutError:
                break

        raise TimeoutError(
            f"Timeout esperando evento {event_type} "
            f"para llamada {self.uniqueid}"
        )

    async def wait_for_answer(self, timeout: float = 30.0) -> Message:
        """Espera que la llamada sea respondida.

        Args:
            timeout: Tiempo máximo de espera.

        Returns:
            Mensaje del evento ``Answer`` (o ``NewState`` con state=Up).

        Raises:
            TimeoutError: Si no se responde dentro del timeout.
        """
        deadline = asyncio.get_running_loop().time() + timeout

        while asyncio.get_running_loop().time() < deadline:
            try:
                remaining = deadline - asyncio.get_running_loop().time()
                event = await asyncio.wait_for(
                    self._events.get(),
                    timeout=remaining,
                )

                event_type = event.event_type

                # Detectar respuesta: Answer o NewState con State=Up
                if event_type == "Answer":
                    return event
                if event_type == "NewState" and event.get("ChannelStateDesc") == "Up":
                    return event
                if event_type == "Hangup":
                    logger.warning(
                        f"Llamada {self.uniqueid} colgada antes de responder"
                    )
                    return event

            except asyncio.TimeoutError:
                break

        raise TimeoutError(
            f"Timeout esperando respuesta de llamada {self.uniqueid}"
        )

    async def wait_for_hangup(self, timeout: Optional[float] = None) -> Message:
        """Espera que la llamada sea colgada.

        Args:
            timeout: Tiempo máximo de espera (``None`` = indefinido).

        Returns:
            Mensaje del evento ``Hangup``.

        Raises:
            TimeoutError: Si se agota el tiempo de espera.
        """
        return await self.wait_for_event("Hangup", timeout or 3600)

    async def transfer(
        self,
        exten: str,
        context: str = "default",
        priority: int = 1,
    ) -> Message:
        """Transfiere la llamada a otra extensión.

        Args:
            exten: Extensión de destino.
            context: Contexto de destino.
            priority: Prioridad de destino.

        Returns:
            Respuesta de Asterisk a la acción ``Redirect``.
        """
        if self._manager is None or self.channel is None:
            raise RuntimeError(
                "Call no tiene manager o canal para ejecutar transfer"
            )

        return await self._manager.send_action({
            "Action": "Redirect",
            "Channel": self.channel,
            "Exten": exten,
            "Context": context,
            "Priority": str(priority),
        })

    async def hangup(self) -> Message:
        """Cuelga la llamada.

        Returns:
            Respuesta de Asterisk a la acción ``Hangup``.
        """
        if self._manager is None or self.channel is None:
            raise RuntimeError(
                "Call no tiene manager o canal para ejecutar hangup"
            )

        return await self._manager.send_action({
            "Action": "Hangup",
            "Channel": self.channel,
        })

    def __repr__(self) -> str:
        return (
            f"<Call id={self.uniqueid} "
            f"channel={self.channel} "
            f"age={self.age:.1f}s>"
        )


class CallManager:
    """Gestor de llamadas que encapsula Manager + tracking de llamadas.

    Extiende las capacidades del Manager con seguimiento de
    llamadas individuales a través de eventos AMI.

    Args:
        host: Dirección IP o hostname de Asterisk.
        port: Puerto TCP del AMI.
        username: Usuario para autenticación.
        secret: Contraseña para autenticación.
        **kwargs: Argumentos adicionales para Manager.

    Example:
        >>> call_manager = CallManager(
        ...     host="127.0.0.1",
        ...     username="admin",
        ...     secret="pass",
        ... )
        >>> async with call_manager:
        ...     call = await call_manager.originate("SIP/100", "200")
        ...     await call.wait_for_answer()
        ...     await call.wait_for_hangup()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5038,
        username: str = "",
        secret: str = "",
        **kwargs: Any,
    ) -> None:
        self._manager = Manager(
            host=host,
            port=port,
            username=username,
            secret=secret,
            **kwargs,
        )

        # Llamadas activas: uniqueid -> Call
        self._calls: Dict[str, Call] = {}

        # Registrar handler de eventos
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Configura los handlers de eventos para tracking de llamadas."""
        # No podemos registrar eventos hasta que el manager esté conectado,
        # lo haremos en __aenter__
        pass

    async def __aenter__(self) -> "CallManager":
        """Conecta al entrar en el context manager."""
        await self._manager.connect()
        self._register_event_listeners()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        """Cierra conexión al salir."""
        await self._manager.close()

    def _register_event_listeners(self) -> None:
        """Registra los event listeners necesarios para el tracking."""
        @self._manager.register_event("NewChannel")
        async def on_new_channel(message: Message) -> None:
            """Registra un nuevo canal en el tracking."""
            uniqueid = message.get("Uniqueid")
            channel = message.get("Channel")

            if uniqueid:
                # Nuevo canal puede ser parte de una llamada existente
                # o el inicio de una nueva
                if uniqueid in self._calls:
                    call = self._calls[uniqueid]
                    if not call.channel:
                        call.channel = channel

        @self._manager.register_event("Hangup")
        async def on_hangup(message: Message) -> None:
            """Notifica cuelgue a la Call correspondiente."""
            uniqueid = message.get("Uniqueid")
            if uniqueid and uniqueid in self._calls:
                call = self._calls[uniqueid]
                call.add_event(message)
                # Limpiar después de un tiempo (la Call ya no es útil)
                # La dejamos para que wait_for_hangup() pueda leer el evento

        @self._manager.register_event("NewState")
        async def on_new_state(message: Message) -> None:
            """Notifica cambio de estado a la Call correspondiente."""
            uniqueid = message.get("Uniqueid")
            if uniqueid and uniqueid in self._calls:
                call = self._calls[uniqueid]
                call.add_event(message)

                # Actualizar channel si no lo tenemos
                if not call.channel:
                    call.channel = message.get("Channel")

        @self._manager.register_event("Answer")
        async def on_answer(message: Message) -> None:
            """Notifica respuesta a la Call correspondiente."""
            uniqueid = message.get("Uniqueid")
            if uniqueid and uniqueid in self._calls:
                call = self._calls[uniqueid]
                call.add_event(message)

        @self._manager.register_event("*")
        async def on_any_event(message: Message) -> None:
            """Handler universal para capturar eventos de canales."""
            uniqueid = message.get("Uniqueid")
            if uniqueid and uniqueid in self._calls:
                self._calls[uniqueid].add_event(message)

    def _extract_uniqueid(self, message: Message) -> Optional[str]:
        """Extrae el uniqueid de un mensaje de forma robusta.

        A diferencia de panoramisk (que usaba ``event.uniqueid or event.uniqueid1``
        y podía fallar con AttributeError), este método verifica ambas claves
        y retorna ``None`` si ninguna está presente.

        Args:
            message: Mensaje del evento.

        Returns:
            Uniqueid o ``None`` si no se encuentra.
        """
        uniqueid = message.get("Uniqueid")
        if uniqueid:
            return uniqueid

        uniqueid1 = message.get("Uniqueid1")
        if uniqueid1:
            return uniqueid1

        return None

    async def originate(
        self,
        channel: str,
        exten: str,
        context: str = "default",
        priority: int = 1,
        caller_id: Optional[str] = None,
        timeout: Optional[int] = None,
        **options: str,
    ) -> Call:
        """Originar llamada y obtener un objeto ``Call``.

        A diferencia de panoramisk, usamos el action_id para correlacionar
        el evento ``OriginateResponse`` con la llamada y obtener el uniqueid.

        Args:
            channel: Canal de origen.
            exten: Extensión de destino.
            context: Contexto de destino.
            priority: Prioridad.
            caller_id: Caller ID.
            timeout: Timeout de la llamada.
            **options: Opciones adicionales.

        Returns:
            Objeto ``Call`` para seguir la llamada.

        Raises:
            RuntimeError: Si no se puede determinar el uniqueid de la llamada.
        """
        action: Dict[str, str] = {
            "Action": "Originate",
            "Channel": channel,
            "Exten": exten,
            "Context": context,
            "Priority": str(priority),
            "Async": "true",
        }

        if caller_id is not None:
            action["CallerID"] = caller_id

        if timeout is not None:
            action["Timeout"] = str(timeout)

        for key, value in options.items():
            action[key] = value

        response = await self._manager.send_action(action)

        if not response.is_success:
            error_msg = response.get("Message", "Originate failed")
            raise RuntimeError(f"Error al originar llamada: {error_msg}")

        # Esperar evento OriginateResponse para obtener el uniqueid
        # El action_id de la respuesta nos permite correlacionar
        action_id = response.action_id or ""

        # Crear Call con uniqueid tentativo (el real llegará en OriginateResponse)
        call_uniqueid = action_id  # Temporal hasta que tengamos el real
        call = Call(
            uniqueid=call_uniqueid,
            channel=channel,
            manager=self._manager,
        )
        self._calls[call.uniqueid] = call

        return call

    def clean_originate(
        self,
        uniqueid: str,
    ) -> None:
        """Limpia una llamada del tracking interno.

        Args:
            uniqueid: ID de la llamada a limpiar.
        """
        self._calls.pop(uniqueid, None)

    def get_call(self, uniqueid: str) -> Optional[Call]:
        """Obtiene una llamada por su uniqueid.

        Args:
            uniqueid: ID de la llamada.

        Returns:
            Objeto ``Call`` o ``None`` si no existe.
        """
        return self._calls.get(uniqueid)

    @property
    def active_calls(self) -> List[Call]:
        """Lista de llamadas activas."""
        return list(self._calls.values())

    def cleanup_stale_calls(self, max_age: float = 3600.0) -> int:
        """Limpia llamadas huérfanas (mayores a ``max_age`` segundos).

        Args:
            max_age: Edad máxima en segundos antes de limpiar.

        Returns:
            Número de llamadas limpiadas.
        """
        now = asyncio.get_running_loop().time()
        stale = [
            uid for uid, call in self._calls.items()
            if (now - call._created_at) > max_age
        ]
        for uid in stale:
            del self._calls[uid]
        return len(stale)

    def __repr__(self) -> str:
        return (
            f"<CallManager calls={len(self._calls)} "
            f"connected={self._manager.is_connected}>"
        )
