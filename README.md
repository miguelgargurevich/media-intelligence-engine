# 🧠 Media Intelligence Engine

> **Microservicio para análisis automático de contenido multimedia**
>
> Extrae conocimiento estructurado de cualquier contenido multimedia a partir de una URL.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Clean Architecture](https://img.shields.io/badge/Architecture-Clean-red)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
[![Deploy](https://img.shields.io/badge/Deploy-Production-brightgreen)](https://mie.gargurevich.dev)

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Arquitectura](#-arquitectura)
- [Pipeline de Análisis](#-pipeline-de-análisis)
- [Stack Tecnológico](#-stack-tecnológico)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [API](#-api)
- [Sistema de Plugins](#-sistema-de-plugins)
- [Configuración](#-configuración)
- [Docker](#-docker)
- [Observabilidad](#-observabilidad)
- [Tests](#-tests)
- [Futuro](#-futuro)
- [Licencia](#-licencia)

---

## 🎯 Descripción

**Media Intelligence Engine** es un microservicio en Python que analiza contenido multimedia publicado en Internet. **NO es un descargador de videos** — su propósito es extraer **conocimiento estructurado** del contenido.

### ¿Qué puede extraer?

- ✅ **Transcripción completa** del audio (Whisper)
- ✅ **Texto visible** en cada fotograma (OCR)
- ✅ **Descripción visual** del contenido (AI Vision)
- ✅ **Comandos** detectados en la terminal/tutoriales
- ✅ **Bloques de código** (Python, JS, Go, etc.)
- ✅ **URLs** mencionadas o mostradas
- ✅ **Tecnologías** identificadas
- ✅ **Línea de tiempo** con todo el contenido sincronizado
- ✅ **Documentos** Markdown y HTML generados automáticamente

---

## 🏗️ Arquitectura

El sistema sigue **Clean Architecture** y **principios SOLID**:

```
┌─────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)               │
│  POST /analyze  |  GET /health  |  GET /metrics     │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│                 Use Cases                            │
│  analyze_media  |  extract_frames  |  run_ocr       │
│  transcribe_audio  |  analyze_vision  |  fuse        │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              Domain Entities                         │
│  Media  |  Frame  |  AudioTrack  |  AnalysisResult   │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              Ports (Interfaces)                      │
│  IDownloader  |  IRecorder  |  IOCREngine           │
│  ISpeechToText  |  IVisionProvider  |  IStorage     │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│          Infrastructure (Adapters)                   │
│  yt-dlp  |  Playwright  |  FFmpeg  |  PaddleOCR    │
│  Whisper  |  GPT-4o  |  Gemini  |  Claude          │
└─────────────────────────────────────────────────────┘
```

### Principios de Diseño

| Principio | Aplicación |
|-----------|-----------|
| **SRP** | Cada módulo tiene una única responsabilidad |
| **OCP** | Nuevos extractores/proveedores sin modificar código existente |
| **LSP** | Interfaces intercambiables (todos los vision providers implementan `IVisionProvider`) |
| **ISP** | Interfaces pequeñas y específicas |
| **DIP** | Capas altas no dependen de implementaciones concretas |

---

## 🔄 Pipeline de Análisis

```
URL ──→ ┌────────── NIVEL 1 ──────────┐
         │  yt-dlp → gallery-dl       │
         │  HTML extraction → DOM     │
         └────────── éxito? ──────────┘
                │ sí           │ no
                ▼              ▼
          Video local    ┌─── NIVEL 2 ────┐
                         │  Playwright    │
                         │  Buscar <video>│
                         └─── éxito? ─────┘
                              │ sí     │ no
                              ▼        ▼
                        Video src  ┌─── NIVEL 3 ────┐
                                   │  Reproducir    │
                                   │  Grabar pantalla│
                                   └────────────────┘
                                        │
                   Todos los caminos convergen
                                        │
                              ▼
                    ┌─── NIVEL 4 ────┐
                    │  Extraer frames │
                    │  (1 fps)       │
                    └────────────────┘
                              │
                    ┌─── NIVEL 5 ────┐
                    │  OCR (Paddle)  │
                    │  texto, código │
                    └────────────────┘
                              │
                    ┌─── NIVEL 6 ────┐
                    │  Whisper STT   │
                    │  transcripción │
                    └────────────────┘
                              │
                    ┌─── NIVEL 7 ────┐
                    │  Vision AI     │
                    │  GPT/Gemini/Claude│
                    └────────────────┘
                              │
                    ┌─── NIVEL 8 ────┐
                    │  Fusion Engine │
                    │  → JSON final  │
                    └────────────────┘
```

---

## 🛠️ Stack Tecnológico

| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| Python | 3.13+ | Lenguaje base |
| FastAPI | 0.115+ | API REST |
| Pydantic | 2.9+ | Validación de datos |
| Playwright | 1.48+ | Automatización de navegador |
| OpenCV | 4.10+ | Extracción de frames |
| Whisper | 20240930 | Transcripción de audio |
| PaddleOCR | 2.9+ | Reconocimiento óptico de caracteres |
| yt-dlp | 2024.11+ | Descarga de medios |
| FFmpeg | latest | Procesamiento de audio/video |
| httpx | 0.28+ | Cliente HTTP asíncrono |
| Celery | 5.4+ | Cola de tareas (preparado) |
| Redis | 7+ | Cache y broker |

### Vision Providers Soportados

El pipeline prueba proveedores en orden hasta que uno funciona:

1. **OpenAI GPT-4o** (default) → `openai`
2. **Google Gemini** → `gemini`
3. **DeepSeek VL** → `deepseek` (OpenAI-compatible API)
4. **Qwen VL** → `qwen` (Alibaba Cloud)
5. **Claude** → `anthropic`
6. **Ollama (local)** → `ollama`

| Proveedor | SDK | Modelo por defecto |
|-----------|-----|-------------------|
| OpenAI GPT | `openai` | `gpt-4o` |
| Google Gemini | `google-generativeai` | `gemini-1.5-pro` |
| DeepSeek VL | `httpx` (API directa) | `deepseek-vl2` |
| Qwen VL | `httpx` (API directa) | `qwen-vl-max` |
| Anthropic Claude | `anthropic` | `claude-3-5-sonnet` |
| Ollama (local) | `ollama` | `llama3.2-vision` |

---

## 🚀 Instalación

### Local

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/media-intelligence-engine.git
cd media-intelligence-engine

# Instalar dependencias
make install

# O manualmente
pip install -e ".[dev,vision]"
pip install yt-dlp gallery-dl
playwright install chromium

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# Iniciar servidor
make run
```

### Docker

```bash
# Construir y ejecutar
make docker-up

# O manualmente
docker compose up -d --build
```

---

## 📖 Uso

### Analizar un video

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=example"
  }'
```

### Respuesta

```json
{
  "title": "Tutorial de Python",
  "description": "Aprende Python desde cero",
  "duration": 1200.5,
  "language": "es",
  "status": "completed",
  "transcript": "Bienvenidos a este tutorial...",
  "transcript_segments": [
    {"text": "Bienvenidos", "start": 0.0, "end": 2.5, "confidence": 0.98}
  ],
  "commands": ["pip install flask", "python app.py"],
  "code_blocks": [
    {"code": "def hello():", "language": "python", "source": "ocr"}
  ],
  "urls": ["https://python.org"],
  "technologies": ["python", "flask"],
  "keywords": ["tutorial", "python", "programacion"],
  "timeline": [
    {
      "timestamp": 0.0,
      "ocr_text": "Python Tutorial",
      "vision_description": "Título del tutorial en pantalla",
      "commands": [],
      "code_blocks": []
    }
  ],
  "summary": "Tutorial completo de Python...",
  "markdown": "# Tutorial de Python\\n...",
  "html": "<h1>Tutorial de Python</h1>..."
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

---

## 📡 API

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/analyze` | Analizar contenido multimedia desde una URL |
| `GET` | `/health` | Health check del servicio |
| `GET` | `/metrics` | Métricas Prometheus |
| `GET` | `/docs` | Documentación Swagger UI |
| `GET` | `/redoc` | Documentación ReDoc |

### POST /analyze

**Request Body:**
```json
{
  "url": "https://...",
  "fps": 1.0,
  "language": "es",
  "vision_provider": "openai",
  "max_duration": 600
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `url` | `string` | ✅ | URL del contenido multimedia |
| `fps` | `float` | ❌ | Frames por segundo (0.1-30) |
| `language` | `string` | ❌ | Código de idioma |
| `vision_provider` | `string` | ❌ | Proveedor de visión AI |
| `max_duration` | `int` | ❌ | Duración máxima en segundos |

---

## 🧩 Sistema de Plugins

El sistema está diseñado para ser extensible mediante plugins. Cada extractor se registra automáticamente:

```python
from src.ports.plugin import register_plugin
from src.infrastructure.plugins.base_extractor import BaseExtractor

@register_plugin
class TikTokExtractor(BaseExtractor):
    platform = "tiktok"
    priority = 20

    def can_handle(self, url):
        return "tiktok.com" in url.domain

    async def extract(self, url, output_dir):
        # Lógica de extracción específica de TikTok
        ...
```

### Plugins incluidos

| Plugin | Prioridad | Plataforma |
|--------|-----------|------------|
| `YouTubeExtractor` | 10 | YouTube |
| `GenericWebExtractor` | 100 | Cualquier web |

### Crear un nuevo extractor

1. Crear archivo en `src/infrastructure/plugins/`
2. Heredar de `BaseExtractor`
3. Decorar con `@register_plugin`
4. Implementar `can_handle()` y `extract()`

---

## ⚙️ Configuración

Toda la configuración se realiza mediante variables de entorno (archivo `.env`):

```bash
# Servidor
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Análisis
DEFAULT_FPS=1.0
DEFAULT_LANGUAGE=es
MAX_FRAMES=500

# API Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...

# Whisper
WHISPER_MODEL=base
WHISPER_DEVICE=cpu

# OCR
OCR_DEVICE=cpu
OCR_LANG=es,en
```

Ver `.env.example` para todas las opciones.

---

## 🐳 Docker

```bash
# Construir imagen
docker build -t media-intelligence-engine .

# Ejecutar con Docker Compose
docker compose up -d

# Ver logs
docker compose logs -f api

# Detener
docker compose down
```

### Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| API | 8000 | Microservicio principal |
| Redis | 6379 | Cache y broker (futuro) |

### Volúmenes

| Montaje | Propósito |
|---------|-----------|
| `./data/downloads` | Archivos descargados |
| `./data/recordings` | Grabaciones de pantalla |
| `./data/output` | Resultados de análisis |
| `./data/temp` | Archivos temporales |

---

## 📊 Observabilidad

### Logging Estructurado

```json
{"event": "Media downloaded", "strategy": "yt-dlp", "path": "/data/downloads/video.mp4", "timestamp": "2024-01-01T00:00:00Z"}
```

### Correlation ID

Cada request recibe un `X-Correlation-ID` para trazabilidad extremo a extremo.

### Health Check

`GET /health` — Verifica que el servicio está operativo.

### Métricas

`GET /metrics` — Endpoint preparado para Prometheus (implementación futura).

### Tracing

Preparado para OpenTelemetry (configuración en `.env`).

---

## 🧪 Tests

```bash
# Tests unitarios
make test

# Tests con cobertura
make test-cov

# Lint
make lint

# Type checking
make typecheck
```

---

## 🔮 Futuro

La arquitectura está preparada para incorporar:

- [ ] **RabbitMQ / Kafka** — Streaming de eventos
- [ ] **Celery Workers** — Procesamiento asíncrono
- [ ] **MinIO** — Almacenamiento S3
- [ ] **PostgreSQL** — Persistencia de resultados
- [ ] **ElasticSearch** — Búsqueda full-text
- [ ] **Qdrant** — Búsqueda vectorial
- [ ] **n8n** — Workflows visuales
- [ ] **MCP Server** — Model Context Protocol
- [ ] **Webhooks** — Notificaciones de análisis completado
- [ ] **Auth** — API Keys y autenticación
- [ ] **Rate Limiting** — Control de uso
- [ ] **Dashboard** — UI web para monitoreo

---

## 📄 Licencia

MIT License — Ver [LICENSE](LICENSE) para más detalles.

---

<p align="center">
  Built with ❤️ for the open source community
</p>