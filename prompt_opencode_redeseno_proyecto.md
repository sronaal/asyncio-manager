# 🚀 PROMPT PROFESIONAL: REDESEÑO DE PANORAMISK

## CONTEXTO Y OBJETIVO

Necesito que diseñes un **cliente AMI (Asterisk Manager Interface) moderno y optimizado** como reemplazo de la librería deprecada Panoramisk. El proyecto será un clon mejorado que:

- ✅ Usa Python moderno (3.10+)
- ✅ Soluciona todos los problemas conocidos de Panoramisk
- ✅ Es compatible con Asterisk 20, 21, 22 y futuras versiones
- ✅ Tiene arquitectura escalable y mantenible
- ✅ Incluye documentación profesional y ejemplos

---

## ESPECIFICACIONES TÉCNICAS

### 1. REQUISITOS DE VERSIONES

```
Python soportadas:
  - Python 3.10 ✅
  - Python 3.11 ✅
  - Python 3.12 ✅
  - Python 3.13+ ✅ (debe ser compatible con futuras)

Asterisk soportado:
  - Asterisk 20.x
  - Asterisk 21.x
  - Asterisk 22.x
  - Arquitectura abierta para futuras versiones
```

### 2. ARQUITECTURA REQUERIDA

```
asyncio_manager/
├── asyncio_manager/
│   ├── __init__.py
│   ├── manager.py          # Clase Manager principal
│   ├── message.py          # Clase Message mejorada
│   ├── protocol.py         # Protocolo AMI
│   ├── call_manager.py     # Gestión de llamadas
│   ├── fast_agi.py         # Servidor FastAGI
│   ├── exceptions.py       # Excepciones personalizadas
│   ├── utils.py            # Utilidades
│   ├── config.py           # Configuración
│   ├── typing_helpers.py   # Type hints
│   └── logger.py           # Logging centralizado
│
├── examples/
│   ├── basic_listener.py
│   ├── call_origination.py
│   ├── fast_agi_server.py
│   ├── call_manager_usage.py
│   ├── queue_management.py
│   └── config_example.ini
│
├── tests/
│   ├── __init__.py
│   ├── test_manager.py
│   ├── test_message.py
│   ├── test_protocol.py
│   ├── test_call_manager.py
│   ├── test_fast_agi.py
│   ├── test_integration.py
│   └── fixtures/
│       ├── asterisk_responses.yaml
│       └── mock_events.yaml
│
├── docs/
│   ├── index.md
│   ├── installation.md
│   ├── getting_started.md
│   ├── api_reference.md
│   ├── examples.md
│   ├── troubleshooting.md
│   └── migration_from_panoramisk.md
│
├── pyproject.toml          # Moderno (NO setup.py)
├── README.md
├── CHANGELOG.md
├── LICENSE
└── .github/
    └── workflows/
        ├── tests.yml
        ├── lint.yml
        └── docs.yml
```

---

## PROBLEMAS A SOLUCIONAR

### Problema 1: Compatibilidad con Python Moderno ✅

**Solución implementada:**
```python
# ❌ VIEJO (Panoramisk)
loop = asyncio.get_event_loop()
manager = Manager(loop=loop, ...)

# ✅ NUEVO (asyncio_manager)
async def main():
    async with Manager(...) as manager:
        await manager.connect()
        # ... tu código ...

asyncio.run(main())
```

**Requisitos:**
- Usar `asyncio.run()` como patrón principal
- Soportar context managers (`async with`)
- Type hints completos (PEP 484)
- Sin dependencia de `get_event_loop()` deprecado
- Compatible con Python 3.13+ donde se elimina `get_event_loop()`

### Problema 2: Latencia de Red y Timeouts ✅

**Solución implementada:**

```python
class Manager:
    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 5038,
        username: str = '',
        secret: str = '',
        timeout: float = 5.0,           # ← TIMEOUT configurable
        read_timeout: float = 30.0,     # ← Para respuestas lentas
        connect_timeout: float = 10.0,  # ← Para conexión
        # ... otros parámetros
    ):
        pass
```

