"""
Biel — Reel Generator (v2)
Cria vídeos Reels (9:16, 1080x1920) com:
  - 3 cenas renderizadas via Playwright (HTML → PNG)
  - Efeito Ken Burns (zoom suave) em cada cena
  - Transições crossfade entre cenas
  - Narração por voz (edge-tts, gratuito) + legenda sincronizada
  - Música de fundo opcional (assets locais versionados)
  - Texto e dados dinâmicos via templates HTML

Pipeline: HTML template → Playwright PNG → ffmpeg video (zoompan + crossfade + narração + legenda + audio)
"""

import os
import json
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from app.logger import get_logger

logger = get_logger(__name__)


def _clean_ffmpeg_error(stderr: str, max_len: int = 1200) -> str:
    """
    O ffmpeg imprime dezenas de linhas de progresso ("frame=0 fps=0.0 ...")
    que, sem TTY, viram uma linha nova a cada atualização — isso lota
    qualquer corte por tamanho antes de chegar na mensagem de erro real.
    Remove essas linhas de progresso e retorna o final do que sobrar.
    """
    lines = [
        l for l in stderr.splitlines()
        if l.strip() and not l.strip().startswith("frame=")
    ]
    cleaned = "\n".join(lines)
    return cleaned[-max_len:] if len(cleaned) > max_len else cleaned


# ── Diretórios ──────────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path("data/biel_reels")
IMAGES_DIR = Path("data/biel_reel_frames")
# Pasta versionada no git (não é cache efêmero) — coloque .mp3
# royalty-free aqui pra ativar música de fundo. Ver get_music_path().
MUSIC_ASSETS_DIR = TEMPLATES_DIR / "assets" / "music"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# ── Dimensões ───────────────────────────────────────────────────
# 720x1280 (em vez de 1080x1920): code -9 = SIGKILL confirmou OOM no
# compose (crossfade decodifica 3 streams + filtro + encode ao mesmo
# tempo). Resolução é o fator que mais pesa em TODO buffer do pipeline
# (Playwright, zoompan, decode, xfade, encode) — cortar 44% dos pixels
# é a alavanca mais forte contra estouro de memória. 720x1280 ainda é
# HD e aceito sem ressalvas por Reels/TikTok.
WIDTH = 720
HEIGHT = 1280
FPS = 30

# ── Duração das cenas (total = 15s) ────────────────────────────
SCENE_DURATIONS = [4, 7, 4]  # hook, content, cta
CROSSFADE_DURATION = 0.5  # segundos de transição

# ── Tópico → cor do acento ──────────────────────────────────────
TOPIC_COLORS = {
    "meme":        "#FFD700",
    "noticias":    "#00D4FF",
    "insight":     "#00FF88",
    "profits":     "#00FF88",
    "erros":       "#FF4444",
    "aprendizados": "#648CFF",
}

TOPIC_TEMPLATE_MAP = {
    "meme":        "reel_meme.html",
    "noticias":    "reel_noticias.html",
    "insight":     "reel_insight.html",
    "profits":     "reel_profits.html",
    "erros":       "reel_erros.html",
    "aprendizados": "reel_aprendizados.html",
}

# ═══════════════════════════════════════════════════════════════════
#  Template Rendering (HTML → PNG via Playwright)
# ═══════════════════════════════════════════════════════════════════

