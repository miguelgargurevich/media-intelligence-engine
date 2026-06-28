# =============================================================================
# Makefile - Media Intelligence Engine
# =============================================================================

.PHONY: help install dev lint format typecheck test test-cov clean run docker-build docker-up docker-down

help:
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║  Media Intelligence Engine - Makefile                       ║"
	@echo "╠══════════════════════════════════════════════════════════════╣"
	@echo "║  install       Instalar dependencias                       ║"
	@echo "║  dev           Instalar en modo desarrollo                 ║"
	@echo "║  lint          Ejecutar Ruff (lint)                        ║"
	@echo "║  format        Ejecutar Black (formato)                    ║"
	@echo "║  typecheck     Ejecutar Mypy (tipado)                      ║"
	@echo "║  test          Ejecutar tests unitarios                    ║"
	@echo "║  test-cov      Ejecutar tests con cobertura                ║"
	@echo "║  clean         Limpiar archivos temporales                 ║"
	@echo "║  run           Iniciar servidor local                      ║"
	@echo "║  docker-build  Construir imagen Docker                     ║"
	@echo "║  docker-up     Iniciar contenedores                        ║"
	@echo "║  docker-down   Detener contenedores                        ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"

install:
	pip install -e ".[dev,vision]"
	pip install yt-dlp gallery-dl
	playwright install chromium

dev: install
	cp -n .env.example .env 2>/dev/null || true

lint:
	ruff check src/ tests/

format:
	black src/ tests/

typecheck:
	mypy src/

test:
	pytest tests/unit/ -v --asyncio-mode=auto

test-cov:
	pytest tests/ -v --cov=src --cov-report=term --cov-report=html --asyncio-mode=auto

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml
	rm -rf data/downloads/* data/recordings/* data/output/* data/temp/*

run:
	uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t media-intelligence-engine .

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api