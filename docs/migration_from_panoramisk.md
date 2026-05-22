# Migration from Panoramisk

## Key Differences

### 1. Context Manager (replaces get_event_loop)

**Before (Panoramisk):**
```python
loop = asyncio.get_event_loop()
manager = Manager(loop=loop, host="...")
```

**After (asyncio-manager):**
```python
async with Manager(host="...") as manager:
    await manager.connect()
```

### 2. Type Hints (new)

**Before (Panoramisk):**
```python
def send_action(self, action):
    pass
```

**After (asyncio-manager):**
```python
async def send_action(self, action: dict[str, str], timeout: float | None = None) -> Message:
    pass
```

### 3. Specific Exceptions

**Before (Panoramisk):** Generic exceptions.

**After (asyncio-manager):**
```python
from asyncio_manager import ConnectionError, AuthenticationError, TimeoutError
```

### 4. Smart Reconnection

**Before (Panoramisk):** Infinite reconnection every 2 seconds.

**After (asyncio-manager):** Exponential backoff with jitter and configurable limit.

### 5. Explicit EventList

**Before (Panoramisk):** Fragile `multi`/`completed` heuristic.

**After (asyncio-manager):** Explicit `send_action_and_wait_all()` support.

### 6. FastAGI without asyncio.coroutine

**Before (Panoramisk):** Uses `asyncio.coroutine()` (broken on Python 3.11+).

**After (asyncio-manager):** Native `async def` only.

### 7. Safe CLI

**Before (Panoramisk):** Unsafe `yaml.load()`.

**After (asyncio-manager):** `yaml.safe_load()` + argparse.

## Import Mapping

| Panoramisk | asyncio-manager |
|---|---|
| `from panoramisk import Manager` | `from asyncio_manager import Manager` |
| `from panoramisk import Message` | `from asyncio_manager import Message` |
| `from panoramisk import CallManager` | `from asyncio_manager import CallManager` |
| `from panoramisk.fast_agi import Application` | `from asyncio_manager import FastAGIServer` |
| `from panoramisk.utils import CaseInsensitiveDict` | `from asyncio_manager.utils import CaseInsensitiveDict` |
