"""
Biel — Visual Generator (v3)
Gera publicações profissionais 1080x1350 (4:5) para Instagram.
4 modelos com identidade visual própria: Mercado, Trade, Insights, Notícia.

Design premium inspirado em Bloomberg, TradingView, CoinMarketCap e Binance.
"""

import os
import math
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("data/biel_images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Dimensões (4:5 Instagram) ──
W, H = 1080, 1350

# ── Paletas por tema ──
THEMES = {
    "market": {
        "name": "MERCADO",
        "primary":   (76, 222, 128),   # Verde
        "secondary": (56, 189, 248),   # Azul
        "accent":    (6, 182, 212),    # Ciano
        "bg_top":    (5, 10, 20),
        "bg_bot":    (10, 20, 40),
        "card_bg":   (15, 25, 45, 200),
        "glow":      (76, 222, 128, 30),
        "hashtag":   "#MERCADOEMOVIMENTO",
    },
    "trade": {
        "name": "TRADE",
        "primary":   (56, 189, 248),   # Azul
        "secondary": (6, 182, 212),    # Ciano
        "accent":    (34, 211, 238),   # Sky
        "bg_top":    (3, 7, 18),
        "bg_bot":    (8, 18, 38),
        "card_bg":   (12, 22, 42, 200),
        "glow":      (56, 189, 248, 30),
        "hashtag":   "#IDEIADETRADE",
    },
    "insight": {
        "name": "INSIGHTS",
        "primary":   (251, 191, 36),   # Dourado
        "secondary": (253, 224, 71),   # Amarelo
        "accent":    (245, 158, 11),   # Amber
        "bg_top":    (12, 10, 5),
        "bg_bot":    (24, 18, 8),
        "card_bg":   (30, 22, 10, 200),
        "glow":      (251, 191, 36, 30),
        "hashtag":   "#INSIGHTTRADERAI",
    },
    "news": {
        "name": "NOTÍCIA",
        "primary":   (168, 85, 247),   # Roxo
        "secondary": (192, 132, 252),  # Violeta
        "accent":    (139, 92, 246),   # Indigo
        "bg_top":    (10, 5, 18),
        "bg_bot":    (18, 8, 30),
        "card_bg":   (22, 10, 35, 200),
        "glow":      (168, 85, 247, 30),
        "hashtag":   "#NOTICIATRADERAI",
    },
}

# ── Cores globais ──
TEXT_WHITE  = (255, 255, 255)
TEXT_GRAY   = (156, 163, 175)
TEXT_DIM    = (75, 85, 99)
GRID_LINE   = (30, 40, 60)
PANEL_BORDER = (40, 50, 70)


# ═══════════════════════════════════════════════════════════════════
#  Fontes
# ═══════════════════════════════════════════════════════════════════

_FONT_CACHE: dict = {}

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = (
        ["segoeuib.ttf", "segoeui.ttf"] if bold else ["segoeui.ttf"],
        ["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf"],
        ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf"] if bold else ["DejaVuSans.ttf"],
    )
    for group in candidates:
        for name in group:
            try:
                f = ImageFont.truetype(name, size)
                _FONT_CACHE[key] = f
                return f
            except (IOError, OSError):
                continue
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


# ═══════════════════════════════════════════════════════════════════
#  Utilitários de desenho
# ═══════════════════════════════════════════════════════════════════

def _draw_gradient(draw, x1, y1, x2, y2, c1, c2):
    steps = 150
    for i in range(steps):
        t = i / steps
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        yy = y1 + (y2 - y1) * i // steps
        yy2 = y1 + (y2 - y1) * (i + 1) // steps
        draw.rectangle([x1, yy, x2, yy2], fill=(r, g, b))


def _rounded_rect(draw, xy, radius, fill=None, outline=None, ow=2):
    x1, y1, x2, y2 = xy
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    def _draw(f):
        draw.pieslice([x1, y1, x1 + r*2, y1 + r*2], 180, 270, fill=f)
        draw.pieslice([x2 - r*2, y1, x2, y1 + r*2], 270, 360, fill=f)
        draw.pieslice([x1, y2 - r*2, x1 + r*2, y2], 90, 180, fill=f)
        draw.pieslice([x2 - r*2, y2 - r*2, x2, y2], 0, 90, fill=f)
        draw.rectangle([x1 + r, y1, x2 - r, y2], fill=f)
        draw.rectangle([x1, y1 + r, x2, y2 - r], fill=f)
    if fill:
        _draw(fill)
    if outline:
        _draw(outline)


def _gloss(draw, xy):
    x1, y1, x2, y2 = xy
    for i in range(15):
        alpha = int(12 * (1 - i / 15))
        draw.rectangle([x1, y1 + i, x2, y1 + i + 1], fill=(255, 255, 255, alpha))


def _grid_bg(draw):
    for x in range(0, W, 90):
        draw.line([(x, 0), (x, H)], fill=GRID_LINE + (20,), width=1)
    for y in range(0, H, 90):
        draw.line([(0, y), (W, y)], fill=GRID_LINE + (20,), width=1)


def _sparkline(draw, xy, values, color):
    x1, y1, x2, y2 = xy
    if not values or len(values) < 2:
        return
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        vmax = vmin + 1
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        px = x1 + (x2 - x1) * i / (n - 1)
        py = y2 - (y2 - y1) * (v - vmin) / (vmax - vmin)
        pts.append((px, py))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color, width=3)
    # Glow
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color + (60,), width=7)
        break
    # Dot at end
    draw.ellipse([pts[-1][0] - 5, pts[-1][1] - 5, pts[-1][0] + 5, pts[-1][1] + 5], fill=color)


