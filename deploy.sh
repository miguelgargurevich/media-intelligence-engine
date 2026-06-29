#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Despliega media-intelligence-engine al VPS.
#
# Flujo:
#   1. Sincroniza el repo en el VPS (clone/pull a REPO_DIR persistente).
#   2. SIEMPRE copia el cookies.txt local al VPS (necesario para descargas
#      autenticadas: Instagram, YouTube, etc.). El archivo NUNCA se commitea.
#   3. Reconstruye y reinicia el contenedor con docker compose.
#   4. Verifica /health.
#
# Uso:
#   ./deploy.sh                       # usa los defaults de abajo
#   COOKIES=~/ruta/cookies.txt ./deploy.sh
#
# Requisitos: acceso SSH al VPS (host configurado en ~/.ssh/config).
# =============================================================================
set -euo pipefail

# ── Config (override por variables de entorno) ───────────────────────────────
VPS="${VPS:-gds-vps}"
REPO_DIR="${REPO_DIR:-/opt/media-intelligence-engine}"
REPO_URL="${REPO_URL:-https://github.com/miguelgargurevich/media-intelligence-engine.git}"
BRANCH="${BRANCH:-main}"
COOKIES="${COOKIES:-$HOME/Downloads/cookies.txt}"

echo "▶ VPS=$VPS  REPO_DIR=$REPO_DIR  BRANCH=$BRANCH"

# ── 0. Validar que las cookies existen localmente ────────────────────────────
if [[ ! -f "$COOKIES" ]]; then
  echo "✖ No se encontró el archivo de cookies: $COOKIES" >&2
  echo "  Exporta tus cookies (formato Netscape) y vuelve a intentar, o pasa COOKIES=..." >&2
  exit 1
fi
echo "✓ Cookies locales: $COOKIES ($(wc -c < "$COOKIES") bytes)"

# ── 1. Sincronizar el repo en el VPS ─────────────────────────────────────────
echo "▶ Sincronizando repo en el VPS..."
ssh "$VPS" "set -e
  if [[ -d '$REPO_DIR/.git' ]]; then
    cd '$REPO_DIR' && git fetch origin && git reset --hard 'origin/$BRANCH'
  else
    git clone --branch '$BRANCH' '$REPO_URL' '$REPO_DIR'
  fi
  git -C '$REPO_DIR' rev-parse --short HEAD"

# ── 2. Copiar SIEMPRE las cookies (antes del compose up: el mount es de archivo)
echo "▶ Copiando cookies al VPS ($REPO_DIR/cookies.txt)..."
scp "$COOKIES" "$VPS:$REPO_DIR/cookies.txt"
ssh "$VPS" "chmod 600 '$REPO_DIR/cookies.txt'"
echo "✓ Cookies copiadas"

# ── 3. Build + restart con docker compose ────────────────────────────────────
echo "▶ Reconstruyendo y reiniciando contenedor..."
ssh "$VPS" "cd '$REPO_DIR' && docker compose up -d --build"

# ── 4. Health check ──────────────────────────────────────────────────────────
echo "▶ Verificando /health..."
ssh "$VPS" "for i in 1 2 3 4 5 6; do
    if curl -sf http://localhost:8000/health >/dev/null; then echo '✓ Servicio OK'; exit 0; fi
    sleep 3
  done
  echo '✖ El servicio no respondió a /health' >&2; exit 1"

echo "✅ Deploy completado: https://mie.gargurevich.dev/health"
