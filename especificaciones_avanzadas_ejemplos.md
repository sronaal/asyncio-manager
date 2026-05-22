# 📚 ESPECIFICACIONES AVANZADAS Y EJEMPLOS

## TABLA DE CONTENIDOS
1. Casos de uso avanzados
2. Problemas específicos a resolver
3. Benchmarks de rendimiento esperados
4. Compatibilidad con diferentes entornos
5. Estrategia de testing

---

## 1. CASOS DE USO AVANZADOS REQUERIDOS

### Caso 1: Centro de Contactos (Contact Center)

```python
"""
Escenario: Sistema que maneja 1000+ llamadas simultáneas
"""

import asyncio
from asyncio_manager import Manager, logger

class ContactCenter:
    def __init__(self):
        self.manager: Manager = None
        self.calls: Dict[str, Call] = {}
        self.queue_stats: Dict[str, int] = {}
    
    async def initialize(self):
        """Inicializa el sistema"""
        self.manager = Manager(
            host='asterisk.example.com',
            username='cc_system',
            secret='secure_password',
            timeout=5.0,
            read_timeout=15.0,
            connect_timeout=10.0,
        )
        
        await self.manager.connect()
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Configura listeners de eventos"""
        
        @self.manager.register_event('NewChannel')
        async def on_new_channel(msg):
            """Cuando hay nueva llamada"""
            channel = msg.get('Channel')
            caller_id = msg.get('CallerIDNum')
            
            logger.info(f"Nueva llamada: {channel} ({caller_id})")
            
            # Guardar en registro
            self.calls[channel] = {
                'caller_id': caller_id,
                'started_at': asyncio.get_event_loop().time(),
                'state': 'ringing',
            }
        
        @self.manager.register_event('VarSet')
        async def on_var_set(msg):
            """Variables cambian (ej: queue assignment)"""
            channel = msg.get('Channel')
            var_name = msg.get('Variable')
            var_value = msg.get('Value')
            
            if channel in self.calls:
                self.calls[channel]['last_var'] = {
                    'name': var_name,
                    'value': var_value,
                }
        
        @self.manager.register_event('BridgeCreate')
        async def on_bridge(msg):
            """Cuando se conectan llamadas"""
            channel1 = msg.get('Channel1')
            channel2 = msg.get('Channel2')
            
            logger.info(f"Llamadas conectadas: {channel1} <-> {channel2}")
            
            if channel1 in self.calls:
                self.calls[channel1]['state'] = 'connected'
            if channel2 in self.calls:
                self.calls[channel2]['state'] = 'connected'
        
        @self.manager.register_event('Hangup')
        async def on_hangup(msg):
            """Cuando se cuelga"""
            channel = msg.get('Channel')
            cause = msg.get('Cause')
            
            if channel in self.calls:
                duration = (
                    asyncio.get_event_loop().time() - 
                    self.calls[channel]['started_at']
                )
                logger.info(
                    f"Cuelgue: {channel} después de {duration:.1f}s "
                    f"(causa: {cause})"
                )
                del self.calls[channel]
    
    async def get_queue_stats(self, queue_name: str):
        """Obtiene estadísticas de cola"""
        response = await self.manager.send_action({
            'Action': 'QueueStatus',
            'Queue': queue_name,
        })
        
        return {
            'members': response.get('Members'),
            'calls': response.get('Calls'),
            'hold_time': response.get('HoldTime'),
        }
    
    async def transfer_call(
        self,
        channel: str,
        exten: str,
        context: str = 'default',
    ):
        """Transfiere llamada"""
        response = await self.manager.send_action({
            'Action': 'Redirect',
            'Channel': channel,
            'Exten': exten,
            'Context': context,
            'Priority': 1,
        })
        
        return response.is_success
    
    async def monitor_queue(self, queue_name: str):
        """Monitorea cola continuamente"""
        while True:
            try:
                stats = await self.get_queue_stats(queue_name)
                logger.info(
                    f"Cola {queue_name}: "
                    f"{stats['members']} agentes, "
                    f"{stats['calls']} llamadas"
                )
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error monitoreando: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        """Ejecuta el sistema"""
        try:
            await self.initialize()
            
            # Monitorear colas en paralelo
            tasks = [
                self.monitor_queue('support'),
                self.monitor_queue('sales'),
                self.monitor_queue('billing'),
            ]
            
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            logger.info("Cerrando...")
            await self.manager.close()

# Uso
if __name__ == '__main__':
    cc = ContactCenter()
    asyncio.run(cc.run())
```

