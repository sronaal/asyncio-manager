# Changelog

## 1.0.0 (2024)

### Primera versión estable

- ✨ Manager con context manager (`async with`)
- ✨ Reconexión inteligente con backoff exponencial y jitter
- ✨ Timeouts configurables (connect, read, action)
- ✨ Autenticación MD5 challenge-response y plain text
- ✨ Eventos con patrones wildcard (`*`, `NewChannel`, `Queue*`)
- ✨ Action con composición (no herencia dual como Panoramisk)
- ✨ Soporte EventList (`send_action_and_wait_all`)
- ✨ CallManager con tracking de llamadas individuales
- ✨ FastAGI server (sin `asyncio.coroutine()` deprecado)
- ✨ CLI con argparse y `yaml.safe_load()`
- ✨ Cero dependencias externas
- ✨ Type hints completos (`mypy --strict`)
- ✨ Tests unitarios (90+ tests)
- ✨ Documentación en Markdown + Sphinx
- ✨ CI/CD con GitHub Actions (black, flake8, mypy, pytest)