**Características:**
- Timeouts configurables por operación
- Buffer adaptativo para respuestas multilinea
- Manejo robusto de latencia alta (WAN)
- Validación de respuestas completas
- Retry automático con backoff exponencial

### Problema 3: Reconexión Inteligente ✅

**Solución implementada:**

```python
# Reconexión con límites inteligentes
class ReconnectionConfig:
    max_attempts: int = 10              # ← Límite de intentos
    initial_delay: float = 1.0          # ← Delay inicial (1s)
    max_delay: float = 60.0             # ← Delay máximo (1m)
    exponential_base: float = 2.0       # ← 2x cada reintento
    jitter: bool = True                 # ← Evita thundering herd

# Resultado: 1s, 2s, 4s, 8s, 16s, 32s, 60s, 60s...
```

**Características:**
- Backoff exponencial con jitter
- Límite configurable de reintentos
- Callbacks para eventos de reconexión
- Detección de conexión abierta/cerrada
- Health checks periódicos

### Problema 4: Manejo Robusto de Errores ✅

**Solución implementada:**

```python
# Excepciones personalizadas
class AsyncioManagerError(Exception):
    """Base exception"""
    pass

class ConnectionError(AsyncioManagerError):
    """No puede conectar"""
    pass

class TimeoutError(AsyncioManagerError):
    """Operación excedió timeout"""
    pass

class AuthenticationError(AsyncioManagerError):
    """Credenciales inválidas"""
    pass

class ProtocolError(AsyncioManagerError):
    """Error en protocolo AMI"""
    pass

# Uso:
try:
    await manager.connect()
except ConnectionError as e:
    logger.error(f"No puede conectar: {e}")
except AuthenticationError:
    logger.error("Credenciales inválidas")
except Exception as e:
    logger.error(f"Error inesperado: {e}")
```

### Problema 5: Parsing Incompleto de Respuestas ✅

**Solución implementada:**

```python
class AMIProtocol:
    """
    Parser robusto de protocolo AMI que:
    - Valida respuestas completas
    - Maneja contenido multilinea
    - Verifica integridad de mensajes
    - Detecta respuestas incompletas
    """
    
    async def read_message(self) -> Message:
        """
        Lee un mensaje completo del AMI
        Lanza TimeoutError si no hay respuesta completa
        """
        pass
```

**Características:**
- Validación de respuestas completas
- Detección de contenido multilinea
- Manejo de contenido binario
- Buffering inteligente
- Timeout con fallback

---

## CARACTERÍSTICAS PRINCIPALES

### 1. Manager (Clase Principal)

```python
class Manager:
    """Cliente AMI asincrónico moderno"""
    
    async def __aenter__(self):
        """Context manager support"""
        await self.connect()
        return self
    
    async def __aexit__(self, *args):
        """Limpieza automática"""
        await self.close()
    
    async def connect(self) -> None:
        """
        Conecta a servidor Asterisk
        - Soporte para SSL/TLS
        - Autenticación segura
        - Reconexión automática
        """
        pass
    
    async def close(self) -> None:
        """Cierra conexión limpiamente"""
        pass
    
    def register_event(
        self,
        pattern: str,
        callback: Callable[[Message], Awaitable[None]],
    ) -> None:
        """
        Registra callback para eventos
        Pattern soporta wildcards: 'NewChannel', 'Queue*', '*'
        """
        pass
    
    async def send_action(self, action: Dict[str, str]) -> Message:
        """
        Envía acción al AMI
        - Soporte para parámetros
        - Manejo de respuestas
        - Timeout configurable
        """
        pass
    
    async def originate(
        self,
        channel: str,
        exten: str,
        context: str = 'default',
        priority: int = 1,
        caller_id: Optional[str] = None,
        timeout: Optional[int] = None,
        async_: bool = True,
    ) -> Message:
        """Helper para originate"""
        pass
```

### 2. Message (Mejorado)

