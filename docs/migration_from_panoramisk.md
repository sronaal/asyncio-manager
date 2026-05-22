# Migración desde Panoramisk

## Diferencias clave

### 1. Context manager (reemplaza get_event_loop)

**Antes (Panoramisk):**
```python
loop = asyncio.get_event_loop()
manager = Manager(loop=loop, host="...")
```

**Después (asyncio-manager):**
```python
async with Manager(host="...") as manager:
    await manager.connect()
```

### 2. Type hints (nuevo)

**Antes (Panoramisk):**
```python
def send_action(self, action):
    pass
```

**Después (asyncio-manager):**
```python
async def send_action(
    self,
    action: Dict[str, str],
    timeout: Optional[float] = None,
) -> Message:
    pass
```

### 3. Excepciones específicas

**Antes (Panoramisk):** Excepciones genéricas.

**Después (asyncio-manager):**
```python
from asyncio_manager import ConnectionError, AuthenticationError, TimeoutError
```

### 4. Reconexión con backoff

**Antes (Panoramisk):** Reconexión infinita cada 2s.

**Después (asyncio-manager):** Backoff exponencial con jitter y límite configurable.

### 5. EventList explícito

**Antes (Panoramisk):** Heurística frágil con `multi`/`completed`.

**Después (asyncio-manager):** Soporte explícito con `send_action_and_wait_all()`.

### 6. FastAGI sin asyncio.coroutine

**Antes (Panoramisk):** Usa `asyncio.coroutine()` (roto en Python 3.11+).

**Después (asyncio-manager):** Solo `async def` nativas.

### 7. CLI segura

**Antes (Panoramisk):** `yaml.load()` inseguro.

**Después (asyncio-manager):** `yaml.safe_load()` + argparse.

## Mapeo de imports

| Panoramisk | asyncio-manager |
|---|---|
| `from panoramisk import Manager` | `from asyncio_manager import Manager` |
| `from panoramisk import Message` | `from asyncio_manager import Message` |
| `from panoramisk import CallManager` | `from asyncio_manager import CallManager` |
| `from panoramisk.fast_agi import Application` | `from asyncio_manager import FastAGIServer` |
| `from panoramisk.utils import CaseInsensitiveDict` | `from asyncio_manager.utils import CaseInsensitiveDict` |
