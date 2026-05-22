"""Cliente AMI asíncrono moderno.

Clase principal ``Manager`` que orquesta la conexión, autenticación,
envío de acciones, registro de eventos y reconexión automática
con backoff exponencial.

Es la puerta de entrada a toda la funcionalidad de la librería.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from asyncio_manager.ami_action import Action
from asyncio_manager.config import ManagerConfig
from asyncio_manager.exceptions import (
    AuthenticationError,
    ConnectionError,
    TimeoutError,
)
from asyncio_manager.message import Message
from asyncio_manager.protocol import AMIProtocol
from asyncio_manager.utils import ReconnectionConfig, calculate_delay

logger = logging.getLogger("asyncio_manager")


class EventCallbackItem:
    """Wrap de un callback de evento con su patrón de匹配.

    Almacena el patrón (con soporte de wildcards) y la función
    asíncrona a ejecutar cuando se recibe un evento que coincide.

    Args:
        pattern: Patrón de evento (ej: ``*``, ``NewChannel``, ``Queue*``).
        callback: Función asíncrona que recibe el ``Message`` del evento.
    """

    def __init__(
        self,
        pattern: str,
        callback: Callable[[Message], Awaitable[None]],
    ) -> None:
        self.pattern: str = pattern
        self.handler: Callable[[Message], Awaitable[None]] = callback

    def match(self, message: Message) -> bool:
        """Verifica si el evento coincide con el patrón.

        Soporta wildcard ``*`` al final del patrón (ej: ``Queue*``)
        y el patrón universal ``*`` para todos los eventos.

        Args:
            message: Mensaje del evento a verificar.

        Returns:
            ``True`` si el evento coincide con el patrón.
        """
        event_type = message.event_type
        if event_type is None:
            return False

        if self.pattern == "*":
            return True

        if self.pattern.endswith("*"):
            prefix = self.pattern[:-1]
            return event_type.startswith(prefix)

        return event_type == self.pattern


class Manager:
    """Cliente AMI asíncrono moderno para Asterisk.

    Es la clase principal de la librería. Maneja la conexión,
    autenticación, envío de acciones, registro de eventos,
    reconexión automática y limpieza de recursos.

    Args:
        host: Dirección IP o hostname de Asterisk.
        port: Puerto TCP del AMI.
        username: Usuario para autenticación.
        secret: Contraseña para autenticación.
        timeout: Timeout para acciones AMI.
        read_timeout: Timeout para lectura de mensajes.
        connect_timeout: Timeout para conexión TCP.
        ssl: Habilita SSL/TLS.
        ssl_verify: Verifica certificado SSL.
        encoding: Codificación de mensajes.
        ping_interval: Intervalo de keep-alive (Ping).
        reconnect_config: Configuración de reconexión.
        config: Objeto ManagerConfig (alternativa a parámetros individuales).

    Example:
        >>> async with Manager(host="127.0.0.1", username="admin", secret="pass") as m:
        ...     await m.connect()
        ...     response = await m.send_action({"Action": "Ping"})
        ...     print(response.is_success)
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5038,
        username: str = "",
        secret: str = "",
        timeout: float = 5.0,
        read_timeout: float = 30.0,
        connect_timeout: float = 10.0,
        ssl: bool = False,
        ssl_verify: bool = True,
        encoding: str = "utf-8",
        ping_interval: float = 10.0,
        reconnect_config: Optional[ReconnectionConfig] = None,
        config: Optional[ManagerConfig] = None,
    ) -> None:
        if config is not None:
            self._config: ManagerConfig = config
        else:
            self._config = ManagerConfig(
                host=host,
                port=port,
                username=username,
                secret=secret,
                timeout=timeout,
                read_timeout=read_timeout,
                connect_timeout=connect_timeout,
                ssl=ssl,
                ssl_verify=ssl_verify,
                encoding=encoding,
                ping_interval=ping_interval,
                reconnect_max_attempts=(
                    reconnect_config.max_attempts
                    if reconnect_config
                    else 10
                ),
                reconnect_initial_delay=(
                    reconnect_config.initial_delay
                    if reconnect_config
                    else 1.0
                ),
                reconnect_max_delay=(
                    reconnect_config.max_delay
                    if reconnect_config
                    else 60.0
                ),
            )

        self._protocol: Optional[AMIProtocol] = None
        self._connected: bool = False
        self._authenticated: bool = False

        # Tarea de Ping
        self._ping_task: Optional[asyncio.Task] = None

        # Reconnection config interno
        self._reconnect_config = reconnect_config or ReconnectionConfig()

        # Callbacks de reconexión
        self._on_reconnect: List[Callable] = []
        self._on_disconnect: List[Callable] = []

    @property
    def is_connected(self) -> bool:
        """Indica si hay una conexión activa y autenticada."""
        return self._connected and self._authenticated

    async def connect(self) -> None:
        """Conecta y autentica contra el servidor Asterisk.

        Establece la conexión TCP, negocia la autenticación
        (MD5 challenge-response o plain text), inicia el keep-alive
        y registra el handler de eventos shutdown.

        Raises:
            ConnectionError: Si no puede conectar.
            AuthenticationError: Si las credenciales son inválidas.
            TimeoutError: Si la operación excede el timeout.
        """
        if self._connected:
            logger.warning("Ya está conectado")
            return

        # Crear protocolo
        self._protocol = AMIProtocol(self._config)

        # Registrar callback de eventos en el protocolo
        # (el manejador real está en Manager)

        # Conectar TCP
        await self._protocol.connect()

        try:
            # Autenticar
            await self._login()

            self._connected = True
            self._authenticated = True

            # Iniciar ping de keep-alive
            self._start_pinger()

            logger.info(
                f"Manager conectado a {self._config.host}:{self._config.port}"
            )

        except Exception:
            await self._protocol.close()
            self._protocol = None
            raise

    async def _login(self) -> None:
        """Realiza la autenticación contra el AMI.

        Intenta primero autenticación MD5 challenge-response.
        Si el servidor no soporta MD5, usa autenticación plain text.

        Raises:
            AuthenticationError: Si las credenciales son inválidas.
        """
        config = self._config

        if not config.username:
            raise AuthenticationError(
                "Se requiere username para autenticar"
            )

        # Step 1: Obtener challenge
        challenge_action = Action({"Action": "Challenge", "AuthType": "MD5"})
        challenge_response = await self._protocol.send_action(challenge_action)

        if challenge_response.is_success and challenge_response.get("Challenge"):
            # Autenticación MD5 challenge-response
            challenge = challenge_response["Challenge"]
            md5_hash = hashlib.md5(
                f"{challenge}{config.secret}".encode()
            ).hexdigest()

            login_action = Action({
                "Action": "Login",
                "Username": config.username,
                "AuthType": "MD5",
                "Key": md5_hash,
                "Events": "on",
            })
        else:
            # Autenticación plain text (fallback)
            login_action = Action({
                "Action": "Login",
                "Username": config.username,
                "Secret": config.secret,
                "Events": "on",
            })

        login_response = await self._protocol.send_action(login_action)

        if not login_response.is_success:
            error_msg = login_response.get("Message", "Authentication failed")
            raise AuthenticationError(
                f"Error de autenticación: {error_msg}"
            )

        logger.info("Autenticación exitosa")

    def _start_pinger(self) -> None:
        """Inicia el keep-alive periódico.

        Envía acciones ``Ping`` a intervalos regulares para
        mantener viva la conexión y detectar caídas tempranas.
        """
        if self._ping_task is not None and not self._ping_task.done():
            self._ping_task.cancel()

        async def pinger():
            while self._connected and self._protocol is not None:
                try:
                    await asyncio.sleep(self._config.ping_interval)
                    if self._connected:
                        ping_action = Action({"Action": "Ping"})
                        await self._protocol.send_action(ping_action)
                        logger.debug("Ping enviado")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Ping falló: {e}")
                    # La reconexión se maneja en send_action
                    break

        self._ping_task = asyncio.create_task(pinger())

    async def close(self) -> None:
        """Cierra la conexión con Asterisk limpiamente.

        Envía un ``Logoff`` antes de cerrar, detiene el pinger,
        y limpia los recursos del protocolo.
        """
        if self._ping_task is not None:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None

        if self._protocol is not None:
            try:
                if self._connected:
                    logoff_action = Action({"Action": "Logoff"})
                    await self._protocol.send_action_raw(logoff_action)
            except Exception:
                pass

            await self._protocol.close()

        self._connected = False
        self._authenticated = False
        self._protocol = None

        logger.info("Manager cerrado")

    async def send_action(
        self,
        action: Dict[str, str],
        timeout: Optional[float] = None,
        as_list: bool = False,
    ) -> Message:
        """Envía una acción al AMI y espera su respuesta.

        Args:
            action: Diccionario con la acción y sus parámetros.
                    Ej: ``{"Action": "Ping"}``.
            timeout: Timeout opcional para esta acción específica.
                     Usa el timeout por defecto si no se especifica.
            as_list: Si es ``True``, espera múltiples eventos (EventList).

        Returns:
            Mensaje de respuesta de Asterisk.

        Raises:
            ConnectionError: Si no hay conexión.
            TimeoutError: Si la acción excede el timeout.
        """
        if not self._connected or self._protocol is None:
            raise ConnectionError("Manager no está conectado")

        # Crear objeto Action con los parámetros
        ami_action = Action(action, as_list=as_list)

        # Timeout específico o el default
        action_timeout = timeout if timeout is not None else self._config.timeout

        try:
            response = await self._protocol.send_action(ami_action)
            return response

        except (ConnectionError, TimeoutError):
            # Intentar reconexión automática
            await self._handle_disconnection()
            raise

        except Exception:
            raise

    async def send_action_and_wait_all(
        self,
        action: Dict[str, str],
        timeout: Optional[float] = None,
    ) -> List[Message]:
        """Envía una acción y espera TODAS sus respuestas (EventList).

        Útil para acciones como ``QueueStatus`` o ``DBGet`` que
        generan múltiples eventos seguidos de un ``*Complete``.

        Args:
            action: Diccionario con la acción y sus parámetros.
            timeout: Timeout opcional.

        Returns:
            Lista de todos los mensajes recibidos (eventos + complete).
        """
        if not self._connected or self._protocol is None:
            raise ConnectionError("Manager no está conectado")

        ami_action = Action(action, as_list=True)
        action_timeout = timeout if timeout is not None else self._config.timeout

        try:
            messages = await ami_action.wait_all(action_timeout)
            return messages
        except (ConnectionError, TimeoutError):
            await self._handle_disconnection()
            raise

    def register_event(
        self,
        pattern: str,
    ) -> Callable:
        """Decorador para registrar callbacks de eventos.

        Soporta wildcards: ``*`` (todos), ``NewChannel`` (exacto),
        ``Queue*`` (prefijo).

        Args:
            pattern: Patrón del evento a escuchar.

        Returns:
            Decorador que registra la función como callback.

        Example:
            >>> manager = Manager(...)
            >>> @manager.register_event("NewChannel")
            ... async def on_new_channel(msg):
            ...     print(f"Nuevo canal: {msg.get('Channel')}")
        """
        def decorator(
            callback: Callable[[Message], Awaitable[None]],
        ) -> Callable[[Message], Awaitable[None]]:
            self._register_event(pattern, callback)
            return callback
        return decorator

    def _register_event(
        self,
        pattern: str,
        callback: Callable[[Message], Awaitable[None]],
    ) -> None:
        """Registra un callback de evento internamente.

        Args:
            pattern: Patrón del evento.
            callback: Función asíncrona a ejecutar.
        """
        if self._protocol is None:
            logger.warning(
                "Evento registrado antes de conectar: "
                "se activará al conectar"
            )
            return

        item = EventCallbackItem(pattern, callback)
        self._protocol.register_event_callback(item)
        logger.debug(f"Evento registrado: {pattern}")

    async def originate(
        self,
        channel: str,
        exten: str,
        context: str = "default",
        priority: int = 1,
        caller_id: Optional[str] = None,
        timeout: Optional[int] = None,
        async_: bool = True,
        **kwargs: str,
    ) -> Message:
        """Helper para originar llamadas (Originate action).

        Args:
            channel: Canal de origen (ej: ``SIP/100``).
            exten: Extensión de destino.
            context: Contexto de destino.
            priority: Prioridad de destino.
            caller_id: Caller ID a mostrar.
            timeout: Timeout de la llamada en segundos.
            async_: Si es ``True``, no espera que se complete la llamada.
            **kwargs: Parámetros adicionales para la acción Originate.

        Returns:
            Respuesta de Asterisk a la acción Originate.

        Example:
            >>> response = await manager.originate(
            ...     channel="SIP/100",
            ...     exten="200",
            ...     caller_id="Test <1234>",
            ... )
        """
        action: Dict[str, str] = {
            "Action": "Originate",
            "Channel": channel,
            "Exten": exten,
            "Context": context,
            "Priority": str(priority),
        }

        if caller_id is not None:
            action["CallerID"] = caller_id

        if timeout is not None:
            action["Timeout"] = str(timeout)

        action["Async"] = "true" if async_ else "false"

        # Parámetros adicionales
        for key, value in kwargs.items():
            action[key] = value

        return await self.send_action(action)

    async def command(
        self,
        command_line: str,
    ) -> Message:
        """Ejecuta un comando CLI de Asterisk.

        Args:
            command_line: Comando a ejecutar (ej: ``pjsip show endpoints``).

        Returns:
            Mensaje con el resultado del comando en ``content``.
        """
        return await self.send_action({
            "Action": "Command",
            "Command": command_line,
        })

    def on_reconnect(self, callback: Callable) -> None:
        """Registra callback para eventos de reconexión exitosa.

        Args:
            callback: Función a llamar cuando se reconecta exitosamente.
        """
        self._on_reconnect.append(callback)

    def on_disconnect(self, callback: Callable) -> None:
        """Registra callback para eventos de desconexión.

        Args:
            callback: Función a llamar cuando se pierde la conexión.
        """
        self._on_disconnect.append(callback)

    async def _handle_disconnection(self) -> None:
        """Maneja una desconexión y dispara reconexión automática.

        Ejecuta los callbacks de desconexión y luego inicia
        el proceso de reconexión con backoff exponencial.
        """
        logger.warning("Conexión perdida, iniciando reconexión...")

        self._connected = False
        self._authenticated = False

        # Callbacks de desconexión
        for cb in self._on_disconnect:
            try:
                await cb()
            except Exception as e:
                logger.error(f"Error en callback de desconexión: {e}")

        # Limpiar protocolo
        if self._protocol is not None:
            await self._protocol.close()
            self._protocol = None

        backoff_config = ReconnectionConfig(
            max_attempts=self._config.reconnect_max_attempts,
            initial_delay=self._config.reconnect_initial_delay,
            max_delay=self._config.reconnect_max_delay,
        )

        for attempt in range(1, backoff_config.max_attempts + 1):
            try:
                logger.info(
                    f"Intento de reconexión {attempt}/"
                    f"{backoff_config.max_attempts}"
                )

                await self.connect()

                logger.info("Reconexión exitosa")

                # Callbacks de reconexión
                for cb in self._on_reconnect:
                    try:
                        await cb()
                    except Exception as e:
                        logger.error(f"Error en callback de reconexión: {e}")
                return

            except Exception as e:
                if attempt >= backoff_config.max_attempts:
                    logger.error(
                        "Máximo de intentos de reconexión "
                        f"({backoff_config.max_attempts}) alcanzado"
                    )
                    raise

                delay = calculate_delay(attempt, backoff_config)
                logger.warning(
                    f"Reconexión fallida: {e}. "
                    f"Reintentando en {delay:.1f}s..."
                )
                await asyncio.sleep(delay)

    async def __aenter__(self) -> "Manager":
        """Context manager: conecta al entrar.

        Returns:
            El Manager con conexión establecida.
        """
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        """Context manager: cierra conexión al salir."""
        await self.close()

    def __repr__(self) -> str:
        return (
            f"<Manager {self._config.host}:{self._config.port} "
            f"connected={self._connected}>"
        )
