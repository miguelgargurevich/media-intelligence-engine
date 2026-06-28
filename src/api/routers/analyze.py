"""Analysis endpoint router."""

from fastapi import APIRouter, HTTPException

from src.api.schemas.requests import AnalyzeRequest
from src.api.schemas.responses import (
    AnalyzeResponse,
    TimelineEntryResponse,
    CodeBlockResponse,
)
from src.services.pipeline import Pipeline

router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze media content from a URL",
    description="Downloads or records media from the given URL, then extracts structured knowledge "
    "including transcript, OCR text, vision analysis, commands, code blocks, URLs, and technologies.",
)
async def analyze_media(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze media content from a URL."""
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
    )