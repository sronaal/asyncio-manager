# Troubleshooting

## ConnectionError

**Possible causes:**
- Asterisk is not running
- AMI port is not accessible (firewall)
- Wrong host or port

**Solution:**
```bash
# Verify Asterisk is running
systemctl status asterisk

# Check AMI port
netstat -tlnp | grep 5038

# Test TCP connection
nc -zv 127.0.0.1 5038
```

## AuthenticationError

**Possible causes:**
- Wrong username or password
- User not configured in manager.conf

**Solution:**
Verify `/etc/asterisk/manager.conf`:
```ini
[admin]
secret = password
read = all
write = all
```

## TimeoutError

**Possible causes:**
- High network latency
- Overloaded Asterisk server
- Timeout set too low

**Solution:**
```python
Manager(
    timeout=10.0,        # Increase action timeout
    read_timeout=60.0,   # Increase read timeout
    connect_timeout=30.0,# Increase connect timeout
)
```

## DisconnectedError

**Possible causes:**
- Lost connection to Asterisk
- Calling `send_action` without connecting first

**Solution:**
```python
if manager.is_connected:
    response = await manager.send_action({"Action": "Ping"})
else:
    await manager.connect()
```

## FastAGI server won't start

**Possible causes:**
- Port already in use
- Firewall blocking

**Solution:**
```bash
# Check port
lsof -i :4574

# Try a different port
server = FastAGIServer()
await server.start(port=4575)
```

## Running tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