### Caso 2: IVR Dinámico

```python
"""
Escenario: Sistema IVR que atiende llamadas y las enruta
"""

from asyncio_manager import FastAGIServer, logger

class DynamicIVR:
    def __init__(self):
        self.server = FastAGIServer()
        self.server.add_script('main_menu', self.handle_main_menu)
        self.server.add_script('sales', self.handle_sales)
        self.server.add_script('support', self.handle_support)
    
    async def handle_main_menu(self, request):
        """Menú principal"""
        logger.info(f"IVR: {request.headers.get('agi_channel')}")
        
        await request.answer()
        
        # Reproducir bienvenida
        await request.send_command('SAY DIGITS 1')  # Bienvenido
        
        # Mostrar opciones
        await request.send_command('SAY DIGITS 1')  # Opción 1
        await request.send_command('SAY DIGITS 2')  # Opción 2
        
        # Obtener entrada
        result = await request.send_command(
            'GET DATA welcome 5000 2'
        )
        
        if result == '1':
            # Transferir a ventas
            await request.send_command(
                'EXEC Goto sales,s,1'
            )
        elif result == '2':
            # Transferir a soporte
            await request.send_command(
                'EXEC Goto support,s,1'
            )
        else:
            await request.hangup()
    
    async def handle_sales(self, request):
        """Menú de ventas"""
        await request.answer()
        await request.send_command('SAY DIGITS 3')  # Vendedor
        # ... lógica de ventas
    
    async def handle_support(self, request):
        """Menú de soporte"""
        await request.answer()
        await request.send_command('SAY DIGITS 4')  # Técnico
        # ... lógica de soporte
    
    async def run(self):
        """Inicia servidor"""
        await self.server.start(host='0.0.0.0', port=4574)
        logger.info("IVR escuchando en 0.0.0.0:4574")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await self.server.stop()

if __name__ == '__main__':
    ivr = DynamicIVR()
    asyncio.run(ivr.run())
```

### Caso 3: Monitor de Llamadas en Tiempo Real

```python
"""
Escenario: Dashboard que muestra llamadas activas
"""

import asyncio
from asyncio_manager import Manager, logger

class CallMonitor:
    def __init__(self):
        self.manager: Manager = None
        self.active_calls: Dict = {}
        self.history: List = []
    
    async def initialize(self):
        self.manager = Manager(
            host='asterisk.local',
            username='monitor',
            secret='password',
        )
        
        await self.manager.connect()
        self._register_listeners()
    
    def _register_listeners(self):
        @self.manager.register_event('NewChannel')
        async def on_new(msg):
            call_id = msg.get('Channel')
            self.active_calls[call_id] = {
                'started': asyncio.get_event_loop().time(),
                'caller': msg.get('CallerIDNum'),
                'exten': msg.get('Exten'),
            }
            await self._broadcast_update()
        
        @self.manager.register_event('Hangup')
        async def on_hangup(msg):
            call_id = msg.get('Channel')
            if call_id in self.active_calls:
                duration = (
                    asyncio.get_event_loop().time() - 
                    self.active_calls[call_id]['started']
                )
                
                self.history.append({
                    'channel': call_id,
                    'duration': duration,
                    'timestamp': asyncio.get_event_loop().time(),
                })
                
                del self.active_calls[call_id]
                await self._broadcast_update()
    
    async def _broadcast_update(self):
        """Aquí se enviaría a WebSocket, etc"""
        logger.info(
            f"Llamadas activas: {len(self.active_calls)}"
        )
    
    async def get_stats(self):
        """Retorna estadísticas"""
        return {
            'active': len(self.active_calls),
            'total_today': len(self.history),
            'avg_duration': (
                sum(c['duration'] for c in self.history) / 
                len(self.history) 
                if self.history else 0
            ),
        }

if __name__ == '__main__':
    monitor = CallMonitor()
    asyncio.run(monitor.initialize())
```

