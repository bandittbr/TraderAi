"""
TradeAI - Biel Agent Models
ORM para o agente Biel: posts, tokens Instagram, configurações.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class BielPost(Base):
    """Histórico de posts publicados pelo Biel no Instagram."""
    __tablename__ = "biel_posts"

    id            = Column(Integer, primary_key=True, index=True)
    post_type     = Column(String(20), nullable=False)   # "image" | "reel"
    caption       = Column(Text, nullable=False)          # Texto gerado pelo Gemini
    image_path    = Column(String(500), nullable=True)    # Caminho local da imagem
    video_path    = Column(String(500), nullable=True)    # Caminho local do vídeo
    instagram_id  = Column(String(100), nullable=True)    # ID do post no Instagram
    status        = Column(String(20), default="pending") # pending|published|failed
    error_msg     = Column(Text, nullable=True)
    regime        = Column(String(20), nullable=True)     # Regime no momento do post
    pnl_snapshot  = Column(Float, nullable=True)          # P&L no momento
    topic         = Column(String(50), nullable=True)     # "market"|"trade"|"insight"|"news"
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    published_at  = Column(DateTime(timezone=True), nullable=True)


class BielToken(Base):
    """Tokens de acesso Instagram com controle de expiração."""
    __tablename__ = "biel_tokens"

    id              = Column(Integer, primary_key=True, index=True)
    account_id      = Column(String(100), nullable=False)   # Instagram Account ID
    access_token    = Column(Text, nullable=False)           # Token atual
    token_type      = Column(String(20), default="long_lived")  # short|long_lived|page
    expires_at      = Column(DateTime(timezone=True), nullable=True)
    app_id          = Column(String(100), nullable=True)
    app_secret      = Column(String(200), nullable=True)
    last_renewed_at = Column(DateTime(timezone=True), nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())


class BielConfig(Base):
    """Configurações do agente Biel."""
    __tablename__ = "biel_config"

    id                  = Column(Integer, primary_key=True, index=True)
    gemini_api_key      = Column(Text, nullable=False)
    posts_per_day       = Column(Integer, default=4)
    post_hours          = Column(String(50), default="8,12,18,22")  # Horários dos posts
    persona_name        = Column(String(50), default="Biel")
    is_active           = Column(Boolean, default=True)
    instagram_account_id = Column(String(100), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())
