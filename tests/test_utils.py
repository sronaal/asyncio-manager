"""Tests para el módulo utils.py."""

import pytest

from asyncio_manager.exceptions import (
    AGIAppError,
    AGIDeadChannelError,
    AGIInvalidCommand,
    AGINoResultError,
    AGIResultHangup,
    AGIUnknownError,
    AGIUsageError,
)
from asyncio_manager.utils import (
    CaseInsensitiveDict,
    IdGenerator,
    ReconnectionConfig,
    calculate_delay,
    parse_agi_result,
)


class TestCaseInsensitiveDict:
    """Tests de CaseInsensitiveDict."""

    def test_basic_access(self):
        d = CaseInsensitiveDict({"Content-Type": "text/plain"})
        assert d["content-type"] == "text/plain"
        assert d["CONTENT-TYPE"] == "text/plain"

    def test_set_and_get(self):
        d = CaseInsensitiveDict()
        d["Test"] = "value"
        assert d["test"] == "value"
        assert d["TEST"] == "value"

    def test_del(self):
        d = CaseInsensitiveDict({"Key": "value"})
        del d["key"]
        assert len(d) == 0

    def test_iter_keys(self):
        d = CaseInsensitiveDict({"Key1": "v1", "Key2": "v2"})
        keys = list(d.keys())
        assert "Key1" in keys
        assert "Key2" in keys

    def test_len(self):
        d = CaseInsensitiveDict({"A": "1", "B": "2", "C": "3"})
        assert len(d) == 3

    def test_copy(self):
        d = CaseInsensitiveDict({"Key": "value"})
        d2 = d.copy()
        assert d2["key"] == "value"
        d2["Key"] = "changed"
        assert d["Key"] == "value"  # original unchanged

    def test_from_keys(self):
        d = CaseInsensitiveDict.from_keys(["a", "b", "c"], value=0)
        assert d["A"] == 0
        assert d["B"] == 0
        assert len(d) == 3

    def test_equality(self):
        d1 = CaseInsensitiveDict({"Key": "value"})
        d2 = CaseInsensitiveDict({"key": "value"})
        assert d1 == d2

    def test_inequality(self):
        d1 = CaseInsensitiveDict({"Key": "value1"})
        d2 = CaseInsensitiveDict({"Key": "value2"})
        assert d1 != d2

    def test_update(self):
        d = CaseInsensitiveDict({"A": "1"})
        d.update({"B": "2"})
        assert d["b"] == "2"

    def test_get_default(self):
        d = CaseInsensitiveDict()
        assert d.get("missing", "default") == "default"


class TestIdGenerator:
    """Tests de IdGenerator."""

    def test_generates_unique_ids(self):
        gen = IdGenerator()
        id1 = gen.generate()
        id2 = gen.generate()
        assert id1 != id2

    def test_format(self):
        gen = IdGenerator()
        id_ = gen.generate()
        assert "-" in id_
        parts = id_.split("-")
        assert len(parts) == 2
        assert len(parts[0]) == 8  # uuid hex[:8]

    def test_incrementing_counter(self):
        gen = IdGenerator()
        id1 = gen.generate()
        id2 = gen.generate()
        counter1 = int(id1.split("-")[1])
        counter2 = int(id2.split("-")[1])
        assert counter2 == counter1 + 1


class TestParseAGIResult:
    """Tests de parse_agi_result."""

    def test_success(self):
        result = parse_agi_result("200 result=1")
        assert result == "result=1"

    def test_hangup(self):
        with pytest.raises(AGIResultHangup):
            parse_agi_result("200 result=hangup")

    def test_invalid_command(self):
        with pytest.raises(AGIInvalidCommand):
            parse_agi_result("510 Invalid command")

    def test_dead_channel(self):
        with pytest.raises(AGIDeadChannelError):
            parse_agi_result("511 Dead channel")

    def test_usage_error(self):
        with pytest.raises(AGIUsageError):
            parse_agi_result("520 Invalid usage")

    def test_app_error(self):
        with pytest.raises(AGIAppError):
            parse_agi_result("200 result=-1")

    def test_trying(self):
        result = parse_agi_result("100 Trying")
        assert result == "Trying"

    def test_no_result(self):
        with pytest.raises(AGINoResultError):
            parse_agi_result("")

    def test_unknown_code(self):
        result = parse_agi_result("300 result=ok")
        assert result == "result=ok"


class TestReconnectionConfig:
    """Tests de ReconnectionConfig y calculate_delay."""

    def test_default_values(self):
        config = ReconnectionConfig()
        assert config.max_attempts == 10
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_calculate_delay_first_attempt(self):
        config = ReconnectionConfig(jitter=False)
        delay = calculate_delay(1, config)
        assert delay == 1.0  # initial_delay * 2^0

    def test_calculate_delay_second_attempt(self):
        config = ReconnectionConfig(jitter=False)
        delay = calculate_delay(2, config)
        assert delay == 2.0  # initial_delay * 2^1

    def test_calculate_delay_capped(self):
        config = ReconnectionConfig(
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=False,
        )
        delay = calculate_delay(10, config)
        assert delay == 10.0  # capped at max_delay

    def test_calculate_delay_with_jitter(self):
        config = ReconnectionConfig(jitter=True)
        delay = calculate_delay(1, config)
        # With jitter ±20%, delay should be between 0.8 and 1.2
        assert 0.8 <= delay <= 1.2
