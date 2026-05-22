"""Ejemplo: Uso de CallManager para gestionar llamadas.

Muestra el ciclo de vida completo: originate, esperar respuesta,
y esperar cuelgue.
"""

import asyncio
import logging

from asyncio_manager import CallManager, setup_logging

logger = setup_logging(level=logging.INFO)


async def main() -> None:
    call_manager = CallManager(
        host="127.0.0.1",
        username="admin",
        secret="password",
    )

    async with call_manager:
        call = await call_manager.originate(
            channel="SIP/2000",
            exten="1000",
            context="default",
            priority=1,
        )

        logger.info(f"Llamada originada: {call.id}")

        try:
            await asyncio.wait_for(
                call.wait_for_answer(),
                timeout=30.0,
            )
            logger.info("Llamada respondida")

            hangup_msg = await call.wait_for_hangup()
            logger.info(f"Llamada finalizada: {hangup_msg}")

        except asyncio.TimeoutError:
            logger.warning("Timeout esperando respuesta")
            await call.hangup()


if __name__ == "__main__":
    asyncio.run(main())
