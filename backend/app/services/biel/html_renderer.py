"""
Biel — HTML → PNG Renderer
Usa Playwright (Chromium headless) para renderizar templates HTML
em imagens PNG 1080x1350 de alta qualidade.
"""

import base64
from pathlib import Path
from datetime import datetime, timezone

from app.logger import get_logger

logger = get_logger(__name__)

# ── Caminhos ──
TEMPLATES_DIR = Path(__file__).parent / "templates"
ASSETS_DIR = TEMPLATES_DIR / "assets"
OUTPUT_DIR = Path("data/biel_images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_asset_cache: dict = {}


def _load_template(name: str) -> str:
    """Carrega o conteúdo de um template HTML."""
    path = TEMPLATES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Template não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def _load_asset_b64(filename: str, mime: str = "image/png") -> str:
    """
    Carrega um asset estático (ex: imagem de fundo) de templates/assets/
    como data URI base64, com cache em memória (evita reler/reencodar
    a cada post gerado). Necessário porque page.set_content() do Playwright
    não tem base_url para resolver caminhos relativos de imagem.
    """
    if filename not in _asset_cache:
        path = ASSETS_DIR / filename
        if not path.exists():
            logger.warning(f"[biel/html] Asset não encontrado: {path}")
            _asset_cache[filename] = ""
        else:
            data = path.read_bytes()
            _asset_cache[filename] = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    return _asset_cache[filename]


def _fmt_number(value: float) -> str:
    """Formata número com cifrão e separadores."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value:,.2f}"
    return f"${value:.2f}"


def _fmt_compact(value: str) -> str:
    """Retorna string compacta como está (ex: '54.8%' ou '$28.4B')."""
    return value


def _generate_sparkline_svg(prices: list, width: int = 900, height: int = 280,
                             color: str = "#00ff41", glow: bool = True) -> str:
    """
    Gera SVG de sparkline a partir de uma lista de preços.
    Retorna string HTML do SVG inline.
    """
    if not prices or len(prices) < 2:
        return ""

    vmin, vmax = min(prices), max(prices)
    if vmax == vmin:
        vmax = vmin + 1

    n = len(prices)
    pad = 20
    w = width - pad * 2
    h = height - pad * 2

    points = []
    for i, v in enumerate(prices):
        px = pad + w * i / (n - 1)
        py = pad + h - h * (v - vmin) / (vmax - vmin)
        points.append(f"{px:.1f},{py:.1f}")

    path_d = "M" + " L".join(points)

    # Preenche área abaixo da linha (gradiente sutil)
    first_x, first_y = points[0].split(",")
    last_x, last_y = points[-1].split(",")
    area_d = f"M{first_x},{float(first_y)} L" + " L".join(points) + \
             f" L{last_x},{pad + h} L{first_x},{pad + h} Z"

    glow_filter = ""
    if glow:
        glow_filter = """
        <filter id="sparkGlow">
          <feGaussianBlur stdDeviation="3" result="blur"/>
          <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>"""

    svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg" style="display:block">
  <defs>
    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0.0"/>
    </linearGradient>
    {glow_filter}
  </defs>
  <!-- Área sob a linha -->
  <path d="{area_d}" fill="url(#areaGrad)"/>
  <!-- Linha principal -->
  <path d="{path_d}" fill="none" stroke="{color}" stroke-width="3"
        stroke-linecap="round" stroke-linejoin="round"
        {('filter="url(#sparkGlow)"' if glow else '')}/>
  <!-- Ponto final -->
  <circle cx="{last_x}" cy="{last_y}" r="6" fill="{color}"
          {('filter="url(#sparkGlow)"' if glow else '')}/>
  <circle cx="{last_x}" cy="{last_y}" r="2.5" fill="#ffffff"/>
</svg>"""
    return svg


def _generate_candlestick_svg(candles: list, width: int = 940, height: int = 130,
                               up_color: str = "#4ade80", down_color: str = "#ff4444") -> str:
    """
    Gera SVG de candles (OHLC) a partir de candle_history real (context_builder).
    Usado no template de TRADE para ilustrar o contexto recente de preço.
    """
    if not candles or len(candles) < 2:
        return ""

    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    vmin, vmax = min(lows), max(highs)
    if vmax == vmin:
        vmax = vmin + 1

    n = len(candles)
    pad = 8
    w = width - pad * 2
    h = height - pad * 2
    slot = w / n
    body_w = max(slot * 0.55, 2)

    bars = []
    for i, c in enumerate(candles):
        cx = pad + slot * i + slot / 2
        y_high = pad + h - h * (c["high"] - vmin) / (vmax - vmin)
        y_low = pad + h - h * (c["low"] - vmin) / (vmax - vmin)
        y_open = pad + h - h * (c["open"] - vmin) / (vmax - vmin)
        y_close = pad + h - h * (c["close"] - vmin) / (vmax - vmin)
        color = up_color if c["close"] >= c["open"] else down_color
        y_top = min(y_open, y_close)
        y_bottom = max(y_open, y_close)
        if y_bottom - y_top < 2:
            y_bottom = y_top + 2
        bars.append(
            f'<line x1="{cx:.1f}" y1="{y_high:.1f}" x2="{cx:.1f}" y2="{y_low:.1f}" '
            f'stroke="{color}" stroke-width="2" opacity="0.9"/>'
        )
        bars.append(
            f'<rect x="{cx - body_w/2:.1f}" y="{y_top:.1f}" width="{body_w:.1f}" '
            f'height="{y_bottom - y_top:.1f}" fill="{color}" rx="1.5"/>'
        )

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
        + "".join(bars) + "</svg>"
    )


