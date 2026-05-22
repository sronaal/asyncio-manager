"""Ejemplo: Servidor FastAGI con menú IVR.

Implementa un sistema IVR simple que saluda al usuario,
ofrece opciones y enruta la llamada según la selección.
"""

import asyncio
import logging

from asyncio_manager import FastAGIServer, Request, setup_logging

logger = setup_logging(level=logging.INFO)


async def ivr_menu_handler(request: Request) -> None:
    """Maneja la lógica del menú IVR.

    Args:
        request: Solicitud FastAGI entrante.
    """
    channel = request.headers.get("agi_channel", "unknown")
    caller_id = request.headers.get("agi_callerid", "unknown")

    logger.info(f"IVR: llamada de {caller_id} en canal {channel}")

    await request.answer()

    await request.say_digits("1")  # "Presione 1"
    await request.say_digits("2")  # "Presione 2"

    result = await request.get_data("welcome", timeout=5000, max_digits=2)

    logger.info(f"Usuario presionó: {result}")

    if result == "1":
        logger.info("Usuario seleccionó opción 1 (ventas)")
        await request.exec_("Goto", "sales,s,1")
    elif result == "2":
        logger.info("Usuario seleccionó opción 2 (soporte)")
        await request.exec_("Goto", "support,s,1")
    else:
        logger.info("Opción no válida, colgando")
        await request.hangup()


async def main() -> None:
    server = FastAGIServer()

    server.add_script("menu", ivr_menu_handler)

    await server.start(host="0.0.0.0", port=4574)
    logger.info("FastAGI Server escuchando en 0.0.0.0:4574")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Cerrando servidor...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
