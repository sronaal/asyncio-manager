# Solución de problemas

## Error: ConnectionError

**Causas posibles:**
- Asterisk no está corriendo
- El puerto AMI no es accesible (firewall)
- Host o puerto incorrectos

**Solución:**
```bash
# Verificar que Asterisk está corriendo
systemctl status asterisk

# Verificar puerto AMI
netstat -tlnp | grep 5038

# Probar conexión TCP
nc -zv 127.0.0.1 5038
```

## Error: AuthenticationError

**Causas posibles:**
- Username o password incorrectos
- El usuario no está configurado en manager.conf

**Solución:**
Verificar `/etc/asterisk/manager.conf`:
```ini
[admin]
secret = password
read = all
write = all
```

## Error: TimeoutError

**Causas posibles:**
- Latencia de red alta
- Asterisk sobrecargado
- Timeout muy bajo

**Solución:**
```python
Manager(
    timeout=10.0,        # Aumentar timeout de acciones
    read_timeout=60.0,   # Aumentar timeout de lectura
    connect_timeout=30.0,# Aumentar timeout de conexión
)
```

## Error: DisconnectedError

**Causas posibles:**
- Se perdió la conexión con Asterisk
- Se llamó a `send_action` sin conectar primero

**Solución:**
```python
if manager.is_connected:
    response = await manager.send_action({"Action": "Ping"})
else:
    await manager.connect()
```

## El servidor FastAGI no acepta conexiones

**Causas posibles:**
- Puerto ocupado
- Firewall bloqueando

**Solución:**
```bash
# Verificar puerto
lsof -i :4574

# Probar con puerto diferente
server = FastAGIServer()
await server.start(port=4575)
```