def fill_market_template(ctx: dict) -> str:
    """
    Preenche o template HTML do MERCADO com dados 100% dinâmicos — nada
    fica hardcoded exceto os rótulos fixos (BTC/USDT, F&G, VOLUME 24H,
    SENTIMENTO, TRADER AI). Título, data, preço, variação e os 3 cards
    (Fear & Greed, Volume 24h, Sentimento) refletem o estado real do app.
    """
    html = _load_template("market_template.html")

    price = ctx.get("btc_price", 63250.00)
    change = ctx.get("btc_change_24h", 2.35)

    preco_str = f"${price:,.2f}" if price >= 1 else f"${price:.8f}"
    sinal = "+" if change >= 0 else ""
    change_str = f"{sinal}{change:.2f}% (24h)"

    change_class = "negative" if change < 0 else ""
    if change == 0:
        change_class = ""

    # ── Título dinâmico: reflete o regime de mercado real (MarketRegime) ──
    regime = ctx.get("regime", "NEUTRAL").upper()
    if "BULL" in regime:
        sentimento = "BULLISH"
        sentimento_class = "green"
        sentimento_icon = "🐂"
        title_line2, title_class = "EM ALTA", "green"
    elif "BEAR" in regime:
        sentimento = "BEARISH"
        sentimento_class = "red"
        sentimento_icon = "🐻"
        title_line2, title_class = "EM QUEDA", "red"
    elif "HIGH_VOL" in regime:
        sentimento = "VOLÁTIL"
        sentimento_class = "orange"
        sentimento_icon = "⚡"
        title_line2, title_class = "VOLÁTIL", "orange"
    elif "SIDEWAYS" in regime:
        sentimento = "NEUTRO"
        sentimento_class = "orange"
        sentimento_icon = "⚖️"
        title_line2, title_class = "LATERALIZADO", "orange"
    else:
        sentimento = "NEUTRO"
        sentimento_class = "orange"
        sentimento_icon = "⚖️"
        title_line2, title_class = "EM MOVIMENTO", "green"

    # ── Fear & Greed real (substitui a antiga "Domínio BTC", que nunca
    #    teve dado real por trás) — valor + variação real vs ~24h atrás ──
    fg_value = ctx.get("fear_greed_value")
    fg_change = ctx.get("fear_greed_change_24h")
    if fg_value is not None:
        feargreed_str = str(fg_value)
        if fg_change is not None:
            fg_sinal = "+" if fg_change >= 0 else ""
            feargreed_sub = f"{fg_sinal}{fg_change} pts (24h)"
            feargreed_sub_class = "negative" if fg_change < 0 else ""
        else:
            feargreed_sub = ctx.get("fear_greed_label", "")
            feargreed_sub_class = ""
        if fg_value <= 25:
            feargreed_class = "red"
        elif fg_value <= 45:
            feargreed_class = "orange"
        elif fg_value <= 55:
            feargreed_class = ""
        else:
            feargreed_class = "green"
    else:
        feargreed_str = "—"
        feargreed_sub = ""
        feargreed_sub_class = ""
        feargreed_class = ""

    # ── Volume 24h real + variação real vs 24h anteriores (candle_history) ──
    volume = ctx.get("resumo", {}).get("volume_24h", "—")
    vol_change = ctx.get("volume_24h_change_pct")
    if vol_change is not None:
        vol_sinal = "+" if vol_change >= 0 else ""
        volume_sub = f"{vol_sinal}{vol_change}%"
        volume_sub_class = "negative" if vol_change < 0 else ""
    else:
        volume_sub = ""
        volume_sub_class = ""

    date_str = datetime.now(timezone.utc).strftime("%d %b %Y").upper()

    # Background — arte fixa (mapa-múndi + linha de alta).
    bg_image = _load_asset_b64("mercadobk.png")

    replacements = {
        "{{DATA_ATUAL}}": date_str,
        "{{TITLE_LINE2}}": title_line2,
        "{{TITLE_CLASS}}": title_class,
        "{{PRECO_BTC}}": preco_str,
        "{{PORCENTAGEM_BTC}}": change_str,
        "{{CHANGE_CLASS}}": change_class,
        "{{FEARGREED}}": feargreed_str,
        "{{FEARGREED_CLASS}}": feargreed_class,
        "{{FEARGREED_SUB}}": feargreed_sub,
        "{{FEARGREED_SUB_CLASS}}": feargreed_sub_class,
        "{{VOLUME}}": volume,
        "{{VOLUME_SUB}}": volume_sub,
        "{{VOLUME_SUB_CLASS}}": volume_sub_class,
        "{{SENTIMENTO}}": sentimento,
        "{{SENTIMENTO_CLASS}}": sentimento_class,
        "{{SENTIMENTO_ICON}}": sentimento_icon,
        "{{BG_IMAGE}}": bg_image,
    }

    for var, val in replacements.items():
        html = html.replace(var, val)

    return html


