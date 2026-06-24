"""
Captura thumbnails dos mapas para os cards do index.
Usa Playwright + Chromium headless.
Guarda em assets/images/cards/<nome>.jpg (600x340px).
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Fix Windows cp1252 console encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://coolio1.github.io/porto_areas_verdes_mudanca"
OUT_DIR = Path(__file__).parent / "assets" / "images" / "cards"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAPS = [
    {
        "slug": "conversao",
        "url": f"{BASE_URL}/acessibilidade/conversao_verde.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
    {
        "slug": "acessibilidade",
        "url": f"{BASE_URL}/acessibilidade/acessibilidade_verde.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
    {
        "slug": "mudancas",
        "url": f"{BASE_URL}/mapa.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
    {
        "slug": "historico",
        "url": f"{BASE_URL}/ndvi_historico.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
    {
        "slug": "verde_privado",
        "url": f"{BASE_URL}/interiores_quarteiroes.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
    {
        "slug": "atropelamentos",
        "url": f"{BASE_URL}/atropelamentos/dashboard_atropelamentos.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 4,
    },
]

VIEWPORT = {"width": 1280, "height": 800}
CARD_W, CARD_H = 600, 340


def capture(page, m):
    slug = m["slug"]
    print(f"  → {slug}: {m['url']}")
    page.goto(m["url"], wait_until="networkidle", timeout=30000)

    # Aguardar tiles do Leaflet
    try:
        page.wait_for_selector(m["wait_for"], timeout=15000)
    except Exception:
        print(f"    ! Selector {m['wait_for']} não encontrado — continuando")

    # Pausa extra para tiles carregarem
    time.sleep(m["extra_wait"])

    # Esconder controlos, legendas e nav antes do screenshot
    page.evaluate("""() => {
        const hide = [
            '.leaflet-control-container',
            '.leaflet-control',
            '.legend', '.info',
            '#legend', '#panel', '#controls', '#sidebar',
            '.legend-container', '.map-legend',
            '#nav', '.nav-fixed', 'nav',
            '.leaflet-bottom', '.leaflet-top',
            '.cand-label', '.park-label'
        ];
        hide.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => { el.style.display = 'none'; });
        });
    }""")

    # Screenshot da área do mapa (#map ou .leaflet-container, senão full page)
    map_el = page.query_selector("#map") or page.query_selector(".leaflet-container")
    out = OUT_DIR / f"{slug}.jpg"

    if map_el:
        box = map_el.bounding_box()
        if box and box["width"] > 100 and box["height"] > 100:
            # Clip ao bounding box do mapa, crop para proporção card
            clip = {
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": min(box["height"], box["width"] * CARD_H / CARD_W),
            }
            page.screenshot(path=str(out), clip=clip, type="jpeg", quality=88)
            print(f"    ✓ guardado ({int(clip['width'])}×{int(clip['height'])}px)")
            return

    # Fallback: screenshot da janela inteira cropada ao topo
    clip = {"x": 0, "y": 0, "width": VIEWPORT["width"], "height": int(VIEWPORT["width"] * CARD_H / CARD_W)}
    page.screenshot(path=str(out), clip=clip, type="jpeg", quality=88)
    print(f"    ✓ fallback screenshot guardado")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()

        for m in MAPS:
            try:
                capture(page, m)
            except Exception as e:
                print(f"    ✗ ERRO em {m['slug']}: {e}")

        browser.close()

    print(f"\nFicheiros em {OUT_DIR}:")
    for f in sorted(OUT_DIR.glob("*.jpg")):
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
