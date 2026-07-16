"""
TradeAI - Broker Service (Binance Real Trading)
Execução de ordens reais via API da Binance.
"""
from __future__ import annotations

import hmac
import hashlib
import time
import json
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum

import httpx
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"


class OrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"


@dataclass
class BinanceCredentials:
    api_key: str
    api_secret: str
    testnet: bool = False


@dataclass
class AccountBalance:
    asset: str
    free: float
    locked: float
    total: float


@dataclass
class Position:
    symbol: str
    position_side: PositionSide
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    leverage: int
    isolated: bool


@dataclass
class OrderResult:
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: float
    status: OrderStatus
    filled_qty: float
    avg_price: float
    commission: float
    commission_asset: str
    created_at: datetime
    updated_at: datetime


class BinanceClient:
    """
    Cliente para Binance Futures API (USDT-M).
    Suporta testnet e mainnet.
    """

    def __init__(self, credentials: BinanceCredentials):
        self.creds = credentials
        self.base_url = (
            "https://testnet.binancefuture.com"
            if credentials.testnet
            else "https://fapi.binance.com"
        )
        self.client = httpx.AsyncClient(timeout=30.0)

    def _sign(self, params: dict) -> str:
        """Gera assinatura HMAC SHA256."""
        query_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        signature = hmac.new(
            self.creds.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _headers(self) -> dict:
        return {"X-MBX-APIKEY": self.creds.api_key}

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        signed: bool = False,
    ) -> dict:
        """Faz requisição HTTP com retry e assinatura."""
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)

        headers = self._headers() if signed else {}

        for attempt in range(3):
            try:
                resp = await self.client.request(method, url, params=params, headers=headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"[binance] HTTP {e.response.status_code}: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"[binance] Request error: {e}")
                if attempt == 2:
                    raise
                await asyncio.sleep(1)

        raise RuntimeError("Max retries exceeded")

    # ── Account & Balance ──────────────────────────────────────────────────

    async def get_account(self) -> dict:
        """Informações da conta (saldo, posições, etc)."""
        return await self._request("GET", "/fapi/v2/account", signed=True)

    async def get_balances(self) -> list[AccountBalance]:
        """Saldos de todos os ativos."""
        data = await self.get_account()
        balances = []
        for b in data.get("assets", []):
            free = float(b.get("walletBalance", 0)) - float(b.get("crossUnPnl", 0))
            locked = float(b.get("maintMargin", 0)) + float(b.get("initialMargin", 0))
            total = free + locked
            if total > 0:
                balances.append(AccountBalance(
                    asset=b["asset"],
                    free=free,
                    locked=locked,
                    total=total,
                ))
        return balances

    async def get_usdt_balance(self) -> float:
        """Saldo livre em USDT."""
        balances = await self.get_balances()
        for b in balances:
            if b.asset == "USDT":
                return b.free
        return 0.0

    # ── Positions ──────────────────────────────────────────────────────────

    async def get_positions(self) -> list[Position]:
        """Posições abertas."""
        data = await self.get_account()
        positions = []
        for p in data.get("positions", []):
            size = float(p.get("positionAmt", 0))
            if size != 0:
                positions.append(Position(
                    symbol=p["symbol"],
                    position_side=PositionSide(p.get("positionSide", "BOTH")),
                    size=abs(size),
                    entry_price=float(p.get("entryPrice", 0)),
                    mark_price=float(p.get("markPrice", 0)),
                    unrealized_pnl=float(p.get("unRealizedProfit", 0)),
                    leverage=int(p.get("leverage", 1)),
                    isolated=p.get("isolated", False),
                ))
        return positions

    # ── Orders ─────────────────────────────────────────────────────────────

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None,
        position_side: PositionSide = PositionSide.BOTH,
        reduce_only: bool = False,
        client_order_id: str | None = None,
    ) -> OrderResult:
        """Coloca ordem no mercado."""
        params = {
            "symbol": symbol,
            "side": side.value,
            "type": order_type.value,
            "quantity": f"{quantity:.6f}",
            "positionSide": position_side.value,
        }

        if reduce_only:
            params["reduceOnly"] = "true"

        if client_order_id:
            params["newClientOrderId"] = client_order_id

        if order_type in (OrderType.LIMIT, OrderType.STOP_MARKET, OrderType.TAKE_PROFIT_MARKET):
            if price is None:
                raise ValueError(f"Price required for {order_type.value}")
            params["price"] = f"{price:.2f}"

        if order_type in (OrderType.STOP_MARKET, OrderType.TAKE_PROFIT_MARKET):
            if stop_price is None:
                raise ValueError(f"Stop price required for {order_type.value}")
            params["stopPrice"] = f"{stop_price:.2f}"

        data = await self._request("POST", "/fapi/v1/order", params=params, signed=True)
        return self._parse_order(data)

    async def cancel_order(self, symbol: str, order_id: int | None = None, client_order_id: str | None = None) -> dict:
        """Cancela ordem."""
        params = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        return await self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    async def cancel_all_orders(self, symbol: str) -> dict:
        """Cancela todas as ordens abertas de um símbolo."""
        return await self._request("DELETE", "/fapi/v1/allOpenOrders", params={"symbol": symbol}, signed=True)

    async def get_order(self, symbol: str, order_id: int | None = None, client_order_id: str | None = None) -> OrderResult:
        """Consulta status de ordem."""
        params = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        data = await self._request("GET", "/fapi/v1/order", params=params, signed=True)
        return self._parse_order(data)

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        """Ordens abertas."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        data = await self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
        return [self._parse_order(o) for o in data]

    # ── Leverage & Margin ──────────────────────────────────────────────────

    async def set_leverage(self, symbol: str, leverage: int) -> dict:
        """Define alavancagem."""
        return await self._request(
            "POST", "/fapi/v1/leverage",
            params={"symbol": symbol, "leverage": leverage},
            signed=True,
        )

    async def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> dict:
        """Define tipo de margem (ISOLATED ou CROSSED)."""
        return await self._request(
            "POST", "/fapi/v1/marginType",
            params={"symbol": symbol, "marginType": margin_type},
            signed=True,
        )

    # ── Market Data ────────────────────────────────────────────────────────

    async def get_ticker(self, symbol: str) -> dict:
        """Ticker 24h."""
        return await self._request("GET", "/fapi/v1/ticker/24hr", params={"symbol": symbol})

    async def get_price(self, symbol: str) -> float:
        """Preço atual."""
        data = await self._request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})
        return float(data["price"])

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> list[list]:
        """Candles OHLCV."""
        return await self._request(
            "GET", "/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    def _parse_order(self, data: dict) -> OrderResult:
        return OrderResult(
            order_id=str(data["orderId"]),
            client_order_id=data.get("clientOrderId", ""),
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            type=OrderType(data["type"]),
            quantity=float(data["origQty"]),
            price=float(data.get("price", 0)),
            status=OrderStatus(data["status"]),
            filled_qty=float(data.get("executedQty", 0)),
            avg_price=float(data.get("avgPrice", 0)),
            commission=float(data.get("commission", 0)),
            commission_asset=data.get("commissionAsset", ""),
            created_at=datetime.fromtimestamp(data["time"] / 1000, tz=timezone.utc),
            updated_at=datetime.fromtimestamp(data["updateTime"] / 1000, tz=timezone.utc),
        )

    async def close(self):
        await self.client.aclose()


# ── Broker Engine (High-level) ────────────────────────────────────────────

class BrokerEngine:
    """
    Engine de alto nível para trading real.
    Gerencia múltiplas credenciais, modo AUTO/Manual, risk management.
    """

    def __init__(self):
        self.clients: dict[str, BinanceClient] = {}  # user_id -> client
        self.auto_mode: dict[str, bool] = {}  # user_id -> True/False
        self.selected_agent: dict[str, str] = {}  # user_id -> agent_name

    def add_user(self, user_id: str, credentials: BinanceCredentials) -> BinanceClient:
        """Adiciona usuário com credenciais Binance."""
        client = BinanceClient(credentials)
        self.clients[user_id] = client
        self.auto_mode[user_id] = False
        self.selected_agent[user_id] = "paper"
        logger.info(f"[broker] Usuário {user_id} adicionado (testnet={credentials.testnet})")
        return client

    def remove_user(self, user_id: str):
        if user_id in self.clients:
            del self.clients[user_id]
            self.auto_mode.pop(user_id, None)
            self.selected_agent.pop(user_id, None)

    def get_client(self, user_id: str) -> BinanceClient | None:
        return self.clients.get(user_id)

    def set_auto_mode(self, user_id: str, enabled: bool):
        self.auto_mode[user_id] = enabled
        logger.info(f"[broker] User {user_id} auto_mode = {enabled}")

    def set_selected_agent(self, user_id: str, agent: str):
        self.selected_agent[user_id] = agent
        logger.info(f"[broker] User {user_id} selected_agent = {agent}")

    def get_status(self, user_id: str) -> dict:
        return {
            "connected": user_id in self.clients,
            "auto_mode": self.auto_mode.get(user_id, False),
            "selected_agent": self.selected_agent.get(user_id, "paper"),
            "testnet": self.clients[user_id].creds.testnet if user_id in self.clients else None,
        }

    # ── Auto Trading Logic ────────────────────────────────────────────────

    async def execute_signal_auto(self, user_id: str, signal: dict) -> dict | None:
        """
        Executa sinal automaticamente via Binance Futures.

        signal dict expected keys:
            symbol:     str   e.g. "BTCUSDT"
            side:       str   "LONG" or "SHORT"
            confidence: float 0-100
            regime:     str   e.g. "trend", "range"
            agent_suggestion: str  e.g. "worker", "scalper"
        Additional optional: entry_price, stop_loss, take_profit, quantity

        Returns dict with order result or skip/error reason.
        """
        if not self.auto_mode.get(user_id):
            return {"status": "skipped", "reason": "auto_mode disabled"}

        client = self.get_client(user_id)
        if not client:
            return {"status": "error", "reason": "no client connected"}

        agent = self.selected_agent.get(user_id, "paper")
        if agent == "paper":
            return {"status": "skipped", "reason": "selected_agent is paper (simulation only)"}

        # Validate required signal fields
        symbol = signal.get("symbol")
        side_raw = signal.get("side", "").upper()
        if not symbol or side_raw not in ("LONG", "SHORT"):
            return {"status": "error", "reason": f"invalid signal: symbol={symbol}, side={side_raw}"}

        try:
            # Map agent direction to Binance order side
            order_side = OrderSide.BUY if side_raw == "LONG" else OrderSide.SELL

            # Quantity: use signal quantity if provided, else compute from balance
            quantity = signal.get("quantity")
            if not quantity or quantity <= 0:
                balance = await client.get_usdt_balance()
                if balance <= 0:
                    return {"status": "error", "reason": "zero USDT balance"}
                # Default: risk 2% of balance per auto-trade
                risk_usd = balance * 0.02
                price = signal.get("entry_price") or await client.get_price(symbol)
                if price <= 0:
                    return {"status": "error", "reason": f"invalid price for {symbol}"}
                quantity = round(risk_usd / price, 6)

            if quantity <= 0:
                return {"status": "error", "reason": "computed quantity is zero"}

            # Place MARKET order (auto-trading uses market execution)
            order_result = await client.place_order(
                symbol=symbol,
                side=order_side,
                order_type=OrderType.MARKET,
                quantity=quantity,
            )

            # Optional: place SL order if stop_loss provided
            stop_loss = signal.get("stop_loss")
            if stop_loss and stop_loss > 0:
                sl_side = OrderSide.SELL if side_raw == "LONG" else OrderSide.BUY
                try:
                    await client.place_order(
                        symbol=symbol,
                        side=sl_side,
                        order_type=OrderType.STOP_MARKET,
                        quantity=quantity,
                        stop_price=float(stop_loss),
                        reduce_only=True,
                    )
                except Exception as sl_err:
                    logger.warning(f"[broker] Failed to place SL order: {sl_err}")

            # Optional: place TP order if take_profit provided
            take_profit = signal.get("take_profit")
            if take_profit and take_profit > 0:
                tp_side = OrderSide.SELL if side_raw == "LONG" else OrderSide.BUY
                try:
                    await client.place_order(
                        symbol=symbol,
                        side=tp_side,
                        order_type=OrderType.TAKE_PROFIT_MARKET,
                        quantity=quantity,
                        stop_price=float(take_profit),
                        reduce_only=True,
                    )
                except Exception as tp_err:
                    logger.warning(f"[broker] Failed to place TP order: {tp_err}")

            logger.info(
                f"[broker] AUTO ORDER EXECUTED: {side_raw} {symbol} qty={quantity:.6f} "
                f"via agent={agent} order_id={order_result.order_id}"
            )
            return {
                "status": "executed",
                "order_id": order_result.order_id,
                "symbol": symbol,
                "side": side_raw,
                "quantity": quantity,
                "avg_price": order_result.avg_price,
                "agent": agent,
            }

        except Exception as e:
            logger.error(f"[broker] Auto trade failed for {user_id}: {e}", exc_info=True)
            return {"status": "error", "reason": str(e)}

    async def process_agent_signal(self, user_id: str, agent_name: str, signal: dict) -> dict | None:
        """
        Called by agent trade engines after opening a paper/sim trade.
        Checks if auto_mode is enabled and selected_agent matches, then places real order.

        Args:
            user_id:    User identifier (typically "default" for single-user)
            agent_name: Name of the agent ("worker", "scalper")
            signal:     Dict with symbol, side, confidence, entry_price, stop_loss, take_profit, quantity

        Returns:
            Result dict from execute_signal_auto, or None if auto-trading not triggered.
        """
        if not self.auto_mode.get(user_id):
            return None

        selected = self.selected_agent.get(user_id, "paper")
        if selected != agent_name:
            return None

        logger.info(
            f"[broker] Agent '{agent_name}' signal received — auto-trading active, executing..."
        )
        signal["agent_suggestion"] = agent_name
        return await self.execute_signal_auto(user_id, signal)


# Instância singleton
broker_engine = BrokerEngine()