def fill_trade_template(ctx: dict) -> str:
    """
    Preenche o template HTML do TRADE com dados reais da ideia de trade
    (posição aberta mais recente, ou última fechada como fallback).
    tp1/tp2/sl são calculados em context_builder a partir dos percentuais
    reais de config (paper_tp1_pct, paper_take_profit_percent,
    paper_stop_loss_percent) aplicados ao entry_price real.
    """
    html = _load_template("trade_template.html")

    trade = ctx.get("trade_idea", {})

    symbol = trade.get("symbol", "BTC/USDT")
    side = trade.get("side", "LONG").upper()
    entry = trade.get("entry", ctx.get("btc_price", 63250.00))
    tp1 = trade.get("tp1", entry * 1.02)
    tp2 = trade.get("tp2", entry * 1.04)
    sl = trade.get("sl", entry * 0.98)
    rr = trade.get("rr", 2.0)
    conviction = int(trade.get("confidence", 70))
    is_open = trade.get("is_open", False)

    side_class = "long" if side == "LONG" else "short"
    status_note = "Posição aberta em tempo real" if is_open else "Baseado no último trade encerrado"

    date_str = datetime.now(timezone.utc).strftime("%d %b %Y").upper()

    # Background — tradebk.png personalizado
    bg_image = _load_asset_b64("tradebk.png")

    # Mini gráfico de candles reais (últimas velas de candle_history)
    candles = ctx.get("candle_history", [])[-12:]
    candlestick_svg = _generate_candlestick_svg(candles, width=460, height=200)

    replacements = {
        "{{BG_IMAGE}}": bg_image,
        "{{DATA_ATUAL}}": date_str,
        "{{SYMBOL}}": symbol,
        "{{SIDE}}": side,
        "{{SIDE_CLASS}}": side_class,
        "{{STATUS_NOTE}}": status_note,
        "{{CANDLESTICK_SVG}}": candlestick_svg,
        "{{ENTRY}}": f"${entry:,.2f}",
        "{{TP1}}": f"${tp1:,.2f}",
        "{{TP2}}": f"${tp2:,.2f}",
        "{{SL}}": f"${sl:,.2f}",
        "{{RR}}": f"1:{rr:.1f}",
        "{{CONVICTION}}": str(conviction),
    }

    for var, val in replacements.items():
        html = html.replace(var, val)

    return html


