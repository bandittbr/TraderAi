"""
Biel — Reel Generator
Cria vídeos no formato Reels (9:16) com imagens geradas + texto + música de fundo.
Usa ffmpeg para composição (deve estar instalado no sistema).
"""

import os
import subprocess
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from app.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("data/biel_reels")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Dimensões do Reels: 1080x1920 (9:16)
WIDTH = 1080
HEIGHT = 1920

# Cores e estilo
BG_COLOR = "0x0D0D0D"
ACCENT_GOLD = "0xFFD700"
ACCENT_BLUE = "0x00D4FF"
ACCENT_GREEN = "0x00FF88"
ACCENT_RED = "0xFF4444"
TEXT_COLOR = "0xFFFFFF"

# Tópicos de reels com cores e emojis
REEL_TOPICS = {
    "meme": {
        "emoji": "😂",
        "color": ACCENT_GOLD,
        "desc": "Memes e humor do trading",
    },
    "noticias": {
        "emoji": "📰",
        "color": ACCENT_BLUE,
        "desc": "Notícias do mercado",
    },
    "insight": {
        "emoji": "💡",
        "color": ACCENT_GREEN,
        "desc": "Insights e análises",
    },
    "profits": {
        "emoji": "💰",
        "color": ACCENT_GREEN,
        "desc": "Resultados e lucros",
    },
    "erros": {
        "emoji": "😅",
        "color": ACCENT_RED,
        "desc": "Erros e aprendizados",
    },
    "aprendizados": {
        "emoji": "📚",
        "color": ACCENT_BLUE,
        "desc": "Dicas e educação",
    },
}


def _create_ffmpeg_filter(
    image_path: str,
    caption: str,
    topic_emoji: str,
    topic_label: str,
    watermark: str = "Biel • TradeAI",
) -> list:
    """
    Monta os filtros ffmpeg para criar um Reels:
    - Imagem de fundo redimensionada para 1080x1920
    - Overlay de gradiente escuro (vignette)
    - Texto do caption centralizado
    - Emoji + label do tópico no topo
    - Marca d'água no rodapé
    """
    filters = []

    # 1. Redimensionar imagem para preencher 1080x1920 (crop central)
    filters.append(
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT}"

    )

    # 2. Escurecer levemente o fundo para o texto aparecer bem
    filters.append(
        f"drawbox=x=0:y=0:w={WIDTH}:h={HEIGHT}:color=black@0.35:t=fill"
    )

    # 3. Faixa semi-transparente no topo para o tópico
    filters.append(
        f"drawbox=x=0:y=0:w={WIDTH}:h=140:color=black@0.5:t=fill"
    )

    # 4. Texto do tópico (emoji + label) no topo
    topic_text = f"{topic_emoji}  {topic_label.upper()}"
    filters.append(
        f"drawtext=text='{topic_text}':"
        f"x=(w-text_w)/2:y=30:"
        f"fontsize=48:fontcolor={ACCENT_GOLD}:"
        f"fontfile='C\\:/Windows/Fonts/arial.ttf':box=0"
    )

    # 5. Caption principal (centralizado, com quebra de linha)
    escaped_caption = caption.replace("'", "\\'").replace(":", "\\:").replace("\n", " ")
    # Limitar a ~4 linhas de ~40 chars para não sobrecarregar
    lines = []
    remaining = escaped_caption
    while remaining and len(lines) < 4:
        if len(remaining) <= 42:
            lines.append(remaining)
            break
        # Quebrar no espaço mais próximo
        break_idx = remaining.rfind(" ", 0, 42)
        if break_idx < 20:
            break_idx = 42
        lines.append(remaining[:break_idx])
        remaining = remaining[break_idx:].strip()

    caption_formatted = "\\n".join(lines)
    # Posição vertical: começa em 500 (abaixo do topo)
    filters.append(
        f"drawtext=text='{caption_formatted}':"
        f"x=(w-text_w)/2:y=500:"
        f"fontsize=42:fontcolor={TEXT_COLOR}:"
        f"line_spacing=12:"
        f"fontfile='C\\:/Windows/Fonts/arial.ttf':box=0"
    )

    # 6. Marca d'água no rodapé
    filters.append(
        f"drawtext=text='{watermark}':"
        f"x=(w-text_w)/2:y=h-80:"
        f"fontsize=28:fontcolor={ACCENT_BLUE}@0.7:"
        f"fontfile='C\\:/Windows/Fonts/arial.ttf':box=0"
    )

    return filters


