"""Servidor FastAGI asíncrono.

Implementa el protocolo FastAGI de Asterisk usando ``asyncio.start_server``.
Permite crear aplicaciones AGI modernas con handlers asíncronos.

A diferencia de panoramisk (que usaba ``asyncio.coroutine()``, decorador
deprecado y eliminado en Python 3.11), esta implementación solo acepta
funciones ``async def`` nativas y agrega timeouts de lectura.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Dict, Optional

from asyncio_manager.exceptions import AGIError

logger = logging.getLogger("asyncio_manager")


class Request:
    """Representa una solicitud entrante del servidor FastAGI.

    Encapsula la conexión TCP con Asterisk, provee los headers AGI
    (variables de canal) y métodos de conveniencia para comandos AGI.

    Args:
        reader: StreamReader para leer datos de Asterisk.
        writer: StreamWriter para enviar datos a Asterisk.
        headers: Diccionario con los headers AGI (variables de canal).
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        headers: Dict[str, str],
    ) -> None:
        self._reader: asyncio.StreamReader = reader
        self._writer: asyncio.StreamWriter = writer
        self._headers: Dict[str, str] = headers
        self._closed: bool = False

    @property
    def headers(self) -> Dict[str, str]:
        """Headers AGI de la solicitud (variables de canal).

        Incluye variables como ``agi_channel``, ``agi_callerid``,
        ``agi_extension``, ``agi_type``, etc.
        """
        return dict(self._headers)

    @property
    def channel(self) -> str:
        """Canal de la llamada (``agi_channel``)."""
        return self._headers.get("agi_channel", "unknown")

    @property
    def caller_id(self) -> str:
        """Caller ID de la llamada (``agi_callerid``)."""
        return self._headers.get("agi_callerid", "unknown")

    @property
    def extension(self) -> str:
        """Extensión de la llamada (``agi_extension``)."""
        return self._headers.get("agi_extension", "unknown")

    async def send_command(self, command: str) -> str:
        """Envía un comando AGI a Asterisk y retorna el resultado.

        Args:
            command: Comando AGI a ejecutar (ej: ``ANSWER``,
                     ``SAY DIGITS 123``, ``GET DATA welcome 5000 2``).

        Returns:
            Resultado del comando (sin el código numérico).

        Raises:
            AGIError: Si ocurre un error en la comunicación.
            ConnectionError: Si la conexión se pierde.
        """
        if self._closed:
            raise AGIError("Conexión AGI cerrada")

        try:
            # Enviar comando
            payload = f"{command}\n"
            self._writer.write(payload.encode())
            await self._writer.drain()

            logger.debug(f"AGI >> {command}")

            # Leer respuesta
            result = await self._read_result()

            logger.debug(f"AGI << {result}")
            return result

        except asyncio.TimeoutError:
            raise AGIError("Timeout en comando AGI")
        except OSError as e:
            raise AGIError(f"Error de conexión AGI: {e}")

    async def _read_result(self) -> str:
        """Lee y parsea el resultado de un comando AGI.

        Maneja respuestas ``100 Trying`` (intermedias) y espera
        la respuesta final (código 200).

        Returns:
            Resultado parseado del comando.

        Raises:
            AGIError: Si la respuesta no es válida.
        """
        from asyncio_manager.utils import parse_agi_result

        while True:
            line = await asyncio.wait_for(
                self._reader.readline(),
                timeout=30.0,
            )

            if not line:
                raise AGIError("Conexión AGI cerrada por Asterisk")

            text = line.decode().strip()

            if not text:
                continue

            result = parse_agi_result(text)

            # Si es 100 Trying, continuar leyendo
            if text.startswith("100"):
                continue

            return result

    async def answer(self) -> str:
        """Responde la llamada (comando ``ANSWER``).

        Returns:
            Resultado del comando.
        """
        return await self.send_command("ANSWER")

    async def hangup(self) -> str:
        """Cuelga la llamada (comando ``HANGUP``).

        Returns:
            Resultado del comando.
        """
        return await self.send_command("HANGUP")

    async def say_digits(self, digits: str) -> str:
        """Reproduce dígitos (comando ``SAY DIGITS``).

        Args:
            digits: Dígitos a reproducir.

        Returns:
            Resultado del comando.
        """
        return await self.send_command(f"SAY DIGITS {digits}")

    async def say_number(self, number: int) -> str:
        """Reproduce un número (comando ``SAY NUMBER``).

        Args:
            number: Número a reproducir.

        Returns:
            Resultado del comando.
        """
        return await self.send_command(f"SAY NUMBER {number}")

    async def get_data(
        self,
        prompt: str,
        timeout: int = 5000,
        max_digits: int = 1,
    ) -> str:
        """Solicita entrada del usuario (comando ``GET DATA``).

        Args:
            prompt: Archivo de audio a reproducir como prompt.
            timeout: Timeout en milisegundos.
            max_digits: Máximo de dígitos a esperar.

        Returns:
            Dígitos ingresados por el usuario.
        """
        return await self.send_command(
            f"GET DATA {prompt} {timeout} {max_digits}"
        )

    async def stream_file(
        self,
        filename: str,
        escape_digits: str = "",
    ) -> str:
        """Reproduce un archivo de audio (comando ``STREAM FILE``).

        Args:
            filename: Nombre del archivo (sin extensión).
            escape_digits: Dígitos que interrumpen la reproducción.

        Returns:
            Resultado del comando.
        """
        return await self.send_command(
            f"STREAM FILE {filename} \"{escape_digits}\""
        )

    async def set_variable(self, name: str, value: str) -> str:
        """Establece una variable de canal (comando ``SET VARIABLE``).

        Args:
            name: Nombre de la variable.
            value: Valor de la variable.

        Returns:
            Resultado del comando.
        """
        return await self.send_command(
            f"SET VARIABLE {name} \"{value}\""
        )

    async def get_variable(self, name: str) -> str:
        """Obtiene una variable de canal (comando ``GET VARIABLE``).

        Args:
            name: Nombre de la variable.

        Returns:
            Valor de la variable.
        """
        return await self.send_command(f"GET VARIABLE {name}")

    async def exec_(self, application: str, *args: str) -> str:
        """Ejecuta una aplicación Asterisk (comando ``EXEC``).

        Args:
            application: Nombre de la aplicación (ej: ``Dial``, ``Goto``).
            *args: Argumentos para la aplicación.

        Returns:
            Resultado del comando.
        """
        cmd = f"EXEC {application} {' '.join(args)}"
        return await self.send_command(cmd)

    async def close(self) -> None:
        """Cierra la conexión AGI."""
        if not self._closed:
            self._closed = True
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass

    def __repr__(self) -> str:
        return (
            f"<Request channel={self.channel} "
            f"caller={self.caller_id}>"
        )