def _load_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Template não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def _fill_template(html: str, data: dict) -> str:
    """Substitui {{VAR}} no template pelos dados do reel."""
    for key, value in data.items():
        placeholder = "{{" + key.upper() + "}}"
        # Tratar valores complexos (listas, dicts)
        if isinstance(value, list):
            if key == "trades_list":
                # Renderizar como HTML de trade items
                items_html = ""
                for t in value:
                    pnl_class = "win" if t.get("is_win", True) else "loss"
                    items_html += (
                        f'<div class="trade-item">'
                        f'<span class="trade-symbol">{t.get("symbol", "—")}</span>'
                        f'<span class="trade-pnl {pnl_class}">{t.get("pnl", "—")}</span>'
                        f'</div>'
                    )
                html = html.replace(placeholder, items_html)
            elif key == "impacts":
                # Renderizar cards de impacto
                for i, impact in enumerate(value[:3]):
                    label = impact[0] if isinstance(impact, (list, tuple)) else impact.get("label", "")
                    val = impact[1] if isinstance(impact, (list, tuple)) else impact.get("value", "")
                    is_pos = impact[2] if isinstance(impact, (list, tuple)) and len(impact) > 2 else True
                    cls = "positive" if is_pos else "negative"
                    html = html.replace(f"{{{{IMPACT_{i+1}_LABEL}}}}", str(label))
                    html = html.replace(f"{{{{IMPACT_{i+1}_VALUE}}}}", str(val))
                    html = html.replace(f"{{{{IMPACT_{i+1}_CLASS}}}}", cls)
            elif key == "insights":
                for i, ins in enumerate(value[:3]):
                    html = html.replace(f"{{{{ICON_{i+1}}}}}", ins.get("icon", "📊"))
                    html = html.replace(f"{{{{TITLE_{i+1}}}}}", ins.get("title", ""))
                    html = html.replace(f"{{{{DESC_{i+1}}}}}", ins.get("desc", ""))
            elif key == "tips":
                for i, tip in enumerate(value[:3]):
                    html = html.replace(f"{{{{TIP_{i+1}_TITLE}}}}", tip.get("title", ""))
                    html = html.replace(f"{{{{TIP_{i+1}_DESC}}}}", tip.get("desc", ""))
        else:
            html = html.replace(placeholder, str(value) if value is not None else "—")

    # Blinda contra placeholder que sobrou sem dado (evita mostrar "{{X}}"
    # cru na tela — acontece pras cenas que não usam certos campos).
    import re
    html = re.sub(r"\{\{[A-Z0-9_]+\}\}", "", html)
    return html


def render_scene_image(topic: str, scene_data: dict, scene_name: str) -> str:
    """
    Renderiza uma cena do reel como PNG 1080x1920 via Playwright.
    
    Args:
        topic: Tópico do reel (meme, noticias, etc.)
        scene_data: Dados para preencher o template
        scene_name: Nome da cena (hook, content, cta)
    
    Returns:
        Caminho do PNG gerado
    """
    template_file = TOPIC_TEMPLATE_MAP.get(topic, "reel_insight.html")
    html = _load_template(template_file)
    html = _fill_template(html, scene_data)

    # Cada template reel_*.html é um card único com 3 blocos marcados
    # data-scene="hook|content|cta". Escondemos os outros dois blocos pra
    # cada screenshot virar uma cena isolada em vez de mostrar o card
    # inteiro (com pedaços vazios) em toda cena.
    other_scenes = [s for s in ("hook", "content", "cta") if s != scene_name]
    hide_css = "".join(f'[data-scene="{s}"]{{display:none !important;}}' for s in other_scenes)
    if hide_css and "</head>" in html:
        html = html.replace("</head>", f"<style>{hide_css}</style></head>")

    filename = f"reel_{topic}_{scene_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
    output_path = str(IMAGES_DIR / filename)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
            page.set_content(html, wait_until="networkidle")
            # Esperar um pouco para fonts carregarem
            page.wait_for_timeout(500)
            page.screenshot(path=output_path)
            browser.close()

        logger.info(f"[biel/reel] Cena renderizada: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"[biel/reel] Playwright falhou: {e}")
        raise RuntimeError(f"Falha ao renderizar cena do reel: {e}")


# ═══════════════════════════════════════════════════════════════════
#  Narração (TTS gratuito via edge-tts — sem API key, sem custo)
# ═══════════════════════════════════════════════════════════════════

# Voz padrão do Biel — masculina, pt-BR, tom confiante.
DEFAULT_VOICE = "pt-BR-AntonioNeural"


def _build_narration_text(topic: str, reel_data: dict) -> str:
    """
    Monta o texto narrado reaproveitando os campos estruturados que o
    brain.py já gera pra cada tópico — sem hashtag/emoji (isso fica só
    na legenda do Instagram, não faz sentido narrar hashtag em voz alta).
    """
    g = reel_data.get

    if topic == "meme":
        parts = [g("hook", "O mercado hoje"), g("hook_sub", ""), g("content", ""), g("content_sub", "")]
    elif topic == "noticias":
        parts = [g("headline", "Atualização do mercado"), g("summary", "")]
        for item in (reel_data.get("impacts") or [])[:3]:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                parts.append(f"{item[0]}: {item[1]}")
    elif topic == "insight":
        parts = [g("question", "O que os dados mostram?")]
        for ins in (reel_data.get("insights") or [])[:3]:
            parts.append(f"{ins.get('title', '')}: {ins.get('desc', '')}")
        parts.append(g("ai_summary", ""))
    elif topic == "profits":
        parts = [
            f"Resultado do dia: {g('pnl_value', '—')}, variação de {g('pnl_pct', '—')}.",
            f"Taxa de acerto: {g('win_rate', '—')}.",
        ]
        if g("best_trade"):
            parts.append(f"Melhor trade: {g('best_trade')}.")
    elif topic == "erros":
        parts = [g("title", "Erros do dia"), g("subtitle", "")]
        if g("error_1_title"):
            parts.append(f"{g('error_1_title')}: {g('error_1_desc', '')}")
        if g("error_2_title"):
            parts.append(f"{g('error_2_title')}: {g('error_2_desc', '')}")
        parts.append(g("lesson", ""))
    elif topic == "aprendizados":
        parts = [g("title", "Aprendizados do dia")]
        for tip in (reel_data.get("tips") or [])[:3]:
            parts.append(f"{tip.get('title', '')}: {tip.get('desc', '')}")
        parts.append(g("takeaway", ""))
    else:
        parts = [reel_data.get("caption", "Confira mais sobre o mercado.")]

    text = " ".join(str(p).strip() for p in parts if p and str(p).strip())

    import re
    text = re.sub(r"<[^>]+>", "", text)  # remove markup HTML residual (ex: <span class="highlight">)
    return text.strip()


async def generate_narration(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> list[dict]:
    """
    Gera áudio de narração via edge-tts (gratuito, sem API key) e retorna
    o timing de cada palavra (em segundos) pra sincronizar as legendas.
    """
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate="+8%")
    word_timings: list[dict] = []

    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                })

    logger.info(f"[biel/reel] Narração gerada: {output_path} ({len(word_timings)} palavras)")
    return word_timings


