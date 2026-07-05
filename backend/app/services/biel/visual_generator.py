"""
Biel — Visual Generator
Gera imagens para posts do Instagram usando matplotlib.
"""

import os
import io
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from app.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("data/biel_images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Paleta visual do Biel — dark theme moderno
BG_COLOR      = "#0D0D0D"
PANEL_COLOR   = "#1A1A2E"
ACCENT_BLUE   = "#00D4FF"
ACCENT_GREEN  = "#00FF88"
ACCENT_RED    = "#FF4444"
ACCENT_GOLD   = "#FFD700"
TEXT_COLOR    = "#FFFFFF"
SUBTEXT_COLOR = "#888888"


def generate_market_image(context: dict) -> str:
    """
    Gera imagem de estado do mercado (regime + fear&greed + BTC price).
    Retorna o caminho do arquivo gerado.
    """
    fig = plt.figure(figsize=(9, 9), facecolor=BG_COLOR)
    gs = GridSpec(3, 2, figure=fig, hspace=0.5, wspace=0.4)

    # ── Header ────────────────────────────────────────────────────────────
    ax_header = fig.add_subplot(gs[0, :])
    ax_header.set_facecolor(BG_COLOR)
    ax_header.axis("off")
    ax_header.text(0.5, 0.8, "⚡ BIEL TRADER", ha="center", va="center",
                   fontsize=28, fontweight="bold", color=ACCENT_GOLD,
                   transform=ax_header.transAxes)
    ax_header.text(0.5, 0.3, context.get("timestamp", ""), ha="center", va="center",
                   fontsize=11, color=SUBTEXT_COLOR, transform=ax_header.transAxes)

    # ── BTC Price ─────────────────────────────────────────────────────────
    ax_btc = fig.add_subplot(gs[1, 0])
    ax_btc.set_facecolor(PANEL_COLOR)
    ax_btc.axis("off")
    btc = context.get("btc_price", 0)
    ax_btc.text(0.5, 0.7, "BTC/USDT", ha="center", va="center",
                fontsize=13, color=SUBTEXT_COLOR, transform=ax_btc.transAxes)
    ax_btc.text(0.5, 0.35, f"${btc:,.0f}", ha="center", va="center",
                fontsize=22, fontweight="bold", color=ACCENT_BLUE,
                transform=ax_btc.transAxes)

    # ── Regime ────────────────────────────────────────────────────────────
    ax_regime = fig.add_subplot(gs[1, 1])
    ax_regime.set_facecolor(PANEL_COLOR)
    ax_regime.axis("off")
    regime = context.get("regime", "N/A")
    regime_color = (ACCENT_GREEN if "BULL" in regime.upper()
                    else ACCENT_RED if "BEAR" in regime.upper()
                    else ACCENT_GOLD)
    ax_regime.text(0.5, 0.7, "REGIME", ha="center", va="center",
                   fontsize=13, color=SUBTEXT_COLOR, transform=ax_regime.transAxes)
    ax_regime.text(0.5, 0.35, regime, ha="center", va="center",
                   fontsize=22, fontweight="bold", color=regime_color,
                   transform=ax_regime.transAxes)

    # ── Fear & Greed ──────────────────────────────────────────────────────
    ax_fg = fig.add_subplot(gs[2, 0])
    ax_fg.set_facecolor(PANEL_COLOR)
    ax_fg.axis("off")
    fg_val = context.get("fear_greed_value", 50)
    fg_label = context.get("fear_greed_label", "Neutral")
    fg_color = (ACCENT_RED if fg_val < 25 else
                ACCENT_GOLD if fg_val < 50 else
                ACCENT_BLUE if fg_val < 75 else ACCENT_GREEN)
    ax_fg.text(0.5, 0.75, "FEAR & GREED", ha="center", va="center",
               fontsize=11, color=SUBTEXT_COLOR, transform=ax_fg.transAxes)
    ax_fg.text(0.5, 0.45, str(fg_val), ha="center", va="center",
               fontsize=26, fontweight="bold", color=fg_color,
               transform=ax_fg.transAxes)
    ax_fg.text(0.5, 0.15, fg_label, ha="center", va="center",
               fontsize=11, color=fg_color, transform=ax_fg.transAxes)

    # ── P&L ───────────────────────────────────────────────────────────────
    ax_pnl = fig.add_subplot(gs[2, 1])
    ax_pnl.set_facecolor(PANEL_COLOR)
    ax_pnl.axis("off")
    pnl = context.get("pnl_total", 0)
    pnl_pct = context.get("pnl_pct", 0)
    pnl_color = ACCENT_GREEN if pnl >= 0 else ACCENT_RED
    sinal = "+" if pnl >= 0 else ""
    ax_pnl.text(0.5, 0.75, "P&L TOTAL", ha="center", va="center",
                fontsize=11, color=SUBTEXT_COLOR, transform=ax_pnl.transAxes)
    ax_pnl.text(0.5, 0.45, f"{sinal}${pnl:,.2f}", ha="center", va="center",
                fontsize=20, fontweight="bold", color=pnl_color,
                transform=ax_pnl.transAxes)
    ax_pnl.text(0.5, 0.15, f"{sinal}{pnl_pct:.1f}%", ha="center", va="center",
                fontsize=13, color=pnl_color, transform=ax_pnl.transAxes)

    # ── Footer ────────────────────────────────────────────────────────────
    fig.text(0.5, 0.02, "TradeAI • Dados simulados • Não é recomendação de investimento",
             ha="center", fontsize=8, color=SUBTEXT_COLOR)

    # Salvar
    filename = f"market_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
    filepath = OUTPUT_DIR / filename
    plt.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)

    logger.info(f"[biel/visual] Imagem gerada: {filepath}")
    return str(filepath)


