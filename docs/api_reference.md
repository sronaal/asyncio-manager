# API Reference

## Manager

### `Manager(host, port, username, secret, ...)`

Main class for connecting to Asterisk AMI.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `host` | `str` | `127.0.0.1` | Asterisk host |
| `port` | `int` | `5038` | AMI port |
| `username` | `str` | `""` | AMI username |
| `secret` | `str` | `""` | AMI password |
| `timeout` | `float` | `5.0` | Action timeout (seconds) |
| `read_timeout` | `float` | `30.0` | Read timeout (seconds) |
| `connect_timeout` | `float` | `10.0` | Connection timeout (seconds) |
| `ssl` | `bool` | `False` | Enable SSL/TLS |
| `ssl_verify` | `bool` | `True` | Verify SSL certificate |
| `encoding` | `str` | `utf-8` | Message encoding |
| `ping_interval` | `float` | `10.0` | Keep-alive interval (seconds) |
| `reconnect_config` | `ReconnectionConfig` | `None` | Reconnection settings |
| `config` | `ManagerConfig` | `None` | Full config object |

**Methods:**

- `async connect()` — Connect and authenticate
- `async close()` — Close connection
- `async send_action(action, timeout, as_list)` — Send AMI action
- `async send_action_and_wait_all(action, timeout)` — Send action and collect EventList
- `async originate(channel, exten, ...)` — Helper for call origination
- `async command(command_line)` — Execute Asterisk CLI command
- `register_event(pattern)` — Decorator for event callbacks

## Message

### `Message(headers, content)`

AMI message (event or response).

**Properties:**

- `is_response` — Is this a response?
- `is_event` — Is this an event?
- `is_success` — Was the action successful?
- `action_id` — Correlated action ID
- `event_type` — Event type (e.g. NewChannel)
- `message` — Text message
- `content` — Multi-line content
- `is_complete_event` — Is this a `*Complete` event?

**Methods:**

- `get_multiline(key)` — Get multi-line value
- `from_line(data)` — Parse from AMI wire format

## CallManager

### `CallManager(host, port, username, secret, ...)`

Call lifecycle manager.

**Methods:**

- `async originate(channel, exten, ...)` — Originate a call
- `get_call(uniqueid)` — Get Call by ID
- `clean_originate(uniqueid)` — Remove call from tracking
- `cleanup_stale_calls(max_age)` — Clean old calls
- `active_calls` — List of active calls

## Call

### `Call(uniqueid, channel, manager)`

Represents an active call.

**Properties:**

- `id` — Call ID
- `age` — Time since creation

**Methods:**

- `async wait_for_answer(timeout)` — Wait for answer
- `async wait_for_hangup(timeout)` — Wait for hangup
- `async transfer(exten, context)` — Transfer call
- `async hangup()` — Hang up call

## FastAGIServer

### `FastAGIServer(host, port, buffer_size)`

Async FastAGI server.

**Methods:**

- `add_script(path, handler)` — Register AGI script handler
- `remove_script(path)` — Remove script handler
- `async start(host, port)` — Start server
- `async stop()` — Stop server

## Request

### `Request(reader, writer, headers)`

FastAGI incoming request.

**Properties:**

- `headers` — AGI headers (channel variables)
- `channel` — Channel name
- `caller_id` — Caller ID
- `extension` — Extension

**Methods:**

- `async send_command(command)` — Send AGI command
- `async answer()` — Answer the call
- `async hangup()` — Hang up
- `async say_digits(digits)` — Say digits
- `async say_number(number)` — Say number
- `async get_data(prompt, timeout, max_digits)` — Get user input
- `async stream_file(filename, escape_digits)` — Play audio file
- `async set_variable(name, value)` — Set channel variable
- `async get_variable(name)` — Get channel variable
- `async exec_(app, *args)` — Execute Asterisk application