async def generate_reel(
    image_path: str,
    caption: str,
    topic: str,
    music_path: str | None = None,
    duration: int = 15,
) -> str:
    """
    Gera um vídeo Reels (9:16) a partir de uma imagem + texto + música.
    
    Args:
        image_path: Caminho da imagem de fundo
        caption: Texto do post
        topic: Tópico do reel (meme, noticias, insight, profits, erros, aprendizados)
        music_path: Caminho opcional do arquivo de música
        duration: Duração em segundos (máx 60 para Reels)
    
    Returns:
        Caminho do arquivo de vídeo gerado
    """
    topic_info = REEL_TOPICS.get(topic, REEL_TOPICS["insight"])
    topic_emoji = topic_info["emoji"]
    topic_label = topic_info["desc"] if topic in REEL_TOPICS else topic

    filename = f"reel_{topic}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.mp4"
    output_path = str(OUTPUT_DIR / filename)

    # Montar string de filtros
    filter_parts = _create_ffmpeg_filter(image_path, caption, topic_emoji, topic_label)
    filter_complex = ",".join(filter_parts)
    filter_complex += f",format=yuv420p[v]"  # nomear saída como [v]

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",                    # loop da imagem
        "-i", image_path,                # input: imagem
    ]

    # Se tem música, adicionar áudio
    if music_path and Path(music_path).exists():
        cmd.extend(["-i", music_path])    # input: áudio
        audio_map = "-map", "1:a:0"
        # Loop de áudio se necessário (curto)
        audio_filter = f"aloop=loop=-1:size={2*44100},atrim=0:{duration}[a]"
        filter_complex = filter_complex.replace("[v]", f";{audio_filter}")
        map_v = "[v]"
        map_a = "[a]"
    else:
        # Sem áudio — silêncio
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"])
        map_v = "[v]"
        map_a = "-map", "1:a:0"

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", map_v,
        "-map", map_a,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        output_path,
    ])

    logger.info(f"[biel/reel] Gerando reel: {filename} (tópico: {topic}, duração: {duration}s)")

    loop = asyncio.get_event_loop()

    def _run_ffmpeg():
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.error(f"[biel/reel] ffmpeg erro: {result.stderr[:500]}")
                raise RuntimeError(f"ffmpeg falhou (código {result.returncode}): {result.stderr[:200]}")
        except FileNotFoundError:
            raise RuntimeError("ffmpeg não encontrado. Instale ffmpeg para gerar reels.")

    await loop.run_in_executor(None, _run_ffmpeg)

    logger.info(f"[biel/reel] Reel gerado: {output_path}")
    return output_path


def get_downloaded_music() -> str | None:
    """
    Retorna o caminho de uma música de fundo pré-baixada.
    Se não existir, baixa uma música royalty-free do Pixabay.
    """
    music_dir = Path("data/biel_music")
    music_dir.mkdir(parents=True, exist_ok=True)

    # Verificar se já temos música baixada
    existing = list(music_dir.glob("*.mp3"))
    if existing:
        return str(existing[0])

    return None


async def download_music(url: str = None) -> str | None:
    """
    Baixa uma música royalty-free para usar como fundo dos reels.
    Se url for None, usa um fallback interno (loop melódico curto gerado via ffmpeg).
    """
    import httpx

    music_dir = Path("data/biel_music")
    music_dir.mkdir(parents=True, exist_ok=True)

    if url:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url)
                if resp.is_success:
                    filepath = music_dir / "bg_music.mp3"
                    with open(filepath, "wb") as f:
                        f.write(resp.content)
                    logger.info(f"[biel/reel] Música baixada: {filepath}")
                    return str(filepath)
        except Exception as e:
            logger.warning(f"[biel/reel] Falha ao baixar música: {e}")

    # Fallback: gerar um tom simples via ffmpeg (beep melódico)
    fallback_path = music_dir / "bg_fallback.mp3"
    if not fallback_path.exists():
        loop = asyncio.get_event_loop()

        def _gen_fallback():
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
                "-f", "lavfi", "-i", "sine=frequency=523:duration=30",
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=30[a]",
                "-map", "[a]",
                "-c:a", "libmp3lame",
                "-b:a", "128k",
                str(fallback_path),
            ], capture_output=True, text=True, timeout=30)

        await loop.run_in_executor(None, _gen_fallback)
        logger.info(f"[biel/reel] Fallback musical gerado: {fallback_path}")

    return str(fallback_path) if fallback_path.exists() else None
