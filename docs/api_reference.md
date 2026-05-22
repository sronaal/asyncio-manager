# Referencia de API

## Manager

### `Manager(host, port, username, secret, ...)`

Clase principal para conectar con Asterisk AMI.

**Parámetros:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `host` | `str` | `127.0.0.1` | Host de Asterisk |
| `port` | `int` | `5038` | Puerto AMI |
| `username` | `str` | `""` | Usuario AMI |
| `secret` | `str` | `""` | Contraseña AMI |
| `timeout` | `float` | `5.0` | Timeout de acciones |
| `read_timeout` | `float` | `30.0` | Timeout de lectura |
| `connect_timeout` | `float` | `10.0` | Timeout de conexión |
| `ssl` | `bool` | `False` | Usar SSL/TLS |
| `ssl_verify` | `bool` | `True` | Verificar SSL |
| `encoding` | `str` | `utf-8` | Codificación |
| `ping_interval` | `float` | `10.0` | Intervalo de Ping |
| `reconnect_config` | `ReconnectionConfig` | `None` | Config de reconexión |
| `config` | `ManagerConfig` | `None` | Config completa |

**Métodos:**

- `async connect()` — Conecta y autentica
- `async close()` — Cierra conexión
- `async send_action(action, timeout, as_list)` — Envía acción
- `async send_action_and_wait_all(action, timeout)` — Envía acción y espera EventList
- `async originate(channel, exten, ...)` — Helper para originar llamadas
- `async command(command_line)` — Ejecuta comando CLI
- `register_event(pattern)` — Decorador para eventos

## Message

### `Message(headers, content)`

Mensaje AMI (evento o respuesta).

**Propiedades:**

- `is_response` — ¿Es respuesta?
- `is_event` — ¿Es evento?
- `is_success` — ¿Fue exitoso?
- `action_id` — ID de acción
- `event_type` — Tipo de evento
- `message` — Mensaje de texto
- `content` — Contenido multilínea
- `is_complete_event` — ¿Es evento *Complete?

**Métodos:**

- `get_multiline(key)` — Obtener valor multilínea
- `from_line(data)` — Parsear desde texto AMI

## CallManager

### `CallManager(host, port, username, secret, ...)`

Gestor de llamadas.

**Métodos:**

- `async originate(channel, exten, ...)` — Originar llamada
- `get_call(uniqueid)` — Obtener Call por ID
- `clean_originate(uniqueid)` — Limpiar llamada
- `cleanup_stale_calls(max_age)` — Limpiar llamadas viejas
- `active_calls` — Lista de llamadas activas

## Call

### `Call(uniqueid, channel, manager)`

Representa una llamada activa.

**Propiedades:**

- `id` — ID de la llamada
- `age` — Tiempo desde creación

**Métodos:**

- `async wait_for_answer(timeout)` — Esperar respuesta
- `async wait_for_hangup(timeout)` — Esperar cuelgue
- `async transfer(exten, context)` — Transferir
- `async hangup()` — Colgar

## FastAGIServer

### `FastAGIServer(host, port, buffer_size)`

Servidor FastAGI.

**Métodos:**

- `add_script(path, handler)` — Registrar script
- `remove_script(path)` — Eliminar script
- `async start(host, port)` — Iniciar servidor
- `async stop()` — Detener servidor

## Request

### `Request(reader, writer, headers)`

Solicitud FastAGI entrante.

**Propiedades:**

- `headers` — Headers AGI
- `channel` — Canal de la llamada
- `caller_id` — Caller ID
- `extension` — Extensión

**Métodos:**

- `async send_command(command)` — Enviar comando AGI
- `async answer()` — Responder llamada
- `async hangup()` — Colgar
- `async say_digits(digits)` — Decir dígitos
- `async say_number(number)` — Decir número
- `async get_data(prompt, timeout, max_digits)` — Obtener datos
- `async stream_file(filename, escape_digits)` — Reproducir audio
- `async set_variable(name, value)` — Fijar variable
- `async get_variable(name)` — Obtener variable
- `async exec_(app, *args)` — Ejecutar aplicación