```python
class Message(CaseInsensitiveDict):
    """
    Encapsula eventos y respuestas AMI
    - Case-insensitive access
    - Type hints
    - Propiedades helpers
    """
    
    @property
    def is_response(self) -> bool:
        """¿Es una respuesta de acción?"""
        pass
    
    @property
    def is_event(self) -> bool:
        """¿Es un evento?"""
        pass
    
    @property
    def is_success(self) -> bool:
        """¿Fue exitosa la acción?"""
        pass
    
    @property
    def action_id(self) -> Optional[str]:
        """ID de acción"""
        pass
    
    @property
    def event_type(self) -> Optional[str]:
        """Tipo de evento"""
        pass
    
    def get_multiline(self, key: str) -> List[str]:
        """Obtener contenido multilinea"""
        pass
```

### 3. CallManager (Mejorado)

```python
class CallManager:
    """Gestión de llamadas individuales"""
    
    async def originate(
        self,
        channel: str,
        exten: str,
        context: str = 'default',
        priority: int = 1,
        **options
    ) -> Call:
        """Originar llamada y obtener Call object"""
        pass
    
    async def wait_for_event(
        self,
        event_type: str,
        timeout: float = 30.0,
        channel_id: Optional[str] = None,
    ) -> Message:
        """Esperar evento específico con timeout"""
        pass

class Call:
    """Representa una llamada activa"""
    
    async def wait_for_answer(self, timeout: float = 30.0) -> None:
        """Esperar que la llamada sea respondida"""
        pass
    
    async def wait_for_hangup(self) -> Message:
        """Esperar que la llamada se cuelgue"""
        pass
    
    async def transfer(self, exten: str, context: str = 'default') -> None:
        """Transferir llamada"""
        pass
    
    async def hangup(self) -> None:
        """Colgar la llamada"""
        pass
```

### 4. FastAGI (Moderno)

```python
class FastAGIServer:
    """Servidor FastAGI asincrónico moderno"""
    
    async def start(self, host: str = '0.0.0.0', port: int = 4574) -> None:
        """Inicia servidor FastAGI"""
        pass
    
    def add_script(
        self,
        path: str,
        handler: Callable[[Request], Awaitable[None]],
    ) -> None:
        """Agrega script AGI"""
        pass

class Request:
    """Solicitud FastAGI"""
    
    @property
    def headers(self) -> Dict[str, str]:
        """Headers AGI (variables)"""
        pass
    
    async def send_command(self, command: str) -> str:
        """Envía comando AGI"""
        pass
    
    async def answer(self) -> None:
        """ANSWER"""
        pass
    
    async def hangup(self) -> None:
        """HANGUP"""
        pass
    
    async def say_digits(self, digits: str) -> None:
        """SAY DIGITS"""
        pass
```

---

## EJEMPLOS DE USO

### Ejemplo 1: Básico - Event Listener

```python
"""examples/basic_listener.py"""

import asyncio
from asyncio_manager import Manager, logger

async def main():
    # Context manager - cierre automático
    async with Manager(
        host='127.0.0.1',
        username='admin',
        secret='password',
    ) as manager:
        
        # Registrar eventos con callbacks async
        @manager.register_event('*')
        async def on_event(message):
            logger.info(f"Evento: {message.event_type} - {message}")
        
        @manager.register_event('NewChannel')
        async def on_new_channel(message):
            logger.info(f"Nueva llamada: {message.get('Channel')}")
            logger.info(f"CallerID: {message.get('CallerIDNum')}")
        
        @manager.register_event('Hangup')
        async def on_hangup(message):
            logger.info(f"Llamada finalizada: {message.get('Channel')}")
        
        # Conectar y escuchar
        await manager.connect()
        
        # Mantener escuchando (Ctrl+C para salir)
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Cerrando...")

if __name__ == '__main__':
    asyncio.run(main())
```

### Ejemplo 2: Originar Llamadas

```python
"""examples/call_origination.py"""

import asyncio
from asyncio_manager import Manager, logger

async def originate_call(manager, phone_number):
    """Origina llamada a un número específico"""
    try:
        response = await manager.originate(
            channel='SIP/provider/{}' .format(phone_number),
            exten='100',
            context='from-internal',
            priority=1,
            caller_id='Test <1234>',
            timeout=30,
            async_=True,  # No esperar resultado
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

async def main():
    async with Manager(
        host='127.0.0.1',
        username='admin',
        secret='password',
        timeout=10.0,        # Timeout por defecto
        read_timeout=30.0,   # Para respuestas lentas
    ) as manager:
        await manager.connect()
        
        # Originar múltiples llamadas
        phone_numbers = [
            '5551234567',
            '5559876543',
            '5555551234',
        ]
        
        tasks = [
            originate_call(manager, num)
            for num in phone_numbers
        ]
        
        results = await asyncio.gather(*tasks)
        logger.info(f"Resultados: {results}")

if __name__ == '__main__':
    asyncio.run(main())
```

