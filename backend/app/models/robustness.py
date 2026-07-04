"""
Fase 10 — Walk Forward Validation Engine ORM Models
Tabelas: walk_forward_results, monte_carlo_results, strategy_stability
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean, func

from app.database import Base


class WalkForwardResult(Base):
    """
    Resultado de uma rodada de Walk Forward Validation.
    Divide o histórico em train / validation / test e calcula métricas em cada fase.
    """
    __tablename__ = "walk_forward_results"

    id              = Column(Integer, primary_key=True, index=True)
    symbol          = Column(String(20), nullable=True)   # None = global
    pattern_key     = Column(String(200), nullable=True)  # None = todos os sinais

    # Configuração da janela
    train_days      = Column(Integer, nullable=False, default=60)
    val_days        = Column(Integer, nullable=False, default=30)
    test_days       = Column(Integer, nullable=False, default=30)

    # Métricas da fase de TREINO
    train_n         = Column(Integer, nullable=True)
    train_wr        = Column(Float, nullable=True)
    train_pf        = Column(Float, nullable=True)
    train_sharpe    = Column(Float, nullable=True)
    train_exp       = Column(Float, nullable=True)
    train_dd        = Column(Float, nullable=True)

    # Métricas da fase de VALIDAÇÃO
    val_n           = Column(Integer, nullable=True)
    val_wr          = Column(Float, nullable=True)
    val_pf          = Column(Float, nullable=True)
    val_sharpe      = Column(Float, nullable=True)
    val_exp         = Column(Float, nullable=True)
    val_dd          = Column(Float, nullable=True)

    # Métricas da fase de TESTE
    test_n          = Column(Integer, nullable=True)
    test_wr         = Column(Float, nullable=True)
    test_pf         = Column(Float, nullable=True)
    test_sharpe     = Column(Float, nullable=True)
    test_exp        = Column(Float, nullable=True)
    test_dd         = Column(Float, nullable=True)

    # Degradação train → test
    wr_degradation  = Column(Float, nullable=True)   # test_wr - train_wr (negativo = pior)
    pf_degradation  = Column(Float, nullable=True)   # test_pf - train_pf
    dd_increase     = Column(Float, nullable=True)   # test_dd - train_dd (positivo = pior)

    # Score de robustez Walk Forward (0-100)
    wf_score        = Column(Float, nullable=True)
    is_robust       = Column(Boolean, nullable=False, default=False)

    computed_at     = Column(DateTime, nullable=False, default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<WalkForwardResult {self.symbol or 'global'} score={self.wf_score:.1f}>"


class MonteCarloResult(Base):
    """
    Resultado de simulação Monte Carlo sobre os trades históricos.
    Embaralha N vezes a sequência de ganhos/perdas e calcula estatísticas.
    """
    __tablename__ = "monte_carlo_results"

    id                  = Column(Integer, primary_key=True, index=True)
    symbol              = Column(String(20), nullable=True)
    pattern_key         = Column(String(200), nullable=True)

    # Configuração
    n_simulations       = Column(Integer, nullable=False, default=5000)
    n_trades            = Column(Integer, nullable=False, default=0)

    # Distribuição de drawdowns (percentis)
    dd_median           = Column(Float, nullable=True)   # mediana
    dd_p95              = Column(Float, nullable=True)   # percentil 95
    dd_p99              = Column(Float, nullable=True)   # percentil 99 (extremo)
    dd_max_observed     = Column(Float, nullable=True)   # máximo observado

    # Distribuição de retornos finais
    ret_median          = Column(Float, nullable=True)
    ret_p5              = Column(Float, nullable=True)   # pior 5%
    ret_p95             = Column(Float, nullable=True)   # melhor 5%

    # Risco de ruína
    ruin_threshold      = Column(Float, nullable=False, default=20.0)   # drawdown % = ruína
    ruin_probability    = Column(Float, nullable=True)    # 0-100%

    # Win rate esperado (média das simulações)
    expected_wr         = Column(Float, nullable=True)
    wr_std              = Column(Float, nullable=True)    # desvio padrão do WR

    # JSON com histograma de drawdowns (para visualização)
    dd_histogram_json   = Column(Text, nullable=True)    # {bins: [], counts: []}

    computed_at         = Column(DateTime, nullable=False, default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<MonteCarloResult {self.symbol or 'global'} ruin={self.ruin_probability:.1f}%>"


class StrategyStability(Base):
    """
    Estabilidade de um padrão/estratégia por dimensão (ativo, regime, timeframe).
    Detecta padrões que só funcionam em condições específicas (overfitting temporal).
    """
    __tablename__ = "strategy_stability"

    id              = Column(Integer, primary_key=True, index=True)
    pattern_key     = Column(String(200), nullable=False, index=True)
    dimension_type  = Column(String(20), nullable=False)   # symbol | regime | timeframe | period
    dimension_value = Column(String(50), nullable=False)   # ex: BTCUSDT, BULL, 1h, Q1-2024

    # Métricas nessa dimensão
    n_trades        = Column(Integer, nullable=True)
    win_rate        = Column(Float, nullable=True)
    profit_factor   = Column(Float, nullable=True)
    expectancy      = Column(Float, nullable=True)

    # Comparação com baseline global do padrão
    baseline_wr     = Column(Float, nullable=True)
    baseline_pf     = Column(Float, nullable=True)
    wr_vs_baseline  = Column(Float, nullable=True)   # win_rate - baseline_wr

    # Score de estabilidade (0-100): quanto mais estável entre dimensões, maior
    stability_score = Column(Float, nullable=True)
    is_unstable     = Column(Boolean, nullable=False, default=False)  # UNSTABLE flag
    unstable_reason = Column(String(100), nullable=True)

    computed_at     = Column(DateTime, nullable=False, default=func.now(), index=True)

    def __repr__(self) -> str:
        return (
            f"<StrategyStability {self.pattern_key} "
            f"{self.dimension_type}={self.dimension_value} "
            f"{'UNSTABLE' if self.is_unstable else 'OK'}>"
        )
