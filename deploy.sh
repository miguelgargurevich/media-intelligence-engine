#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Despliega media-intelligence-engine al VPS (Traefik/coolify).
#
# El servicio se enruta vía el proxy Traefik existente (coolify-proxy) por la
# red `coolify`; el docker-compose.yml ya trae los labels de Traefik y NO
# publica puertos al host.
#
# Flujo:
#   1. Sincroniza el repo en el VPS (clone/pull a REPO_DIR persistente).
#   2. SIEMPRE copia el cookies.txt local al VPS (descargas autenticadas).
#   3. Verifica que exista el .env en el VPS (secreto del servidor, no se copia).
#   4. docker compose build (sin downtime) → recrea el contenedor → /health.
#
# Uso:
#   ./deploy.sh
#   COOKIES=~/ruta/cookies.txt ./deploy.sh
#
# Requisitos: acceso SSH al VPS (host en ~/.ssh/config) y .env ya presente en REPO_DIR.
# =============================================================================
set -euo pipefail

# ── Config (override por variables de entorno) ───────────────────────────────
VPS="${VPS:-gds-vps}"
REPO_DIR="${REPO_DIR:-/opt/media-intelligence-engine}"
REPO_URL="${REPO_URL:-https://github.com/miguelgargurevich/media-intelligence-engine.git}"
BRANCH="${BRANCH:-main}"
COOKIES="${COOKIES:-$HOME/Downloads/cookies.txt}"

echo "▶ VPS=$VPS  REPO_DIR=$REPO_DIR  BRANCH=$BRANCH"

# ── 0. Validar cookies locales ───────────────────────────────────────────────
if [[ ! -f "$COOKIES" ]]; then
  echo "✖ No se encontró el archivo de cookies: $COOKIES" >&2
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
  echo -n '  commit: '; git -C '$REPO_DIR' rev-parse --short HEAD"

# ── 2. Copiar SIEMPRE las cookies (antes del up: el mount es de archivo) ──────
echo "▶ Copiando cookies al VPS ($REPO_DIR/cookies.txt)..."
scp "$COOKIES" "$VPS:$REPO_DIR/cookies.txt"
ssh "$VPS" "chmod 600 '$REPO_DIR/cookies.txt'"
echo "✓ Cookies copiadas"

# ── 3. Validar .env en el VPS (secreto del servidor, no se commitea ni copia) ─
ssh "$VPS" "test -f '$REPO_DIR/.env'" || {
  echo "✖ Falta $REPO_DIR/.env en el VPS (API keys). Copialo una vez:" >&2
  echo "    scp tu/.env $VPS:$REPO_DIR/.env" >&2
  exit 1
}

# ── 4. Build (sin downtime) → recrear contenedor → health ────────────────────
echo "▶ Construyendo imagen (sin downtime)..."
ssh "$VPS" "cd '$REPO_DIR' && docker compose build"

echo "▶ Recreando contenedor..."
ssh "$VPS" "cd '$REPO_DIR' && docker rm -f mie-api >/dev/null 2>&1 || true && docker compose up -d"

echo "▶ Verificando /health (interno y público)..."
ssh "$VPS" "for i in 1 2 3 4 5 6 7 8; do
    if docker exec mie-api curl -sf http://localhost:8000/health >/dev/null 2>&1; then echo '  ✓ contenedor OK'; break; fi
    sleep 3
  done"
if curl -sf --max-time 10 https://mie.gargurevich.dev/health >/dev/null; then
  echo "✅ Deploy OK: https://mie.gargurevich.dev/health responde"
else
  echo "⚠ El endpoint público no respondió aún (Traefik puede tardar unos segundos)." >&2
fi
