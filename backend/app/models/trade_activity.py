"""
TradeAI - Trade Activity Log
Registra CADA ação dos agentes (abertura, fechamento, atualização de stops)
como eventos imutáveis. Serve como fonte de verdade para:
  1. Gráficos com markers de trade
  2. Dashboard de performance por agente
  3. Sistema de auto-melhoria (feedback loop)
  4. Backup/perseveração mesmo se a tabela de trades for perdida
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.database import Base


class TradeActivity(Base):
    """
    Log imutável de cada ação de trading.
    Cada row = um evento (trade aberto, fechado, stop ajustado, etc.)
    """
    __tablename__ = "trade_activity"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Identificação ──────────────────────────────────────────────────────────
    agent = Column(String(20), nullable=False, index=True)        # "paper", "scalper", "worker"
    event = Column(String(20), nullable=False, index=True)        # "open", "close", "update", "signal"
    symbol = Column(String(20), nullable=False, index=True)       # "BTCUSDT", "ETHUSDT"
    trade_id = Column(Integer, nullable=True)                     # ID na tabela original (paper_trades, etc.)

    # ── Dados do preço ─────────────────────────────────────────────────────────
    price = Column(Float, nullable=False)                         # Preço no momento do evento
    quantity = Column(Float, nullable=True)                       # Quantidade negociada

    # ── Dados do trade ─────────────────────────────────────────────────────────
    side = Column(String(10), nullable=True)                      # "LONG" ou "SHORT"
    pnl = Column(Float, nullable=True)                            # P&L em USD (só no close)
    pnl_pct = Column(Float, nullable=True)                        # P&L em % (só no close)
    reason = Column(String(50), nullable=True)                    # "signal", "tp1", "tp2", "sl", "trailing", "time_stop"

    # ── Contexto ───────────────────────────────────────────────────────────────
    confidence = Column(Float, nullable=True)                     # Confiança do sinal (0-100)
    regime = Column(String(20), nullable=True)                    # "BULL", "BEAR", "SIDEWAYS", "HIGH_VOL"
    balance_after = Column(Float, nullable=True)                  # Saldo da conta após o evento

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Metadata ───────────────────────────────────────────────────────────────
    extra = Column(Text, nullable=True)                           # JSON com dados extras (stops, scores, etc.)

    def __repr__(self) -> str:
        return (
            f"<TradeActivity {self.agent} {self.event} {self.symbol} "
            f"@ {self.price} pnl={self.pnl}>"
        )

    def to_dict(self) -> dict:
        """Serializa para broadcast WebSocket."""
        return {
            "type": "trade_activity",
            "agent": self.agent,
            "event": self.event,
            "symbol": self.symbol,
            "trade_id": self.trade_id,
            "price": self.price,
            "quantity": self.quantity,
            "side": self.side,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "reason": self.reason,
            "confidence": self.confidence,
            "regime": self.regime,
            "balance_after": self.balance_after,
            "timestamp": int(self.created_at.timestamp() * 1000) if self.created_at else None,
        }
