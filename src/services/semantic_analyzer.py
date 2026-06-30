"""
Semantic analyzer - enriches analysis with LLM-powered semantic data.
Cascading providers: DeepSeek → Gemini → Groq.
Produces: sentiment, topicType, chapters, highlights, participants, tasks,
          agreements, risks, openQuestions, nextSteps, technologies,
          codeBlocks, commands, urls, hashtags, followUpEmail, diagrams (Mermaid).
"""

import json
import asyncio
from typing import Optional

from src.infrastructure.config.settings import settings
from src.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

UNIVERSAL_SYSTEM_PROMPT = """Eres un analista universal de contenido multimedia.
Analizas transcripciones de cualquier tipo de video (tutoriales, reuniones, presentaciones, demos, podcasts, entrevistas, reels, TikTok, YouTube, etc.).

Tu tarea es:
1. PRIMERO detecta el tipo de contenido (topicType)
2. LUEGO extrae SOLO los campos que tengan sentido para ese tipo
3. Si un campo no aplica, devuélvelo como array vacío [] o null
4. NO inventes información que no esté en la transcripción
5. Los timestamps en formato [MM:SS] o [HH:MM:SS] cuando sea posible
6. Responde SIEMPRE en español y SOLO el JSON, sin texto adicional"""

UNIVERSAL_JSON_SHAPE = """{
  "title": string,               // título conciso y descriptivo (máx 80 chars) SIEMPRE
  "summary": string[],           // 5-10 puntos ejecutivos SIEMPRE
  "sentiment": "POSITIVE"|"NEUTRAL"|"NEGATIVE",  // SIEMPRE
  "topicType": "tutorial"|"reunion"|"presentacion"|"demo"|"podcast"|"entrevista"|"short"|"otro",
  "chapters": [{ "title": string, "summary": string, "startSec": number|null }],
  "highlights": [{ "quote": string, "atSec": number|null }],
  "keywords": string[],           // SIEMPRE (10-20 keywords)
  "markdown": string,
  "html": string,

  "participants": string[],
  "tasks": [{ "title": string, "assignee": string, "priority": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL", "status": "TODO"|"IN_PROGRESS"|"DONE"|"BLOCKED" }],
  "agreements": [{ "title": string, "description": string, "owner": string, "targetDate": string|null }],
  "risks": [{ "risk": string, "impact": "LOW"|"MEDIUM"|"HIGH", "mitigation": string }],
  "openQuestions": string[],
  "nextSteps": string[],
  "technologies": string[],
  "codeBlocks": [{ "language": string, "code": string }],
  "commands": string[],
  "urls": string[],
  "hashtags": string[],
  "followUpEmail": { "subject": string, "body": string } | null,
  "diagrams": [{ "type": "flowchart"|"sequenceDiagram"|"mindmap"|"timeline"|"classDiagram", "title": string, "mermaid": string }]
}"""


async def call_llm_provider(url: str, headers: dict, body: dict, timeout: int) -> Optional[str]:
    """Call an LLM provider and return the content text, or None on failure."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.is_success:
                data = resp.json()
                # Handle OpenAI/DeepSeek format
                if "choices" in data:
                    msg = data["choices"][0].get("message", {})
                    return msg.get("content")
                # Handle Gemini format
                if "candidates" in data:
                    parts = data["candidates"][0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text")
                # Handle other formats
                if "content" in data:
                    return data["content"]
            else:
                logger.warning(f"LLM provider returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"LLM provider error: {e}")
    return None


async def deepinfra_analyze(user_prompt: str) -> Optional[str]:
    """Call DeepInfra (OpenAI-compatible) — primario barato."""
    if not settings.deepinfra_llm_api_key:
        return None
    return await call_llm_provider(
        url="https://api.deepinfra.com/v1/openai/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.deepinfra_llm_api_key}",
            "Content-Type": "application/json",
        },
        body={
            "model": settings.deepinfra_llm_model,
            "messages": [
                {"role": "system", "content": UNIVERSAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 16000,
            "response_format": {"type": "json_object"},
        },
        timeout=settings.semantic_timeout_seconds,
    )


async def deepseek_analyze(user_prompt: str) -> Optional[str]:
    """Call DeepSeek Chat API."""
    if not settings.deepseek_llm_api_key:
        return None
    return await call_llm_provider(
        url="https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.deepseek_llm_api_key}",
            "Content-Type": "application/json",
        },
        body={
            "model": settings.deepseek_llm_model,
            "messages": [
                {"role": "system", "content": UNIVERSAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 16000,
            "response_format": {"type": "json_object"},
        },
        timeout=settings.semantic_timeout_seconds,
    )


async def gemini_analyze(user_prompt: str) -> Optional[str]:
    """Call Gemini API."""
    if not settings.gemini_api_key:
        return None
    model_id = getattr(settings, "gemini_model", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={settings.gemini_api_key}"
    return await call_llm_provider(
        url=url,
        headers={"Content-Type": "application/json"},
        body={
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": UNIVERSAL_SYSTEM_PROMPT}]},
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 16384},
        },
        timeout=settings.semantic_timeout_seconds,
    )


async def groq_analyze(user_prompt: str) -> Optional[str]:
    """Call Groq API (LLaMA 3.3)."""
    if not settings.groq_api_key:
        return None
    return await call_llm_provider(
        url="https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        body={
            "model": settings.groq_llm_model,
            "messages": [
                {"role": "system", "content": UNIVERSAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 16000,
            "response_format": {"type": "json_object"},
        },
        timeout=settings.semantic_timeout_seconds,
    )


async def enrich_semantics(
    transcript: str,
    title: str = "",
    timeline: Optional[list] = None,
) -> dict:
    """
    Run the cascading LLM analysis on a transcript.
    Returns a dict with all enriched fields, or an empty fallback.
    """
    if not transcript or len(transcript) < 20:
        return _empty_semantics("Transcript too short")

    meta = f"Título del video: {title}" if title else ""
    timeline_context = ""
    if timeline and len(timeline) > 0:
        timeline_context = (
            "\n\nContexto visual (timeline con OCR y descripciones de frames):\n"
            + json.dumps(timeline[:20], ensure_ascii=False, indent=2)
        )

    user_prompt = f"""{meta}

