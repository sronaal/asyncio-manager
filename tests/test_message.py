"""Tests para el módulo message.py."""

import pytest

from asyncio_manager.message import Message


class TestMessageCreation:
    """Tests de creación y propiedades básicas de Message."""

    def test_from_line_event(self, sample_event):
        """Crea un Message desde un evento AMI."""
        msg = Message.from_line(sample_event)
        assert msg.is_event
        assert not msg.is_response
        assert msg.event_type == "NewChannel"
        assert msg["Channel"] == "SIP/100-00000001"
        assert msg["Uniqueid"] == "1234567890.1"

    def test_from_line_response(self, sample_response):
        """Crea un Message desde una respuesta AMI."""
        msg = Message.from_line(sample_response)
        assert not msg.is_event
        assert msg.is_response
        assert msg.action_id == "test-001"
        assert msg.is_success

    def test_from_line_empty_returns_valid(self):
        """from_line nunca retorna None (bug de panoramisk corregido)."""
        msg = Message.from_line("")
        assert msg is not None
        assert isinstance(msg, Message)
        assert len(msg) == 0

    def test_from_line_no_event_or_response(self):
        """Mensaje sin Event ni Response sigue siendo Message válido."""
        raw = "Key1: Value1\r\nKey2: Value2\r\n\r\n"
        msg = Message.from_line(raw)
        assert msg is not None
        assert not msg.is_event
        assert not msg.is_response

    def test_case_insensitive_access(self, sample_event):
        """Acceso case-insensitive a los headers."""
        msg = Message.from_line(sample_event)
        assert msg["channel"] == "SIP/100-00000001"
        assert msg["CHANNEL"] == "SIP/100-00000001"
        assert msg["UniqueID"] == "1234567890.1"

    def test_has_body_follows(self):
        """Mensaje con Response: Follows tiene contenido."""
        raw = (
            "Response: Follows\r\n"
            "ActionID: test-003\r\n"
            "\r\n"
            "Privilege: Command\r\n"
            "Content line 1\r\n"
            "Content line 2\r\n"
        )
        msg = Message.from_line(raw)
        assert msg.is_response
        assert msg.is_success
        assert len(msg.content) > 0

    def test_complete_event_detection(self, sample_event_complete):
        """Detección de eventos *Complete."""
        msg = Message.from_line(sample_event_complete)
        assert msg.is_event
        assert msg.is_complete_event

    def test_non_complete_event(self, sample_event):
        """Evento normal NO es complete."""
        msg = Message.from_line(sample_event)
        assert msg.is_event
        assert not msg.is_complete_event


class TestMessageProperties:
    """Tests de las propiedades de Message."""

    def test_is_success_event(self):
        """Eventos siempre son success."""
        msg = Message({"Event": "NewChannel"})
        assert msg.is_success

    def test_is_success_response_success(self):
        """Response: Success es success."""
        msg = Message({"Response": "Success"})
        assert msg.is_success

    def test_is_success_response_error(self):
        """Response: Error no es success."""
        msg = Message({"Response": "Error"})
        assert not msg.is_success

    def test_action_id_present(self):
        """Extrae ActionID correctamente."""
        msg = Message({"ActionID": "custom-123", "Response": "Success"})
        assert msg.action_id == "custom-123"

    def test_action_id_none(self):
        """Message sin ActionID retorna None."""
        msg = Message({"Response": "Success"})
        assert msg.action_id is None

    def test_get_multiline(self):
        """Obtener valores multilínea."""
        msg = Message({"Data": "line1\nline2\nline3"})
        lines = msg.get_multiline("Data")
        assert len(lines) == 3
        assert lines[0] == "line1"

    def test_get_multiline_missing(self):
        """Clave inexistente retorna lista vacía."""
        msg = Message({"Response": "Success"})
        assert msg.get_multiline("Nope") == []

    def test_repr(self):
        """Representación del mensaje."""
        msg = Message({"Event": "TestEvent"})
        rep = repr(msg)
        assert "TestEvent" in rep


class TestMessageEdgeCases:
    """Tests de casos borde."""

    def test_multiline_values_in_headers(self):
        """Headers con valores multilínea (continuación con espacio)."""
        raw = "Variable: VAR1=value1\n Variable: VAR2=value2\r\n\r\n"
        msg = Message.from_line(raw)
        assert msg is not None

    def test_unicode_content(self):
        """Contenido Unicode en los valores."""
        msg = Message({"CallerIDName": "José Pérez"})
        assert msg["CallerIDName"] == "José Pérez"

    def test_many_headers(self):
        """Mensaje con muchos headers."""
        headers = {f"Key{i}": f"Value{i}" for i in range(100)}
        headers["Event"] = "TestEvent"
        msg = Message(headers)
        assert msg.event_type == "TestEvent"
        assert len(msg) == 101

    def test_empty_headers(self):
        """Message sin headers."""
        msg = Message({})
        assert not msg.is_event
        assert not msg.is_response
        assert msg.action_id is None

    def test_from_line_with_content(self):
        """Mensaje con contenido posterior (respuesta Command)."""
        raw = (
            "Response: Success\r\n"
            "ActionID: test-cmd\r\n"
            "Message: Command output follows\r\n"
            "\r\n"
            "SIP/100-00000001\r\n"
            "SIP/200-00000002\r\n"
        )
        msg = Message.from_line(raw)
        assert len(msg.content) == 2
        assert "SIP/100" in msg.content[0]
