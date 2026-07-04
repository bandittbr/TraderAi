"""
TradeAI - Modelo: Trade Lifecycle (Fase 12)
Registra cada evento do ciclo de vida de um paper trade:
  OPEN | BREAK_EVEN_ACTIVATED | TRAILING_UPDATED | PARTIAL_EXIT
  TRAILING_STOP | BREAK_EVEN_STOP | TIME_STOP | EXIT_SCORE | CLOSED
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey
from app.database import Base


class TradeLifecycle(Base):
    __tablename__ = "trade_lifecycle"

    id         = Column(Integer, primary_key=True, autoincrement=True, index=True)
    trade_id   = Column(Integer, ForeignKey("paper_trades.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    # Tipo do evento
    event_type = Column(String(30), nullable=False)
    # OPEN | BREAK_EVEN_ACTIVATED | TRAILING_UPDATED | PARTIAL_EXIT
    # TRAILING_STOP | BREAK_EVEN_STOP | TIME_STOP | EXIT_SCORE
    # SIGNAL_CLOSE  | STOP_LOSS       | TAKE_PROFIT  | CLOSED

    # Contexto do evento
    price      = Column(Float, nullable=True)
    quantity   = Column(Float, nullable=True)
    pnl        = Column(Float, nullable=True)
    notes      = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TradeLifecycle trade={self.trade_id} event={self.event_type} price={self.price}>"
