"""
TradeAI - Biel Agent Models
ORM para o agente Biel: posts, tokens Instagram, configurações, métricas de engajamento.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class BielPost(Base):
    """Histórico de posts publicados pelo Biel no Instagram."""
    __tablename__ = "biel_posts"

    id            = Column(Integer, primary_key=True, index=True)
    post_type     = Column(String(20), nullable=False)   # "image" | "reel"
    caption       = Column(Text, nullable=False)          # Texto gerado pelo Gemini/Llama
    image_path    = Column(String(500), nullable=True)    # Caminho local da imagem
    video_path    = Column(String(500), nullable=True)    # Caminho local do vídeo
    instagram_id  = Column(String(100), nullable=True)    # ID do post no Instagram
    status        = Column(String(20), default="pending") # pending|published|failed
    error_msg     = Column(Text, nullable=True)
    regime        = Column(String(20), nullable=True)     # Regime no momento do post
    pnl_snapshot  = Column(Float, nullable=True)          # P&L no momento
    topic         = Column(String(50), nullable=True)     # Imagens: "market"|"trade"|"insight"|"news"
    reel_topic    = Column(String(50), nullable=True)     # Reels: "meme"|"noticias"|"insight"|"profits"|"erros"|"aprendizados"
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    published_at  = Column(DateTime(timezone=True), nullable=True)


class BielPostMetrics(Base):
    """
    Métricas de engajamento coletadas do Instagram via Graph API Insights.
    Cada registro corresponde a um snapshot no tempo de um post publicado.
    Permite tracking de evolução ao longo do tempo (ex: likes às 24h vs 7d).
    """
    __tablename__ = "biel_post_metrics"

    id              = Column(Integer, primary_key=True, index=True)
    post_id         = Column(Integer, ForeignKey("biel_posts.id"), nullable=False, index=True)
    instagram_id    = Column(String(100), nullable=False, index=True)

    # Métricas do Instagram Insights API
    like_count      = Column(Integer, default=0)
    comments_count  = Column(Integer, default=0)
    shares_count    = Column(Integer, default=0)
    saves_count     = Column(Integer, default=0)
    reach           = Column(Integer, default=0)   # contas únicas que viram
    impressions     = Column(Integer, default=0)   # total de exibições
    plays           = Column(Integer, default=0)   # reproduções (reels)
    profile_visits  = Column(Integer, default=0)   # visitas ao perfil vindas do post
    follows         = Column(Integer, default=0)   # novos seguidores vindos do post

    # Engagement score pré-calculado (para ordenação rápida)
    engagement_score = Column(Float, default=0.0)  # fórmula ponderada

    # Controle de coleta
    fetched_at      = Column(DateTime(timezone=True), server_default=func.now())
    hours_after_post = Column(Integer, default=0)  # quantas horas depois do post (0 = first fetch)

    # Timestamp do post no Instagram (para referência)
    post_published_at = Column(DateTime(timezone=True), nullable=True)


class BielTopicPerformance(Base):
    """
    Performance acumulada por tópico — atualizada a cada ciclo de coleta.
    Usado pelo _pick_reel_topic() para escolher tópicos com prioridade adaptativa.
    """
    __tablename__ = "biel_topic_performance"

    id              = Column(Integer, primary_key=True, index=True)
    topic           = Column(String(50), nullable=False, unique=True)  # "profits", "meme", etc.
    post_type       = Column(String(20), nullable=False)  # "image" | "reel"

    # Métricas acumuladas (média ponderada, decay temporal)
    avg_engagement  = Column(Float, default=0.0)    # score médio de engajamento
    avg_reach       = Column(Float, default=0.0)    # alcance médio
    avg_likes       = Column(Float, default=0.0)    # likes médios
    avg_comments    = Column(Float, default=0.0)    # comments médios
    avg_saves       = Column(Float, default=0.0)    # saves médios
    total_posts     = Column(Integer, default=0)    # total de posts com métricas

    # Peso adaptativo (1.0 = neutro, >1.0 = mais frecuente, <1.0 = menos)
    weight          = Column(Float, default=1.0)

    # Controle
    last_updated    = Column(DateTime(timezone=True), server_default=func.now())


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
    gemini_api_key      = Column(Text, nullable=False)   # FIXME: criptografar antes de salvar
    posts_per_day       = Column(Integer, default=4)
    post_hours          = Column(String(50), default="8,12,18,22")  # Horários dos posts
    reels_per_day       = Column(Integer, default=2)       # Quantos reels por dia
    reel_hours          = Column(String(50), default="9,21")  # Horários dos reels
    persona_name        = Column(String(50), default="Biel")
    is_active           = Column(Boolean, default=True)
    instagram_account_id = Column(String(100), nullable=True)
    music_url           = Column(String(500), nullable=True)  # URL da música de fundo para reels
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())