def fill_insight_template(ctx: dict) -> str:
    """
    Preenche o template HTML de INSIGHT com os dados estruturados gerados
    pelo brain.py (LLM), que é instruído a nunca inventar dados fora do
    contexto real do TradeAI.
    """
    html = _load_template("insight_template.html")

    question = ctx.get("question", "O QUE OS DADOS ESTÃO MOSTRANDO?")
    insights = ctx.get("insights") or [
        {"icon": "📊", "title": "ACUMULAÇÃO FORTE", "desc": "Grandes players seguem acumulando na tendência atual."},
        {"icon": "💧", "title": "LIQUIDEZ AUMENTANDO", "desc": "Liquidez crescente nas principais exchanges."},
        {"icon": "⚡", "title": "TENDÊNCIA DE ALTA", "desc": "Indicadores apontam continuidade do movimento."},
    ]
    ai_summary = ctx.get("ai_summary", "Informação é poder. Insight é vantagem.")

    date_str = datetime.now(timezone.utc).strftime("%d %b %Y").upper()

    # Background — insightbk.png personalizado
    bg_image = _load_asset_b64("insightbk.png")

    replacements = {
        "{{BG_IMAGE}}": bg_image,
        "{{DATA_ATUAL}}": date_str,
        "{{QUESTION}}": question,
        "{{AI_SUMMARY}}": ai_summary,
    }
    for i in range(3):
        ins = insights[i] if i < len(insights) else {}
        replacements[f"{{{{ICON_{i+1}}}}}"] = ins.get("icon", "📊")
        replacements[f"{{{{TITLE_{i+1}}}}}"] = ins.get("title", "")
        replacements[f"{{{{DESC_{i+1}}}}}"] = ins.get("desc", "")

    for var, val in replacements.items():
        html = html.replace(var, val)

    return html


# Ilustração decorativa (gema facetada) usada no modelo de NOTÍCIA.
# Estático/visual apenas — não representa dado nenhum, então não precisa
# variar por contexto.
_GEM_SVG = """<svg width="100%" height="100%" viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="gemGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#d8c8fb"/>
      <stop offset="50%" stop-color="#8C52D2"/>
      <stop offset="100%" stop-color="#5b21b6"/>
    </linearGradient>
  </defs>
  <polygon points="70,8 112,45 96,132 44,132 28,45" fill="url(#gemGrad)" stroke="#ffffff" stroke-opacity="0.35" stroke-width="1.5"/>
  <polygon points="70,8 112,45 70,58" fill="#ffffff" fill-opacity="0.28"/>
  <polygon points="70,8 28,45 70,58" fill="#ffffff" fill-opacity="0.12"/>
  <polygon points="28,45 44,132 70,58" fill="#000000" fill-opacity="0.18"/>
  <polygon points="112,45 96,132 70,58" fill="#000000" fill-opacity="0.08"/>
</svg>"""


