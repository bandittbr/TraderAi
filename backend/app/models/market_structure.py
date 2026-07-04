"""
ORM — market_structure_snapshot

Persiste o resultado de cada análise de Market Structure para
rastreabilidade histórica e consulta pelo Signal Engine V4.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.database import Base


class MarketStructureSnapshot(Base):
    __tablename__ = "market_structure_snapshots"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    symbol          = Column(String(20),  nullable=False, index=True)
    timeframe       = Column(String(10),  nullable=False)
    computed_at     = Column(DateTime,    nullable=False, default=datetime.utcnow, index=True)

    # Tendência estrutural
    trend           = Column(String(12),  nullable=False)   # BULLISH / BEARISH / RANGING / UNDEFINED
    confidence      = Column(Float,       nullable=False, default=0.0)
    structure_label = Column(String(20),  nullable=False, default="UNDEFINED")

    # Swing labels
    last_swing_high = Column(Float,       nullable=True)
    last_swing_low  = Column(Float,       nullable=True)
    last_high_label = Column(String(4),   nullable=True)    # HH / LH
    last_low_label  = Column(String(4),   nullable=True)    # HL / LL

    # Contagens HH/HL/LH/LL
    hh_count        = Column(Integer,     nullable=False, default=0)
    hl_count        = Column(Integer,     nullable=False, default=0)
    lh_count        = Column(Integer,     nullable=False, default=0)
    ll_count        = Column(Integer,     nullable=False, default=0)

    # BOS
    bos_bullish     = Column(Boolean,     nullable=False, default=False)
    bos_bearish     = Column(Boolean,     nullable=False, default=False)
    bos_level       = Column(Float,       nullable=True)
    is_choch        = Column(Boolean,     nullable=False, default=False)

    # SR Zones (JSON serializado)
    nearest_support       = Column(Float,   nullable=True)
    nearest_resistance    = Column(Float,   nullable=True)
    price_near_support    = Column(Boolean, nullable=False, default=False)
    price_near_resistance = Column(Boolean, nullable=False, default=False)
    support_zones         = Column(Text,    nullable=True)    # JSON
    resistance_zones      = Column(Text,    nullable=True)    # JSON

    candles_analyzed = Column(Integer, nullable=False, default=0)
