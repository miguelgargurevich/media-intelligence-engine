"""
Análisis completo de los Instagram Reels descargados.
Extrae: frames, OCR, transcripción de audio, y genera informe markdown.

Uso:
    cd media-intelligence-engine
    .venv/bin/python tests/integration/test_full_analysis.py
"""

import asyncio
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.infrastructure.config.settings import settings


def generate_informe(title: str, transcript: str, frames_texts: list[dict], duracion: float, video_path: Path) -> str:
    """
    Genera un informe estructurado a partir del contenido extraído del video.
    Detecta URLs, comandos, tecnologías y código mencionados.
    """
    lines = []
    lines.append(f"# 📋 Informe de Análisis: {title}")
    lines.append("")
    lines.append(f"- **Fuente:** {video_path.name}")
    lines.append(f"- **Duración:** {duracion:.1f}s" if duracion else "")
    lines.append(f"- **Fecha análisis:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Detectar URLs en el texto
    all_text = transcript + "\n" + "\n".join(f.get("text", "") for f in frames_texts)
    urls = list(set(re.findall(r'https?://[^\s<>"\']+', all_text)))
    if urls:
        lines.append("## 🔗 URLs Mencionadas")
        lines.append("")
        for u in urls:
            lines.append(f"- {u}")
        lines.append("")

    # Detectar comandos
    cmd_patterns = [
        r'(?:^|\n)\s*\$?\s*(npm|pip|git|docker|kubectl|ssh|curl|wget|yarn|brew|apt|cd|ls|mkdir|rm|cp|mv|python|node)\s+[^\n]+',
        r'(?:^|\n)\s*```(?:bash|sh|shell)\s*\n([\s\S]*?)```',
    ]
    commands = []
    for pattern in cmd_patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        commands.extend(matches)
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
        "node": "Node.js", "rust": "Rust", "go": "Go",
        "sql": "SQL", "redis": "Redis", "postgresql": "PostgreSQL", "mongodb": "MongoDB",
        "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
        "git": "Git", "github": "GitHub", "tailwind": "Tailwind CSS",
        "next.js": "Next.js", "nuxt": "Nuxt", "svelte": "Svelte",
        "tensorflow": "TensorFlow", "pytorch": "PyTorch", "llm": "LLM",
        "ai": "AI", "openai": "OpenAI", "gpt": "GPT",
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

    # Bloques de código detectados en OCR
    code_pattern = re.findall(r'```(\w*)\n(.*?)```', all_text, re.DOTALL)
    if code_pattern:
        lines.append("## 📝 Bloques de Código")
        lines.append("")
        for lang, code in code_pattern:
            lines.append(f"```{lang}")
            lines.append(code.strip())
            lines.append("```")
            lines.append("")

    # Transcripción
    if transcript.strip():
        lines.append("## 📜 Transcripción del Audio")
        lines.append("")
        lines.append(transcript.strip())
        lines.append("")

    # Texto de frames (OCR)
    ocr_texts = [f.get("text", "") for f in frames_texts if f.get("text", "").strip()]
    if ocr_texts:
        lines.append("## 📸 Texto Detectado en Pantalla (OCR)")
        lines.append("")
        for ft in frames_texts:
            if ft.get("text", "").strip():
                lines.append(f"**[{ft['timestamp']:.1f}s]** {ft['text'].strip()}")
        lines.append("")

    # Resumen
    lines.append("---")
    lines.append("## 📊 Resumen")
    lines.append("")
    lines.append(f"- **URLs encontradas:** {len(urls)}")
    lines.append(f"- **Comandos detectados:** {len(commands)}")
    lines.append(f"- **Tecnologías identificadas:** {len(tecnologias)}")
    lines.append(f"- **Frames analizados:** {len(frames_texts)}")
    lines.append(f"- **Transcripción:** {'✅ Disponible' if transcript.strip() else '❌ No disponible'}")

    return "\n".join(lines)


async def analyze_video(video_path: Path, nombre: str) -> str:
    """Analiza un video completo y genera informe."""
    print(f"\n{'='*60}")
    print(f"Analizando {nombre}: {video_path.name}")
    print(f"{'='*60}")

    if not video_path.exists() or video_path.stat().st_size < 1000:
        print(f"✗ {nombre}: Archivo no válido o muy pequeño")
        return ""

    import cv2

    # Obtener duración y FPS
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"✗ {nombre}: No se puede abrir el video")
        return ""

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duracion = total_frames / video_fps if video_fps > 0 else 0
    print(f"  Duración: {duracion:.1f}s | FPS: {video_fps:.1f} | Frames: {total_frames}")

    # Extraer frames (1 frame por segundo)
    frames_texts = []
    frame_interval = max(1, int(video_fps))
    frame_idx = 0
    saved_idx = 0
    temp_dir = Path("data/temp/frames")
    temp_dir.mkdir(parents=True, exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0 and saved_idx < 20:  # max 20 frames
            timestamp = frame_idx / video_fps
            frame_path = temp_dir / f"{nombre}_{saved_idx:04d}.jpg"
            cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

            # Intentar OCR si está disponible
            ocr_text = ""
            try:
                import pytesseract
                ocr_text = pytesseract.image_to_string(str(frame_path), lang='eng+spa').strip()
            except ImportError:
                pass

            if ocr_text:
                print(f"  [Frame {saved_idx} @ {timestamp:.1f}s] OCR: {ocr_text[:100]}...")

            frames_texts.append({
                "index": saved_idx,
                "timestamp": timestamp,
                "path": str(frame_path),
                "text": ocr_text,
            })
            saved_idx += 1

        frame_idx += 1

    cap.release()
    print(f"  Frames extraídos: {len(frames_texts)}")

    # Extraer audio y transcribir con Whisper
    audio_path = Path(f"data/temp/audio_{nombre}.wav")
    transcript = ""

    try:
        import subprocess
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
            print(f"  Audio extraído: {audio_path.stat().st_size / 1024:.1f} KB")

            # Transcribir con Whisper
            try:
                import whisper
                print(f"  Transcribiendo con Whisper (modelo base)...")
                model = whisper.load_model("base")
                result = model.transcribe(str(audio_path), language="es")
                transcript = result.get("text", "")
                print(f"  Transcripción: {transcript[:200]}...")
            except Exception as e:
                print(f"  Whisper error: {e!s}")
        else:
            print(f"  ✗ No se pudo extraer audio")
    except Exception as e:
        print(f"  Audio extraction error: {e!s}")

    # Generar informe
    informe = generate_informe(
        title=nombre,
        transcript=transcript,
        frames_texts=frames_texts,
        duracion=duracion,
        video_path=video_path,
    )

    return informe


async def main():
    # Buscar los videos descargados
    download_dir = Path("data/downloads")
    videos = list(download_dir.rglob("*.mp4")) + list(download_dir.rglob("*.mov")) + list(download_dir.rglob("*.webm"))

    if not videos:
        print("No se encontraron videos en data/downloads/")
        print("Ejecuta primero: .venv/bin/python tests/integration/test_instagram_download.py")
        return

    print(f"Videos encontrados: {len(videos)}")
    for v in videos:
        print(f"  - {v} ({v.stat().st_size / 1024 / 1024:.2f} MB)")

    informes = []
    for i, video_path in enumerate(videos):
        nombre = f"IG #{i+1}"
        informe = await analyze_video(video_path, nombre)
        if informe:
            informes.append(informe)

    # Guardar informes
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, informe in enumerate(informes):
        output_path = output_dir / f"informe_ig_{i+1}.md"
        output_path.write_text(informe, encoding="utf-8")
        print(f"\nInforme guardado: {output_path}")

    # Generar informe combinado si hay varios
    if len(informes) > 1:
        combined = ["# 📋 Informe Combinado\n"]
        for i, informe in enumerate(informes):
            combined.append(f"\n---\n## Video IG #{i+1}\n")
            combined.append(informe)
        combined_path = output_dir / "informe_combinado.md"
        combined_path.write_text("\n".join(combined), encoding="utf-8")
        print(f"Informe combinado: {combined_path}")

    print(f"\n{'='*60}")
    print("Análisis completado.")
    print(f"Revisa los informes en: {output_dir.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())