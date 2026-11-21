"""Tema «Casos» com os casos REAIS de `_casos/` em file:// (Edge): marcadores, fotos da ficha, ficha não tapada.
Uso: python mapa_unico/tests/pw_casos_reais.py   (depois de `python mapa_unico/mapa_unico.py --casos`)"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from casos_pipeline.modelo import listar_casos  # noqa: E402

URL = (RAIZ / "mapa_unico" / "mapa_unico.html").as_uri()
casos = listar_casos()
falhas = []


def ok(nome, cond, extra=""):
    print(("OK   " if cond else "FALHA"), nome, extra)
    if not cond:
        falhas.append(nome)


if not casos:
    print("sem casos em _casos/: nada a verificar")
    sys.exit(0)
com_fotos = next((c for c in casos if c.get("fotos")), casos[0])
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    for w in (1280, 390):
        pg = b.new_page(viewport={"width": w, "height": 800})
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: erros.append(m.text) if m.type == "error" and "tile" not in m.text.lower() and "ERR_" not in m.text else None)
        pg.goto(URL + f"#tema=casos&caso={com_fotos['slug']}")
        pg.wait_for_selector(".caso-mk", timeout=30000)
        pg.wait_for_selector("#ficha.on .fcorpo", timeout=10000)
        pg.wait_for_timeout(1500)
        t = f"[{w}px] "
        ok(t + "um marcador por caso", pg.locator(".caso-mk").count() == len(casos), str(pg.locator(".caso-mk").count()))
        imgs = pg.evaluate("[...document.querySelectorAll('#ficha .fcorpo img')].map(i => i.naturalWidth)")
        ok(t + "fotos da ficha carregam", len(imgs) == min(2, len(com_fotos.get("fotos") or [])) and all(n > 0 for n in imgs), str(imgs))
        if w == 1280:
            ok(t + "ficha não fica tapada pelo cartão «Números»", pg.evaluate(
                "(() => { const f = document.getElementById('ficha').getBoundingClientRect(); const e = document.elementFromPoint(f.left + f.width / 2, f.bottom - 80); return !!e && !!e.closest('#ficha'); })()"))
        ok(t + "sem erros de JavaScript", not erros, str(erros[:3]))
        pg.close()
    b.close()
print("\nFALHAS:", falhas if falhas else "nenhuma")
sys.exit(1 if falhas else 0)
