# Primeros pasos

## Conexión básica

La forma más simple de usar asyncio-manager es con un context manager:

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
        print("Conectado a Asterisk!")

        response = await manager.send_action({"Action": "Ping"})
        print(f"Ping exitoso: {response.is_success}")

asyncio.run(main())
```

## Usando configuración desde archivo

```python
from asyncio_manager import Manager, ManagerConfig

config = ManagerConfig.from_file("config.ini")

async with Manager(config=config) as manager:
    await manager.connect()
    # ...
```

## Usando configuración desde variables de entorno

```python
import os
os.environ["ASTERISK_HOST"] = "10.0.0.1"
os.environ["ASTERISK_USERNAME"] = "admin"
os.environ["ASTERISK_SECRET"] = "password"

from asyncio_manager import Manager, ManagerConfig

config = ManagerConfig.from_env()
async with Manager(config=config) as manager:
    await manager.connect()
```

## Escuchar eventos

```python
@manager.register_event("NewChannel")
async def on_new_channel(message):
    print(f"Nuevo canal: {message.get('Channel')}")

@manager.register_event("*")
async def on_all_events(message):
    print(f"Evento: {message.event_type}")
```

## Enviar acciones

```python
response = await manager.send_action({
    "Action": "Originate",
    "Channel": "SIP/100",
    "Exten": "200",
    "Context": "default",
    "Priority": "1",
    "CallerID": "Test <1234>",
    "Async": "true",
})
```

## Manejo de errores

```python
from asyncio_manager import (
    ConnectionError,
    AuthenticationError,
    TimeoutError,
)

try:
    await manager.connect()
except ConnectionError as e:
    print(f"No se pudo conectar: {e}")
except AuthenticationError as e:
    print(f"Credenciales inválidas: {e}")
except TimeoutError as e:
    print(f"Timeout: {e}")
```