---

## 2. PROBLEMAS ESPECÍFICOS A RESOLVER

### Problema A: Latencia de Red Alta

**Escenario:**
```
Servidor Asterisk en Bogotá
Cliente asyncio-manager en Madrid
Latencia: 150-200ms
```

**Solución implementada:**

```python
class Manager:
    def __init__(
        self,
        host: str,
        username: str,
        secret: str,
        # ← PARÁMETROS CLAVE
        read_timeout: float = 30.0,      # Esperar respuesta completa
        socket_buffer_size: int = 65536,  # Buffer para datos
        validate_complete: bool = True,   # Validar integridad
    ):
        pass

class AMIProtocol:
    async def read_message(self) -> Message:
        """
        Lee mensaje COMPLETO del AMI
        
        Con latencia alta, los mensajes pueden llegar fragmentados:
        - Primer fragmento llega en 50ms
        - Segundo fragmento llega en 100ms
        - Tercero en 150ms
        
        Este método espera recibir el mensaje COMPLETO.
        """
        buffer = bytearray()
        
        while True:
            # Leer con timeout adaptativo
            try:
                chunk = await asyncio.wait_for(
                    self.reader.read(4096),
                    timeout=self.read_timeout,
                )
                
                if not chunk:
                    raise ConnectionError("Conexión cerrada")
                
                buffer.extend(chunk)
                
                # Verificar si tenemos mensaje completo
                if self._is_message_complete(buffer):
                    return self._parse_message(buffer)
                    
            except asyncio.TimeoutError:
                if buffer:
                    # Tenemos datos pero incompleto
                    logger.warning(
                        "Mensaje incompleto después de "
                        f"{self.read_timeout}s"
                    )
                    raise ProtocolError("Mensaje incompleto")
                raise
    
    def _is_message_complete(self, buffer: bytearray) -> bool:
        """
        Verifica si mensaje está completo
        
        Patrón AMI: Los mensajes terminan con línea vacía
        "\r\n\r\n"
        """
        return buffer.endswith(b'\r\n\r\n')
```

### Problema B: Reconexión Inteligente

**Problema original:**
```
Asterisk cae:
│
└─→ Panoramisk intenta reconectar INFINITAMENTE
    ├─ Attempt 1: FALLA
    ├─ Attempt 2: FALLA  ← Loop infinito
    ├─ Attempt 3: FALLA
    └─ ... por siempre ...
```

**Solución:**

```python
@dataclass
class ReconnectionConfig:
    max_attempts: int = 10
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

class Manager:
    async def _reconnect_with_backoff(self):
        """
        Reconecta con backoff exponencial y límite
        
        Sequence:
        Attempt 1: Wait 1s    ← initial_delay
        Attempt 2: Wait 2s    ← 1 * 2^1
        Attempt 3: Wait 4s    ← 1 * 2^2
        Attempt 4: Wait 8s
        Attempt 5: Wait 16s
        Attempt 6: Wait 32s
        Attempt 7: Wait 60s   ← capped at max_delay
        Attempt 8: Wait 60s
        Attempt 9: Wait 60s
        Attempt 10: Wait 60s
        Attempt 11: GIVE UP   ← max_attempts excedido
        """
        
        config = self.reconnect_config
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                logger.info(f"Reintentando conexión (intento {attempt})")
                await self.connect()
                logger.info("Reconexión exitosa")
                return
                
            except Exception as e:
                if attempt >= config.max_attempts:
                    logger.error(
                        f"Máximo de intentos ({config.max_attempts}) "
                        f"excedido. Abandonando."
                    )
                    raise
                
                # Calcular delay
                delay = min(
                    config.initial_delay * (config.exponential_base ** (attempt - 1)),
                    config.max_delay,
                )
                
                # Agregar jitter (±20%)
                if config.jitter:
                    jitter = delay * 0.2 * (random.random() * 2 - 1)
                    delay = max(0.1, delay + jitter)
                
                logger.warning(
                    f"Conexión falló: {e}. "
                    f"Reintentando en {delay:.1f}s"
                )
                
                await asyncio.sleep(delay)
```

