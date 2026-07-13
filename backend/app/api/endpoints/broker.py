"""
TradeAI - Broker API Endpoints (Binance Real Trading)
Endpoints para conectar, consultar e operar na Binance Futures.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import Optional
from app.services.broker.engine import broker_engine, BinanceCredentials, OrderSide, OrderType, PositionSide

router = APIRouter(prefix="/broker", tags=["Corretora"])


# ── Models ────────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    api_key: str = Field(..., description="Binance API Key")
    api_secret: str = Field(..., description="Binance API Secret")
    testnet: bool = Field(True, description="Usar testnet (recomendado para testes)")


class ConnectResponse(BaseModel):
    status: str
    message: str
    testnet: bool
    balance_usdt: float


class StatusResponse(BaseModel):
    connected: bool
    auto_mode: bool
    selected_agent: str
    testnet: Optional[bool] = None
    balance_usdt: Optional[float] = None


class AutoModeRequest(BaseModel):
    enabled: bool


class AgentSelectRequest(BaseModel):
    agent: str = Field(..., description="paper, worker, scalper, groq")


class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Ex: BTCUSDT")
    side: str = Field(..., description="BUY ou SELL")
    order_type: str = Field("MARKET", description="MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET")
    quantity: float = Field(..., gt=0)
    price: Optional[float] = None
    stop_price: Optional[float] = None
    position_side: str = Field("BOTH", description="LONG, SHORT, BOTH")
    reduce_only: bool = False
    client_order_id: Optional[str] = None


class LeverageRequest(BaseModel):
    symbol: str
    leverage: int = Field(..., ge=1, le=125)


class MarginTypeRequest(BaseModel):
    symbol: str
    margin_type: str = Field("ISOLATED", description="ISOLATED ou CROSSED")


# ── Dependency ───────────────────────────────────────────────────────────

async def get_client(user_id: str = "default"):
    client = broker_engine.get_client(user_id)
    if not client:
        raise HTTPException(status_code=401, detail="Não conectado. Use POST /broker/connect primeiro.")
    return client


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/connect", response_model=ConnectResponse)
async def connect_binance(req: ConnectRequest, user_id: str = "default"):
    """
    Conecta à Binance Futures com API Key/Secret.
    Salva credenciais em memória (não persiste no banco).
    """
    try:
        creds = BinanceCredentials(
            api_key=req.api_key,
            api_secret=req.api_secret,
            testnet=req.testnet,
        )
        client = broker_engine.add_user(user_id, creds)
        
        # Testa conexão
        balance = await client.get_usdt_balance()
        
        return ConnectResponse(
            status="connected",
            message="Conectado à Binance Futures com sucesso",
            testnet=req.testnet,
            balance_usdt=balance,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao conectar: {str(e)}")


@router.post("/disconnect")
async def disconnect_binance(user_id: str = "default"):
    """Desconecta e remove credenciais."""
    broker_engine.remove_user(user_id)
    return {"status": "disconnected", "message": "Credenciais removidas"}


@router.get("/status", response_model=StatusResponse)
async def get_status(user_id: str = "default"):
    """Status da conexão e modo de operação."""
    status = broker_engine.get_status(user_id)
    
    balance = None
    if status["connected"]:
        client = broker_engine.get_client(user_id)
        if client:
            balance = await client.get_usdt_balance()
    
    return StatusResponse(
        connected=status["connected"],
        auto_mode=status["auto_mode"],
        selected_agent=status["selected_agent"],
        testnet=status["testnet"],
        balance_usdt=balance,
    )


@router.post("/auto-mode")
async def set_auto_mode(req: AutoModeRequest, user_id: str = "default"):
    """Ativa/desativa modo AUTO (IA escolhe agente e executa)."""
    if not broker_engine.get_client(user_id):
        raise HTTPException(status_code=401, detail="Não conectado")
    
    broker_engine.set_auto_mode(user_id, req.enabled)
    return {"status": "ok", "auto_mode": req.enabled}


@router.post("/select-agent")
async def select_agent(req: AgentSelectRequest, user_id: str = "default"):
    """Define qual agente opera no modo MANUAL."""
    valid_agents = ["paper", "worker", "scalper", "groq"]
    if req.agent not in valid_agents:
        raise HTTPException(status_code=400, detail=f"Agente inválido. Use: {valid_agents}")
    
    broker_engine.set_selected_agent(user_id, req.agent)
    return {"status": "ok", "selected_agent": req.agent}


@router.get("/balance")
async def get_balance(user_id: str = "default", client=Depends(get_client)):
    """Saldos de todos os ativos."""
    balances = await client.get_balances()
    return {"balances": [{"asset": b.asset, "free": b.free, "locked": b.locked, "total": b.total} for b in balances]}


@router.get("/positions")
async def get_positions(user_id: str = "default", client=Depends(get_client)):
    """Posições abertas."""
    positions = await client.get_positions()
    return {"positions": [
        {
            "symbol": p.symbol,
            "side": p.position_side.value,
            "size": p.size,
            "entry_price": p.entry_price,
            "mark_price": p.mark_price,
            "unrealized_pnl": p.unrealized_pnl,
            "leverage": p.leverage,
            "isolated": p.isolated,
        }
        for p in positions
    ]}


@router.post("/order")
async def place_order(req: OrderRequest, user_id: str = "default", client=Depends(get_client)):
    """Coloca ordem real na Binance Futures."""
    try:
        result = await client.place_order(
            symbol=req.symbol,
            side=OrderSide(req.side),
            order_type=OrderType(req.order_type),
            quantity=req.quantity,
            price=req.price,
            stop_price=req.stop_price,
            position_side=PositionSide(req.position_side),
            reduce_only=req.reduce_only,
            client_order_id=req.client_order_id,
        )
        return {
            "status": "success",
            "order": {
                "order_id": result.order_id,
                "client_order_id": result.client_order_id,
                "symbol": result.symbol,
                "side": result.side.value,
                "type": result.type.value,
                "quantity": result.quantity,
                "price": result.price,
                "status": result.status.value,
                "filled_qty": result.filled_qty,
                "avg_price": result.avg_price,
                "commission": result.commission,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao colocar ordem: {str(e)}")


@router.delete("/order/{symbol}")
async def cancel_order(
    symbol: str,
    order_id: Optional[int] = None,
    client_order_id: Optional[str] = None,
    user_id: str = "default",
    client=Depends(get_client),
):
    """Cancela ordem específica."""
    try:
        result = await client.cancel_order(symbol, order_id, client_order_id)
        return {"status": "cancelled", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao cancelar: {str(e)}")


@router.delete("/orders/{symbol}")
async def cancel_all_orders(symbol: str, user_id: str = "default", client=Depends(get_client)):
    """Cancela todas as ordens abertas de um símbolo."""
    try:
        result = await client.cancel_all_orders(symbol)
        return {"status": "cancelled_all", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro: {str(e)}")


@router.get("/open-orders")
async def get_open_orders(symbol: Optional[str] = None, user_id: str = "default", client=Depends(get_client)):
    """Ordens abertas."""
    orders = await client.get_open_orders(symbol)
    return {"orders": [
        {
            "order_id": o.order_id,
            "client_order_id": o.client_order_id,
            "symbol": o.symbol,
            "side": o.side.value,
            "type": o.type.value,
            "quantity": o.quantity,
            "price": o.price,
            "status": o.status.value,
            "filled_qty": o.filled_qty,
            "avg_price": o.avg_price,
        }
        for o in orders
    ]}


@router.post("/leverage")
async def set_leverage(req: LeverageRequest, user_id: str = "default", client=Depends(get_client)):
    """Define alavancagem para um símbolo."""
    try:
        result = await client.set_leverage(req.symbol, req.leverage)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro: {str(e)}")


@router.post("/margin-type")
async def set_margin_type(req: MarginTypeRequest, user_id: str = "default", client=Depends(get_client)):
    """Define tipo de margem (ISOLATED/CROSSED)."""
    try:
        result = await client.set_margin_type(req.symbol, req.margin_type)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro: {str(e)}")


@router.get("/ticker/{symbol}")
async def get_ticker(symbol: str, user_id: str = "default", client=Depends(get_client)):
    """Ticker 24h."""
    data = await client.get_ticker(symbol)
    return data


@router.get("/price/{symbol}")
async def get_price(symbol: str, user_id: str = "default", client=Depends(get_client)):
    """Preço atual."""
    price = await client.get_price(symbol)
    return {"symbol": symbol, "price": price}


@router.get("/klines/{symbol}")
async def get_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 100,
    user_id: str = "default",
    client=Depends(get_client),
):
    """Candles OHLCV."""
    data = await client.get_klines(symbol, interval, limit)
    return {"symbol": symbol, "interval": interval, "klines": data}