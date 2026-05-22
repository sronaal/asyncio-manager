# Instalación

## Requisitos

- Python 3.10 o superior
- Acceso a un servidor Asterisk con AMI habilitado

## Instalación desde PyPI

```bash
pip install asyncio-manager
```

## Instalación desde código fuente

```bash
git clone https://github.com/anomalyco/asyncio-manager.git
cd asyncio-manager
pip install -e .
```

## Instalación con dependencias de desarrollo

```bash
pip install -e ".[dev]"
```

Esto instala:
- `pytest` — Para ejecutar tests
- `pytest-asyncio` — Soporte async en tests
- `pytest-cov` — Cobertura de código
- `black` — Formateo de código
- `isort` — Orden de imports
- `flake8` — Linting
- `mypy` — Type checking

## Instalación con dependencias de documentación

```bash
pip install -e ".[docs]"
```

## Configuración de Asterisk

Para que asyncio-manager pueda conectarse, Asterisk debe tener el
manager habilitado en `manager.conf`:

```ini
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

[admin]
secret = password
read = all
write = all
```

## Verificar instalación

```python
from asyncio_manager import Manager
print(Manager.__module__)  # asyncio_manager.manager
```
