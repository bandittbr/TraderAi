"""
Metrics Engine — Phase 6

Calcula métricas de performance puras sobre listas de trades/sinais.
Todas as funções são STATELESS (sem I/O), auditáveis e testáveis.

Métricas implementadas:
  win_rate        — percentual de trades positivos
  profit_factor   — soma ganhos / soma perdas absolutas
  expectancy      — WR * AvgGain - LR * AvgLoss (em %)
  sharpe_ratio    — retorno médio / desvio-padrão (anualizado por ciclos)
  calmar_ratio    — retorno médio anual / max drawdown
  max_drawdown    — maior perda acumulada em sequência de perdas (%)
  avg_duration    — duração média das operações (minutos)
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Optional, Sequence


# ─────────────────────────────────────────────
# Estrutura de resultado
# ─────────────────────────────────────────────

@dataclass
class PerformanceMetrics:
    # Contagens
    total_trades:    int   = 0
    wins:            int   = 0
    losses:          int   = 0

    # Taxas
    win_rate:        float = 0.0   # 0–100 %
    loss_rate:       float = 0.0   # 0–100 %

    # Retornos
    avg_pnl_pct:     float = 0.0
    avg_win_pct:     float = 0.0
    avg_loss_pct:    float = 0.0   # valor negativo
    total_pnl_pct:   float = 0.0

    # Métricas de qualidade
    profit_factor:   float = 0.0
    expectancy:      float = 0.0   # % por trade
    sharpe_ratio:    float = 0.0
    calmar_ratio:    float = 0.0
    max_drawdown:    float = 0.0   # % (negativo = perda)
    max_consecutive_wins:   int = 0
    max_consecutive_losses: int = 0

    # Tempo
    avg_duration_min: float = 0.0
    median_duration_min: float = 0.0

    # LONG vs SHORT (Phase 6+)
    long_trades:     int   = 0
    short_trades:    int   = 0
    win_rate_long:   float = 0.0
    win_rate_short:  float = 0.0
    pf_long:         float = 0.0   # profit factor LONG
    pf_short:        float = 0.0   # profit factor SHORT


# ─────────────────────────────────────────────
# Cálculos individuais
# ─────────────────────────────────────────────

def calc_win_rate(pnls: Sequence[float]) -> float:
    """Taxa de vitória em %. pnls: lista de retornos percentuais."""
    if not pnls:
        return 0.0
    wins = sum(1 for p in pnls if p > 0)
    return (wins / len(pnls)) * 100.0


def calc_profit_factor(pnls: Sequence[float]) -> float:
    """
    Profit Factor = Soma dos ganhos / |Soma das perdas|
    Retorna 0 se não há perdas, float('inf') se não há perdas mas há ganhos.
    """
    gains = sum(p for p in pnls if p > 0)
    losses = abs(sum(p for p in pnls if p < 0))
    if losses == 0:
        return gains if gains > 0 else 0.0
    return round(gains / losses, 4)


def calc_expectancy(pnls: Sequence[float]) -> float:
    """
    Expectância = (WinRate * AvgGain) - (LossRate * |AvgLoss|)
    Resultado em % por trade. Expectância positiva = edge real.
    """
    if not pnls:
        return 0.0
    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total  = len(pnls)

    wr  = len(wins)   / total
    lr  = len(losses) / total
    avg_win  = statistics.mean(wins)   if wins   else 0.0
    avg_loss = statistics.mean(losses) if losses else 0.0  # negativo

    return round((wr * avg_win) + (lr * avg_loss), 4)


def calc_sharpe_ratio(
    pnls: Sequence[float],
    cycles_per_year: int = 8760,   # 8760 candles de 1h em 1 ano
    risk_free_rate: float = 0.0,
) -> float:
    """
    Sharpe Ratio = (MédiaRetornos - TaxaLivre) / DesvPadrão * sqrt(ciclos/ano)
    Anualizado assumindo ciclos_por_ano (padrão: 8760 = candles horários).
    Retorna 0.0 se desvio padrão = 0.
    """
    if len(pnls) < 2:
        return 0.0
    mean_ret = statistics.mean(pnls) - risk_free_rate
    stdev    = statistics.stdev(pnls)
    if stdev == 0:
        return 0.0
    raw_sharpe = mean_ret / stdev
    annualized = raw_sharpe * math.sqrt(cycles_per_year)
    return round(annualized, 4)


def calc_max_drawdown(pnls: Sequence[float]) -> float:
    """
    Calcula o Maximum Drawdown simulando equity curve.
    Retorna valor negativo (ex: -15.3 significa -15.3% de drawdown máximo).
    """
    if not pnls:
        return 0.0

    equity = 100.0
    peak   = 100.0
    max_dd = 0.0

    for pnl in pnls:
        equity *= (1.0 + pnl / 100.0)
        if equity > peak:
            peak = equity
        dd = (equity - peak) / peak * 100.0
        if dd < max_dd:
            max_dd = dd

    return round(max_dd, 4)


def calc_calmar_ratio(
    pnls: Sequence[float],
    max_drawdown: Optional[float] = None,
) -> float:
    """
    Calmar Ratio = Retorno Anualizado / |Max Drawdown|
    Annualização simplificada: multiplica avg por 8760.
    """
    if not pnls:
        return 0.0
    if max_drawdown is None:
        max_drawdown = calc_max_drawdown(pnls)
    if max_drawdown >= 0:
        return 0.0  # sem drawdown = calmar indefinido, retorna 0

    avg_per_candle = statistics.mean(pnls)
    annual_return  = avg_per_candle * 8760
    return round(annual_return / abs(max_drawdown), 4)


def calc_consecutive(pnls: Sequence[float]) -> tuple[int, int]:
    """Retorna (max_consecutive_wins, max_consecutive_losses)."""
    if not pnls:
        return 0, 0
    max_w = max_l = cur_w = cur_l = 0
    for p in pnls:
        if p > 0:
            cur_w += 1; cur_l = 0
        elif p < 0:
            cur_l += 1; cur_w = 0
        else:
            cur_w = cur_l = 0
        max_w = max(max_w, cur_w)
        max_l = max(max_l, cur_l)
    return max_w, max_l


# ─────────────────────────────────────────────
# Função de conveniência — calcula tudo
# ─────────────────────────────────────────────

def compute_metrics(
    pnls: Sequence[float],
    durations_min: Optional[Sequence[int]] = None,
    cycles_per_year: int = 8760,
    sides: Optional[Sequence[str]] = None,   # "LONG" | "SHORT" por trade
) -> PerformanceMetrics:
    """
    Calcula todas as métricas a partir de uma sequência de PnL% (por trade).

    Args:
        pnls: lista de resultados em %, um por trade (+ ganho, - perda)
        durations_min: opcional, lista de durações em minutos por trade
        cycles_per_year: para anualização do Sharpe (padrão: 8760 candles/h)
        sides: opcional, lista de "LONG"/"SHORT" correspondente a cada pnl

    Returns:
        PerformanceMetrics populado (inclui métricas LONG/SHORT se sides fornecido)
    """
    m = PerformanceMetrics()

    if not pnls:
        return m

    pnls_list = list(pnls)
    m.total_trades = len(pnls_list)

    wins_list   = [p for p in pnls_list if p > 0]
    losses_list = [p for p in pnls_list if p < 0]

    m.wins   = len(wins_list)
    m.losses = len(losses_list)

    if m.total_trades > 0:
        m.win_rate  = round((m.wins  / m.total_trades) * 100.0, 2)
        m.loss_rate = round((m.losses / m.total_trades) * 100.0, 2)

    m.avg_pnl_pct   = round(statistics.mean(pnls_list), 4)
    m.total_pnl_pct = round(sum(pnls_list), 4)
    m.avg_win_pct   = round(statistics.mean(wins_list),   4) if wins_list   else 0.0
    m.avg_loss_pct  = round(statistics.mean(losses_list), 4) if losses_list else 0.0

    m.profit_factor = calc_profit_factor(pnls_list)
    m.expectancy    = calc_expectancy(pnls_list)
    m.max_drawdown  = calc_max_drawdown(pnls_list)
    m.sharpe_ratio  = calc_sharpe_ratio(pnls_list, cycles_per_year)
    m.calmar_ratio  = calc_calmar_ratio(pnls_list, m.max_drawdown)

    m.max_consecutive_wins, m.max_consecutive_losses = calc_consecutive(pnls_list)

    if durations_min:
        durs = [d for d in durations_min if d is not None]
        if durs:
            m.avg_duration_min    = round(statistics.mean(durs), 1)
            m.median_duration_min = round(statistics.median(durs), 1)

    # ── LONG vs SHORT ────────────────────────────────────────────────────────
    if sides and len(sides) == len(pnls_list):
        long_pnls  = [p for p, s in zip(pnls_list, sides) if s == "LONG"]
        short_pnls = [p for p, s in zip(pnls_list, sides) if s == "SHORT"]

        m.long_trades  = len(long_pnls)
        m.short_trades = len(short_pnls)

        if long_pnls:
            lw = sum(1 for p in long_pnls if p > 0)
            m.win_rate_long = round((lw / len(long_pnls)) * 100.0, 2)
            m.pf_long       = calc_profit_factor(long_pnls)

        if short_pnls:
            sw = sum(1 for p in short_pnls if p > 0)
            m.win_rate_short = round((sw / len(short_pnls)) * 100.0, 2)
            m.pf_short       = calc_profit_factor(short_pnls)

    return m
