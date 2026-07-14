"""
Tests for BrokerEngine auto-trading logic.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.broker.engine import (
    BrokerEngine,
    BinanceCredentials,
    OrderSide,
    OrderType,
)


@pytest.fixture
def engine():
    """Fresh BrokerEngine with a mock client."""
    eng = BrokerEngine()
    creds = BinanceCredentials(api_key="test", api_secret="test", testnet=True)
    eng.add_user("default", creds)
    return eng


@pytest.fixture
def mock_client(engine):
    """Mock the BinanceClient methods."""
    client = engine.get_client("default")
    client.get_usdt_balance = AsyncMock(return_value=1000.0)
    client.get_price = AsyncMock(return_value=50000.0)
    client.place_order = AsyncMock(return_value=MagicMock(
        order_id="12345",
        avg_price=50000.0,
        status="FILLED",
    ))
    return client


class TestAutoMode:
    def test_auto_mode_off_by_default(self, engine):
        assert engine.auto_mode.get("default") is False

    def test_toggle_auto_mode(self, engine):
        engine.set_auto_mode("default", True)
        assert engine.auto_mode["default"] is True
        engine.set_auto_mode("default", False)
        assert engine.auto_mode["default"] is False

    def test_selected_agent_paper_by_default(self, engine):
        assert engine.selected_agent.get("default") == "paper"


class TestExecuteSignalAuto:
    @pytest.mark.asyncio
    async def test_skipped_when_auto_disabled(self, engine):
        result = await engine.execute_signal_auto("default", {"symbol": "BTCUSDT", "side": "LONG"})
        assert result["status"] == "skipped"
        assert result["reason"] == "auto_mode disabled"

    @pytest.mark.asyncio
    async def test_skipped_when_agent_is_paper(self, engine):
        engine.set_auto_mode("default", True)
        result = await engine.execute_signal_auto("default", {"symbol": "BTCUSDT", "side": "LONG"})
        assert result["status"] == "skipped"
        assert "paper" in result["reason"]

    @pytest.mark.asyncio
    async def test_error_when_no_client(self, engine):
        engine.set_auto_mode("default", True)
        engine.selected_agent["default"] = "worker"
        # Remove client but keep auto_mode and selected_agent set
        client = engine.clients.pop("default")
        result = await engine.execute_signal_auto("default", {"symbol": "BTCUSDT", "side": "LONG"})
        assert result["status"] == "error"
        assert "no client" in result["reason"]

    @pytest.mark.asyncio
    async def test_invalid_signal_side(self, engine):
        engine.set_auto_mode("default", True)
        engine.selected_agent["default"] = "worker"
        result = await engine.execute_signal_auto("default", {"symbol": "BTCUSDT", "side": "INVALID"})
        assert result["status"] == "error"
        assert "invalid signal" in result["reason"]

    @pytest.mark.asyncio
    async def test_successful_market_order(self, engine, mock_client):
        engine.set_auto_mode("default", True)
        engine.selected_agent["default"] = "worker"

        signal = {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "confidence": 85.0,
            "entry_price": 50000.0,
            "quantity": 0.001,
        }
        result = await engine.execute_signal_auto("default", signal)

        assert result["status"] == "executed"
        assert result["order_id"] == "12345"
        assert result["side"] == "LONG"
        mock_client.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_computes_quantity_from_balance(self, engine, mock_client):
        engine.set_auto_mode("default", True)
        engine.selected_agent["default"] = "groq"

        signal = {
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "confidence": 70.0,
        }
        result = await engine.execute_signal_auto("default", signal)

        assert result["status"] == "executed"
        # quantity should be computed: 2% of 1000 USDT / 50000 = 0.0004
        call_kwargs = mock_client.place_order.call_args
        assert call_kwargs[1]["quantity"] == pytest.approx(0.0004, abs=0.0001)


class TestProcessAgentSignal:
    @pytest.mark.asyncio
    async def test_returns_none_when_auto_disabled(self, engine):
        result = await engine.process_agent_signal("default", "worker", {"symbol": "X"})
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_agent_mismatch(self, engine):
        engine.set_auto_mode("default", True)
        engine.selected_agent["default"] = "groq"
        result = await engine.process_agent_signal("default", "worker", {"symbol": "X"})
        assert result is None

    @pytest.mark.asyncio
    async def test_executes_when_agent_matches(self, engine, mock_client):
        engine.set_auto_mode("default", True)
        engine.selected_agent["default"] = "worker"

        signal = {"symbol": "BTCUSDT", "side": "LONG", "quantity": 0.001}
        result = await engine.process_agent_signal("default", "worker", signal)

        assert result["status"] == "executed"
        mock_client.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_injects_agent_suggestion(self, engine, mock_client):
        engine.set_auto_mode("default", True)
        engine.selected_agent["default"] = "scalper"

        signal = {"symbol": "BTCUSDT", "side": "SHORT", "quantity": 0.001}
        await engine.process_agent_signal("default", "scalper", signal)

        assert signal["agent_suggestion"] == "scalper"
