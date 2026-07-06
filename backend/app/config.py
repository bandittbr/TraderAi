"""
TradeAI - Configuração Centralizada
Todas as configurações do sistema são gerenciadas aqui via variáveis de ambiente.
Utiliza pydantic-settings para validação automática de tipos.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """
    Configurações globais da aplicação.
    Os valores são lidos do arquivo .env ou de variáveis de ambiente do sistema.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Aplicação ──────────────────────────────────────────────────────────────
    app_name: str = "TradeAI"
    app_version: str = "12.5.0"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_debug: bool = True

    # ── Banco de Dados ─────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/tradeai.db"

    # ── CORS ───────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── Logs ───────────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_file: str = "logs/tradeai.log"

    # ── Segurança (Fase 2) ─────────────────────────────────────────────────────
    secret_key: str = "change-this-secret-key-in-production"

    # ── Paper Trading (Fase 4) ─────────────────────────────────────────────────
    paper_initial_balance:    float = 200.0
    paper_risk_per_trade:     float = 10.0   # USD por trade
    paper_stop_loss_percent:  float = 2.0    # % abaixo do entry (hard SL)
    paper_take_profit_percent: float = 4.0   # % acima do entry (TP2 / full close)

    # ── Trade Management Engine (Fase 12) ─────────────────────────────────────
    paper_max_hours_open:         float = 48.0   # Time Stop: fechar após N horas
    paper_break_even_trigger_pct: float = 1.5    # % lucro para mover stop ao entry
    paper_trailing_start_pct:     float = 2.0    # % lucro para ativar trailing stop
    paper_trailing_distance_pct:  float = 1.0    # % de distância do trailing stop
    paper_tp1_pct:                float = 2.0    # % lucro para saída parcial 50% (TP1)
    paper_exit_score_threshold:   float = 30.0   # Exit Score abaixo disso → fechar

    @property
    def cors_origins_list(self) -> List[str]:
        """Retorna a lista de origens CORS permitidas."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


# Instância singleton das configurações — importar de qualquer módulo
settings = Settings()
