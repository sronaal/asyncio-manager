# asyncio-manager

Modern async Asterisk Manager Interface (AMI) client for Python 3.10+.
A drop-in replacement for the deprecated Panoramisk library.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/asyncio-manager/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Features

- ✨ **Modern async/await** — no deprecated `get_event_loop()`
- 🔒 **Zero external dependencies** — stdlib only
- 📝 **Full type hints** — ready for `mypy --strict`
- 🔄 **Context manager** — `async with Manager(...) as m:`
- ⏱️ **Configurable timeouts** — connect, read, action
- 🔁 **Smart reconnection** — exponential backoff with jitter
- 📋 **EventList support** — collect events until `*Complete`
- 📞 **Call tracking** — `CallManager` + `Call` individual lifecycle
- 🎙️ **FastAGI** — async AGI server (no `asyncio.coroutine()`)
- 🔐 **SSL/TLS** — secure connections
- 🐍 **Python 3.10, 3.11, 3.12, 3.13+**
- 📞 **Asterisk 20, 21, 22+**

## Installation

```bash
pip install asyncio-manager
```

With dev dependencies:

```bash
pip install -e ".[dev]"
```

## Quick Start

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
            print(f"Event: {message.event_type}")

        response = await manager.send_action({"Action": "Ping"})
        print(f"Ping success: {response.is_success}")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass

asyncio.run(main())
```

### From config file

```python
from asyncio_manager import Manager, ManagerConfig

config = ManagerConfig.from_file("config.ini")

async with Manager(config=config) as manager:
    await manager.connect()
```

### From environment variables

```python
from asyncio_manager import Manager, ManagerConfig

config = ManagerConfig.from_env()
async with Manager(config=config) as manager:
    await manager.connect()
```

## CLI

```bash
# Send a Ping action
asyncio-manager --username admin --secret password action Ping

# Originate a call
asyncio-manager originate SIP/100 200 --caller-id "Test <1234>"

# Monitor events
asyncio-manager monitor --filter "NewChannel"

# Run an Asterisk CLI command
asyncio-manager command "pjsip show endpoints"
```

## Examples

See [examples/](examples/) for complete working examples:

- `basic_listener.py` — Event listener with callbacks
- `call_origination.py` — Concurrent call origination
- `fast_agi_server.py` — IVR server with FastAGI
- `call_manager_usage.py` — Call lifecycle management
- `queue_management.py` — Queue monitoring and EventList

## Documentation

Full documentation is available in [docs/](docs/):

- [Installation](docs/installation.md)
- [Getting Started](docs/getting_started.md)
- [API Reference](docs/api_reference.md)
- [Examples](docs/examples.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Migration from Panoramisk](docs/migration_from_panoramisk.md)

## Migration from Panoramisk

| Panoramisk (deprecated) | asyncio-manager |
|---|---|
| `loop = asyncio.get_event_loop()` | `asyncio.run(main())` |
| `manager = Manager(loop=loop)` | `async with Manager() as m:` |
| `asyncio.coroutine()` (broken on 3.11+) | Native `async def` only |
| `yaml.load()` (unsafe) | `yaml.safe_load()` |
| Infinite fixed 2s reconnection | Exponential backoff + jitter + limit |
| Dual inheritance (Future + Dict) | Composition (internal Future) |
| Fragile multi/completed heuristic | Explicit EventList `send_action_and_wait_all()` |
| No type hints | 100% type hints, `mypy --strict` |

## License

MIT
