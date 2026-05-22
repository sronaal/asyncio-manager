"""Tests para el módulo ami_action.py."""

import asyncio

import pytest

from asyncio_manager.ami_action import Action
from asyncio_manager.message import Message


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestActionCreation:
    """Tests de creación de Action."""

    def test_action_creation(self):
        """Crear acción básica."""
        action = Action({"Action": "Ping"})
        assert action.action_id is not None
        assert action.headers["Action"] == "Ping"
        assert action.action_id == action.headers["ActionID"]

    def test_action_id_generated(self):
        """ActionID se genera automáticamente."""
        action = Action({"Action": "Ping"})
        assert len(action.action_id) > 0
        assert "-" in action.action_id

    def test_custom_action_id(self):
        """ActionID personalizado."""
        action = Action({"Action": "Ping"}, action_id="custom-001")
        assert action.action_id == "custom-001"

    def test_is_event_list_default(self):
        """Por defecto no es EventList."""
        action = Action({"Action": "Ping"})
        assert not action.is_event_list

    def test_is_event_list_true(self):
        """Modo EventList explícito."""
        action = Action({"Action": "QueueStatus"}, as_list=True)
        assert action.is_event_list

    def test_done_false_initially(self):
        """Acción no está completada inicialmente."""
        action = Action({"Action": "Ping"})
        assert not action.done


class TestActionLifecycle:
    """Tests del ciclo de vida de Action."""

    @pytest.mark.asyncio
    async def test_add_message_completes(self):
        """Agregar mensaje completa la acción."""
        action = Action({"Action": "Ping"})
        assert not action.done

        msg = Message({"Response": "Success", "ActionID": action.action_id})
        action.add_message(msg)

        assert action.done
        result = await action.wait()
        assert result.is_success

    @pytest.mark.asyncio
    async def test_wait_timeout(self):
        """wait lanza TimeoutError si no hay respuesta."""
        action = Action({"Action": "Ping"})

        with pytest.raises(Exception):
            await action.wait(timeout=0.1)

    @pytest.mark.asyncio
    async def test_set_exception(self):
        """set_exception propaga el error en wait."""
        action = Action({"Action": "Ping"})
        action.set_exception(RuntimeError("Test error"))

        with pytest.raises(RuntimeError, match="Test error"):
            await action.wait()

    @pytest.mark.asyncio
    async def test_cancel(self):
        """Cancelar la acción."""
        action = Action({"Action": "Ping"})
        action.cancel()
        assert action.done

    @pytest.mark.asyncio
    async def test_messages_list(self):
        """Lista de mensajes acumulados."""
        action = Action({"Action": "Ping"})
        msg1 = Message({"Response": "Success"})
        msg2 = Message({"Event": "SomeEvent"})

        action.add_message(msg1)
        action.add_message(msg2)

        assert len(action.messages) == 2


class TestActionEventList:
    """Tests de EventList en Action."""

    @pytest.mark.asyncio
    async def test_wait_all_collects_events(self):
        """wait_all recolecta todos los eventos de EventList."""
        action = Action({"Action": "QueueStatus"}, as_list=True)

        # Simular eventos intermedios
        action.add_message(Message({"Event": "QueueStatusEntry", "Queue": "support"}))
        action.add_message(Message({"Event": "QueueStatusEntry", "Queue": "sales"}))

        # Evento Complete
        complete = Message({"Event": "QueueStatusComplete", "ActionID": action.action_id})
        action.add_message(complete)

        # Esperar todos
        messages = await action.wait_all(timeout=1.0)
        assert len(messages) == 3
        assert messages[-1].is_complete_event

    @pytest.mark.asyncio
    async def test_wait_all_normal_mode(self):
        """En modo normal, wait_all retorna lista con única respuesta."""
        action = Action({"Action": "Ping"})
        msg = Message({"Response": "Success", "ActionID": action.action_id})
        action.add_message(msg)

        messages = await action.wait_all(timeout=1.0)
        assert len(messages) == 1
        assert messages[0].is_success


class TestActionSerialization:
    """Tests de serialización de Action."""

    def test_str_contains_action(self):
        """String de acción contiene Action: Ping."""
        action = Action({"Action": "Ping"})
        serialized = str(action)
        assert "Action: Ping" in serialized
        assert serialized.endswith("\r\n\r\n")

    def test_str_contains_action_id(self):
        """String contiene ActionID."""
        action = Action({"Action": "Ping"}, action_id="my-id")
        serialized = str(action)
        assert "ActionID: my-id" in serialized

    def test_multiline_value(self):
        """Valores multilínea serializados correctamente."""
        action = Action({"Action": "SetVar", "Variable": "VAR=val1\nVAR=val2"})
        serialized = str(action)
        assert "Variable: VAR=val1" in serialized
        assert "Variable: VAR=val2" in serialized
