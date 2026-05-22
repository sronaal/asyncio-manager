"""Configuración de la conexión AMI.

Define el dataclass ``ManagerConfig`` que centraliza todos los
parámetros de conexión y permite cargarlos desde archivos INI
o variables de entorno.
"""

import os
from configparser import ConfigParser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ManagerConfig:
    """Configuración completa para una conexión AMI.

    Todos los parámetros tienen valores por defecto sensibles,
    permitiendo crear una instancia sin argumentos y solo
    sobrescribir los necesarios.

    Attributes:
        host: Dirección IP o hostname del servidor Asterisk.
        port: Puerto TCP del AMI (default: 5038).
        username: Usuario para autenticación AMI.
        secret: Contraseña para autenticación AMI.
        timeout: Timeout para acciones AMI en segundos.
        read_timeout: Timeout para lectura de mensajes en segundos.
        connect_timeout: Timeout para establecer conexión en segundos.
        ssl: Habilita conexión SSL/TLS.
        ssl_verify: Verifica el certificado SSL (si ssl=True).
        encoding: Codificación para los mensajes AMI (default: 'utf-8').
        ping_interval: Intervalo de keep-alive en segundos (default: 10).
        reconnect_max_attempts: Máximo de reintentos de reconexión.
        reconnect_initial_delay: Delay inicial de reconexión en segundos.
        reconnect_max_delay: Delay máximo de reconexión en segundos.
    """

    host: str = "127.0.0.1"
    port: int = 5038
    username: str = ""
    secret: str = ""
    timeout: float = 5.0
    read_timeout: float = 30.0
    connect_timeout: float = 10.0
    ssl: bool = False
    ssl_verify: bool = True
    encoding: str = "utf-8"
    ping_interval: float = 10.0
    reconnect_max_attempts: int = 10
    reconnect_initial_delay: float = 1.0
    reconnect_max_delay: float = 60.0

    @classmethod
    def from_file(cls, path: str) -> "ManagerConfig":
        """Carga la configuración desde un archivo INI.

        El archivo debe tener una sección ``[asterisk]`` con las
        opciones de configuración. Las opciones faltantes usan
        los valores por defecto.

        Args:
            path: Ruta al archivo INI de configuración.

        Returns:
            Nueva instancia de ManagerConfig con los valores del archivo.

        Example:
            >>> config = ManagerConfig.from_file("config.ini")
            >>> async with Manager(config=config) as m:
            ...     await m.connect()
        """
        config = ConfigParser()
        config.read(path)

        section = config["asterisk"] if config.has_section("asterisk") else {}

        return cls(
            host=section.get("host", "127.0.0.1"),
            port=int(section.get("port", 5038)),
            username=section.get("username", ""),
            secret=section.get("secret", ""),
            timeout=float(section.get("timeout", "5.0")),
            read_timeout=float(section.get("read_timeout", "30.0")),
            connect_timeout=float(section.get("connect_timeout", "10.0")),
            ssl=section.getboolean("ssl", fallback=False),
            ssl_verify=section.getboolean("ssl_verify", fallback=True),
            encoding=section.get("encoding", "utf-8"),
            ping_interval=float(section.get("ping_interval", "10.0")),
            reconnect_max_attempts=int(section.get("reconnect_max_attempts", "10")),
            reconnect_initial_delay=float(section.get("reconnect_initial_delay", "1.0")),
            reconnect_max_delay=float(section.get("reconnect_max_delay", "60.0")),
        )

    @classmethod
    def from_env(cls, prefix: str = "ASTERISK_") -> "ManagerConfig":
        """Carga la configuración desde variables de entorno.

        Las variables de entorno se mapean con el prefijo indicado:

        - ``<prefix>HOST``
        - ``<prefix>PORT``
        - ``<prefix>USERNAME``
        - ``<prefix>SECRET``
        - ``<prefix>SSL``
        - etc.

        Args:
            prefix: Prefijo de las variables de entorno (default: ``ASTERISK_``).

        Returns:
            Nueva instancia de ManagerConfig con los valores de entorno.

        Example:
            >>> config = ManagerConfig.from_env()
            >>> async with Manager(config=config) as m:
            ...     await m.connect()
        """
        get_env = lambda key: os.getenv(f"{prefix}{key}")

        def get_env_int(key: str, default: int) -> int:
            val = get_env(key)
            return int(val) if val is not None else default

        def get_env_float(key: str, default: float) -> float:
            val = get_env(key)
            return float(val) if val is not None else default

        def get_env_bool(key: str, default: bool) -> bool:
            val = get_env(key)
            if val is None:
                return default
            return val.lower() in ("true", "1", "yes")

        return cls(
            host=get_env("HOST") or "127.0.0.1",
            port=get_env_int("PORT", 5038),
            username=get_env("USERNAME") or "",
            secret=get_env("SECRET") or "",
            timeout=get_env_float("TIMEOUT", 5.0),
            read_timeout=get_env_float("READ_TIMEOUT", 30.0),
            connect_timeout=get_env_float("CONNECT_TIMEOUT", 10.0),
            ssl=get_env_bool("SSL", False),
            ssl_verify=get_env_bool("SSL_VERIFY", True),
            encoding=get_env("ENCODING") or "utf-8",
            ping_interval=get_env_float("PING_INTERVAL", 10.0),
            reconnect_max_attempts=get_env_int("RECONNECT_MAX_ATTEMPTS", 10),
            reconnect_initial_delay=get_env_float("RECONNECT_INITIAL_DELAY", 1.0),
            reconnect_max_delay=get_env_float("RECONNECT_MAX_DELAY", 60.0),
        )

    def to_dict(self) -> dict:
        """Convierte la configuración a diccionario (sin secret).

        Útil para logging o depuración: el campo ``secret`` se omite.

        Returns:
            Diccionario con todos los campos excepto la contraseña.
        """
        data = {k: v for k, v in self.__dict__.items() if k != "secret"}
        return data