### Problema C: Manejo de Errores Específicos

```python
# exceptions.py

class AsyncioManagerError(Exception):
    """Error base"""
    pass

class ConnectionError(AsyncioManagerError):
    """No puede conectar a Asterisk"""
    pass

class AuthenticationError(AsyncioManagerError):
    """Credenciales inválidas"""
    pass

class TimeoutError(AsyncioManagerError):
    """Operación excedió timeout"""
    pass

class ProtocolError(AsyncioManagerError):
    """Problema en protocolo AMI"""
    pass

class DisconnectedError(AsyncioManagerError):
    """Manager no está conectado"""
    pass

# manager.py
class Manager:
    async def send_action(self, action: Dict) -> Message:
        if not self._connected:
            raise DisconnectedError("Manager no conectado")
        
        try:
            response = await asyncio.wait_for(
                self._send_and_wait(action),
                timeout=self.timeout,
            )
            
            if response.is_success:
                return response
            else:
                # Error en acción
                raise ActionError(
                    f"Acción falló: {response.message}"
                )
                
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Acción no respondió en {self.timeout}s"
            )
```

---

## 3. BENCHMARKS DE RENDIMIENTO ESPERADOS

### Test 1: Throughput de Acciones

```python
@pytest.mark.asyncio
async def test_action_throughput():
    """
    Esperado: ≥100 acciones/segundo
    (Dependiendo de Asterisk)
    """
    
    async with Manager(...) as mgr:
        await mgr.connect()
        
        start = time.time()
        count = 0
        
        for i in range(1000):
            try:
                response = await mgr.send_action({
                    'Action': 'Ping',
                })
                if response.is_success:
                    count += 1
            except:
                pass
        
        elapsed = time.time() - start
        throughput = count / elapsed
        
        print(f"Throughput: {throughput:.1f} actions/sec")
        assert throughput >= 100, f"Bajo throughput: {throughput}"
```

### Test 2: Manejo de Concurrencia

```python
@pytest.mark.asyncio
async def test_concurrent_actions():
    """
    Esperado: Manejar 100+ acciones simultáneas
    """
    
    async with Manager(...) as mgr:
        await mgr.connect()
        
        # Lanzar 100 acciones concurrentes
        tasks = [
            mgr.send_action({'Action': 'Ping'})
            for _ in range(100)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verificar que la mayoría fueron exitosas
        successes = sum(
            1 for r in results 
            if isinstance(r, Message) and r.is_success
        )
        
        assert successes >= 90, f"Solo {successes}/100 exitosas"
```

### Test 3: Uso de Memoria

```python
import tracemalloc

@pytest.mark.asyncio
async def test_memory_usage():
    """
    Esperado: <100MB en operación normal
    """
    
    tracemalloc.start()
    
    async with Manager(...) as mgr:
        await mgr.connect()
        
        # Simular 1 hora de operación
        for i in range(3600):
            await mgr.send_action({'Action': 'Ping'})
            if i % 100 == 0:
                current, peak = tracemalloc.get_traced_memory()
                print(f"Memory: {current / 1024 / 1024:.1f} MB")
    
    current, peak = tracemalloc.get_traced_memory()
    assert peak < 100_000_000, f"Pico: {peak / 1024 / 1024:.1f} MB"
```

---

## 4. COMPATIBILIDAD CON DIFERENTES ENTORNOS

### Entorno 1: Docker + Kubernetes

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY asyncio_manager/ ./asyncio_manager/
COPY examples/ ./examples/

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "asyncio_manager.examples.listener"]
```

### Entorno 2: Cloud (AWS, Azure, GCP)

```python
# Soporte para variables de entorno

import os
from asyncio_manager import Manager