def _narration_duration(word_timings: list[dict]) -> float:
    if not word_timings:
        return 0.0
    return max(w["end"] for w in word_timings)


# ═══════════════════════════════════════════════════════════════════
#  Legendas (burned-in, sincronizadas com a narração)
# ═══════════════════════════════════════════════════════════════════

def _ass_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs == 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _build_subtitle_ass(word_timings: list[dict], output_path: str, group_size: int = 4) -> str | None:
    """
    Gera um .ass com legendas em grupos curtos de palavras, no timing
    exato retornado pelo edge-tts. A maioria assiste Reels sem som —
    isso sozinho já aumenta retenção.
    """
    if not word_timings:
        return None

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {WIDTH}\n"
        f"PlayResY: {HEIGHT}\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,DejaVu Sans,58,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,190,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    lines = []
    for i in range(0, len(word_timings), group_size):
        group = word_timings[i:i + group_size]
        start = _ass_timestamp(group[0]["start"])
        end = _ass_timestamp(group[-1]["end"])
        text = " ".join(w["word"] for w in group).upper().strip()
        if not text:
            continue
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")

    return output_path


# ═══════════════════════════════════════════════════════════════════
#  Music Management (assets locais versionados — sem downloads quebrados)
# ═══════════════════════════════════════════════════════════════════

def get_music_path(topic: str | None = None) -> str | None:
    """
    Retorna uma trilha de fundo local, se existir.

    Não baixa nada da internet (os links antigos do Pixabay estavam
    quebrados — nunca baixavam de verdade) e não gera tom sintético de
    fallback (o drone senoidal antigo soava robótico; a narração sozinha,
    sem música nenhuma, já soa melhor que isso).

    Pra ativar música de fundo: coloque .mp3 royalty-free em
    backend/app/services/biel/templates/assets/music/ — um arquivo
    "{topic}.mp3" tem prioridade (ex: profits.mp3), senão pega
    qualquer .mp3 disponível na pasta.
    """
    if topic:
        specific = MUSIC_ASSETS_DIR / f"{topic}.mp3"
        if specific.exists():
            return str(specific)

    if MUSIC_ASSETS_DIR.exists():
        existing = sorted(MUSIC_ASSETS_DIR.glob("*.mp3"))
        if existing:
            return str(existing[0])
    return None