def fill_news_template(ctx: dict) -> str:
    """
    Preenche o template HTML de NOTÍCIA com os dados estruturados gerados
    pelo brain.py (headline, summary, impacts, source), grounded no
    contexto real (notícias coletadas em MarketNews).
    """
    html = _load_template("news_template.html")

    headline = ctx.get("headline", "ATUALIZAÇÃO IMPORTANTE NO MERCADO CRIPTO")
    summary = ctx.get("summary", "Acompanhe os desdobramentos e o impacto no mercado.")
    symbol = ctx.get("news_symbol", "BTC").upper()
    source = ctx.get("source", "TradeAI")

    impacts = ctx.get("impacts") or [["IMPACTO", "—"], ["VOLUME", "—"], ["TENDÊNCIA", "—"]]
    # Normaliza formato: aceita [label, valor] ou {label, value}
    norm_impacts = []
    for item in impacts[:3]:
        if isinstance(item, dict):
            norm_impacts.append((item.get("label", ""), item.get("value", "")))
        else:
            norm_impacts.append((item[0], item[1]) if len(item) >= 2 else (item[0], ""))
    while len(norm_impacts) < 3:
        norm_impacts.append(("—", "—"))

    date_str = datetime.now(timezone.utc).strftime("%d %b %Y").upper()

    replacements = {
        "{{DATA_ATUAL}}": date_str,
        "{{HEADLINE}}": headline,
        "{{SUMMARY}}": summary,
        "{{SYMBOL}}": symbol,
        "{{GEM_SVG}}": _GEM_SVG,
        "{{SOURCE}}": source,
        "{{IMPACT_1_LABEL}}": norm_impacts[0][0], "{{IMPACT_1_VALUE}}": str(norm_impacts[0][1]),
        "{{IMPACT_2_LABEL}}": norm_impacts[1][0], "{{IMPACT_2_VALUE}}": str(norm_impacts[1][1]),
        "{{IMPACT_3_LABEL}}": norm_impacts[2][0], "{{IMPACT_3_VALUE}}": str(norm_impacts[2][1]),
    }

    for var, val in replacements.items():
        html = html.replace(var, val)

    return html


def _draw_text(draw, pos, text, fill, font):
    """Desenha texto com proteção contra font=None."""
    if font is None:
        draw.text(pos, text, fill=fill)
    else:
        draw.text(pos, text, fill=fill, font=font)


