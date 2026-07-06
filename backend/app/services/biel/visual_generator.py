"""
Biel — Visual Generator (v2)
Gera imagens profissionais para Instagram usando Pillow.
Design moderno dark-theme com gradientes, glassmorphism e tipografia limpa.
"""

import os
import math
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("data/biel_images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Constantes de design ──
W, H = 1080, 1080

# Paleta
BG_TOP       = (13, 13, 26)
BG_BOTTOM    = (26, 26, 46)
PANEL_BG     = (20, 20, 45, 200)   # RGBA — glassmorphism
ACCENT_BLUE  = (0, 212, 255)
ACCENT_GREEN = (0, 255, 136)
ACCENT_RED   = (255, 68, 68)
ACCENT_GOLD  = (255, 215, 0)
TEXT_WHITE   = (255, 255, 255)
TEXT_GRAY    = (140, 140, 160)
TEXT_DIM     = (60, 60, 80)
GRID_LINE    = (40, 40, 60)

# ── Fontes ──
_FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}

def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Carrega fonte com cache — fallback cross-platform."""
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    # Ordem de preferência: Segoe UI (Windows), Arial, DejaVu Sans (Linux), fallback
    candidates = (
        ["segoeui.ttf", "segoeuib.ttf"] if bold else ["segoeui.ttf"],
        ["arial.ttf", "arialbd.ttf"] if bold else ["arial.ttf"],
        ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"],
        ["tahoma.ttf"], ["Verdana.ttf"],
    )
    for group in candidates:
        for name in group:
            try:
                f = ImageFont.truetype(name, size)
                _FONT_CACHE[key] = f
                return f
            except (IOError, OSError):
                continue
    # Fallback: default PIL
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


# ═══════════════════════════════════════════════════════════════════
#  Utilitários de desenho
# ═══════════════════════════════════════════════════════════════════

def _draw_gradient(draw: ImageDraw, x1, y1, x2, y2, color1, color2, vertical=True):
    """Desenha gradiente linear."""
    steps = 120
    for i in range(steps):
        t = i / steps
        color = tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1[:3], color2[:3]))
        if vertical:
            draw.rectangle([x1, y1 + (y2 - y1) * t / steps * steps, x2, y1 + (y2 - y1) * (t + 1) / steps * steps], fill=color)
        else:
            draw.rectangle([x1 + (x2 - x1) * t / steps * steps, y1, x1 + (x2 - x1) * (t + 1) / steps * steps, y2], fill=color)


def _rounded_rect(draw: ImageDraw, xy, radius, fill=None, outline=None, outline_width=2):
    """Desenha retângulo com cantos arredondados."""
    x1, y1, x2, y2 = xy
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    # Helper cantos
    def _corners(fill_c):
        draw.pieslice([x1, y1, x1 + r * 2, y1 + r * 2], 180, 270, fill=fill_c)
        draw.pieslice([x2 - r * 2, y1, x2, y1 + r * 2], 270, 360, fill=fill_c)
        draw.pieslice([x1, y2 - r * 2, x1 + r * 2, y2], 90, 180, fill=fill_c)
        draw.pieslice([x2 - r * 2, y2 - r * 2, x2, y2], 0, 90, fill=fill_c)
        draw.rectangle([x1 + r, y1, x2 - r, y2], fill=fill_c)
        draw.rectangle([x1, y1 + r, x2, y2 - r], fill=fill_c)

    if fill:
        _corners(fill)
    if outline:
        # desenha um fill outline sutil por cima
        _corners(outline + (60,))


def _draw_gloss(draw: ImageDraw, xy):
    """Overlay de brilho sutil no topo do card."""
    x1, y1, x2, y2 = xy
    for i in range(20):
        t = 1 - i / 20
        alpha = int(15 * t)
        draw.rectangle([x1, y1 + i, x2, y1 + i + 1], fill=(255, 255, 255, alpha))


def _draw_gauge(draw: ImageDraw, cx: int, cy: int, radius: int, value: int, label: str, color):
    """Desenha medidor semicircular (Fear & Greed style)."""
    # Arco de fundo (180 graus)
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    # Fundo do arco
    draw.pieslice(bbox, 180, 0, fill=(40, 40, 60), outline=(50, 50, 70), width=4)

    # Arco preenchido
    angle = 180 * value / 100
    draw.pieslice(bbox, 180, 180 - angle, fill=color, outline=color, width=6)

    # Valor central
    font_val = _get_font(38, bold=True)
    font_label = _get_font(14)
    # Sombra
    draw.text((cx + 2, cy - 15 + 2), str(value), font=font_val, fill=(0, 0, 0, 100), anchor="mm")
    draw.text((cx, cy - 15), str(value), font=font_val, fill=TEXT_WHITE, anchor="mm")
    draw.text((cx, cy + 15), label, font=font_label, fill=TEXT_GRAY, anchor="mm")


def _draw_sparkline(draw: ImageDraw, xy, values, color):
    """Desenha mini gráfico de linha (sparkline)."""
    x1, y1, x2, y2 = xy
    if not values or len(values) < 2:
        return
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        vmax = vmin + 1
    n = len(values)
    points = []
    for i, v in enumerate(values):
        px = x1 + (x2 - x1) * i / (n - 1)
        py = y2 - (y2 - y1) * (v - vmin) / (vmax - vmin)
        points.append((px, py))

    # Sombra
    for i, (px, py) in enumerate(points):
        draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=color)
    # Linhas
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=color, width=3)

    # Gradiente do fill
    if len(points) > 1:
        poly = [(x1, y2)] + points + [(x2, y2)]
        for i in range(len(poly) - 1):
            alpha = int(40 * (1 - i / len(poly)))
            draw.line([poly[i], poly[i + 1]], fill=color + (alpha,), width=6)


# ═══════════════════════════════════════════════════════════════════
#  Geradores de imagem
# ═══════════════════════════════════════════════════════════════════

def _generate_base_image(topic_label: str, emoji: str) -> tuple[Image.Image, ImageDraw.Draw]:
    """Cria imagem base com gradiente de fundo e header."""
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    _draw_gradient(draw, 0, 0, W, H, BG_TOP, BG_BOTTOM)

    # Grid decorativo sutil
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=GRID_LINE + (30,), width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=GRID_LINE + (30,), width=1)

    # Header
    font_title = _get_font(36, bold=True)
    font_sub = _get_font(14)
    # Glow no título
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.text((W // 2 + dx, 48 + dy), f"{emoji}  BIEL TRADER", font=font_title, fill=(0, 0, 0, 80), anchor="mm")
    draw.text((W // 2, 48), f"{emoji}  BIEL TRADER", font=font_title, fill=ACCENT_GOLD, anchor="mm")

    timestamp = datetime.now(timezone.utc).strftime("%d %b %Y • %H:%M UTC")
    draw.text((W // 2, 90), timestamp, font=font_sub, fill=TEXT_GRAY, anchor="mm")

    # Tag
    font_tag = _get_font(12, bold=True)
    draw.text((W // 2, 118), f"#{topic_label.upper().replace(' ', '')}", font=font_tag, fill=TEXT_DIM, anchor="mm")

    return img, draw


def _finalize(img: Image.Image, topic: str) -> str:
    """Salva imagem final e retorna caminho."""
    # Converte para RGB e adiciona footer
    draw = ImageDraw.Draw(img)
    font_footer = _get_font(11)
    draw.text((W // 2, H - 30), "TradeAI • Dados em tempo real • Não é recomendação de investimento",
              font=font_footer, fill=TEXT_DIM, anchor="mm")

    rgb = Image.new("RGB", (W, H), (0, 0, 0))
    rgb.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)

    filename = f"{topic}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
    filepath = OUTPUT_DIR / filename
    rgb.save(filepath, quality=95)
    logger.info(f"[biel/visual] Imagem salva: {filepath}")
    return str(filepath)


# ─── MARKET IMAGE ───────────────────────────────────────────────────

def generate_market_image(context: dict) -> str:
    """
    Gera imagem de mercado com visual profissional:
    - BTC price com sparkline
    - Fear & Greed gauge
    - Regime indicator
    - P&L
    """
    img, draw = _generate_base_image("Mercado", "📊")

    btc_price = context.get("btc_price", 0)
    regime = context.get("regime", "NEUTRAL")
    fg_value = context.get("fear_greed_value", 50)
    fg_label = context.get("fear_greed_label", "Neutral")
    pnl = context.get("pnl_total", 0)
    pnl_pct = context.get("pnl_pct", 0)
    regime_color = ACCENT_GREEN if "BULL" in str(regime).upper() else (ACCENT_RED if "BEAR" in str(regime).upper() else ACCENT_GOLD)

    # ── Card: BTC Price ──
    cx, cy = 540, 300
    _rounded_rect(draw, (60, 180, 1020, 420), 24, fill=PANEL_BG)
    _draw_gloss(draw, (60, 180, 1020, 195))

    draw.text((540, 220), "BTC/USDT", font=_get_font(14), fill=TEXT_GRAY, anchor="mm")
    # Preço grande
    font_price = _get_font(56, bold=True)
    price_text = f"${btc_price:,.0f}"
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.text((540 + dx, 310 + dy), price_text, font=font_price, fill=(0, 0, 0, 80), anchor="mm")
    draw.text((540, 310), price_text, font=font_price, fill=ACCENT_BLUE, anchor="mm")

    # Variação percentual (mockada - idealmente viria do context)
    change_24h = context.get("btc_change_24h", None)
    if change_24h is not None:
        change_color = ACCENT_GREEN if change_24h >= 0 else ACCENT_RED
        sign = "+" if change_24h >= 0 else ""
        draw.text((540, 360), f"24h: {sign}{change_24h:.2f}%", font=_get_font(14, bold=True), fill=change_color, anchor="mm")

    # ── Card inferior esquerdo: Regime + P&L ──
    _rounded_rect(draw, (60, 460, 520, 640), 24, fill=PANEL_BG)
    _draw_gloss(draw, (60, 460, 520, 475))

    draw.text((290, 500), "REGIME", font=_get_font(12), fill=TEXT_GRAY, anchor="mm")
    font_regime = _get_font(40, bold=True)
    draw.text((290, 560), regime, font=font_regime, fill=regime_color, anchor="mm")

    pnl_color = ACCENT_GREEN if pnl >= 0 else ACCENT_RED
    sign = "+" if pnl >= 0 else ""
    draw.text((290, 620), f"P&L: {sign}${pnl:,.2f} ({sign}{pnl_pct:.1f}%)",
              font=_get_font(16, bold=True), fill=pnl_color, anchor="mm")

    # ── Card inferior direito: Fear & Greed ──
    _rounded_rect(draw, (560, 460, 1020, 640), 24, fill=PANEL_BG)
    _draw_gloss(draw, (560, 460, 1020, 475))

    fg_color = (ACCENT_RED if fg_value < 25 else
                ACCENT_GOLD if fg_value < 50 else
                ACCENT_BLUE if fg_value < 75 else ACCENT_GREEN)

    # Semi-circle gauge for Fear & Greed
    _draw_gauge(draw, 790, 580, 100, fg_value, fg_label.upper(), fg_color)

    # ── Barra inferior: Resumo do mercado ──
    _rounded_rect(draw, (60, 680, 1020, 800), 24, fill=PANEL_BG)

    # Métricas em linha
    metrics_data = context.get("resumo", {})
    metrics = [
        ("DOMÍNIO BTC", metrics_data.get("btc_dominance", "58.2%"), ACCENT_BLUE),
        ("VOLUME 24H", metrics_data.get("volume_24h", "$28.4B"), ACCENT_GOLD),
        ("ALT SEASON", metrics_data.get("alt_season", "Não"), ACCENT_GOLD if "sim" in str(metrics_data.get("alt_season", "")).lower() else TEXT_GRAY),
        ("TOTAL TRADES", str(context.get("total_trades", "—")), TEXT_WHITE),
    ]

    for i, (label, value, color) in enumerate(metrics):
        x = 180 + i * 260
        draw.text((x, 720), label, font=_get_font(11), fill=TEXT_GRAY, anchor="mm")
        draw.text((x, 765), value, font=_get_font(20, bold=True), fill=color, anchor="mm")

    # ── Sparkline BTC (opcional) ──
    price_history = context.get("btc_price_history", [])
    if price_history and len(price_history) >= 2:
        _draw_sparkline(draw, (80, 196, 320, 240), price_history, ACCENT_BLUE)

    return _finalize(img, "market")


# ─── TRADE IMAGE ────────────────────────────────────────────────────

def generate_trade_image(context: dict) -> str:
    """
    Gera imagem de resultados de trade:
    - Win rate com gauge circular
    - Lista de trades recentes
    - P&L e saldo
    """
    img, draw = _generate_base_image("Resultados", "📈")

    trades = context.get("ultimos_trades", [])
    win_rate = context.get("win_rate_recente", 0)
    pnl = context.get("pnl_total", 0)
    saldo = context.get("saldo", 10000)

    # ── Card: Win Rate (esquerda) ──
    _rounded_rect(draw, (60, 180, 480, 440), 24, fill=PANEL_BG)
    _draw_gloss(draw, (60, 180, 480, 195))

    draw.text((270, 225), "WIN RATE", font=_get_font(14), fill=TEXT_GRAY, anchor="mm")
    wr_color = ACCENT_GREEN if win_rate >= 50 else (ACCENT_GOLD if win_rate >= 30 else ACCENT_RED)

    # Gauge circular completo
    bbox = [270 - 80, 320 - 80, 270 + 80, 320 + 80]
    draw.arc(bbox, 0, 360, fill=ACCENT_GREEN if win_rate >= 50 else ACCENT_RED, width=12)
    draw.arc(bbox, 0, int(360 * win_rate / 100), fill=wr_color, width=12)

    font_wr = _get_font(42, bold=True)
    draw.text((270, 320), f"{win_rate}%", font=font_wr, fill=TEXT_WHITE, anchor="mm")
    draw.text((270, 370), f"{len(trades)} trades", font=_get_font(14), fill=TEXT_GRAY, anchor="mm")

    # ── Card: Últimos trades (direita) ──
    _rounded_rect(draw, (520, 180, 1020, 440), 24, fill=PANEL_BG)
    _draw_gloss(draw, (520, 180, 1020, 195))

    draw.text((770, 220), "ÚLTIMOS TRADES", font=_get_font(14), fill=TEXT_GRAY, anchor="mm")

    # Cabeçalho da tabela
    draw.text((560, 252), "PAR", font=_get_font(10), fill=TEXT_DIM, anchor="mm")
    draw.text((720, 252), "LADO", font=_get_font(10), fill=TEXT_DIM, anchor="mm")
    draw.text((880, 252), "P&L", font=_get_font(10), fill=TEXT_DIM, anchor="mm")
    draw.line([(540, 268), (1000, 268)], fill=GRID_LINE + (60,), width=1)

    y = 290
    for t in trades[:6]:
        t_color = ACCENT_GREEN if t.get("pnl", 0) >= 0 else ACCENT_RED
        emoji_t = "✅" if t.get("pnl", 0) >= 0 else "❌"
        symbol = t.get("symbol", "???")
        side = t.get("side", "???").upper()
        t_pnl = t.get("pnl", 0)
        t_sign = "+" if t_pnl >= 0 else ""

        draw.text((560, y), f"{emoji_t} {symbol}", font=_get_font(14, bold=True), fill=TEXT_WHITE, anchor="mm")
        draw.text((720, y), side, font=_get_font(12), fill=ACCENT_BLUE, anchor="mm")
        draw.text((920, y), f"{t_sign}${t_pnl:.2f}", font=_get_font(14, bold=True), fill=t_color, anchor="mm")
        y += 38

    # ── Card: Resumo Financeiro ──
    _rounded_rect(draw, (60, 480, 1020, 620), 24, fill=PANEL_BG)
    _draw_gloss(draw, (60, 480, 1020, 495))

    pnl_color = ACCENT_GREEN if pnl >= 0 else ACCENT_RED
    pnl_sign = "+" if pnl >= 0 else ""

    metrics = [
        ("SALDO", f"${saldo:,.2f}", TEXT_WHITE),
        ("P&L TOTAL", f"{pnl_sign}${pnl:,.2f}", pnl_color),
        ("WIN RATE", f"{win_rate}%", wr_color),
        ("TRADES", str(len(trades)), ACCENT_BLUE),
    ]

    for i, (label, value, color) in enumerate(metrics):
        x = 180 + i * 240
        draw.text((x, 530), label, font=_get_font(12), fill=TEXT_GRAY, anchor="mm")
        draw.text((x, 575), value, font=_get_font(28, bold=True), fill=color, anchor="mm")
        if i < len(metrics) - 1:
            draw.line([(x + 100, 520), (x + 100, 600)], fill=GRID_LINE + (40,), width=1)

    # ── Barra de progresso de trades vencidos vs perdidos (se houver dados) ──
    wins = sum(1 for t in trades if t.get("pnl", 0) >= 0)
    losses = len(trades) - wins
    if len(trades) > 0:
        _rounded_rect(draw, (60, 660, 1020, 740), 20, fill=PANEL_BG)
        total_bar = 900
        bar_x, bar_y = 90, 700
        draw.rectangle([bar_x, bar_y, bar_x + total_bar, bar_y + 16], fill=(40, 40, 60))

        if wins > 0:
            win_w = int(total_bar * wins / len(trades))
            draw.rectangle([bar_x, bar_y, bar_x + win_w, bar_y + 16], fill=ACCENT_GREEN + (200,))

        draw.text((bar_x + total_bar // 2, bar_y + 8),
                  f"{wins} Wins  •  {losses} Losses  •  {len(trades)} Total",
                  font=_get_font(14, bold=True), fill=TEXT_WHITE, anchor="mm")

    return _finalize(img, "trade")


# ═══════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════

async def generate_image(context: dict, topic: str) -> str:
    """Entry point async para gerar imagem baseada no tópico."""
    loop = asyncio.get_event_loop()
    if topic in ("trade",):
        return await loop.run_in_executor(None, generate_trade_image, context)
    else:
        return await loop.run_in_executor(None, generate_market_image, context)
