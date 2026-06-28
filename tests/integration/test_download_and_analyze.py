"""
Script completo: Descarga ambos Reels de Instagram y analiza su contenido.
Genera informes detallados con URLs, tecnologías, comandos y transcripción.

Uso:
    cd media-intelligence-engine
    .venv/bin/python tests/integration/test_download_and_analyze.py
"""

import asyncio
import sys
import re
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.domain.value_objects.url import URL
from src.infrastructure.plugins.instagram_extractor import InstagramExtractor
from src.infrastructure.config.settings import settings


def generate_informe(title: str, transcript: str, frames_texts: list[dict], 
                     duracion: float, video_path: Path, metadata: dict = None) -> str:
    """Genera un informe markdown estructurado del video."""
    lines = []
    lines.append(f"# 📋 Informe de Análisis: {title}")
    lines.append("")
    lines.append(f"- **Fuente:** {video_path.name}")
    lines.append(f"- **Tamaño:** {video_path.stat().st_size / 1024 / 1024:.2f} MB")
    lines.append(f"- **Duración:** {duracion:.1f}s" if duracion else "")
    lines.append(f"- **Fecha análisis:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if metadata:
        lines.append(f"- **Plataforma:** {metadata.get('platform', 'N/A')}")
        lines.append(f"- **Estrategia descarga:** {metadata.get('strategy', 'N/A')}")
    lines.append("")

    # Texto completo
    all_text = transcript + "\n" + "\n".join(f.get("text", "") for f in frames_texts)

    # Detectar URLs
    urls = list(set(re.findall(r'https?://[^\s<>"\']+', all_text)))
    if urls:
        lines.append("## 🔗 URLs Mencionadas")
        lines.append("")
        for u in urls:
            lines.append(f"- {u}")
        lines.append("")

    # Detectar comandos
    cmd_pattern = re.compile(r'(?:^|\n)\s*\$?\s*(npm|pip|git|docker|kubectl|ssh|curl|wget|yarn|brew|apt|cd|ls|mkdir|rm|cp|mv|python|node|npx|pnpm)\s+([^\n]+)', re.IGNORECASE)
    commands = [m.group(0).strip() for m in cmd_pattern.finditer(all_text)]
    if commands:
        lines.append("## 💻 Comandos Detectados")
        lines.append("")
        lines.append("```bash")
        for cmd in commands[:20]:
            lines.append(cmd)
        lines.append("```")
        lines.append("")

    # Detectar tecnologías
    tech_keywords = {
        "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
        "react": "React", "vue": "Vue.js", "angular": "Angular",
        "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
        "aws": "AWS", "gcp": "GCP", "azure": "Azure",
        "node": "Node.js", "rust": "Rust", "golang": "Go", "go ": "Go",
        "sql": "SQL", "redis": "Redis", "postgres": "PostgreSQL", "mongo": "MongoDB",
        "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
        "git": "Git", "github": "GitHub", "tailwind": "Tailwind CSS",
        "next.js": "Next.js", "nuxt": "Nuxt", "svelte": "Svelte",
        "tensorflow": "TensorFlow", "pytorch": "PyTorch", "llm": "LLM",
        "ia": "Inteligencia Artificial", "ai ": "Inteligencia Artificial", "openai": "OpenAI", "gpt": "GPT",
        "html": "HTML", "css": "CSS", "api": "API", "rest": "REST API",
        "linux": "Linux", "terminal": "Terminal", "bash": "Bash",
    }
    text_lower = all_text.lower()
    tecnologias = set()
    for keyword, name in tech_keywords.items():
        if keyword in text_lower:
            tecnologias.add(name)
    if tecnologias:
        lines.append("## 🛠️ Tecnologías Identificadas")
        lines.append("")
        for tech in sorted(tecnologias):
            lines.append(f"- {tech}")
        lines.append("")

    # Transcripción
    if transcript.strip():
        lines.append("## 📜 Transcripción del Audio")
        lines.append("")
        lines.append(transcript.strip())
        lines.append("")

    # OCR de frames
    ocr_entries = [(f.get("timestamp", 0), f.get("text", "")) for f in frames_texts if f.get("text", "").strip()]
    if ocr_entries:
        lines.append("## 📸 Texto Detectado en Pantalla (OCR)")
        lines.append("")
        for ts, txt in ocr_entries:
            lines.append(f"**[{ts:.1f}s]** {txt.strip()}")
        lines.append("")

    # Resumen
    lines.append("---")
    lines.append("## 📊 Resumen")
    lines.append(f"- **URLs encontradas:** {len(urls)}")
    lines.append(f"- **Comandos detectados:** {len(commands)}")
    lines.append(f"- **Tecnologías identificadas:** {len(tecnologias)}")
    lines.append(f"- **Frames analizados:** {len(frames_texts)}")
    lines.append(f"- **Transcripción:** {'✅ Disponible' if transcript.strip() else '❌ No disponible'}")

    return "\n".join(lines)


async def download_and_analyze(name: str, url_str: str, output_dir: Path) -> dict:
    """Descarga un reel y lo analiza, retornando el informe y metadatos."""
    print(f"\n{'='*60}")
    print(f"Procesando {name}: {url_str[:60]}...")
    print(f"{'='*60}")

    # Directorio específico para este reel
    reel_dir = output_dir / name.replace(" ", "_").replace("#", "")
    reel_dir.mkdir(parents=True, exist_ok=True)

    # 1. Descargar
    extractor = InstagramExtractor()
    url = URL.from_string(url_str)
    
    if not extractor.can_handle(url):
        return {"error": "URL no reconocida como Instagram", "informe": ""}

    try:
        result = await extractor.extract(url, reel_dir)
        if not result.get("success"):
            return {"error": f"Descarga falló: {result.get('error')}", "informe": ""}
        
        video_path = Path(result["file_path"]) if result.get("file_path") else None
        if not video_path or not video_path.exists():
            # Buscar en subdirectorios
            videos = list(reel_dir.rglob("*.mp4")) + list(reel_dir.rglob("*.mov"))
            video_path = videos[0] if videos else None

        if not video_path:
            return {"error": "No se encontró el archivo de video", "informe": ""}

        print(f"✅ Video descargado: {video_path.name} ({video_path.stat().st_size/1024/1024:.2f} MB)")

    except Exception as e:
        return {"error": f"Error en descarga: {e!s}", "informe": ""}

    # 2. Analizar video
    try:
        import cv2
        import asyncio
        import subprocess

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {"error": "No se puede abrir el video", "informe": ""}

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duracion = total_frames / video_fps if video_fps > 0 else 0
        print(f"  Duración: {duracion:.1f}s | FPS: {video_fps:.1f} | Frames: {total_frames}")

        # Extraer frames (1 por segundo, max 30)
        frames_texts = []
        frame_interval = max(1, int(video_fps))
        frame_idx = 0
        saved_idx = 0
        temp_dir = Path("data/temp") / name.replace(" ", "_")
        temp_dir.mkdir(parents=True, exist_ok=True)

        while saved_idx < 30:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / video_fps
                frame_path = temp_dir / f"frame_{saved_idx:04d}.jpg"
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                # OCR con pytesseract si está disponible
                ocr_text = ""
                try:
                    import pytesseract
                    ocr_text = pytesseract.image_to_string(str(frame_path), lang='eng+spa').strip()
                    if ocr_text:
                        print(f"  [Frame {saved_idx} @ {timestamp:.1f}s] OCR: {ocr_text[:120]}...")
                except ImportError:
                    pass

                frames_texts.append({
                    "index": saved_idx,
                    "timestamp": timestamp,
                    "text": ocr_text,
                })
                saved_idx += 1

            frame_idx += 1

        cap.release()
        print(f"  Frames extraídos: {len(frames_texts)}")

        # Extraer audio y transcribir
        transcript = ""
        audio_path = temp_dir / "audio.wav"
        try:
            cmd = [
                settings.ffmpeg_path,
                "-i", str(video_path),
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1",
                "-y", str(audio_path),
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            if audio_path.exists() and audio_path.stat().st_size > 0:
                print(f"  Audio extraído: {audio_path.stat().st_size/1024:.1f} KB")
                try:
                    import whisper
                    print(f"  Transcribiendo con Whisper...")
                    model = whisper.load_model("base")
                    result = model.transcribe(str(audio_path), language="es")
                    transcript = result.get("text", "")
                    print(f"  📝 Transcripción: {transcript[:300]}...")
                except Exception as e:
                    print(f"  Whisper error: {e!s}")
        except Exception as e:
            print(f"  Audio error: {e!s}")

        # Generar informe
        informe = generate_informe(
            title=name,
            transcript=transcript,
            frames_texts=frames_texts,
            duracion=duracion,
            video_path=video_path,
            metadata=result,
        )

        return {
            "error": None,
            "informe": informe,
            "video": str(video_path),
            "duracion": duracion,
            "transcript": transcript,
        }

    except Exception as e:
        return {"error": f"Error en análisis: {e!s}", "informe": ""}


async def main():
    reels = [
        ("IG #1 - Dev", "https://www.instagram.com/reel/DYpsvyDu2by/?igsh=MXF3a2JuM2JxdnZrcg=="),
        ("IG #2 - Dev", "https://www.instagram.com/reel/DEXjF7Jg3ZD/?igsh=bHJsOWpzMXprcmNk"),
    ]

    download_dir = Path("data/downloads/instagram_reels")
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    informes = []
    for name, url_str in reels:
        result = await download_and_analyze(name, url_str, download_dir)
        if result["informe"]:
            informes.append((name, result["informe"]))
        else:
            print(f"✗ {name}: {result.get('error', 'Error desconocido')}")

    # Guardar informes individuales
    for i, (name, informe) in enumerate(informes):
        safe_name = name.replace(" ", "_").replace("#", "")
        output_path = output_dir / f"informe_{safe_name}.md"
        output_path.write_text(informe, encoding="utf-8")
        print(f"\n✅ Informe guardado: {output_path}")

    # Informe combinado
    if len(informes) > 1:
        combined = "# 📋 Informe Combinado - Instagram Reels\n\n"
        combined += "## Resumen General\n\n"
        combined += f"**Videos analizados:** {len(informes)}\n"
        combined += f"**Fecha:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        combined += "---\n"

        for i, (name, informe) in enumerate(informes):
            combined += f"\n---\n## {name}\n\n"
            # Extraer solo secciones relevantes del informe individual
            for section in informe.split("## "):
                if any(s in section for s in ["🔗 URLs", "💻 Comandos", "🛠️ Tecnologías", "📜 Transcripción", "📊 Resumen"]):
                    combined += "## " + section + "\n"

        combined_path = output_dir / "informe_combinado.md"
        combined_path.write_text(combined, encoding="utf-8")
        print(f"✅ Informe combinado: {combined_path}")

    print(f"\n{'='*60}")
    print("✅ Proceso completo finalizado.")
    print(f"📁 Informes disponibles en: {output_dir.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())