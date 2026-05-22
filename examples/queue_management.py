"""Ejemplo: Gestión de colas (QueueStatus).

Muestra cómo obtener estadísticas de colas usando send_action_and_wait_all
que recolecta todos los eventos hasta el *Complete.
"""

import asyncio
import logging

from asyncio_manager import Manager, setup_logging

logger = setup_logging(level=logging.INFO)


async def get_queue_stats(manager: Manager, queue_name: str) -> None:
    """Obtiene y muestra estadísticas de una cola.

    Args:
        manager: Instancia de Manager conectada.
        queue_name: Nombre de la cola a consultar.
    """
    logger.info(f"Consultando cola: {queue_name}")

    messages = await manager.send_action_and_wait_all({
        "Action": "QueueStatus",
        "Queue": queue_name,
    })

    logger.info(f"Recibidos {len(messages)} mensajes para cola {queue_name}")

    for msg in messages:
        if msg.is_event:
            logger.info(f"  Evento: {msg.event_type} -> {dict(msg)}")


async def main() -> None:
    async with Manager(
        host="127.0.0.1",
        username="admin",
        secret="password",
    ) as manager:
        await manager.connect()

        queues = ["support", "sales", "billing"]

        tasks = [
            get_queue_stats(manager, queue)
            for queue in queues
        ]

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