### Ejemplo 3: FastAGI Server

```python
"""examples/fast_agi_server.py"""

import asyncio
from asyncio_manager import FastAGIServer, logger

async def ivr_menu_handler(request):
    """Maneja llamada IVR"""
    # Obtener variables AGI
    channel = request.headers.get('agi_channel', 'unknown')
    caller_id = request.headers.get('agi_callerid', 'unknown')
    
    logger.info(f"IVR: {channel} desde {caller_id}")
    
    # Responder llamada
    await request.answer()
    
    # Reproducir menú
    await request.say_digits('1')  # Presione 1
    await request.say_digits('2')  # Presione 2
    
    # Obtener entrada
    result = await request.send_command(
        'GET DATA welcome 5000 2'
    )
    
    logger.info(f"Usuario presionó: {result}")
    
    # Procesar entrada
    if result == '1':
        logger.info("Usuario seleccionó opción 1")
    elif result == '2':
        logger.info("Usuario seleccionó opción 2")

async def main():
    server = FastAGIServer()
    
    # Registrar handler
    server.add_script('menu', ivr_menu_handler)
    
    # Iniciar servidor
    await server.start(host='0.0.0.0', port=4574)
    logger.info("FastAGI Server escuchando en 0.0.0.0:4574")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Cerrando servidor...")
        await server.stop()

if __name__ == '__main__':
    asyncio.run(main())
```

### Ejemplo 4: CallManager

```python
"""examples/call_manager_usage.py"""

import asyncio
from asyncio_manager import CallManager, logger

async def main():
    call_manager = CallManager(
        host='127.0.0.1',
        username='admin',
        secret='password',
    )
    
    async with call_manager:
        # Originar y seguir llamada
        call = await call_manager.originate(
            channel='SIP/2000',
            exten='1000',
            context='default',
            priority=1,
        )
        
        logger.info(f"Llamada originada: {call.id}")
        
        # Esperar respuesta
        try:
            await asyncio.wait_for(
                call.wait_for_answer(),
                timeout=30.0,
            )
            logger.info("Llamada respondida")
            
            # Esperar que se cuelgue
            hangup_msg = await call.wait_for_hangup()
            logger.info(f"Llamada finalizada: {hangup_msg}")
            
        except asyncio.TimeoutError:
            logger.warning("Timeout esperando respuesta")
            await call.hangup()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## REQUISITOS TÉCNICOS DETALLADOS

### 1. Dependencias Externas

```toml
[project]
name = "asyncio-manager"
version = "1.0.0"
description = "Modern async Asterisk AMI client"
requires-python = ">=3.10"
dependencies = [
    # ✅ CERO dependencias externas (solo stdlib)
    # Usar: asyncio, logging, ssl, socket, etc.
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "isort>=5.12",
    "flake8>=6.0",
    "mypy>=1.0",
    "sphinx>=6.0",
]
```

### 2. Type Hints Completos

```python
# Todas las funciones deben tener type hints
from typing import Optional, Dict, List, Callable, Awaitable

async def send_action(
    self,
    action: Dict[str, str],
    timeout: Optional[float] = None,
) -> Message:
    """
    Envía acción al AMI
    
    Args:
        action: Diccionario con acción y parámetros
        timeout: Timeout en segundos
    
    Returns:
        Mensaje de respuesta
    
    Raises:
        TimeoutError: Si excede timeout
        ConnectionError: Si no está conectado
    """
    pass