config = {
    'host': os.getenv('ASTERISK_HOST', '127.0.0.1'),
    'port': int(os.getenv('ASTERISK_PORT', 5038)),
    'username': os.getenv('ASTERISK_USER'),
    'secret': os.getenv('ASTERISK_SECRET'),
    'ssl': os.getenv('ASTERISK_SSL', 'false').lower() == 'true',
    'ssl_verify': os.getenv('ASTERISK_SSL_VERIFY', 'true').lower() == 'true',
}

async with Manager(**config) as mgr:
    await mgr.connect()
```

### Entorno 3: Testing/Mocking

```python
# Soporte para mocking de Asterisk

from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    """Test sin necesidad de Asterisk real"""
    
    with patch('asyncio_manager.manager.AMIProtocol') as mock_protocol:
        mock_protocol.return_value.read_message = AsyncMock()
        mock_protocol.return_value.read_message.return_value = Message({
            'Response': 'Success',
            'Message': 'Authentication accepted',
        })
        
        manager = Manager(...)
        await manager.connect()
        
        assert manager.is_connected
```

---

## 5. ESTRATEGIA DE TESTING

### Unit Tests por Módulo

```
tests/
├── test_manager.py           (30+ tests)
│   ├── test_connect
│   ├── test_disconnect
│   ├── test_send_action
│   ├── test_register_event
│   ├── test_timeouts
│   ├── test_reconnection
│   └── ...
│
├── test_message.py           (15+ tests)
│   ├── test_case_insensitive
│   ├── test_multiline
│   ├── test_properties
│   └── ...
│
├── test_protocol.py          (20+ tests)
│   ├── test_message_parsing
│   ├── test_incomplete_messages
│   ├── test_invalid_data
│   └── ...
│
├── test_call_manager.py      (20+ tests)
│   ├── test_originate
│   ├── test_wait_for_answer
│   ├── test_transfer
│   └── ...
│
├── test_fast_agi.py          (15+ tests)
│   ├── test_server_start
│   ├── test_script_execution
│   ├── test_agi_commands
│   └── ...
│
├── test_integration.py       (25+ tests)
│   ├── test_full_call_flow
│   ├── test_concurrent_calls
│   ├── test_high_latency
│   ├── test_reconnection_recovery
│   └── ...
│
└── test_performance.py       (10+ tests)
    ├── test_throughput
    ├── test_memory
    ├── test_cpu_usage
    └── ...
```

### Coverage Requerida

```
Mínimo: 90%
Objetivo: 95%+

Por módulo:
- manager.py:          95%+
- protocol.py:         95%+
- message.py:          100%
- exceptions.py:       100%
- call_manager.py:     90%+
```

### CI/CD Pipeline

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Lint with flake8
        run: flake8 asyncio_manager tests
      
      - name: Type check with mypy
        run: mypy asyncio_manager --strict
      
      - name: Format check with black
        run: black --check asyncio_manager tests
      
      - name: Run tests
        run: pytest --cov=asyncio_manager --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

---

## COMPATIBILIDAD ASTERISK: Tabla Detallada

```
Versión    Lanzada      EOL          Estado         Prioridad
─────────────────────────────────────────────────────────────
18.x       2020-10      2023-10      EOL            Legacy ⚠️
19.x       2021-10      2022-10      EOL            Legacy ⚠️
20.x       2022-12      2025-12      Soportada      ✅ ALTA
21.x       2023-10      2026-10      Soportada      ✅ ALTA
22.x       2024-10      2027-10      Soportada      ✅ ALTA
23.x       2025-10?     2028-10?     Planeada       📋 MEDIA
24.x       2026-10?     2029-10?     Futura         📋 BAJA
```

---

## CONCLUSIÓN

Este prompt proporciona:
1. ✅ Especificaciones completas y detalladas
2. ✅ Ejemplos reales de código
3. ✅ Problemas específicos a resolver
4. ✅ Requisitos de testing
5. ✅ Benchmarks de rendimiento
6. ✅ Estrategia de CI/CD

Resultado esperado: **Librería producción-lista, moderna y mantenible**