class FastAGIServer:
    """Servidor FastAGI asíncrono.

    Escucha conexiones entrantes de Asterisk y enruta las solicitudes
    a los handlers registrados según el nombre del script.

    Args:
        host: Dirección IP donde escuchar (default: ``0.0.0.0``).
        port: Puerto donde escuchar (default: ``4574``).
        buffer_size: Tamaño del buffer de lectura (default: 4096).

    Example:
        >>> server = FastAGIServer()
        >>> @server.add_script("ivr")
        ... async def ivr_handler(request):
        ...     await request.answer()
        ...     result = await request.get_data("welcome", 5000, 1)
        ...     await request.hangup()
        >>> await server.start()
        >>> # ... esperar ...
        >>> await server.stop()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 4574,
        buffer_size: int = 4096,
    ) -> None:
        self._host: str = host
        self._port: int = port
        self._buffer_size: int = buffer_size
        self._server: Optional[asyncio.AbstractServer] = None

        # Rutas: nombre_script -> handler
        self._routes: Dict[str, Callable[[Request], Awaitable[None]]] = {}

    def add_script(
        self,
        path: str,
        handler: Optional[Callable[[Request], Awaitable[None]]] = None,
    ) -> Callable:
        """Agrega o registra un handler para un script AGI.

        Puede usarse como método o como decorador::

            # Como método
            server.add_script("ivr", my_handler)

            # Como decorador
            @server.add_script("ivr")
            async def my_handler(request):
                ...

        Args:
            path: Nombre del script (ruta AGI).
            handler: Función asíncrona que maneja la solicitud.

        Returns:
            El handler si se usa como decorador.
        """
        if handler is not None:
            self._routes[path] = handler
            logger.info(f"Script AGI registrado: {path}")
            return handler

        def decorator(
            func: Callable[[Request], Awaitable[None]],
        ) -> Callable[[Request], Awaitable[None]]:
            self._routes[path] = func
            logger.info(f"Script AGI registrado: {path}")
            return func

        return decorator

    def remove_script(self, path: str) -> None:
        """Elimina un handler de script AGI.

        Args:
            path: Nombre del script a eliminar.
        """
        self._routes.pop(path, None)
        logger.info(f"Script AGI removido: {path}")

    async def start(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        """Inicia el servidor FastAGI.

        Args:
            host: Dirección IP (opcional, sobreescribe la del constructor).
            port: Puerto (opcional, sobreescribe la del constructor).

        Raises:
            OSError: Si no se puede iniciar el servidor.
        """
        actual_host = host if host is not None else self._host
        actual_port = port if port is not None else self._port

        self._server = await asyncio.start_server(
            self._handle_client,
            host=actual_host,
            port=actual_port,
        )

        addr = self._server.sockets[0].getsockname()
        logger.info(f"FastAGI escuchando en {addr[0]}:{addr[1]}")

    async def stop(self) -> None:
        """Detiene el servidor FastAGI."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("FastAGI servidor detenido")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Maneja una conexión entrante de Asterisk.

        Lee los headers AGI, identifica el script solicitado,
        y ejecuta el handler correspondiente.

        Args:
            reader: StreamReader para leer datos.
            writer: StreamWriter para enviar datos.
        """
        peer = writer.get_extra_info("peername")
        logger.info(f"Nueva conexión AGI desde {peer}")

        try:
            # Leer headers AGI con timeout
            headers = await self._read_headers(reader)

            if headers is None:
                logger.warning(f"Conexión AGI sin headers: {peer}")
                writer.close()
                return

            # Identificar script solicitado
            script_name = headers.get("agi_network_script", "default")
            logger.info(
                f"Solicitud AGI: script={script_name} "
                f"channel={headers.get('agi_channel', 'unknown')}"
            )

            # Crear Request
            request = Request(reader, writer, headers)

            # Buscar y ejecutar handler
            handler = self._routes.get(script_name)
            if handler is None:
                logger.warning(f"Script no encontrado: {script_name}")
                # Buscar handler default
                handler = self._routes.get("default")

            if handler is None:
                logger.error(f"No hay handler para script: {script_name}")
                await request.hangup()
            else:
                try:
                    await handler(request)
                except Exception as e:
                    logger.error(
                        f"Error ejecutando handler {script_name}: {e}"
                    )
                finally:
                    await request.close()

        except asyncio.TimeoutError:
            logger.error(f"Timeout leyendo headers AGI de {peer}")
        except Exception as e:
            logger.error(f"Error en conexión AGI: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _read_headers(
        self,
        reader: asyncio.StreamReader,
        timeout: float = 10.0,
    ) -> Optional[Dict[str, str]]:
        """Lee los headers de una solicitud AGI.

        Los headers AGI se envían como líneas ``key: value\\n``
        terminadas con una línea vacía ``\\n``.

        Args:
            reader: StreamReader para leer datos.
            timeout: Timeout máximo para leer todos los headers.

        Returns:
            Diccionario con los headers, o ``None`` si no se reciben.
        """
        headers: Dict[str, str] = {}
        buffer = b""

        try:
            while True:
                chunk = await asyncio.wait_for(
                    reader.read(self._buffer_size),
                    timeout=timeout,
                )

                if not chunk:
                    break

                buffer += chunk

                # Verificar si tenemos todos los headers (terminan con \n\n)
                if b"\n\n" in buffer:
                    break

        except asyncio.TimeoutError:
            if not buffer:
                return None

        # Parsear headers
        text = buffer.decode("utf-8", errors="replace")
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key.strip()] = value.strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        return headers if headers else None

    @property
    def is_running(self) -> bool:
        """Indica si el servidor está activo."""
        return self._server is not None and not self._server.is_serving()

    def __repr__(self) -> str:
        return (
            f"<FastAGIServer {self._host}:{self._port} "
            f"routes={len(self._routes)}>"
        )
