"""Fixtures compartidos para los tests de asyncio-manager.

Proporciona fixtures reutilizables sin mutación de estado global
(a diferencia de panoramisk, que mutaba ``utils.EOL``).
"""

import pytest


@pytest.fixture
def sample_headers():
    """Headers de ejemplo para pruebas."""
    return {
        "ActionID": "test-001",
        "Response": "Success",
        "Message": "Authentication accepted",
    }


@pytest.fixture
def sample_event():
    """Evento AMI de ejemplo para pruebas."""
    return (
        "Event: NewChannel\r\n"
        "Channel: SIP/100-00000001\r\n"
        "Uniqueid: 1234567890.1\r\n"
        "CallerIDNum: 5551234\r\n"
        "Exten: 200\r\n"
        "Context: from-internal\r\n"
        "\r\n"
    )


@pytest.fixture
def sample_response():
    """Respuesta AMI de ejemplo para pruebas."""
    return (
        "Response: Success\r\n"
        "ActionID: test-001\r\n"
        "Message: Action completed\r\n"
        "\r\n"
    )


@pytest.fixture
def sample_event_complete():
    """Evento de finalización de lista (EventList Complete)."""
    return (
        "Event: QueueStatusComplete\r\n"
        "ActionID: test-002\r\n"
        "\r\n"
    )