# ═══════════════════════════════════════════════════════════════════
#  Video Composition (ffmpeg)
# ═══════════════════════════════════════════════════════════════════

def _build_scene_video(image_path: str, duration: float, zoom_start: float,
                       zoom_end: float, x_drift: float = 0, y_drift: float = 0) -> str:
    """
    Gera vídeo de uma cena com efeito Ken Burns (zoom + pan suave).
    
    Args:
        image_path: Caminho da imagem PNG
        duration: Duração em segundos
        zoom_start: Nível inicial de zoom (1.0 = sem zoom)
        zoom_end: Nível final de zoom
        x_drift: Deslocamento horizontal (proporção 0-1)
        y_drift: Deslocamento vertical (proporção 0-1)
    
    Returns:
        Caminho do vídeo MP4 gerado
    """
    total_frames = int(duration * FPS)
    output_path = str(IMAGES_DIR / f"scene_{Path(image_path).stem}.mp4")

    # zoompan: zoom suave de zoom_start → zoom_end com pan
    # x e y centram a imagem com drift sutil
    zoom_expr = f"if(eq(on,1),{zoom_start},{zoom_start}+({zoom_end}-{zoom_start})*on/{total_frames})"
    x_expr = f"iw/2-(iw/zoom/2)+{x_drift}*iw*on/{total_frames}"
    y_expr = f"ih/2-(ih/zoom/2)+{y_drift}*ih*on/{total_frames}"

    cmd = [
        "ffmpeg", "-y",
        "-filter_threads", "2",
        "-loop", "1",
        "-i", image_path,
        "-vf",
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}'"
        f":d={total_frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"format=yuv420p",
        "-t", str(duration),
        "-c:v", "libx264",
        "-threads", "2",
        "-x264-params", "threads=2:lookahead-threads=1:rc-lookahead=10:bframes=0:ref=1",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        err = _clean_ffmpeg_error(result.stderr)
        logger.error(f"[biel/reel] Scene video falhou (code {result.returncode}): {err}")
        raise RuntimeError(f"ffmpeg scene falhou (code {result.returncode}): {err}")

    return output_path