```

### 3. Logging Centralizado

```python
# logging.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> None:
    """Configura logging centralizado"""
    
    logger = logging.getLogger('asyncio_manager')
    logger.setLevel(level)
    
    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(console)
    
    # File handler
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10_000_000,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
```

### 4. Configuración desde Archivo INI

```python
# config.py
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ManagerConfig:
    host: str = '127.0.0.1'
    port: int = 5038
    username: str = ''
    secret: str = ''
    timeout: float = 5.0
    read_timeout: float = 30.0
    connect_timeout: float = 10.0
    ssl: bool = False
    ssl_verify: bool = True
    encoding: str = 'utf-8'
    
    @classmethod
    def from_file(cls, path: str) -> 'ManagerConfig':
        """Carga desde archivo INI"""
        config = ConfigParser()
        config.read(path)
        
        section = config['asterisk'] if 'asterisk' in config else {}
        return cls(
            host=section.get('host', '127.0.0.1'),
            port=int(section.get('port', 5038)),
            username=section.get('username', ''),
            secret=section.get('secret', ''),
            # ...
        )
```

---

## PRUEBAS REQUERIDAS

### 1. Unit Tests

```python
# tests/test_manager.py
import pytest
import asyncio
from asyncio_manager import Manager, ConnectionError

@pytest.mark.asyncio
async def test_connect_valid_credentials():
    """Test conexión con credenciales válidas"""
    pass

@pytest.mark.asyncio
async def test_connect_invalid_credentials():
    """Test fallo con credenciales inválidas"""
    with pytest.raises(ConnectionError):
        async with Manager(
            username='invalid',
            secret='invalid',
        ) as manager:
            await manager.connect()

@pytest.mark.asyncio
async def test_timeout_handling():
    """Test manejo de timeouts"""
    pass

@pytest.mark.asyncio
async def test_reconnection_backoff():
    """Test backoff exponencial en reconexión"""
    pass
```

### 2. Integration Tests

```python
# tests/test_integration.py
@pytest.mark.asyncio
async def test_originate_and_hangup():
    """Test originate llamada completa"""
    pass

@pytest.mark.asyncio
async def test_event_callbacks():
    """Test que callbacks se ejecuten"""
    pass

@pytest.mark.asyncio
async def test_high_latency():
    """Test comportamiento con latencia alta (WAN)"""
    pass

@pytest.mark.asyncio
async def test_reconnection_recovery():
    """Test recuperación de desconexión"""
    pass
```

### 3. Performance Tests

```python
# tests/test_performance.py
@pytest.mark.asyncio
async def test_concurrent_actions():
    """Test 100+ acciones concurrentes"""
    pass

@pytest.mark.asyncio
async def test_message_throughput():
    """Test throughput de eventos/segundo"""
    pass

@pytest.mark.asyncio
async def test_memory_usage():
    """Test uso de memoria en operaciones largas"""
    pass
```

---

## COMPATIBILIDAD CON ASTERISK

### Versiones Soportadas

```python
ASTERISK_VERSIONS = {
    20: {
        'release_date': '2022-12-20',
        'eol_date': '2025-12-20',
        'status': 'supported',
    },
    21: {
        'release_date': '2023-10-05',
        'eol_date': '2026-10-05',
        'status': 'supported',
    },
    22: {
        'release_date': '2024-10-10',
        'eol_date': '2027-10-10',
        'status': 'supported',
    },
    23: {
        'release_date': '2025-10-XX',  # Futura
        'eol_date': '2028-10-XX',
        'status': 'planned',
    },
}
```

### Validación de Compatibilidad

```python
async def validate_asterisk_version(manager) -> None:
    """Valida que Asterisk sea versión soportada"""
    response = await manager.send_action({'Action': 'CoreStatus'})
    version = response.get('SystemUptime')
    
    # Verificar versión
    # Logear warning si no está soportada
```

---

## DOCUMENTACIÓN REQUERIDA

### 1. README.md Completo
```markdown
# asyncio-manager

Modern async Asterisk Manager Interface (AMI) client for Python 3.10+

## Features
- Modern async/await syntax
- Type hints throughout
- Zero external dependencies
- Python 3.10, 3.11, 3.12+ support
- Asterisk 20, 21, 22 support
- Robust error handling
- Connection recovery with exponential backoff
- ... (más features)