def _metric_card(draw, cx, y, label, value, color, width=220, height=90):
    x1 = cx - width // 2
    x2 = cx + width // 2
    _rounded_rect(draw, (x1, y, x2, y + height), 14, fill=(15, 25, 45, 180))
    draw.text((cx, y + 22), label, font=_font(11), fill=TEXT_GRAY, anchor="mm")
    draw.text((cx, y + 60), value, font=_font(18, bold=True), fill=color, anchor="mm")


def _conviction_bar(draw, x, y, w, h, pct, color):
    # Background
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=(30, 40, 60))
    # Fill
    if pct > 0:
        fw = max(int(w * pct / 100), 4)
        draw.rounded_rectangle([x, y, x + fw, y + h], radius=h // 2, fill=color)


def _logo_header(draw, theme):
    """Desenha logo Trader AI + tema no topo."""
    p = THEMES[theme]
    # Logo
    draw.text((40, 35), "TRADER", font=_font(22, bold=True), fill=TEXT_WHITE)
    draw.text((40, 63), "AI", font=_font(22, bold=True), fill=p["primary"])
    # Linha decorativa
    draw.line([(40, 90), (200, 90)], fill=p["primary"], width=2)
    # Tema tag à direita
    tag = p["name"]
    tw = len(tag) * 10
    _rounded_rect(draw, (W - 40 - tw - 24, 35, W - 40, 65), 10, fill=p["card_bg"], outline=p["primary"] + (60,))
    draw.text((W - 40 - 12 - tw // 2, 50), tag, font=_font(12, bold=True), fill=p["primary"], anchor="mm")


def _footer(draw, theme):
    p = THEMES[theme]
    draw.line([(40, H - 80), (W - 40, H - 80)], fill=GRID_LINE + (40,), width=1)
    draw.text((40, H - 60), "TradeAI", font=_font(11, bold=True), fill=p["primary"])
    draw.text((40, H - 40), "tradeai.vercel.app", font=_font(9), fill=TEXT_DIM)
    draw.text((W - 40, H - 50), p["hashtag"], font=_font(10, bold=True), fill=TEXT_DIM + (80,), anchor="rm")


# ═══════════════════════════════════════════════════════════════════
#  1. MODELO MERCADO
# ═══════════════════════════════════════════════════════════════════

def generate_market_image(ctx: dict) -> str:
    """
    Publicação MERCADO — 1080x1350
    Dashboard premium: gráfico de linha, BTC price, cards inferiores.
    """
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    p = THEMES["market"]

    _draw_gradient(draw, 0, 0, W, H, p["bg_top"], p["bg_bot"])
    _grid_bg(draw)

    # ── Logo + Header ──
    _logo_header(draw, "market")

    # ── Título principal ──
    draw.text((40, 125), "Mercado em Movimento", font=_font(38, bold=True), fill=TEXT_WHITE)
    draw.text((40, 170), "Análise geral do mercado em tempo real • "
              + datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC"),
              font=_font(13), fill=TEXT_GRAY)

    # ── Gráfico de linha principal ──
    chart_x1, chart_y1, chart_x2, chart_y2 = 40, 220, 1040, 520
    _rounded_rect(draw, (chart_x1, chart_y1, chart_x2, chart_y2), 18, fill=p["card_bg"], outline=PANEL_BORDER + (40,))
    _gloss(draw, (chart_x1, chart_y1, chart_x2, chart_y1 + 15))

    # Título do gráfico
    draw.text((chart_x1 + 20, chart_y1 + 15), "BTC/USDT • Preço", font=_font(12), fill=TEXT_GRAY)
    draw.text((chart_x1 + 20, chart_y1 + 38), f"${ctx.get('btc_price', 0):,.0f}",
              font=_font(36, bold=True), fill=p["primary"])

    # Variação 24h
    change = ctx.get("btc_change_24h")
    if change is not None:
        c_color = p["primary"] if change >= 0 else (255, 68, 68)
        sign = "+" if change >= 0 else ""
        draw.text((chart_x1 + 280, chart_y1 + 38), f"{sign}{change:.2f}%",
                  font=_font(18, bold=True), fill=c_color)

    # Sparkline no gráfico
    prices = ctx.get("btc_price_history", [])
    if prices and len(prices) >= 2:
        _sparkline(draw, (chart_x1 + 40, chart_y1 + 80, chart_x2 - 40, chart_y2 - 30), prices, p["primary"])
        # Labels de eixo
        draw.text((chart_x1 + 40, chart_y2 - 15), f"${min(prices):,.0f}", font=_font(9), fill=TEXT_DIM)
        draw.text((chart_x2 - 40, chart_y2 - 15), f"${max(prices):,.0f}", font=_font(9), fill=TEXT_DIM)
    else:
        # Placeholder
        draw.text(((chart_x1 + chart_x2) // 2, (chart_y1 + chart_y2) // 2),
                  "Aguardando dados de preço...", font=_font(14), fill=TEXT_DIM, anchor="mm")

    # ── Cards inferiores (2 linhas de 2) ──
    cards = [
        ("DOMÍNIO BTC", ctx.get("resumo", {}).get("btc_dominance", "58.2%")),
        ("VOLUME 24H", ctx.get("resumo", {}).get("volume_24h", "$28.4B")),
        ("FEAR & GREED", f"{ctx.get('fear_greed_value', 50)} — {ctx.get('fear_greed_label', 'Neutral')}"),
        ("REGIME", ctx.get("regime", "NEUTRAL")),
    ]
    card_w, card_h = 470, 95
    gap = 30
    start_y = 560
    for i, (label, value) in enumerate(cards):
        col = i % 2
        row = i // 2
        cx = 40 + col * (card_w + gap) + card_w // 2
        cy = start_y + row * (card_h + gap)

        # Card color
        c_color = p["primary"]
        if label == "FEAR & GREED":
            fg = ctx.get("fear_greed_value", 50)
            c_color = (255, 68, 68) if fg < 25 else (251, 191, 36) if fg < 50 else p["secondary"]
        elif label == "REGIME":
            reg = ctx.get("regime", "")
            c_color = p["primary"] if "BULL" in str(reg).upper() else (255, 68, 68) if "BEAR" in str(reg).upper() else (251, 191, 36)
        elif label == "VOLUME 24H":
            c_color = p["secondary"]

        _rounded_rect(draw, (cx - card_w // 2, cy, cx + card_w // 2, cy + card_h),
                      14, fill=p["card_bg"])
        draw.text((cx, cy + 22), label, font=_font(11), fill=TEXT_GRAY, anchor="mm")
        draw.text((cx, cy + 62), value, font=_font(20, bold=True), fill=c_color, anchor="mm")

    # ── P&L Snapshot ──
    pnl = ctx.get("pnl_total", 0)
    pnl_pct = ctx.get("pnl_pct", 0)
    sign = "+" if pnl >= 0 else ""
    pnl_color = p["primary"] if pnl >= 0 else (255, 68, 68)
    draw.text((40, 790), f"P&L Acumulado: {sign}${pnl:,.2f} ({sign}{pnl_pct:.1f}%)",
              font=_font(14, bold=True), fill=pnl_color)

    # ── Footer ──
    _footer(draw, "market")

    return _save(img, "market")


# ═══════════════════════════════════════════════════════════════════
#  2. MODELO TRADE
# ═══════════════════════════════════════════════════════════════════

def generate_trade_image(ctx: dict) -> str:
    """
    Publicação TRADE — 1080x1350
    Setup de trade com entradas, stops, alvos e convicção.
    """
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    p = THEMES["trade"]

    _draw_gradient(draw, 0, 0, W, H, p["bg_top"], p["bg_bot"])
    _grid_bg(draw)

    # ── Logo + Header ──
    _logo_header(draw, "trade")

    draw.text((40, 125), "Ideia de Trade", font=_font(38, bold=True), fill=TEXT_WHITE)
    draw.text((40, 170), "Setup técnico analisado pela IA • "
              + datetime.now(timezone.utc).strftime("%d %b %Y"),
              font=_font(13), fill=TEXT_GRAY)

    # ── Mini gráfico de candles (decorativo) ──
    _rounded_rect(draw, (40, 210, 1040, 360), 16, fill=p["card_bg"], outline=PANEL_BORDER + (40,))
    _gloss(draw, (40, 210, 1040, 225))

    # Candle stick chart decorativo
    candle_data = ctx.get("candle_history", [])
    if candle_data and len(candle_data) >= 3:
        for i, c in enumerate(candle_data[-20:]):
            open_p, high, low, close = c["open"], c["high"], c["low"], c["close"]
            is_green = close >= open_p
            c_color = p["primary"] if is_green else (255, 68, 68)
            x = 80 + i * 48
            # Wick
            draw.line([(x, int(240 + (5000 - high) / 10)), (x, int(240 + (5000 - low) / 10))],
                      fill=c_color, width=2)
            # Body
            top = min(open_p, close)
            bot = max(open_p, close)
            yt = int(240 + (5000 - top) / 10)
            yb = int(240 + (5000 - bot) / 10)
            draw.rectangle([x - 6, min(yt, yb), x + 6, max(yt, yb)], fill=c_color)
    else:
        # Candles simulados
        import random
        random.seed(42)
        price = 65000
        for i in range(20):
            change = random.uniform(-500, 500)
            o = price
            c = price + change
            h = max(o, c) + random.uniform(0, 200)
            l = min(o, c) - random.uniform(0, 200)
            is_g = c >= o
            cc = p["primary"] if is_g else (255, 68, 68)
            x = 80 + i * 48
            draw.line([(x, int(240 + (5000 - h) / 10)), (x, int(240 + (5000 - l) / 10))], fill=cc, width=2)
            t, b = min(o, c), max(o, c)
            yt = int(240 + (5000 - t) / 10)
            yb = int(240 + (5000 - b) / 10)
            draw.rectangle([x - 6, min(yt, yb), x + 6, max(yt, yb)], fill=cc)
            price = c

    # ── Card principal: Dados do Trade ──
    trades = ctx.get("ultimos_trades", [])
    trade = trades[0] if trades else {}

    symbol = trade.get("symbol", "BTC/USDT")
    side = trade.get("side", "LONG").upper()
    entry = trade.get("entry_price", ctx.get("btc_price", 65000))
    tp1 = trade.get("tp1", entry * 1.02)
    tp2 = trade.get("tp2", entry * 1.04)
    sl = trade.get("sl", entry * 0.98)
    conviction = trade.get("conviction", 78)

    # Esquerda: Info do par
    _rounded_rect(draw, (40, 400, 520, 620), 16, fill=p["card_bg"])
    _gloss(draw, (40, 400, 520, 415))

    draw.text((280, 430), symbol, font=_font(28, bold=True), fill=TEXT_WHITE, anchor="mm")

    # Badge LONG/SHORT
    side_color = p["primary"] if side == "LONG" else (255, 68, 68)
    _rounded_rect(draw, (280 - 50, 458, 280 + 50, 482), 8, fill=side_color + (40,), outline=side_color + (80,))
    draw.text((280, 470), side, font=_font(14, bold=True), fill=side_color, anchor="mm")

    # Entrada
    draw.text((280, 510), "Entrada", font=_font(11), fill=TEXT_GRAY, anchor="mm")
    draw.text((280, 540), f"${entry:,.0f}", font=_font(26, bold=True), fill=p["secondary"], anchor="mm")

    # Risco/Retorno
    risk = abs(entry - sl)
    reward = abs(tp1 - entry)
    rr = reward / risk if risk > 0 else 0
    draw.text((280, 580), f"Risco:Retorno 1:{rr:.1f}", font=_font(14, bold=True), fill=TEXT_GRAY, anchor="mm")

    # Direita: Alvos e Stop
    _rounded_rect(draw, (560, 400, 1040, 620), 16, fill=p["card_bg"])
    _gloss(draw, (560, 400, 1040, 415))

    targets = [("TP 1", tp1, p["primary"]), ("TP 2", tp2, p["secondary"]), ("STOP", sl, (255, 68, 68))]
    for i, (label, price_t, color) in enumerate(targets):
        y = 440 + i * 65
        draw.text((640, y), label, font=_font(12), fill=TEXT_GRAY, anchor="mm")
        draw.text((640, y + 25), f"${price_t:,.0f}", font=_font(18, bold=True), fill=color, anchor="mm")
        if i < 2:
            draw.line([(560, y + 45), (1040, y + 45)], fill=GRID_LINE + (40,), width=1)

    # ── Barra de Convicção ──
    _rounded_rect(draw, (40, 660, 1040, 720), 14, fill=p["card_bg"])
    draw.text((60, 690), f"Convicção da Operação: {conviction}%", font=_font(14, bold=True), fill=TEXT_WHITE, anchor="lm")
    _conviction_bar(draw, 350, 685, 500, 14, conviction, p["primary"])

    # ── Últimos resultados ──
    _rounded_rect(draw, (40, 760, 1040, 920), 16, fill=p["card_bg"])
    _gloss(draw, (40, 760, 1040, 775))
    draw.text((60, 790), "Últimos Trades", font=_font(14, bold=True), fill=p["secondary"])

    y = 830
    for t in trades[:4]:
        t_color = p["primary"] if t.get("pnl", 0) >= 0 else (255, 68, 68)
        em = "✅" if t.get("pnl", 0) >= 0 else "❌"
        s = "+" if t.get("pnl", 0) >= 0 else ""
        draw.text((80, y), f"{em} {t.get('symbol', '???')} {t.get('side', '').upper()[:4]}  {s}${t.get('pnl', 0):,.2f}",
                  font=_font(14, bold=True), fill=t_color, anchor="lm")
        y += 40

    # ── Win Rate ──
    wr = ctx.get("win_rate_recente", 0)
    wr_color = p["primary"] if wr >= 50 else (251, 191, 36) if wr >= 30 else (255, 68, 68)
    draw.text((600, 830), f"Win Rate: {wr}%", font=_font(18, bold=True), fill=wr_color, anchor="mm")

    wins = sum(1 for t in trades if t.get("pnl", 0) >= 0)
    total = len(trades)
    if total > 0:
        losses = total - wins
        _conviction_bar(draw, 600, 870, 350, 12, wins / total * 100 if total else 0, p["primary"])
        draw.text((600, 895), f"{wins}W / {losses}L", font=_font(11), fill=TEXT_GRAY, anchor="mm")

    # ── Footer ──
    _footer(draw, "trade")

    return _save(img, "trade")


# ═══════════════════════════════════════════════════════════════════
#  3. MODELO INSIGHTS
# ═══════════════════════════════════════════════════════════════════

def generate_insight_image(ctx: dict) -> str:
    """
    Publicação INSIGHTS — 1080x1350
    Inteligência de mercado com 3 insights principais.
    """
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    p = THEMES["insight"]

    _draw_gradient(draw, 0, 0, W, H, p["bg_top"], p["bg_bot"])
    _grid_bg(draw)

    # ── Logo + Header ──
    _logo_header(draw, "insight")

    draw.text((40, 125), "Insight AI", font=_font(38, bold=True), fill=TEXT_WHITE)
    draw.text((40, 170), "Inteligência de mercado • Análise institucional • "
              + datetime.now(timezone.utc).strftime("%d %b %Y"),
              font=_font(13), fill=TEXT_GRAY)

    # ── Pergunta principal ──
    question = ctx.get("question", "O que a IA está enxergando no mercado?")
    _rounded_rect(draw, (40, 210, 1040, 300), 16, fill=p["card_bg"], outline=p["primary"] + (40,))
    draw.text((540, 235), "⚡", font=_font(28), fill=p["primary"], anchor="mm")
    draw.text((540, 280), question, font=_font(20, bold=True), fill=p["primary"], anchor="mm")

    # ── 3 Insights ──
    insights = ctx.get("insights", [
        {"icon": "📊", "title": "Acumulação em Large Caps",
         "desc": "Baleias estão acumulando BTC e ETH em carteiras frias. Fluxo de exchange em baixa."},
        {"icon": "💧", "title": "Liquidez Concentrada",
         "desc": "Liquidez está migrando para DEXs. CEXs perdem dominância — sinal de maturidade do mercado."},
        {"icon": "📈", "title": "Tendência de Alta",
         "desc": "Estrutura de mercado favorece alta no curto prazo. Suporte em $62k e resistência em $72k."},
    ])

    insight_y = 340
    for i, ins in enumerate(insights):
        y = insight_y + i * 220
        _rounded_rect(draw, (40, y, 1040, y + 190), 16, fill=p["card_bg"])
        if i == 0:
            _gloss(draw, (40, y, 1040, y + 15))

        # Ícone grande
        draw.text((100, y + 50), ins["icon"], font=_font(36), anchor="mm")
        # Título
        draw.text((160, y + 30), ins["title"], font=_font(18, bold=True), fill=TEXT_WHITE, anchor="lm")
        # Descrição
        draw.text((160, y + 60), ins["desc"], font=_font(13), fill=TEXT_GRAY, anchor="lm")
        # Linha decorativa
        draw.line([(160, y + 135), (1000, y + 135)], fill=p["primary"] + (40,), width=1)

        # Tag inferior
        tags = ["Acumulação", "Liquidez", "Tendência"]
        _rounded_rect(draw, (160, y + 145, 160 + len(tags[i]) * 10 + 24, y + 170),
                      8, fill=p["primary"] + (30,))
        draw.text((160 + len(tags[i]) * 5 + 12, y + 157), tags[i], font=_font(9, bold=True), fill=p["primary"], anchor="mm")

    # ── Resumo da IA ──
    _rounded_rect(draw, (40, 980, 1040, 1080), 16, fill=p["card_bg"], outline=p["primary"] + (40,))
    _gloss(draw, (40, 980, 1040, 995))
    draw.text((540, 1010), "🤖 Resumo da IA", font=_font(14, bold=True), fill=p["primary"], anchor="mm")
    ai_summary = ctx.get("ai_summary",
                         "Mercado apresenta sinais mistos. Acumulação institucional contrasta com "
                         "baixa liquidez de varejo. Cenário de médio prazo segue construtivo.")
    draw.text((540, 1050), ai_summary, font=_font(13), fill=TEXT_GRAY, anchor="mm")

    # ── Footer ──
    _footer(draw, "insight")

    return _save(img, "insight")


# ═══════════════════════════════════════════════════════════════════
#  4. MODELO NOTÍCIA
# ═══════════════════════════════════════════════════════════════════

def generate_news_image(ctx: dict) -> str:
    """
    Publicação NOTÍCIA — 1080x1350
    Capa de notícia financeira premium com headline, impacto e fonte.
    """
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    p = THEMES["news"]

    _draw_gradient(draw, 0, 0, W, H, p["bg_top"], p["bg_bot"])
    _grid_bg(draw)

    # ── Logo + Header ──
    _logo_header(draw, "news")

    # ── Tag NOTÍCIA ──
    _rounded_rect(draw, (40, 115, 40 + 100, 145), 10, fill=p["primary"] + (60,), outline=p["primary"] + (80,))
    draw.text((90, 130), "NOTÍCIA", font=_font(12, bold=True), fill=p["primary"], anchor="mm")

    draw.text((160, 130), datetime.now(timezone.utc).strftime("%d %b %Y"),
              font=_font(13), fill=TEXT_GRAY, anchor="lm")

    # ── Headline grande ──
    headline = ctx.get("headline", "ETF de Ethereum à Vista: "
                        "SEC Aprova os Primeiros Fundos Spot de ETH nos EUA")
    draw.text((40, 180), headline, font=_font(32, bold=True), fill=TEXT_WHITE)

    # ── Imagem/Ilustração (placeholder com gradiente + símbolo) ──
    img_x1, img_y1, img_x2, img_y2 = 40, 280, 1040, 520
    _rounded_rect(draw, (img_x1, img_y1, img_x2, img_y2), 18, fill=(20, 10, 35))
    _draw_gradient(draw, img_x1, img_y1, img_x2, img_y2, (30, 15, 50), (15, 5, 25))

    # Ilustração central
    symbol = ctx.get("news_symbol", "ETH")
    icons = {"BTC": "₿", "ETH": "⟠", "SOL": "◎", "DEFAULT": "◈"}
    icon_text = icons.get(symbol.upper(), icons["DEFAULT"])

    # Glow do ícone
    for r in range(40, 0, -5):
        alpha = int(15 * (1 - r / 40))
        draw.ellipse([540 - r, 400 - r, 540 + r, 400 + r], fill=p["primary"] + (alpha,))

    draw.text((540, 380), icon_text, font=_font(60), fill=p["primary"], anchor="mm")
    draw.text((540, 450), symbol.upper(), font=_font(28, bold=True), fill=TEXT_WHITE, anchor="mm")

    # Grid decorativo na imagem
    for x in range(img_x1, img_x2, 60):
        draw.line([(x, img_y1), (x, img_y2)], fill=(255, 255, 255, 8), width=1)
    for y in range(img_y1, img_y2, 60):
        draw.line([(img_x1, y), (img_x2, y)], fill=(255, 255, 255, 8), width=1)

    # ── Resumo da notícia ──
    summary = ctx.get("summary",
                      "A SEC aprovou os primeiros ETFs spot de Ethereum nos Estados Unidos, "
                      "marcando um marco histórico para o mercado cripto. Os fundos começam "
                      "a ser negociados esta semana.")
    _rounded_rect(draw, (40, 560, 1040, 660), 16, fill=p["card_bg"])
    draw.text((60, 590), "📰", font=_font(20), anchor="lm")
    draw.text((100, 590), summary, font=_font(14), fill=TEXT_GRAY, anchor="lm")

    # ── Box: Impacto no Mercado ──
    _rounded_rect(draw, (40, 700, 1040, 830), 16, fill=p["card_bg"], outline=p["primary"] + (40,))
    _gloss(draw, (40, 700, 1040, 715))
    draw.text((540, 725), "📊 Impacto no Mercado", font=_font(16, bold=True), fill=p["primary"], anchor="mm")

    impacts_raw = ctx.get("impacts", [
        ("Preço ETH", "+8.5%"),
        ("Preço BTC", "+2.1%"),
        ("Volume DEX", "+$420M"),
    ])
    impacts = [ (item[0], item[1], item[2] if len(item) > 2 else p["primary"]) for item in impacts_raw ]
    for i, (label, value, color) in enumerate(impacts):
        cx = 250 + i * 320
        draw.text((cx, 765), label, font=_font(12), fill=TEXT_GRAY, anchor="mm")
        draw.text((cx, 800), value, font=_font(22, bold=True), fill=color, anchor="mm")

    # ── Fonte ──
    source = ctx.get("source", "CoinDesk • Reuters • Bloomberg")
    draw.text((40, 880), f"Fonte: {source}", font=_font(12), fill=TEXT_DIM, anchor="lm")

    # ── Footer ──
    _footer(draw, "news")

    return _save(img, "news")


# ═══════════════════════════════════════════════════════════════════
#  Salvar
# ═══════════════════════════════════════════════════════════════════

def _save(img: Image.Image, topic: str) -> str:
    """Converte para RGB e salva como PNG."""
    rgb = Image.new("RGB", (W, H), (0, 0, 0))
    rgb.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
    filename = f"{topic}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
    filepath = OUTPUT_DIR / filename
    rgb.save(filepath, quality=95)
    logger.info(f"[biel/visual] Publicação salva: {filepath}")
    return str(filepath)


# ═══════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════

async def generate_image(context: dict, topic: str) -> str:
    """Gera publicação conforme o tópico usando o modelo apropriado."""
    loop = asyncio.get_event_loop()
    if topic == "trade":
        return await loop.run_in_executor(None, generate_trade_image, context)
    elif topic == "insight":
        return await loop.run_in_executor(None, generate_insight_image, context)
    elif topic == "news":
        return await loop.run_in_executor(None, generate_news_image, context)
    else:
        return await loop.run_in_executor(None, generate_market_image, context)
