"""Verificação do tema «Regra 3-30-300» em file:// com Edge (Playwright).
Uso: python mapa_unico/tests/pw_regra.py [pasta para capturas de ecrã]"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
URL = (RAIZ / "mapa_unico" / "mapa_unico.html").as_uri()
CAPT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
falhas = []


def ok(nome, cond, extra=""):
    print(("OK   " if cond else "FALHA"), nome, extra)
    if not cond:
        falhas.append(nome)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    for largura, altura in ((1280, 800), (360, 740), (320, 640)):
        pg = b.new_page(viewport={"width": largura, "height": altura})
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: erros.append(m.text) if m.type == "error" and "tile" not in m.text.lower() and "ERR_" not in m.text else None)
        pg.goto(URL + "#tema=regra")
        pg.wait_for_selector("#tema-regra .cam", timeout=60000)
        pg.wait_for_timeout(1500)
        tag = f"[{largura}px] "
        if largura == 1280:
            ordem = pg.eval_on_selector_all("#tabs .tab", "t => t.map(x => x.dataset.t)")
            ok(tag + "separador «regra» em 2.º", ordem[:2] == ["acessibilidade", "regra"], str(ordem))
            rot = pg.eval_on_selector_all("#tema-regra .camadas .cam label", "e => e.map(x => x.textContent)")
            ok(tag + "5 camadas + parques", len(rot) == 6, str(len(rot)))
            ok(tag + "2 camadas ligadas à partida", pg.evaluate("MU.TEMAS.regra._camadas.filter(l => l.linha.cb.checked).length") == 2)
            ok(tag + "2 imagens no mapa", pg.evaluate("document.querySelectorAll('#map .leaflet-pane[class*=mu-regra] img').length") == 2,
               str(pg.evaluate("document.querySelectorAll('#map .leaflet-pane[class*=mu-regra] img').length")))
            txt = pg.text_content("#nums-card")
            ok(tag + "números-chave no cartão do mapa", "2,3" in txt and "4,3" in txt and "10,7" in txt)
            ok(tag + "painel sem bloco de números", pg.locator("#tema-regra .nums").count() == 0)
            ok(tag + "cartão aberto à partida no ecrã grande", pg.is_visible("#nums-card") and not pg.is_visible("#nums-chip"))
            pg.click("#nums-x")
            ok(tag + "X fecha o cartão e aparece «Números»", not pg.is_visible("#nums-card") and pg.is_visible("#nums-chip"))
            pg.click("#nums-chip")
            ok(tag + "«Números» reabre o cartão", pg.is_visible("#nums-card") and not pg.is_visible("#nums-chip"))
            pg.click("#tema-regra summary")
            ok(tag + "limitações dizem o limiar sensível", "19,4" in pg.inner_text("#tema-regra") and "24,8" in pg.inner_text("#tema-regra"))
            ok(tag + "ODbL na fonte", "ODbL" in pg.inner_text("#fonte"))
            if CAPT:
                pg.screenshot(path=str(CAPT / "regra_1280.png"))
            # trocar de tema e voltar não deixa camadas penduradas
            pg.evaluate("location.hash = 'tema=hoje'")
            pg.wait_for_timeout(1500)
            ok(tag + "ao sair, sem camadas da regra no mapa", pg.evaluate("document.querySelectorAll('#map .leaflet-pane[class*=mu-regra] img').length") == 0)
        # separadores inteiros dentro do painel, sem corte nem scroll horizontal
        caixas = pg.eval_on_selector_all("#tabs .tab", "t => t.map(x => { const r = x.getBoundingClientRect(); return [r.left, r.right, x.scrollWidth, x.clientWidth]; })")
        vw = pg.evaluate("window.innerWidth")
        ok(tag + "5 separadores dentro da largura", len(caixas) == 5 and all(c[0] >= -0.5 and c[1] <= vw + 0.5 for c in caixas), str([(round(c[0]), round(c[1])) for c in caixas]))
        ok(tag + "rótulos sem corte", all(c[2] <= c[3] + 1 for c in caixas), str([(c[2], c[3]) for c in caixas]))
        ok(tag + "sem scroll horizontal da página", not pg.evaluate("document.documentElement.scrollWidth > window.innerWidth"))
        ok(tag + "sem erros de JavaScript", not erros, str(erros[:3]))
        if largura < 600:
            ok(tag + "abre com os números fechados", not pg.is_visible("#nums-card") and pg.is_visible("#nums-chip"))
        if CAPT and largura < 600:
            pg.click("#nums-chip")
            pg.wait_for_timeout(300)
            pg.screenshot(path=str(CAPT / f"regra_{largura}_nums.png"))
            pg.click("#nums-x")
            pg.click("#alca")
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(CAPT / f"regra_{largura}.png"))
        pg.close()
    b.close()

print("\nFALHAS:", falhas if falhas else "nenhuma")
sys.exit(1 if falhas else 0)
