"""Analysis endpoint router."""

from fastapi import APIRouter, HTTPException

from src.api.schemas.requests import AnalyzeRequest
from src.api.schemas.responses import (
    AnalyzeResponse,
    TimelineEntryResponse,
    CodeBlockResponse,
)
from src.domain.entities.analysis import AnalysisResult
from src.domain.value_objects.url import URL
from src.infrastructure.config.settings import settings
from src.infrastructure.config.logging_config import get_logger
from src.services import ig_bridge_queue
from src.services.pipeline import Pipeline

logger = get_logger(__name__)

router = APIRouter(tags=["analysis"])

# Dominios cuya descarga el VPS NO puede hacer (bloqueo por IP de datacenter) y se
# derivan al PUENTE residencial (daemon en el Mac). Hoy solo Instagram está verificado.
_BRIDGE_DOMAINS = ("instagram.com",)


def build_analyze_response(result: AnalysisResult) -> AnalyzeResponse:
    """Mapea un AnalysisResult del pipeline al schema de respuesta de la API."""
    return AnalyzeResponse(
        title=result.title,
        description=result.description,
        duration=result.duration,
        language=result.language,
        source_url=result.source_url,
        status=result.status,
        error=result.error,
        transcript=result.transcript,
        transcript_segments=result.transcript_segments,
        visual_summary=result.visual_summary,
        timeline=[
            TimelineEntryResponse(
                timestamp=entry.timestamp,
                text=entry.text,
                ocr_text=entry.ocr_text,
                vision_description=entry.vision_description,
                commands=entry.commands or [],
                code_blocks=entry.code_blocks or [],
                urls=entry.urls or [],
                technologies=entry.technologies or [],
                keywords=entry.keywords or [],
            )
            for entry in result.timeline
        ],
        commands=result.commands,
        code_blocks=[
            CodeBlockResponse(
                code=b.get("code", ""),
                language=b.get("language"),
                source=b.get("source", "unknown"),
            )
            for b in result.code_blocks
        ],
        urls=result.urls,
        technologies=result.technologies,
        keywords=result.keywords,
        summary=result.summary,
        markdown=result.markdown,
        html=result.html,
        sentiment=result.sentiment,
        topic_type=result.topic_type,
        chapters=result.chapters,
        highlights=result.highlights,
        participants=result.participants,
        tasks=result.tasks,
        agreements=result.agreements,
        risks=result.risks,
        open_questions=result.open_questions,
        next_steps=result.next_steps,
        hashtags=result.hashtags,
        follow_up_email=result.follow_up_email,
        diagrams=result.diagrams,
    )


def _should_bridge(url_str: str) -> bool:
    if not settings.ig_bridge_enabled:
        return False
    try:
        domain = URL.from_string(url_str).domain.lower()
    except Exception:
        return False
    return any(d in domain for d in _BRIDGE_DOMAINS)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze media content from a URL",
    description="Downloads or records media from the given URL, then extracts structured knowledge "
    "including transcript, OCR text, vision analysis, commands, code blocks, URLs, and technologies.",
)
async def analyze_media(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze media content from a URL."""
    # Instagram (y similares) no se pueden bajar desde el VPS por el bloqueo de IP del
    # datacenter. En vez de intentar y fallar, encolamos la URL para que el puente
    # residencial (Mac) la baje y la suba a /analyze-file. Respondemos status="queued".
    if _should_bridge(request.url):
        qid = ig_bridge_queue.enqueue(
            url=request.url,
            language=request.language,
            max_duration=request.max_duration,
        )
        logger.info("URL derivada al puente residencial", url=request.url, queue_id=qid)
        return AnalyzeResponse(
            source_url=request.url,
            status="queued",
            title="Instagram — en cola (puente residencial)",
            summary=(
                "Instagram bloquea la descarga desde el servidor. La URL quedó EN COLA y la "
                "está bajando el puente residencial; el análisis aparecerá en el dashboard y "
                "te avisaré por acá cuando esté listo. No hace falta que reenvíes el enlace."
            ),
        )

    pipeline = Pipeline()
    result = await pipeline.run(
        url_str=request.url,
        fps=request.fps,
        language=request.language,
        vision_provider=request.vision_provider,
        max_duration=request.max_duration,
    )

    if result.status == "failed" and result.error:
        raise HTTPException(status_code=422, detail=result.error)

    return build_analyze_response(result)