def generate_trade_image(context: dict) -> str:
    """
    Gera imagem de resultado de trades (lista de trades recentes + win rate).
    """
    trades = context.get("ultimos_trades", [])
    win_rate = context.get("win_rate_recente", 0)

    fig, axes = plt.subplots(1, 1, figsize=(9, 9), facecolor=BG_COLOR)
    axes.set_facecolor(BG_COLOR)
    axes.axis("off")

    # Header
    axes.text(0.5, 0.95, "⚡ BIEL — RESULTADOS", ha="center", va="top",
              fontsize=24, fontweight="bold", color=ACCENT_GOLD,
              transform=axes.transAxes)
    axes.text(0.5, 0.88, context.get("timestamp", ""), ha="center", va="top",
              fontsize=10, color=SUBTEXT_COLOR, transform=axes.transAxes)

    # Win Rate gauge
    wr_color = ACCENT_GREEN if win_rate >= 50 else ACCENT_RED
    axes.text(0.5, 0.78, f"WIN RATE", ha="center", va="top",
              fontsize=13, color=SUBTEXT_COLOR, transform=axes.transAxes)
    axes.text(0.5, 0.70, f"{win_rate}%", ha="center", va="top",
              fontsize=36, fontweight="bold", color=wr_color,
              transform=axes.transAxes)

    # Lista de trades
    y = 0.58
    axes.text(0.5, y, "ÚLTIMOS TRADES", ha="center", va="top",
              fontsize=12, color=SUBTEXT_COLOR, transform=axes.transAxes)
    y -= 0.06

    for t in trades[:5]:
        color = ACCENT_GREEN if t["pnl"] >= 0 else ACCENT_RED
        sinal = "+" if t["pnl"] >= 0 else ""
        emoji = "✅" if t["pnl"] >= 0 else "❌"
        line = f"{emoji}  {t['symbol']} {t['side']}   {sinal}${t['pnl']:.2f}"
        axes.text(0.5, y, line, ha="center", va="top",
                  fontsize=13, color=color, transform=axes.transAxes)
        y -= 0.08

    # P&L
    pnl = context.get("pnl_total", 0)
    saldo = context.get("saldo", 10000)
    pnl_color = ACCENT_GREEN if pnl >= 0 else ACCENT_RED
    axes.text(0.5, 0.08, f"Saldo: ${saldo:,.2f}  |  P&L: {'+' if pnl>=0 else ''}${pnl:,.2f}",
              ha="center", va="bottom", fontsize=12, color=pnl_color,
              transform=axes.transAxes)

    fig.text(0.5, 0.02, "TradeAI • Dados simulados • Não é recomendação de investimento",
             ha="center", fontsize=8, color=SUBTEXT_COLOR)

    filename = f"trade_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
    filepath = OUTPUT_DIR / filename
    plt.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)

    logger.info(f"[biel/visual] Imagem trade gerada: {filepath}")
    return str(filepath)


async def generate_image(context: dict, topic: str) -> str:
    """Entry point async para gerar imagem baseada no tópico."""
    loop = asyncio.get_event_loop()
    if topic in ("trade",):
        return await loop.run_in_executor(None, generate_trade_image, context)
    else:
        return await loop.run_in_executor(None, generate_market_image, context)
