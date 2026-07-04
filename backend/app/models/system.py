"""
TradeAI - Modelo: SystemLog
Registra eventos do sistema para auditoria e diagnóstico.
Fase 2+: adicionar modelos de Ativo, Sinal, Ordem, Carteira etc.
"""

from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.database import Base


class SystemLog(Base):
    """
    Tabela de logs persistidos no banco de dados.
    Complementa o sistema de logging em arquivo para eventos críticos.
    """

    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<SystemLog id={self.id} level={self.level} source={self.source}>"
