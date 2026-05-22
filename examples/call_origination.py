"""Ejemplo: Originar llamadas usando el Manager.

Muestra cómo originate múltiples llamadas de forma concurrente
y verificar el resultado de cada una.
"""

import asyncio
import logging

from asyncio_manager import Manager, setup_logging

logger = setup_logging(level=logging.INFO)


async def originate_call(manager: Manager, phone_number: str) -> str | None:
    """Origina una llamada a un número específico.

    Args:
        manager: Instancia de Manager conectada.
        phone_number: Número telefónico a llamar.

    Returns:
        ActionID de la llamada originada, o None si falló.
    """
    try:
        response = await manager.originate(
            channel=f"SIP/provider/{phone_number}",
            exten="100",
            context="from-internal",
            priority=1,
            caller_id="Test <1234>",
            timeout=30,
            async_=True,
        )

        if response.is_success:
            logger.info(f"Llamada originada: {response.action_id}")
            return response.action_id
        else:
            logger.error(f"Fallo al originar: {response}")
            return None

    except asyncio.TimeoutError:
        logger.error("Timeout al originar")
        return None
    except Exception as e:
        logger.error(f"Error al originar: {e}")
        return None


async def main() -> None:
    async with Manager(
        host="127.0.0.1",
        username="admin",
        secret="password",
        timeout=10.0,
        read_timeout=30.0,
    ) as manager:
        await manager.connect()

        phone_numbers = [
            "5551234567",
            "5559876543",
            "5555551234",
        ]

        tasks = [
            originate_call(manager, num)
            for num in phone_numbers
        ]

        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r is not None)
        logger.info(f"Resultados: {success_count}/{len(results)} exitosas")


if __name__ == "__main__":
    asyncio.run(main())
