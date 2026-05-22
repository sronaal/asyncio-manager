"""Protocolo de comunicación AMI (Asterisk Manager Interface).

Implementa el protocolo de capa de transporte para comunicarse
con Asterisk vía TCP. Maneja la codificación/decodificación de
mensajes, buffering de datos fragmentados, y timeouts de lectura.

A diferencia de panoramisk (``AMIProtocol`` via ``asyncio.Protocol``),
esta implementación usa ``asyncio.StreamReader``/``StreamWriter``
para un control más simple y robusto del flujo de datos.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any, Dict, Optional

from asyncio_manager.ami_action import Action
from asyncio_manager.config import ManagerConfig
from asyncio_manager.exceptions import ConnectionError, ProtocolError, TimeoutError
from asyncio_manager.message import Message
from asyncio_manager.utils import EOL

logger = logging.getLogger("asyncio_manager")


class AMIProtocol:
    """Maneja la comunicación de bajo nivel con Asterisk AMI.

    Gestiona la conexión TCP, el envío de acciones, la recepción
    de mensajes y eventos, y la correlación entre acciones y sus
    respuestas mediante ActionID.

    Args:
        config: Configuración de la conexión AMI.

    Example:
        >>> config = ManagerConfig(host="127.0.0.1", port=5038)
        >>> protocol = AMIProtocol(config)
        >>> await protocol.connect()
        >>> action = Action({"Action": "Ping"})
        >>> response = await protocol.send_action(action)
        >>> await protocol.close()
    """

    def __init__(self, config: ManagerConfig) -> None:
        self._config: ManagerConfig = config
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected: bool = False

        # Acciones pendientes: action_id -> Action
        self._pending_actions: Dict[str, Action] = {}

        # Buffer de datos parciales para mensajes fragmentados
        self._buffer: bytearray = bytearray()

        # Callbacks de eventos registrados
        self._event_callbacks: list = []

        # Callbacks de ciclo de vida
        self._on_connect: list = []
        self._on_disconnect: list = []

        # Tarea de recepción de mensajes
        self._reader_task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        """Indica si hay una conexión activa con Asterisk."""
        return self._connected

    async def connect(self) -> None:
        """Establece la conexión TCP con el servidor Asterisk.

        Soporta conexiones SSL/TLS si está configurado.
        Lanza ``ConnectionError`` si no puede conectar dentro
        del ``connect_timeout`` configurado.

        Raises:
            TimeoutError: Si la conexión excede el connect_timeout.
            ConnectionError: Si el servidor rechaza la conexión.
        """
        config = self._config

        try:
            if config.ssl:
                ssl_context = ssl.create_default_context()
                if not config.ssl_verify:
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
            else:
                ssl_context = None

            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    config.host,
                    config.port,
                    ssl=ssl_context,
                ),
                timeout=config.connect_timeout,
            )

            self._connected = True
            logger.info(
                f"Conectado a {config.host}:{config.port} "
                f"({'SSL' if config.ssl else 'TCP'})"
            )

            # Iniciar tarea de lectura continua
            self._reader_task = asyncio.create_task(self._read_loop())

            # Disparar callbacks de conexión
            for cb in self._on_connect:
                await cb()

        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Conexión a {config.host}:{config.port} "
                f"excedió {config.connect_timeout}s"
            )
        except OSError as e:
            raise ConnectionError(
                f"No se pudo conectar a {config.host}:{config.port}: {e}"
            )

    async def close(self) -> None:
        """Cierra la conexión con Asterisk limpiamente.

        Cancela la tarea de lectura, cierra el writer y
        notifica a las acciones pendientes con un error.
        """
        self._connected = False

        # Cancelar tarea de lectura
        if self._reader_task is not None and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        # Cerrar writer
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass

        # Notificar acciones pendientes
        for action_id, action in list(self._pending_actions.items()):
            if not action.done:
                action.set_exception(
                    ConnectionError("Conexión cerrada durante la operación")
                )

        self._pending_actions.clear()
        self._buffer.clear()

        logger.info("Conexión cerrada")

    async def send_action(
        self,
        action: Action,
    ) -> Message:
        """Envía una acción al AMI y espera su respuesta.

        Registra la acción como pendiente, la serializa y la envía
        por el socket. Luego espera la respuesta correlacionada
        por ActionID.

        Args:
            action: Acción a enviar.

        Returns:
            Mensaje de respuesta de Asterisk.

        Raises:
            DisconnectedError: Si no hay conexión activa.
            TimeoutError: Si la respuesta excede el timeout configurado.
        """
        if not self._connected or self._writer is None:
            from asyncio_manager.exceptions import DisconnectedError
            raise DisconnectedError("No hay conexión activa con Asterisk")

        # Registrar acción pendiente
        self._pending_actions[action.action_id] = action

        # Serializar y enviar
        payload = str(action)
        data = payload.encode(self._config.encoding)

        try:
            self._writer.write(data)
            await self._writer.drain()

            logger.debug(f"Enviado: {action.headers.get('Action', 'Unknown')} "
                         f"[{action.action_id}]")

        except OSError as e:
            self._connected = False
            del self._pending_actions[action.action_id]
            raise ConnectionError(f"Error al enviar datos: {e}")

        # Esperar respuesta con timeout
        try:
            response = await action.wait(timeout=self._config.timeout)
            return response
        except TimeoutError:
            del self._pending_actions[action.action_id]
            raise
        except Exception:
            del self._pending_actions[action.action_id]
            raise

    async def send_action_raw(
        self,
        action: Action,
    ) -> None:
        """Envía una acción sin esperar respuesta (fire-and-forget).

        Útil para acciones que no requieren confirmación o para
        escenarios donde la respuesta se maneja como evento.

        Args:
            action: Acción a enviar.

        Raises:
            DisconnectedError: Si no hay conexión activa.
        """
        if not self._connected or self._writer is None:
            from asyncio_manager.exceptions import DisconnectedError
            raise DisconnectedError("No hay conexión activa con Asterisk")

        payload = str(action)
        data = payload.encode(self._config.encoding)

        try:
            self._writer.write(data)
            await self._writer.drain()
            logger.debug(f"Enviado (fire-and-forget): {action.action_id}")
        except OSError as e:
            self._connected = False
            raise ConnectionError(f"Error al enviar datos: {e}")

    def register_event_callback(
        self,
        callback: Any,
    ) -> None:
        """Registra un callback para eventos entrantes.

        Args:
            callback: Objeto callback (patrón + función).
        """
        self._event_callbacks.append(callback)

    def on_connect(self, callback: Any) -> None:
        """Registra un callback para cuando se establece conexión.

        Args:
            callback: Función asíncrona a llamar al conectar.
        """
        self._on_connect.append(callback)

    def on_disconnect(self, callback: Any) -> None:
        """Registra un callback para cuando se pierde conexión.

        Args:
            callback: Función asíncrona a llamar al desconectar.
        """
        self._on_disconnect.append(callback)

    async def _read_loop(self) -> None:
        """Bucle principal de lectura de mensajes desde Asterisk.

        Lee datos del socket, arma mensajes completos (separados
        por ``\\r\\n\\r\\n``), los parsea y los distribuye a la
        acción pendiente correspondiente o a los callbacks de eventos.
        """
        try:
            while self._connected and self._reader is not None:
                try:
                    chunk = await asyncio.wait_for(
                        self._reader.read(4096),
                        timeout=self._config.read_timeout,
                    )
                except asyncio.TimeoutError:
                    # Timeout de lectura: verificar salud
                    if self._connected:
                        logger.debug("Timeout de lectura (esperando datos...)")
                        await self._ping_check()
                    continue

                if not chunk:
                    logger.warning("Conexión cerrada por el servidor")
                    self._connected = False
                    for cb in self._on_disconnect:
                        await cb()
                    break

                self._buffer.extend(chunk)
                await self._process_buffer()

        except asyncio.CancelledError:
            logger.debug("Bucle de lectura cancelado")
        except Exception as e:
            logger.error(f"Error en bucle de lectura: {e}")
            self._connected = False
            for cb in self._on_disconnect:
                await cb()

    async def _process_buffer(self) -> None:
        """Procesa el buffer de datos, extrayendo mensajes completos.

        Busca el delimitador ``\\r\\n\\r\\n`` y por cada mensaje
        completo lo parsea y distribuye.
        """
        while True:
            # Buscar delimitador de fin de mensaje
            delim = b"\r\n\r\n"
            idx = self._buffer.find(delim)

            if idx == -1:
                break

            # Extraer mensaje completo (incluyendo el delimitador)
            msg_len = idx + len(delim)
            raw_msg = self._buffer[:msg_len]
            self._buffer = self._buffer[msg_len:]

            # Parsear y distribuir
            if raw_msg.strip():
                await self._dispatch_message(raw_msg)

    async def _dispatch_message(self, raw_data: bytes) -> None:
        """Parsea y distribuye un mensaje AMI completo.

        Determina si el mensaje es una respuesta a una acción pendiente
        o un evento, y lo dirige adecuadamente.

        Args:
            raw_data: Datos crudos del mensaje (bytes).
        """
        try:
            text = raw_data.decode(self._config.encoding)
            message = Message.from_line(text)
        except Exception as e:
            logger.warning(f"Error parseando mensaje: {e}")
            return

        # Buscar acción pendiente por ActionID
        msg_action_id = message.action_id

        if msg_action_id and msg_action_id in self._pending_actions:
            action = self._pending_actions[msg_action_id]
            action.add_message(message)

            # Si la acción se completó, removerla
            if action.done:
                del self._pending_actions[msg_action_id]
        else:
            # Si no tiene action_id o no está pendiente, es un evento
            if message.is_event:
                self._dispatch_event(message)
            elif message.is_response:
                logger.debug(
                    f"Respuesta sin acción pendiente: "
                    f"{message.get('Response')}"
                )
            else:
                logger.debug(f"Mensaje no clasificado: {message}")

    def _dispatch_event(self, message: Message) -> None:
        """Distribuye un evento a los callbacks registrados.

        Args:
            message: Mensaje de evento a distribuir.
        """
        event_type = message.event_type or "Unknown"
        logger.debug(f"Evento recibido: {event_type}")

        for callback in self._event_callbacks:
            try:
                if hasattr(callback, "match") and not callback.match(message):
                    continue
                # Si es un EventCallbackItem, ejecutar su handler
                if hasattr(callback, "handler"):
                    asyncio.create_task(callback.handler(message))
            except Exception as e:
                logger.error(f"Error en callback de evento: {e}")

    async def _ping_check(self) -> None:
        """Envía un Ping para verificar la salud de la conexión."""
        try:
            ping_action = Action({"Action": "Ping"})
            await self.send_action(ping_action)
        except Exception:
            logger.warning("Ping falló, conexión posiblemente muerta")

    def __repr__(self) -> str:
        config = self._config
        return (
            f"<AMIProtocol {config.host}:{config.port} "
            f"connected={self._connected}>"
        )
