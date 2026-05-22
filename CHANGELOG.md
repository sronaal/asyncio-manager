# Changelog

## 1.0.0 (2025)

### First stable release

- ✨ Manager with context manager (`async with`)
- ✨ Smart reconnection with exponential backoff and jitter
- ✨ Configurable timeouts (connect, read, action)
- ✨ MD5 challenge-response and plain text authentication
- ✨ Event callbacks with wildcard patterns (`*`, `NewChannel`, `Queue*`)
- ✨ Action with composition pattern (no dual inheritance)
- ✨ EventList support (`send_action_and_wait_all`)
- ✨ CallManager with individual call tracking
- ✨ FastAGI server (no deprecated `asyncio.coroutine()`)
- ✨ CLI with argparse and `yaml.safe_load()`
- ✨ Zero external dependencies
- ✨ Full type hints (`mypy --strict`)
- ✨ 89+ unit tests
- ✨ Documentation in English and Spanish
- ✨ CI/CD with GitHub Actions (black, flake8, mypy, pytest)
