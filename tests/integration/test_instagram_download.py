"""
Test de descarga de Instagram Reels usando InstagramExtractor/GalleryDLDownloader.

Uso:
    cd media-intelligence-engine
    python tests/integration/test_instagram_download.py
"""

import asyncio
import sys
from pathlib import Path

# Asegurar que podemos importar desde src
sys.path.insert(0, str(Path(__file__).parent.parent))  # tests/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # raíz del proyecto

from src.domain.value_objects.url import URL
from src.infrastructure.plugins.instagram_extractor import InstagramExtractor


async def main():
    reels = [
        ("IG #1", "https://www.instagram.com/reel/DYpsvyDu2by/?igsh=MXF3a2JuM2JxdnZrcg=="),
        ("IG #2", "https://www.instagram.com/reel/DEXjF7Jg3ZD/?igsh=bHJsOWpzMXprcmNk"),
    ]

    extractor = InstagramExtractor()
    output_dir = Path("data/downloads")

    for name, url_str in reels:
        print(f"\n{'='*60}")
        print(f"Descargando {name}: {url_str}")
        print(f"{'='*60}")

        url = URL.from_string(url_str)

        # Verificar que el extractor puede manejar esta URL
        if extractor.can_handle(url):
            print(f"✓ {name}: URL reconocida como Instagram")
        else:
            print(f"✗ {name}: URL NO reconocida como Instagram")
            continue

        try:
            result = await extractor.extract(url, output_dir)
            print(f"\nResultado para {name}:")
            for key, value in result.items():
                print(f"  {key}: {value}")

            if result.get("success"):
                print(f"\n✓ {name}: DESCARGA EXITOSA")
                if result.get("file_path"):
                    path = Path(result["file_path"])
                    if path.exists():
                        print(f"  Archivo existe en: {path}")
                        print(f"  Tamaño: {path.stat().st_size / 1024 / 1024:.2f} MB")
            else:
                print(f"\n✗ {name}: DESCARGA FALLÓ")
                if result.get("error"):
                    print(f"  Error: {result['error']}")

        except Exception as e:
            print(f"\n✗ {name}: EXCEPCIÓN: {e!s}")


if __name__ == "__main__":
    asyncio.run(main())