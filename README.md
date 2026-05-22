# asyncio-manager

Cliente AMI (Asterisk Manager Interface) asíncrono moderno para Python 3.10+.
Reemplazo moderno de la librería Panoramisk (deprecada).

## Características

- ✨ **Async/await moderno** — sin `get_event_loop()` deprecado
- 🔒 **Cero dependencias externas** — solo librería estándar de Python
- 📝 **Type hints completos** — compatible con `mypy --strict`
- 🔄 **Context manager** — `async with Manager(...) as m:`
- ⏱️ **Timeouts configurables** — connect, read, action timeouts
- 🔁 **Reconexión inteligente** — backoff exponencial con jitter
- 📋 **Soporte EventList** — recolecta eventos hasta `*Complete`
- 📞 **CallManager** — seguimiento de llamadas individuales
- 🎙️ **FastAGI** — servidor AGI asíncrono (sin `asyncio.coroutine()`)
- 🔐 **SSL/TLS** — conexiones seguras
- 🐍 **Python 3.10, 3.11, 3.12, 3.13+**
- 📞 **Asterisk 20, 21, 22+**

## Instalación

```bash
pip install asyncio-manager
```

### Dependencias de desarrollo

```bash
pip install -e ".[dev]"
```

## Uso rápido

```python
import asyncio
from asyncio_manager import Manager

async def main():
    async with Manager(
        host="127.0.0.1",
        username="admin",
        secret="password",
    ) as manager:
        await manager.connect()

        @manager.register_event("*")
        async def on_event(message):
            print(f"Evento: {message.event_type}")

        response = await manager.send_action({"Action": "Ping"})
        print(f"Ping: {response.is_success}")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass

asyncio.run(main())
```

## Documentación

La documentación completa está disponible en [docs/](docs/):

- [Instalación](docs/installation.md)
- [Primeros pasos](docs/getting_started.md)
- [Referencia de API](docs/api_reference.md)
- [Ejemplos](docs/examples.md)
- [Solución de problemas](docs/troubleshooting.md)
- [Migración desde Panoramisk](docs/migration_from_panoramisk.md)

## CLI

```bash
# Enviar acción Ping
asyncio-manager --username admin --secret password action Ping

# Originar llamada
asyncio-manager originate SIP/100 200 --caller-id "Test <1234>"

# Monitorear eventos
asyncio-manager monitor --filter "NewChannel"

# Ejecutar comando Asterisk
asyncio-manager command "pjsip show endpoints"
```

## Ejemplos

Ver [examples/](examples/) para ejemplos completos:

- `basic_listener.py` — Listener de eventos
- `call_origination.py` — Originar llamadas concurrentes
- `fast_agi_server.py` — Servidor IVR con FastAGI
- `call_manager_usage.py` — Ciclo de vida de llamadas
- `queue_management.py` — Monitoreo de colas

## Migración desde Panoramisk

Ver [docs/migration_from_panoramisk.md](docs/migration_from_panoramisk.md).

## Licencia

MIT