def _build_compose_cmd(
    scene_videos: list[str],
    narration_path: str | None,
    music_path: str | None,
    subtitle_path: str | None,
    output_path: str,
    total_duration: float,
    burn_subtitles: bool,
) -> list[str]:
    """Monta o comando ffmpeg de composição final. `burn_subtitles=False`
    permite gerar o mesmo vídeo sem o filtro `ass` (usado como fallback
    caso a legenda esteja causando falha)."""
    n = len(scene_videos)
    fade_dur = CROSSFADE_DURATION

    # ── Vídeo: crossfade entre cenas ──
    video_filters = []
    for i in range(n):
        video_filters.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")

    if n == 1:
        video_out = "v0"
    else:
        prev = "v0"
        total_config = sum(SCENE_DURATIONS)
        for i in range(1, n):
            out_label = f"cf{i}"
            offset = sum(SCENE_DURATIONS[:i]) / total_config * total_duration - fade_dur * i
            video_filters.append(
                f"[{prev}][v{i}]xfade=transition=fade:duration={fade_dur}:offset={max(offset, 0):.2f}[{out_label}]"
            )
            prev = out_label
        video_out = prev

    # Legenda queimada (opcional)
    if burn_subtitles and subtitle_path and Path(subtitle_path).exists():
        escaped = str(subtitle_path).replace("\\", "/").replace(":", "\\:")
        video_filters.append(f"[{video_out}]ass='{escaped}'[vfinal]")
        video_out = "vfinal"

    # ── Áudio: narração (principal) + música de fundo ducked (opcional) ──
    audio_inputs = []
    next_idx = n

    nar_idx = None
    if narration_path and Path(narration_path).exists():
        audio_inputs.append(narration_path)
        nar_idx = next_idx
        next_idx += 1

    music_idx = None
    if music_path and Path(music_path).exists():
        audio_inputs.append(music_path)
        music_idx = next_idx
        next_idx += 1

    audio_filters = []
    fade_out_start = max(total_duration - 0.6, 0)
    if nar_idx is not None and music_idx is not None:
        audio_filters.append(
            f"[{nar_idx}:a]apad,atrim=0:{total_duration},afade=t=in:st=0:d=0.3,"
            f"afade=t=out:st={fade_out_start:.2f}:d=0.6[nar]"
        )
        audio_filters.append(
            f"[{music_idx}:a]aloop=loop=-1:size={int(44100 * 60)},atrim=0:{total_duration},"
            f"volume=0.13,afade=t=in:st=0:d=1,afade=t=out:st={max(total_duration - 1, 0):.2f}:d=1[mus]"
        )
        audio_filters.append("[nar][mus]amix=inputs=2:duration=first:dropout_transition=0,volume=2[aout]")
    elif nar_idx is not None:
        audio_filters.append(
            f"[{nar_idx}:a]apad,atrim=0:{total_duration},afade=t=in:st=0:d=0.3,"
            f"afade=t=out:st={fade_out_start:.2f}:d=0.6[aout]"
        )
    else:
        audio_filters.append(f"anullsrc=r=44100:cl=stereo,atrim=0:{total_duration}[aout]")

    all_filters = ";".join(video_filters) + ";" + ";".join(audio_filters)

    cmd = ["ffmpeg", "-y", "-filter_complex_threads", "2", "-filter_threads", "2"]
    for sv in scene_videos:
        cmd.extend(["-i", sv])
    for a in audio_inputs:
        cmd.extend(["-i", a])

    cmd.extend([
        "-filter_complex", all_filters,
        "-map", f"[{video_out}]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-threads", "2",
        "-x264-params", "threads=2:lookahead-threads=1:rc-lookahead=10:bframes=0:ref=1",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-t", str(total_duration),
        "-movflags", "+faststart",
        output_path,
    ])
    return cmd


def _compose_final_video(
    scene_videos: list[str],
    narration_path: str | None,
    music_path: str | None,
    subtitle_path: str | None,
    output_path: str,
    total_duration: float,
) -> str:
    """
    Compõe o vídeo final: cenas com crossfade + legenda queimada
    (opcional) + narração por voz (principal) mixada com música de
    fundo ducked (opcional).

    Se a legenda queimada (`ass=`) fizer o ffmpeg falhar (ex.: build sem
    fontconfig/fonts configurados no container), tenta de novo sem
    legenda em vez de derrubar o post inteiro — vídeo sem legenda é
    melhor que nenhum vídeo.
    """
    has_subs = bool(subtitle_path and Path(subtitle_path).exists())

    cmd = _build_compose_cmd(
        scene_videos, narration_path, music_path, subtitle_path,
        output_path, total_duration, burn_subtitles=has_subs,
    )
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

    if result.returncode != 0 and has_subs:
        err = _clean_ffmpeg_error(result.stderr)
        logger.error(
            f"[biel/reel] Compose com legenda falhou (code {result.returncode}): {err} "
            f"— tentando novamente sem legenda queimada"
        )
        cmd_retry = _build_compose_cmd(
            scene_videos, narration_path, music_path, subtitle_path,
            output_path, total_duration, burn_subtitles=False,
        )
        result = subprocess.run(cmd_retry, capture_output=True, text=True, timeout=180)

    if result.returncode != 0:
        err = _clean_ffmpeg_error(result.stderr)
        logger.error(f"[biel/reel] Compose final falhou (code {result.returncode}): {err}")
        raise RuntimeError(f"ffmpeg compose falhou (code {result.returncode}): {err}")

    return output_path


# ═══════════════════════════════════════════════════════════════════
#  Scene Data Builders
# ═══════════════════════════════════════════════════════════════════

