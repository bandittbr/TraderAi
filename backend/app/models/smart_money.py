"""
ORM — smart_money_snapshots

Persiste o resultado de cada análise SMC para rastreabilidade.
"""
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from app.database import Base


class SmartMoneySnapshot(Base):
    __tablename__ = "smart_money_snapshots"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    symbol      = Column(String(20), nullable=False, index=True)
    timeframe   = Column(String(10), nullable=False)
    computed_at = Column(DateTime,   nullable=False, default=datetime.utcnow, index=True)

    # Sweeps
    has_recent_buy_sweep  = Column(Boolean, nullable=False, default=False)
    has_recent_sell_sweep = Column(Boolean, nullable=False, default=False)
    sweep_bias            = Column(String(10), nullable=True)
    last_sweep_type       = Column(String(30), nullable=True)
    last_sweep_price      = Column(Float,      nullable=True)

    # FVG
    has_bullish_fvg    = Column(Boolean, nullable=False, default=False)
    has_bearish_fvg    = Column(Boolean, nullable=False, default=False)
    bullish_fvg_top    = Column(Float,   nullable=True)
    bullish_fvg_bottom = Column(Float,   nullable=True)
    bearish_fvg_top    = Column(Float,   nullable=True)
    bearish_fvg_bottom = Column(Float,   nullable=True)

    # Volume Profile
    volume_profile_score = Column(Float, nullable=False, default=50.0)
    poc                  = Column(Float, nullable=True)
    value_area_high      = Column(Float, nullable=True)
    value_area_low       = Column(Float, nullable=True)
    hvn_levels           = Column(Text,  nullable=True)   # JSON
    lvn_levels           = Column(Text,  nullable=True)   # JSON
    near_hvn             = Column(Boolean, nullable=False, default=False)
    near_lvn             = Column(Boolean, nullable=False, default=False)

    # Liquidity Score
    liquidity_score  = Column(Float,      nullable=False, default=50.0)
    liquidity_label  = Column(String(15), nullable=True)

    candles_analyzed = Column(Integer, nullable=False, default=0)
