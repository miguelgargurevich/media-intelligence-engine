"""Puente de descarga residencial (Instagram) — endpoints para el daemon del Mac.

Flujo:
  1. /analyze recibe una URL de IG → la encola (ig_bridge_queue) y responde "queued".
  2. El daemon del Mac hace GET /ig-queue/pending, reclama el ítem (/claim), baja el
     reel con la sesión viva del navegador (IP residencial) y sube el archivo a
     /analyze-file.
  3. mie corre el pipeline sobre el archivo, guarda el análisis en dashboardIA y avisa
     por Telegram. Marca el ítem como done (o failed).

Sin auth (decisión del usuario): mismo criterio que /analyze.
"""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.api.routers.analyze import build_analyze_response
from src.infrastructure.config.logging_config import get_logger
from src.infrastructure.config.settings import settings
from src.services import ig_bridge_queue
from src.services.dashboard_sink import notify_telegram, save_to_dashboard
from src.services.pipeline import Pipeline

logger = get_logger(__name__)

router = APIRouter(tags=["bridge"], prefix="/ig-queue")


@router.get("/pending", summary="Lista las descargas de Instagram pendientes (para el daemon residencial)")
async def pending(limit: int = 20) -> dict:
    if not settings.ig_bridge_enabled:
        return {"enabled": False, "items": []}
    return {"enabled": True, "items": ig_bridge_queue.list_pending(limit=limit)}


@router.post("/{item_id}/claim", summary="Reclama un ítem (lo marca processing) para evitar doble proceso")
async def claim(item_id: int) -> dict:
    ok = ig_bridge_queue.claim(item_id)
    return {"claimed": ok, "id": item_id}


@router.post("/{item_id}/fail", summary="Marca un ítem como fallido (o lo re-encola)")
async def fail(item_id: int, error: str = Form(""), requeue: bool = Form(False)) -> dict:
    ig_bridge_queue.mark_failed(item_id, error=error, requeue=requeue)
    return {"ok": True, "id": item_id, "requeued": requeue}


# El endpoint de subida vive fuera del prefix /ig-queue.
file_router = APIRouter(tags=["bridge"])


@file_router.post(
    "/analyze-file",
    summary="Analiza un archivo de media YA descargado (subido por el puente residencial)",
    description="Recibe un archivo (multipart) ya bajado en una IP residencial (ej. reel de "
    "Instagram bajado por el Mac), corre el pipeline completo, guarda el análisis en dashboardIA "
    "y avisa por Telegram. Pensado para el daemon del puente; no para uso interactivo.",
)
async def analyze_file(
    file: UploadFile = File(...),
    source_url: str = Form(...),
    queue_id: Optional[int] = Form(None),
    language: Optional[str] = Form(None),
    max_duration: Optional[int] = Form(None),
) -> dict:
    # Persistir el upload en el dir de descargas.
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    fd, tmp_path = tempfile.mkstemp(prefix="bridge_", suffix=suffix, dir=str(settings.download_dir))
    try:
        import os
        with os.fdopen(fd, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)

        logger.info("Bridge file recibido", source_url=source_url, path=tmp_path, queue_id=queue_id)

        pipeline = Pipeline()
        kwargs = {}
        if language:
            kwargs["language"] = language
        if max_duration:
            kwargs["max_duration"] = max_duration
        result = await pipeline.run_from_file(file_path=tmp_path, source_url=source_url, **kwargs)

        if result.status == "failed":
            if queue_id:
                ig_bridge_queue.mark_failed(queue_id, error=result.error or "pipeline failed")
            raise HTTPException(status_code=422, detail=result.error or "Pipeline failed")

        response = build_analyze_response(result)
        raw = response.model_dump()

        # Guardar en dashboardIA (VideoTranscription + RAG), como hace el MCP en el flujo normal.
        saved = await save_to_dashboard(raw, source_url, language)

        # Avisar por Telegram que quedó listo.
        title = result.title or "Reel de Instagram"
        summary = (result.summary or "").strip()
        if len(summary) > 600:
            summary = summary[:600].rstrip() + "…"
        msg = f"✅ Análisis listo: {title}\n{source_url}"
        if summary:
            msg += f"\n\n{summary}"
        if saved and saved.get("id"):
            msg += "\n\n📊 Guardado en tu dashboard (Transcripciones de video)."
        await notify_telegram(msg)

        if queue_id:
            ig_bridge_queue.mark_done(queue_id)

        return {
            "status": result.status,
            "title": result.title,
            "saved": bool(saved and saved.get("id")),
            "dashboard_id": (saved or {}).get("id"),
            "notified": True,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("analyze-file failed", error=str(exc))
        if queue_id:
            ig_bridge_queue.mark_failed(queue_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
