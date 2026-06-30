"""Cola del puente de descarga residencial (Instagram).

Instagram bloquea la IP del datacenter (Contabo), así que mie no puede bajar reels
directamente. Cuando llega una URL de IG, se ENCOLA aquí; un daemon que corre en una
máquina con IP residencial (el Mac de Miguel) consulta la cola, baja el reel con la
sesión viva del navegador y sube el archivo a `POST /analyze-file`.

Almacenamiento: SQLite en el volumen persistente `/data` (sobrevive redeploys y es
compartido entre los workers de uvicorn vía WAL). Stdlib only.
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional

from src.infrastructure.config.settings import settings
from src.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

_DB_PATH = Path("/data") / "ig_bridge_queue.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _init() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ig_queue (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                url          TEXT NOT NULL,
                language     TEXT,
                max_duration INTEGER,
                status       TEXT NOT NULL DEFAULT 'pending',
                error        TEXT,
                attempts     INTEGER NOT NULL DEFAULT 0,
                created_at   REAL NOT NULL,
                updated_at   REAL NOT NULL
            )
            """
        )
        conn.commit()


# Inicializa al importar (idempotente).
try:
    _init()
except Exception as exc:  # pragma: no cover - no debe tumbar el arranque
    logger.warning("ig_bridge_queue init failed", error=str(exc))


def enqueue(url: str, language: Optional[str] = None, max_duration: Optional[int] = None) -> int:
    """Agrega una URL pendiente. Evita duplicados que ya estén pending/processing."""
    now = time.time()
    with _connect() as conn:
        existing = conn.execute(
            "SELECT id FROM ig_queue WHERE url = ? AND status IN ('pending','processing')",
            (url,),
        ).fetchone()
        if existing:
            return int(existing["id"])
        cur = conn.execute(
            "INSERT INTO ig_queue (url, language, max_duration, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?)",
            (url, language, max_duration, now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_pending(limit: int = 20) -> list[dict]:
    """Devuelve ítems pendientes (los más viejos primero)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, url, language, max_duration, attempts FROM ig_queue "
            "WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def claim(item_id: int) -> bool:
    """Marca un ítem como 'processing' (solo si estaba pending). Evita doble proceso."""
    now = time.time()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE ig_queue SET status='processing', attempts=attempts+1, updated_at=? "
            "WHERE id=? AND status='pending'",
            (now, item_id),
        )
        conn.commit()
        return cur.rowcount > 0


def mark_done(item_id: int) -> None:
    now = time.time()
    with _connect() as conn:
        conn.execute(
            "UPDATE ig_queue SET status='done', error=NULL, updated_at=? WHERE id=?",
            (now, item_id),
        )
        conn.commit()


def mark_failed(item_id: int, error: str, requeue: bool = False) -> None:
    """Marca fallo. Si requeue=True vuelve a 'pending' para reintentar."""
    now = time.time()
    status = "pending" if requeue else "failed"
    with _connect() as conn:
        conn.execute(
            "UPDATE ig_queue SET status=?, error=?, updated_at=? WHERE id=?",
            (status, (error or "")[:1000], now, item_id),
        )
        conn.commit()
