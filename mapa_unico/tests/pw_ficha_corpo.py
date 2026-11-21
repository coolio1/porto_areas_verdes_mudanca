"""MU.ficha aceita `corpo` (HTML já escapado); sem `corpo` a ficha fica igual. file:// com Edge (Playwright).
Uso: python mapa_unico/tests/pw_ficha_corpo.py"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
URL = (RAIZ / "mapa_unico" / "mapa_unico.html").as_uri()
falhas = []


def ok(nome, cond, extra=""):
    print(("OK   " if cond else "FALHA"), nome, extra)
    if not cond:
        falhas.append(nome)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1280, "height": 800})
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(URL + "#tema=acessibilidade")
    pg.wait_for_function("window.MU && MU.map && MU.tema", timeout=60000)

    pg.evaluate("MU.ficha({titulo:'T',sub:'s',linhas:[['a','b']]})")
    sem = pg.inner_html("#ficha")
    ok("sem corpo: sem bloco .corpo", pg.locator("#ficha .corpo").count() == 0)
    ok("sem corpo: título e linhas como antes", "<h3>T</h3>" in sem and "<dt>a</dt><dd>b</dd>" in sem)

    pg.evaluate("MU.ficha({titulo:'T',sub:'s',linhas:[['a','b']],corpo:'<p id=\"c\">x</p>'})")
    ok("com corpo: conteúdo presente", pg.locator("#ficha .corpo #c").count() == 1)
    ok("com corpo: o resto da ficha igual (corpo acrescentado no fim)", pg.inner_html("#ficha").startswith(sem))
    pg.click("#ficha .x")
    ok("× fecha a ficha com corpo", not pg.evaluate("document.getElementById('ficha').classList.contains('on')"))
    ok("sem erros de página", not erros, str(erros))
    b.close()

print("\nFALHAS:", falhas if falhas else "nenhuma")
sys.exit(1 if falhas else 0)