Analiza la siguiente transcripción y devuelve EXCLUSIVAMENTE un objeto JSON con esta forma exacta:

{UNIVERSAL_JSON_SHAPE}

Reglas IMPORTANTES:
- "title": título corto y descriptivo del contenido (máx 80 caracteres), en español, sin comillas ni emojis.
- "summary": máximo 10 puntos ejecutivos, cada uno una frase.
- "topicType": detecta el tipo de contenido automáticamente
- Extrae campos condicionales SOLO si aparecen explícita o implícitamente
- Si un campo no aplica, devuelve array vacío [] o null
- Para "short" (reels/TikTok), prioriza: summary, sentiment, keywords, hashtags, highlights
- Para "tutorial"/"demo", prioriza: chapters, technologies, codeBlocks, commands, urls
- Para "reunion", prioriza: participants, tasks, agreements, risks, openQuestions, nextSteps, followUpEmail, diagrams
- Para "presentacion", prioriza: chapters, highlights, diagrams
- Para "podcast"/"entrevista", prioriza: participants, chapters, highlights, openQuestions
- "diagrams": genera 0-2 diagramas Mermaid que aporten valor. Solo si aplican.
- No añadas comentarios ni markdown alrededor del JSON. Solo el JSON.
{timeline_context}

TRANSCRIPCIÓN:
\"\"\"
{transcript[:100_000]}
\"\"\""""

    last_err = ""
    raw_text = None

    # Cascada: DeepInfra → DeepSeek (primarios) → Gemini → Groq (fallback free)
    for attempt_name, attempt_fn in [
        ("DeepInfra", deepinfra_analyze),
        ("DeepSeek", deepseek_analyze),
        ("Gemini", gemini_analyze),
        ("Groq", groq_analyze),
    ]:
        logger.info(f"Semantic analysis attempt: {attempt_name}")
        try:
            raw_text = await attempt_fn(user_prompt)
            if raw_text:
                logger.info(f"Semantic analysis succeeded: {attempt_name}")
                break
            last_err += f" | {attempt_name}: empty response"
        except Exception as e:
            last_err += f" | {attempt_name}: {e}"
            logger.warning(f"Semantic analysis failed: {attempt_name}: {e}")

    if not raw_text:
        logger.warning(f"All semantic providers failed: {last_err}")
        return _empty_semantics(last_err.lstrip(" | "))

    # Clean and parse
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("\n", 1)[0] if "\n" in cleaned else cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON from semantic analysis, using fallback")
        return _empty_semantics("Error parsing JSON from semantic analysis")


def _empty_semantics(reason: str = "") -> dict:
    return {
        "title": "",
        "summary": [reason or "No se pudo analizar el contenido"],
        "sentiment": "NEUTRAL",
        "topicType": "otro",
        "chapters": [],
        "highlights": [],
        "keywords": [],
        "markdown": "",
        "html": "",
        "participants": [],
        "tasks": [],
        "agreements": [],
        "risks": [],
        "openQuestions": [],
        "nextSteps": [],
        "technologies": [],
        "codeBlocks": [],
        "commands": [],
        "urls": [],
        "hashtags": [],
        "followUpEmail": None,
        "diagrams": [],
    }