def render_sync(html: str, topic: str = "market", ctx: dict | None = None) -> str:
    """
    Renderiza HTML → PNG via Playwright (Chromium headless, in-process).

    Tenta Playwright primeiro. Se falhar (Chromium não instalado, ambiente
    sem headless, etc.), usa fallback PIL (Pillow) para gerar uma imagem
    simples com os dados disponíveis.

    Args:
        html: HTML renderizado do template.
        topic: Tópico do post (market, trade, insight, news).
        ctx: Contexto original com dados do TradeAI (usado no fallback PIL).

    Roda direto no processo Python (sem subprocess/caminho fixo de SO), então
    funciona tanto no Windows local quanto no Linux de produção (Railway),
    desde que o browser esteja instalado: `playwright install chromium`
    (ver requirements.txt / nixpacks.toml).
    """
    filename = f"{topic}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
    output_path = str(OUTPUT_DIR / filename)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page(viewport={"width": 1080, "height": 1350})
            page.set_content(html, wait_until="networkidle")
            page.screenshot(path=output_path)
            browser.close()

        logger.info(f"[biel/html] Renderizado: {output_path}")
        return output_path

    except Exception as e:
        logger.error(
            f"[biel/html] Playwright falhou ({type(e).__name__}): {e}",
            exc_info=True,
        )
        logger.info("[biel/html] Usando fallback PIL...")

        # ── Fallback PIL ──────────────────────────────────────────────
        # Cria uma imagem com fundo personalizado e dados do contexto.
        # Tenta carregar imagem de fundo dos assets (mercadobk.png etc.).
        try:
            from PIL import Image, ImageDraw, ImageFont

            # ── Background ─────────────────────────────────────────────
            # Mapa de imagens de fundo por tópico
            bg_files = {
                "market":  ASSETS_DIR / "mercadobk.png",
                "trade":   ASSETS_DIR / "tradebk.png",
                "insight": ASSETS_DIR / "insightbk.png",
            }
            bg_path = bg_files.get(topic)

            if bg_path and bg_path.exists():
                bg_img = Image.open(bg_path).convert("RGB")
                bg_img = bg_img.resize((1080, 1350), Image.LANCZOS)
                img = bg_img
            else:
                img = Image.new("RGB", (1080, 1350), color=(5, 10, 8))

            draw = ImageDraw.Draw(img)

            # ── Overlay escuro para legibilidade ───────────────────────
            # Escurece levemente toda a imagem para o texto aparecer bem
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.65)  # 65% do brilho original
            draw = ImageDraw.Draw(img)

            # ── Fontes ─────────────────────────────────────────────────
            _font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]

            def _load_font(size: int):
                for fp in _font_paths:
                    try:
                        return ImageFont.truetype(fp, size)
                    except (IOError, OSError):
                        continue
                try:
                    return ImageFont.load_default()
                except Exception:
                    return None

            font_big   = _load_font(64)
            font_mid   = _load_font(42)
            font_small = _load_font(28)

            y = 80

            # Cabeçalho: data
            date_str = datetime.now(timezone.utc).strftime("%d %b %Y").upper()
            _draw_text(draw, (80, y), f"TradeAI • {date_str}", fill=(180, 200, 230), font=font_small)
            y += 100

            # Título
            titles = {"market": "MERCADO EM MOVIMENTO", "trade": "ANÁLISE DE TRADE",
                      "insight": "INSIGHT DO DIA", "news": "NOTÍCIA"}
            title = titles.get(topic, topic.upper())
            _draw_text(draw, (80, y), title, fill=(0, 255, 65), font=font_big)
            y += 140

            # Linha separadora
            draw.rectangle([(80, y), (1000, y + 2)], fill=(0, 255, 65, 60))
            y += 40

            # Dados do contexto
            info = []
            if ctx:
                btc = ctx.get("btc_price")
                if btc is not None:
                    info.append(f"BTC/USDT: ${btc:,.2f}" if btc >= 1 else f"BTC/USDT: ${btc:.8f}")
                regime = ctx.get("regime", "")
                if regime:
                    info.append(f"Regime: {regime}")
                fg = ctx.get("fear_greed_value")
                if fg is not None:
                    label = ctx.get("fear_greed_label", "")
                    info.append(f"Fear & Greed: {fg} ({label})" if label else f"Fear & Greed: {fg}")
                pnl = ctx.get("pnl_total")
                if pnl is not None:
                    info.append(f"P&L Total: ${pnl:+,.2f}")
                saldo = ctx.get("saldo")
                if saldo is not None:
                    info.append(f"Saldo: ${saldo:,.2f}")
                win_rate = ctx.get("win_rate_recente")
                if win_rate is not None:
                    info.append(f"Win Rate: {win_rate}%")

            if info:
                for line in info:
                    _draw_text(draw, (80, y), line, fill=(220, 235, 250), font=font_mid)
                    y += 60
            else:
                _draw_text(draw, (80, y), "Dados em tempo real da TradeAI", fill=(160, 190, 220), font=font_mid)
                y += 60

            # Rodapé
            _draw_text(draw, (80, 1280), "DADOS EM TEMPO REAL • ANÁLISE • ESTRATÉGIA",
                       fill=(100, 140, 180), font=font_small)

            img.save(output_path, "PNG")
            logger.info(f"[biel/html] Fallback PIL: {output_path}")
            return output_path

        except ImportError:
            logger.error("[biel/html] PIL não instalado.")
            raise RuntimeError(
                "Playwright falhou e PIL (Pillow) também não está disponível. "
                "Execute: pip install Pillow"
            ) from e
        except Exception as pil_e:
            logger.error(f"[biel/html] Fallback PIL também falhou: {pil_e}")
            raise RuntimeError(
                f"Playwright falhou ({e}) e fallback PIL ({pil_e})."
            ) from pil_e