def _build_scene_data(topic: str, reel_data: dict, context: dict) -> list[dict]:
    """
    Monta os dados para cada cena do reel baseado no tópico.
    Retorna lista de 3 dicts: [hook_data, content_data, cta_data].
    """
    caption = reel_data.get("caption", "")
    cta = reel_data.get("cta", "SALVA E COMPARTILHA")

    if topic == "meme":
        return [
            {  # Hook
                "HOOK": reel_data.get("hook", "MEME DO DIA"),
                "HOOK_SUB": reel_data.get("hook_sub", "Todo trader identifica"),
            },
            {  # Content
                "CONTENT": reel_data.get("content", "O MERCADO HOJE"),
                "CONTENT_SUB": reel_data.get("content_sub", "Quando o plano não sobrevive ao primeiro contato"),
            },
            {  # CTA
                "CTA": cta,
            },
        ]

    elif topic == "noticias":
        impacts = reel_data.get("impacts", [["—", "—", True]] * 3)
        # Normalizar impacts
        norm_impacts = []
        for item in impacts[:3]:
            if isinstance(item, (list, tuple)):
                label = item[0] if len(item) > 0 else "—"
                val = item[1] if len(item) > 1 else "—"
                is_pos = item[2] if len(item) > 2 else True
            else:
                label = item.get("label", "—")
                val = item.get("value", "—")
                is_pos = item.get("is_positive", True)
            norm_impacts.append({"label": label, "value": val, "is_positive": is_pos})

        return [
            {  # Hook
                "HEADLINE": reel_data.get("headline", "ATUALIZAÇÃO DO MERCADO"),
                "SUMMARY": reel_data.get("summary", "Acompanhe os últimos acontecimentos."),
            },
            {  # Content (impacts)
                "IMPACT_1_LABEL": norm_impacts[0]["label"],
                "IMPACT_1_VALUE": norm_impacts[0]["value"],
                "IMPACT_1_CLASS": "positive" if norm_impacts[0]["is_positive"] else "negative",
                "IMPACT_2_LABEL": norm_impacts[1]["label"],
                "IMPACT_2_VALUE": norm_impacts[1]["value"],
                "IMPACT_2_CLASS": "positive" if norm_impacts[1]["is_positive"] else "negative",
                "IMPACT_3_LABEL": norm_impacts[2]["label"],
                "IMPACT_3_VALUE": norm_impacts[2]["value"],
                "IMPACT_3_CLASS": "positive" if norm_impacts[2]["is_positive"] else "negative",
                "SOURCE": reel_data.get("source", "TradeAI"),
            },
            {  # CTA
                "CTA": cta,
            },
        ]

    elif topic == "insight":
        insights = reel_data.get("insights", [
            {"icon": "📊", "title": "ANÁLISE", "desc": "Dados indicam movimento importante."},
            {"icon": "💧", "title": "LIQUIDEZ", "desc": "Fluxo mudando no mercado."},
            {"icon": "📈", "title": "TENDÊNCIA", "desc": "Estrutura formando."},
        ])
        return [
            {  # Hook
                "QUESTION": reel_data.get("question", "O QUE OS DADOS MOSTRAM?"),
            },
            {  # Content (insights)
                "ICON_1": insights[0]["icon"] if len(insights) > 0 else "📊",
                "TITLE_1": insights[0]["title"] if len(insights) > 0 else "",
                "DESC_1": insights[0]["desc"] if len(insights) > 0 else "",
                "ICON_2": insights[1]["icon"] if len(insights) > 1 else "💧",
                "TITLE_2": insights[1]["title"] if len(insights) > 1 else "",
                "DESC_2": insights[1]["desc"] if len(insights) > 1 else "",
                "ICON_3": insights[2]["icon"] if len(insights) > 2 else "📈",
                "TITLE_3": insights[2]["title"] if len(insights) > 2 else "",
                "DESC_3": insights[2]["desc"] if len(insights) > 2 else "",
                "AI_SUMMARY": reel_data.get("ai_summary", "Cenário em desenvolvimento."),
            },
            {  # CTA
                "CTA": cta,
            },
        ]

    elif topic == "profits":
        trades_list = reel_data.get("trades_list", [])
        # Formatar trades_list para HTML
        trades_html = ""
        for t in trades_list[:3]:
            pnl_class = "win" if t.get("is_win", True) else "loss"
            trades_html += (
                f'<div class="trade-item">'
                f'<span class="trade-symbol">{t.get("symbol", "—")}</span>'
                f'<span class="trade-pnl {pnl_class}">{t.get("pnl", "—")}</span>'
                f'</div>'
            )

        return [
            {  # Hook
                "PNL_VALUE": reel_data.get("pnl_value", "—"),
                "PNL_PCT": reel_data.get("pnl_pct", "—"),
            },
            {  # Content (stats)
                "WIN_RATE": reel_data.get("win_rate", "—"),
                "SALDO": reel_data.get("saldo", "—"),
                "TRADES_TODAY": reel_data.get("trades_today", "0"),
                "BEST_TRADE": reel_data.get("best_trade", "—"),
                "TRADES_LIST": trades_html,
            },
            {  # CTA
                "CTA": cta,
            },
        ]

    elif topic == "erros":
        return [
            {  # Hook
                "TITLE": reel_data.get("title", "ERROS DO DIA"),
                "SUBTITLE": reel_data.get("subtitle", "Aprendendo com os erros"),
            },
            {  # Content (errors)
                "ERROR_1_TITLE": reel_data.get("error_1_title", "ERRO 1"),
                "ERROR_1_DESC": reel_data.get("error_1_desc", "Análise indevida."),
                "ERROR_2_TITLE": reel_data.get("error_2_title", "ERRO 2"),
                "ERROR_2_DESC": reel_data.get("error_2_desc", "Gestão de risco precária."),
                "LESSON": reel_data.get("lesson", "Sempre gerencie o risco."),
            },
            {  # CTA
                "CTA": cta,
            },
        ]

    elif topic == "aprendizados":
        tips = reel_data.get("tips", [
            {"title": "DICA 1", "desc": "Mantenha a disciplina."},
            {"title": "DICA 2", "desc": "Analise seus erros."},
            {"title": "DICA 3", "desc": "Não entre sem confirmação."},
        ])
        return [
            {  # Hook
                "TITLE": reel_data.get("title", "APRENDIZADOS DO DIA"),
            },
            {  # Content (tips)
                "TIP_1_TITLE": tips[0]["title"] if len(tips) > 0 else "",
                "TIP_1_DESC": tips[0]["desc"] if len(tips) > 0 else "",
                "TIP_2_TITLE": tips[1]["title"] if len(tips) > 1 else "",
                "TIP_2_DESC": tips[1]["desc"] if len(tips) > 1 else "",
                "TIP_3_TITLE": tips[2]["title"] if len(tips) > 2 else "",
                "TIP_3_DESC": tips[2]["desc"] if len(tips) > 2 else "",
                "TAKEAWAY": reel_data.get("takeaway", "Consistência é a chave."),
            },
            {  # CTA
                "CTA": cta,
            },
        ]

    # Fallback
    return [
        {"HOOK": "CONTEÚDO DO DIA"},
        {"CONTENT": "Algo interessante aconteceu no mercado."},
        {"CTA": "SEGUE PRA MAIS"},
    ]


