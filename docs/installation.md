# Installation

## Requirements

- Python 3.10 or higher
- Access to an Asterisk server with AMI enabled

## Install from PyPI

```bash
pip install asyncio-manager
```

## Install from source

```bash
git clone https://github.com/sronaal/asyncio-manager.git
cd asyncio-manager
pip install -e .
```

## Install with dev dependencies

```bash
pip install -e ".[dev]"
```

This installs:
- `pytest` — Run tests
- `pytest-asyncio` — Async test support
- `pytest-cov` — Code coverage
- `black` — Code formatting
- `isort` — Import sorting
- `flake8` — Linting
- `mypy` — Type checking

## Install with docs dependencies

```bash
pip install -e ".[docs]"
```

## Asterisk Configuration

Add the following to `/etc/asterisk/manager.conf`:

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

## Verify installation

```bash
python -c "from asyncio_manager import Manager; print('OK')"
```