## Installation
## Quick Start
## Examples
## API Reference
## Troubleshooting
```

### 2. Migration Guide (De Panoramisk)
```markdown
# Migration from Panoramisk

## Key Differences

### Before (Panoramisk)
```python
loop = asyncio.get_event_loop()
manager = Manager(loop=loop, ...)
```

### After (asyncio-manager)
```python
async with Manager(...) as manager:
    await manager.connect()
```

## Common Issues and Solutions
- Timeout problems
- Reconnection loops
- Event handling
```

### 3. API Reference Completa

```markdown
# API Reference

## Manager

### Constructor
```python
Manager(
    host: str = '127.0.0.1',
    port: int = 5038,
    username: str = '',
    secret: str = '',
    timeout: float = 5.0,
    read_timeout: float = 30.0,
    connect_timeout: float = 10.0,
    ssl: bool = False,
    ssl_verify: bool = True,
    encoding: str = 'utf-8',
    reconnect_config: Optional[ReconnectionConfig] = None,
)
```

### Methods
- `async connect()` - Conecta a Asterisk
- `async close()` - Cierra conexión
- `register_event(pattern, callback)` - Registra callback
- `async send_action(action)` - Envía acción
... (todos los métodos documentados)
```

---

## CHECKLIST DE CALIDAD

- [ ] Código formateado con Black
- [ ] Imports ordenados con isort
- [ ] Linting con flake8 (0 errores)
- [ ] Type checking con mypy (strict mode)
- [ ] 100% type hints
- [ ] Coverage >90% en tests
- [ ] Docstrings en todas las funciones públicas
- [ ] Sin dependencias externas
- [ ] Compatible Python 3.10+
- [ ] Compatible Asterisk 20, 21, 22
- [ ] Ejemplos funcionales
- [ ] Documentación completa
- [ ] GitHub Actions CI/CD
- [ ] CHANGELOG mantenido
- [ ] README completo

---

## ESTRUCTURA DE ENTREGAS

### Fase 1: Core (Semana 1-2)
- [ ] Manager base
- [ ] Message class
- [ ] AMI Protocol
- [ ] Tests básicos
- [ ] README

### Fase 2: Features (Semana 3-4)
- [ ] CallManager
- [ ] FastAGI Server
- [ ] Event handling
- [ ] Integration tests
- [ ] Ejemplos

### Fase 3: Polish (Semana 5)
- [ ] Documentación completa
- [ ] Performance tests
- [ ] CI/CD setup
- [ ] Release 1.0.0

---

## CONSIDERACIONES IMPORTANTES

1. **Cero Dependencias Externas:**
   - Solo usar librería estándar de Python
   - No usar: aiohttp, pydantic, requests, etc.
   - Razón: Máxima compatibilidad y mantenimiento

2. **Type Hints Estrictos:**
   - Usar `mypy --strict`
   - Todos los argumentos deben tener tipos
   - Documentar tipos complejos

3. **Error Handling Robusto:**
   - Excepciones personalizadas específicas
   - Mensajes de error descriptivos
   - Logging en puntos críticos

4. **Documentación de Producción:**
   - Ejemplos reales y funcionales
   - Guía de troubleshooting
   - Casos de uso comunes

5. **Compatibilidad Futura:**
   - Diseño modular para nuevas versiones
   - Configuración por versión de Asterisk
   - Arquitectura extensible

---

## NOTAS FINALES

Este proyecto debe ser:
✅ **Production-ready** desde el día 1
✅ **Moderno** (Python 3.10+, async/await, type hints)
✅ **Confiable** (manejo robusto de errores)
✅ **Documentado** (profesionalmente)
✅ **Mantenible** (código limpio y tests)
✅ **Compatible** (Asterisk 20-22+, Python 3.10+)

---

## CONTEXTO: Por qué reemplazar Panoramisk

Panoramisk está:
- 🔴 Abandonado (5 años sin actualizaciones)
- 🔴 Incompatible (Python 3.13+ rompe)
- 🔴 Buggy (bugs abiertos 8+ años)
- 🔴 Insostenible (sin mantenimiento)

Este proyecto es la solución moderna.