# ═══════════════════════════════════════════════════════════════════
#  Main Entry Point
# ═══════════════════════════════════════════════════════════════════

async def generate_reel(
    topic: str,
    reel_data: dict,
    context: dict,
    voice: str | None = None,
) -> str:
    """
    Gera um vídeo Reel completo (9:16) com 3 cenas, Ken Burns, narração
    por voz (edge-tts, gratuito), legenda sincronizada queimada no vídeo
    e música de fundo opcional (assets locais versionados no git).

    A duração total é determinada automaticamente pelo tamanho real da
    narração (não é mais um valor fixo de 15s) — assim o vídeo sempre
    "faz sentido": nunca corta a fala nem sobra silêncio morto.

    Args:
        topic: Tópico do reel (meme, noticias, insight, profits, erros, aprendizados)
        reel_data: Dados estruturados gerados pelo brain.py
        context: Contexto do TradeAI (preços, trades, etc.)
        voice: Voz do edge-tts (opcional, default DEFAULT_VOICE)

    Returns:
        Caminho do vídeo MP4 gerado
    """
    logger.info(f"[biel/reel] Iniciando geração de reel: {topic}")

    # 1. Narração — gera áudio + timing de palavras (usado pra legenda)
    narration_text = _build_narration_text(topic, reel_data)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    narration_path = str(OUTPUT_DIR / f"narration_{topic}_{ts}.mp3")
    word_timings: list[dict] = []
    try:
        word_timings = await generate_narration(narration_text, narration_path, voice or DEFAULT_VOICE)
    except Exception as e:
        logger.error(f"[biel/reel] Falha ao gerar narração (edge-tts): {e}")
        narration_path = None

    narration_dur = _narration_duration(word_timings)
    total_duration = min(max(narration_dur + 1.6, 10.0), 45.0) if narration_dur else 15.0

    # 2. Montar dados das 3 cenas
    scenes = _build_scene_data(topic, reel_data, context)
    scene_names = ["hook", "content", "cta"]

    # 3. Durações das cenas proporcionais à duração total real
    total_config = sum(SCENE_DURATIONS)
    scene_durations = [d * total_duration / total_config for d in SCENE_DURATIONS]

    # 4. Renderizar imagens das cenas via Playwright
    scene_images = []
    for scene_data, scene_name in zip(scenes, scene_names):
        img_path = await asyncio.get_event_loop().run_in_executor(
            None, render_scene_image, topic, scene_data, scene_name
        )
        scene_images.append(img_path)

    logger.info(f"[biel/reel] {len(scene_images)} cenas renderizadas")

    # 5. Gerar vídeos individuais com Ken Burns
    # Variações de zoom por cena: hook (zoom in), content (zoom out), cta (estático)
    zoom_configs = [
        (1.0, 1.15, 0.0, 0.02),   # hook: zoom in sutil + pan para cima
        (1.1, 1.0, 0.01, -0.01),   # content: zoom out + pan sutil
        (1.05, 1.05, 0.0, 0.0),    # cta: estável (zoom leve)
    ]

    scene_videos = []
    for i, (img_path, dur) in enumerate(zip(scene_images, scene_durations)):
        z_start, z_end, x_d, y_d = zoom_configs[i % len(zoom_configs)]
        vid_path = await asyncio.get_event_loop().run_in_executor(
            None, _build_scene_video, img_path, dur, z_start, z_end, x_d, y_d
        )
        scene_videos.append(vid_path)

    logger.info(f"[biel/reel] {len(scene_videos)} cenas de vídeo geradas")

    # 6. Legenda sincronizada (só se a narração deu certo)
    subtitle_path = None
    if word_timings:
        subtitle_path = _build_subtitle_ass(word_timings, str(OUTPUT_DIR / f"subs_{topic}_{ts}.ass"))

    # 7. Música de fundo local (opcional — ver get_music_path)
    music_path = get_music_path(topic)

    # 8. Compor vídeo final: crossfade + legenda + narração + música
    filename = f"reel_{topic}_{ts}.mp4"
    output_path = str(OUTPUT_DIR / filename)

    final_path = await asyncio.get_event_loop().run_in_executor(
        None, _compose_final_video,
        scene_videos, narration_path, music_path, subtitle_path, output_path, total_duration,
    )

    # 9. Limpar temporários
    cleanup = scene_images + scene_videos
    if narration_path:
        cleanup.append(narration_path)
    if subtitle_path:
        cleanup.append(subtitle_path)
    for f in cleanup:
        try:
            Path(f).unlink(missing_ok=True)
        except Exception:
            pass

    logger.info(f"[biel/reel] Reel final gerado: {final_path} ({total_duration:.1f}s)")
    return final_path


# ═══════════════════════════════════════════════════════════════════
#  Compatibilidade com código antigo
# ═══════════════════════════════════════════════════════════════════

# Manter REEL_TOPICS para compatibilidade com post_engine.py
REEL_TOPICS = {
    "meme": {
        "emoji": "😂",
        "color": "#FFD700",
        "desc": "Memes e humor do trading",
    },
    "noticias": {
        "emoji": "📰",
        "color": "#00D4FF",
        "desc": "Notícias do mercado",
    },
    "insight": {
        "emoji": "💡",
        "color": "#00FF88",
        "desc": "Insights e análises",
    },
    "profits": {
        "emoji": "💰",
        "color": "#00FF88",
        "desc": "Resultados e lucros",
    },
    "erros": {
        "emoji": "😅",
        "color": "#FF4444",
        "desc": "Erros e aprendizados",
    },
    "aprendizados": {
        "emoji": "📚",
        "color": "#648CFF",
        "desc": "Dicas e educação",
    },
}
