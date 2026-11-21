"""Tema «Casos» em file:// com Edge (Playwright), com dados de teste (nunca os reais).
Copia o HTML e `contexto.js` para uma pasta temporária e escreve aí `dados/casos.js` de teste.
Uso: python mapa_unico/tests/pw_casos.py [pasta para capturas de ecrã]"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
CAPT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
falhas = []


def ok(nome, cond, extra=""):
    print(("OK   " if cond else "FALHA"), nome, extra)
    if not cond:
        falhas.append(nome)


def caso(slug, tipo, lat, lon, titulo, fotos=(), galeria="horrores", aprox=False):
    return {
        "slug": slug, "titulo": titulo, "galeria": galeria, "tipo": tipo, "lat": lat, "lon": lon,
        "aproximada": aprox, "ano": "2019", "estado": "abatido", "contestacao": "Petição de moradores.",
        "criterio": "documental", "nota_editorial": "", "freguesia": "Cedofeita",
        "corpo_html": "<p>Descrição do caso.</p>",
        "fotos": [{"papel": p, "src": f"../Horrores/media/{slug}/{p}.jpg", "ano": "2015", "fonte": "Arquivo", "url": "https://x.pt/f"}
                  for p in fotos],
        "referencias": [{"titulo": "Notícia", "url": "https://x.pt/n", "data": "2019-03-01"}],
        "url": f"../casos/{slug}/",
    }


def montar(casos):
    tmp = Path(tempfile.mkdtemp(prefix="pw_casos_"))
    (tmp / "mapa_unico" / "dados").mkdir(parents=True)
    (tmp / "assets" / "js").mkdir(parents=True)
    (tmp / "casos").mkdir()
    shutil.copy(RAIZ / "casos" / "index.html", tmp / "casos")
    shutil.copy(RAIZ / "mapa_unico" / "dados" / "contexto.js", tmp / "mapa_unico" / "dados")
    shutil.copy(RAIZ / "assets" / "js" / "moldura.js", tmp / "assets" / "js")
    tipos = ["arvores", "demolicao", "patrimonio_alterado", "lojas_historicas"]
    d = {"casos": casos, "numeros": {
        "total": len(casos), "por_tipo": {t: sum(c["tipo"] == t for c in casos) for t in tipos},
        "por_galeria": {g: sum(c["galeria"] == g for c in casos) for g in ("horrores", "sucessos")}}}
    (tmp / "mapa_unico" / "dados" / "casos.js").write_text(
        "MU.DADOS['casos'] = " + json.dumps(d, ensure_ascii=False) + ";\n", encoding="utf-8")
    for c in casos:
        for f in c["fotos"]:
            p = tmp / "Horrores" / "media" / c["slug"] / Path(f["src"]).name
            p.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (300, 200), (90, 120, 90)).save(p)
    return (tmp / "casos" / "index.html").as_uri(), tmp


CASOS = [
    caso("a-rua", "arvores", 41.1480, -8.6250, "Árvores da Rua A", fotos=("antes", "depois")),
    caso("b-casa", "demolicao", 41.1560, -8.6100, "Casa B"),
    caso("c-html", "patrimonio_alterado", 41.1540, -8.6400, "&lt;b&gt;x&lt;/b&gt; &amp; Cª", fotos=("antes",)),
    caso("d-suc", "arvores", 41.1600, -8.5900, "Sucesso D", galeria="sucessos"),
]


def abrir(b, url, hash_="#tema=casos", **kw):
    pg = b.new_page(viewport={"width": 1280, "height": 800}, **kw)
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" and "tile" not in m.text.lower()
          and "ERR_" not in m.text and "404" not in m.text else None)
    pg.goto(url + hash_)
    pg.wait_for_selector("#tema-casos .casos-filtros, #tema-casos .casos-vazio", timeout=30000)
    pg.wait_for_timeout(500)
    return pg, erros


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    url, tmp = montar(CASOS)
    pg, erros = abrir(b, url)
    ok("separador «casos» existe", pg.locator("#tabs .tab[data-t=casos]").count() == 1)
    ok("um marcador por caso", pg.locator(".caso-mk").count() == 4, str(pg.locator(".caso-mk").count()))
    ok("cartão «Números» com o total", "4" in (pg.text_content("#nums-card") or ""))

    # hover = cartão com o título
    pg.hover(".caso-mk[data-slug=a-rua]")
    pg.wait_for_selector(".leaflet-tooltip.caso-hover", timeout=3000)
    ok("hover mostra cartão com o título", "Árvores da Rua A" in pg.text_content(".leaflet-tooltip.caso-hover"))
    ok("cartão de hover com foto quando há", pg.locator(".leaflet-tooltip.caso-hover img").count() == 1)
    ok("cartão de hover com ligação à página", pg.get_attribute(".leaflet-tooltip.caso-hover a.ver-caso", "href") == "../casos/a-rua/")
    bx = pg.locator(".leaflet-tooltip.caso-hover").bounding_box()
    pg.mouse.move(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)
    pg.wait_for_timeout(800)
    ok("cartão fica aberto com o rato em cima dele", pg.locator(".leaflet-tooltip.caso-hover").count() == 1)
    pg.mouse.move(5, 5)
    pg.wait_for_timeout(900)
    ok("cartão fecha depois de o rato sair de ambos", pg.locator(".leaflet-tooltip.caso-hover").count() == 0)

    # clique = ficha fixa; × fecha
    pg.click(".caso-mk[data-slug=a-rua]")
    pg.wait_for_selector("#ficha.on .fcorpo", timeout=3000)
    ok("clique abre a ficha com antes e depois", pg.locator("#ficha .fcorpo img").count() == 2)
    ok("ficha por cima do cartão «Números» (nada tapado)", pg.evaluate("(() => { const f = document.getElementById('ficha').getBoundingClientRect(); const e = document.elementFromPoint(f.left + f.width / 2, f.bottom - 8); return !!e && !!e.closest('#ficha'); })()"))
    ok("ficha com ligação à página do caso", pg.get_attribute("#ficha a.ver-caso", "href") == "../casos/a-rua/")
    ok("ligação à página no topo da ficha (antes das fotos)", pg.evaluate("document.querySelector('#ficha a.ver-caso').getBoundingClientRect().bottom <= document.querySelector('#ficha .fcorpo').getBoundingClientRect().top + 1"))
    ok("ficha compacta: resumo e sem lista de referências", pg.locator("#ficha .resumo").count() == 1 and pg.locator("#ficha ol.refs").count() == 0)
    ok("hash ganha o caso", "caso=a-rua" in pg.evaluate("location.hash"))
    pg.mouse.move(5, 5)
    ok("ficha fica aberta depois do rato sair", pg.evaluate("document.getElementById('ficha').classList.contains('on')"))
    pg.click("#ficha .x")
    ok("× fecha a ficha", not pg.evaluate("document.getElementById('ficha').classList.contains('on')"))
    ok("× limpa o caso do hash", "caso=" not in pg.evaluate("location.hash"))

    # caso sem foto: sem <img> (hover e ficha)
    pg.hover(".caso-mk[data-slug=b-casa]")
    pg.wait_for_selector(".leaflet-tooltip.caso-hover:has-text('Casa B')", timeout=3000)
    ok("sem foto: hover sem <img>", pg.locator(".leaflet-tooltip.caso-hover:has-text('Casa B') img").count() == 0)
    pg.click(".caso-mk[data-slug=b-casa]")
    pg.wait_for_selector("#ficha.on .fcorpo", timeout=3000)
    ok("sem foto: ficha sem <img>", pg.locator("#ficha .fcorpo img").count() == 0)

    # título com HTML já escapado aparece como texto
    pg.click(".caso-mk[data-slug=c-html]")
    pg.wait_for_selector("#ficha.on h3", timeout=3000)
    ok("título escapado visível como texto", pg.text_content("#ficha h3") == "<b>x</b> & Cª", repr(pg.text_content("#ficha h3")))
    ok("título sem elemento <b> injectado", pg.locator("#ficha h3 b").count() == 0)

    # filtro por tipo e por galeria
    pg.click("#ficha .x")
    pg.uncheck("#tema-casos input[data-tipo=arvores]")
    ok("filtro por tipo esconde marcadores", pg.locator(".caso-mk").count() == 2, str(pg.locator(".caso-mk").count()))
    pg.check("#tema-casos input[data-tipo=arvores]")
    pg.uncheck("#tema-casos input[data-galeria=sucessos]")
    ok("filtro por galeria esconde sucessos", pg.locator(".caso-mk[data-slug=d-suc]").count() == 0)
    if CAPT:
        pg.screenshot(path=str(CAPT / "casos_1280.png"))
    ok("sem erros de página (1280)", not erros, str(erros))
    pg.close()

    # caso por hash
    pg, erros = abrir(b, url, "#tema=casos&caso=c-html")
    pg.wait_for_selector("#ficha.on h3", timeout=5000)
    ok("hash abre a ficha do caso", pg.text_content("#ficha h3") == "<b>x</b> & Cª")
    pg.close()

    # toque: um toque abre a ficha e não deixa o cartão preso
    ctx = b.new_context(has_touch=True, viewport={"width": 390, "height": 760})
    pgt = ctx.new_page()
    pgt.goto(url + "#tema=casos")
    pgt.wait_for_selector("#tema-casos .casos-filtros", timeout=30000)
    pgt.wait_for_timeout(500)
    pgt.tap(".caso-mk[data-slug=a-rua]")
    pgt.wait_for_selector("#ficha.on .fcorpo", timeout=3000)
    ok("toque abre a ficha", True)
    try:   # o cartão desvanece (≤ 1 s) antes de sair do DOM; preso = continua lá
        pgt.wait_for_function("document.querySelectorAll('.leaflet-tooltip.caso-hover').length === 0", timeout=2000)
        preso = False
    except Exception:
        preso = True
    ok("toque não deixa o cartão de hover aberto", not preso)
    if CAPT:
        pgt.screenshot(path=str(CAPT / "casos_390.png"))
    pgt.close()
    ctx.close()

    # sem casos: mensagem e nada no mapa
    url0, tmp0 = montar([])
    pg, erros = abrir(b, url0)
    ok("sem casos: mensagem", "Ainda sem casos" in (pg.text_content("#tema-casos") or ""))
    ok("sem casos: nenhum marcador", pg.locator(".caso-mk").count() == 0)
    ok("sem casos: sem erros", not erros, str(erros))
    pg.close()
    b.close()

for d in (tmp, tmp0):
    shutil.rmtree(d, ignore_errors=True)
print("\nFALHAS:", falhas if falhas else "nenhuma")
sys.exit(1 if falhas else 0)
