"""Ejemplo básico: Listener de eventos AMI.

Conecta a Asterisk y escucha todos los eventos,
mostrando en consola cada evento recibido.
"""

import asyncio
import logging

from asyncio_manager import Manager, setup_logging

logger = setup_logging(level=logging.INFO)


async def main() -> None:
    async with Manager(
        host="127.0.0.1",
        username="admin",
        secret="password",
        timeout=5.0,
    ) as manager:
        await manager.connect()

        @manager.register_event("*")
        async def on_event(message):
            logger.info(f"Evento: {message.event_type} - {dict(message)}")

        @manager.register_event("NewChannel")
        async def on_new_channel(message):
            logger.info(f"Nueva llamada: {message.get('Channel')}")
            logger.info(f"  CallerID: {message.get('CallerIDNum')}")

        @manager.register_event("Hangup")
        async def on_hangup(message):
            logger.info(f"Llamada finalizada: {message.get('Channel')}")

        logger.info("Escuchando eventos... (Ctrl+C para salir)")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Cerrando...")


if __name__ == "__main__":
    asyncio.run(main())
