"""Interfaz de línea de comandos para asyncio-manager.

Permite enviar acciones AMI desde la terminal, configurar conexiones
y ejecutar tareas comunes como monitoreo y originate de llamadas.

A diferencia de panoramisk (``command.py`` que usaba ``yaml.load()``
inseguro), esta CLI usa ``yaml.safe_load()`` y argparse moderno.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any, Dict, List, Optional

from asyncio_manager.logger import logger, setup_logging
from asyncio_manager.manager import Manager


def create_parser() -> argparse.ArgumentParser:
    """Crea el parser de argumentos de la CLI.

    Returns:
        ArgumentParser configurado con todos los subcomandos.
    """
    parser = argparse.ArgumentParser(
        prog="asyncio-manager",
        description="Cliente AMI asíncrono moderno para Asterisk",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host de Asterisk (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5038,
        help="Puerto AMI (default: 5038)",
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Usuario AMI",
    )
    parser.add_argument(
        "--secret",
        default="password",
        help="Contraseña AMI",
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Usar SSL/TLS",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout en segundos (default: 5.0)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Modo verbose (debug logging)",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Comando a ejecutar",
    )

    # Subcomando: action
    action_parser = subparsers.add_parser(
        "action",
        help="Envía una acción AMI",
    )
    action_parser.add_argument(
        "action_name",
        help="Nombre de la acción (ej: Ping)",
    )
    action_parser.add_argument(
        "params",
        nargs="*",
        help="Parámetros en formato key=value (ej: Channel=SIP/100)",
    )
    action_parser.add_argument(
        "--wait-all",
        action="store_true",
        help="Esperar todos los eventos (EventList)",
    )

    # Subcomando: originate
    originate_parser = subparsers.add_parser(
        "originate",
        help="Originar una llamada",
    )
    originate_parser.add_argument(
        "channel",
        help="Canal de origen (ej: SIP/100)",
    )
    originate_parser.add_argument(
        "exten",
        help="Extensión de destino",
    )
    originate_parser.add_argument(
        "--context",
        default="default",
        help="Contexto de destino (default: default)",
    )
    originate_parser.add_argument(
        "--priority",
        type=int,
        default=1,
        help="Prioridad (default: 1)",
    )
    originate_parser.add_argument(
        "--caller-id",
        help="Caller ID",
    )
    originate_parser.add_argument(
        "--sync",
        action="store_true",
        help="Esperar que la llamada se complete (no async)",
    )

    # Subcomando: monitor
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Monitorear eventos en tiempo real",
    )
    monitor_parser.add_argument(
        "--filter",
        default="*",
        help="Filtro de eventos (default: *)",
    )

    # Subcomando: command
    cmd_parser = subparsers.add_parser(
        "command",
        help="Ejecuta un comando CLI de Asterisk",
    )
    cmd_parser.add_argument(
        "command_line",
        nargs="+",
        help="Comando a ejecutar (ej: pjsip show endpoints)",
    )

    return parser


def parse_params(params: List[str]) -> Dict[str, str]:
    """Parsea parámetros en formato ``key=value``.

    Args:
        params: Lista de strings ``key=value``.

    Returns:
        Diccionario con los parámetros parseados.
    """
    result: Dict[str, str] = {}
    for param in params:
        if "=" in param:
            key, value = param.split("=", 1)
            result[key] = value
    return result


async def cmd_action(args: argparse.Namespace) -> None:
    """Ejecuta el subcomando ``action``.

    Args:
        args: Argumentos parseados.
    """
    params = parse_params(args.params)
    action: Dict[str, str] = {"Action": args.action_name}
    action.update(params)

    async with Manager(
        host=args.host,
        port=args.port,
        username=args.username,
        secret=args.secret,
        ssl=args.ssl,
        timeout=args.timeout,
    ) as manager:
        await manager.connect()

        if args.wait_all:
            messages = await manager.send_action_and_wait_all(action)
            print(f"Respuestas ({len(messages)}):")
            for msg in messages:
                print(f"  {msg.event_type or 'Response'}: {dict(msg)}")
        else:
            response = await manager.send_action(action)
            print(f"Response: {response.is_success}")
            print(f"Message: {response.message}")
            print(f"Headers: {dict(response)}")
            if response.content:
                print("Content:")
                for line in response.content:
                    print(f"  {line}")


async def cmd_originate(args: argparse.Namespace) -> None:
    """Ejecuta el subcomando ``originate``.

    Args:
        args: Argumentos parseados.
    """
    async with Manager(
        host=args.host,
        port=args.port,
        username=args.username,
        secret=args.secret,
        ssl=args.ssl,
        timeout=args.timeout,
    ) as manager:
        await manager.connect()

        response = await manager.originate(
            channel=args.channel,
            exten=args.exten,
            context=args.context,
            priority=args.priority,
            caller_id=args.caller_id,
            async_=not args.sync,
        )

        print(f"Originate: {response.is_success}")
        print(f"Message: {response.message}")


async def cmd_monitor(args: argparse.Namespace) -> None:
    """Ejecuta el subcomando ``monitor``.

    Args:
        args: Argumentos parseados.
    """
    async with Manager(
        host=args.host,
        port=args.port,
        username=args.username,
        secret=args.secret,
        ssl=args.ssl,
        timeout=args.timeout,
    ) as manager:
        await manager.connect()

        event_filter = args.filter

        @manager.register_event(event_filter)
        async def on_event(message):
            print(f"[{message.event_type}] {dict(message)}")

        print(f"Monitoreando eventos (filtro: {event_filter})...")
        print("Presiona Ctrl+C para salir.")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nMonitoreo finalizado")


async def cmd_command(args: argparse.Namespace) -> None:
    """Ejecuta el subcomando ``command``.

    Args:
        args: Argumentos parseados.
    """
    command_line = " ".join(args.command_line)

    async with Manager(
        host=args.host,
        port=args.port,
        username=args.username,
        secret=args.secret,
        ssl=args.ssl,
        timeout=args.timeout,
    ) as manager:
        await manager.connect()

        response = await manager.command(command_line)

        print(f"Response: {response.is_success}")
        if response.content:
            for line in response.content:
                print(line)
        else:
            print(dict(response))


COMMANDS = {
    "action": cmd_action,
    "originate": cmd_originate,
    "monitor": cmd_monitor,
    "command": cmd_command,
}


def main() -> None:
    """Punto de entrada principal de la CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if args.verbose:
        setup_logging(level=10)  # DEBUG

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    cmd_func = COMMANDS.get(args.command)
    if cmd_func is None:
        print(f"Comando desconocido: {args.command}")
        sys.exit(1)

    try:
        asyncio.run(cmd_func(args))
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario")
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
