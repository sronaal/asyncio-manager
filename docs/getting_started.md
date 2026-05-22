# Getting Started

## Basic Connection

The simplest way to use asyncio-manager is with a context manager:

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
        print("Connected to Asterisk!")

        response = await manager.send_action({"Action": "Ping"})
        print(f"Ping successful: {response.is_success}")

asyncio.run(main())
```

## Using Config File

```python
from asyncio_manager import Manager, ManagerConfig

config = ManagerConfig.from_file("config.ini")

async with Manager(config=config) as manager:
    await manager.connect()
    # ...
```

## Using Environment Variables

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

## Listening to Events

```python
@manager.register_event("NewChannel")
async def on_new_channel(message):
    print(f"New channel: {message.get('Channel')}")

@manager.register_event("*")
async def on_all_events(message):
    print(f"Event: {message.event_type}")
```

## Sending Actions

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

## Error Handling

```python
from asyncio_manager import (
    ConnectionError,
    AuthenticationError,
    TimeoutError,
)

try:
    await manager.connect()
except ConnectionError as e:
    print(f"Cannot connect: {e}")
except AuthenticationError as e:
    print(f"Invalid credentials: {e}")
except TimeoutError as e:
    print(f"Timeout: {e}")
```
