"""Persistencia del análisis en dashboardIA + notificación a Telegram.

En el flujo normal, el MCP `mie-mcp` (en el bot) guarda el análisis en dashboardIA
(POST /api/mie/save) y el bot responde inline. Pero en el flujo del PUENTE de descarga
residencial el MCP no está en el loop: el Mac sube el archivo directo a mie, así que es
mie quien debe (1) guardar en dashboardIA y (2) avisar por Telegram cuando termina.

Stdlib + httpx (ya presente). Las creds vienen de envs (Coolify).
"""

from typing import Optional

import httpx

from src.infrastructure.config.settings import settings
from src.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def save_to_dashboard(analysis: dict, url: str, language: Optional[str] = None) -> Optional[dict]:
    """POST del análisis CRUDO al backend dashboardIA (VideoTranscription + RAG).

    Mismo contrato que usa el MCP: POST {DASHBOARD_API_BASE}/api/mie/save con header
    X-Service-Token. Devuelve el JSON de respuesta o None si no está configurado/falla.
    """
    base = (settings.dashboard_api_base or "").rstrip("/")
    token = settings.dashboard_service_token or ""
    if not base or not token:
        logger.warning("dashboard save skipped: DASHBOARD_API_BASE/SERVICE_TOKEN no configurados")
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                f"{base}/api/mie/save",
                headers={"X-Service-Token": token},
                json={"analysis": analysis, "url": url, "language": language},
            )
            res.raise_for_status()
            data = res.json()
            logger.info("Saved to dashboardIA", id=data.get("id"))
            return data
    except Exception as exc:
        logger.warning("dashboard save failed", error=str(exc))
        return None


async def notify_telegram(text: str) -> bool:
    """Manda un mensaje al chat de Miguel vía la Bot API de Telegram.

    Usa el MISMO bot token del bot de OpenClaw (sendMessage no choca con el getUpdates
    del gateway). chat_id fijo en env (es el chat personal de Miguel).
    """
    token = settings.telegram_bot_token or ""
    chat_id = settings.telegram_notify_chat_id or ""
    if not token or not chat_id:
        logger.warning("telegram notify skipped: TELEGRAM_BOT_TOKEN/NOTIFY_CHAT_ID no configurados")
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            )
            res.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("telegram notify failed", error=str(exc))
        return False
