"""Verificação do tema Histórico em file:// com Edge (Playwright). Uso: python mapa_unico/tests/pw_historico.py"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
URL = (RAIZ / "mapa_unico" / "mapa_unico.html").as_uri()
ORDEM = ["2023-24", "2016-17", "2001-05", "1995-00", "1985-90", "1979", "1972-76", "1947"]
falhas = []


def ok(nome, cond, extra=""):
    print(("OK   " if cond else "FALHA"), nome, extra)
    if not cond:
        falhas.append(nome)


def imgs(pg, pane):
    return pg.evaluate(f"MU.map.getPane('{pane}').querySelectorAll('img').length")


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1280, "height": 800})
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" and "tile" not in m.text.lower() and "ERR_" not in m.text else None)
    pg.goto(URL + "#tema=historico")
    pg.wait_for_function("window.MU && MU.historico && MU.historico.estado().epoca", timeout=60000)
    pg.wait_for_timeout(1500)

    ok("a) ordem das épocas", pg.evaluate("MU.historico.epocas") == ORDEM)
    botoes = pg.eval_on_selector_all("#h-tempo button", "b => b.map(x => x.dataset.epoca)")
    ok("a) botões da linha do tempo pela ordem pedida", botoes == ORDEM, str(botoes))
    ok("b) abre em 2023-24", pg.evaluate("MU.historico.estado().epoca") == "2023-24")
    ok("c) sem camadas NDVI (só o interruptor perda/ganho; o método NDVI pode ser citado na fonte)", pg.eval_on_selector_all("#tema-historico input[type=checkbox]", "e => e.length") == 1 and not pg.evaluate("Object.keys(MU.DADOS.historico).some(k => k.startsWith('ndvi_'))"))
    ok("d) um par de overlays de época", imgs(pg, "hMascPane") == 2, str(imgs(pg, "hMascPane")))
    cols = pg.eval_on_selector_all("#h-graf button", "b => b.map(x => x.dataset.epoca)")
    ok("e) minigráfico com 8 colunas na mesma ordem", cols == ORDEM, str(cols))
    pg.click("#h-graf button[data-epoca='1947']")
    pg.wait_for_timeout(500)
    ok("e) clicar na barra selecciona a época", pg.evaluate("MU.historico.estado().epoca") == "1947")
    ok("e) 1947 usa o pane 1947 (2 imagens) e deixa o das máscaras vazio", imgs(pg, "h1947Pane") == 2 and imgs(pg, "hMascPane") == 0)
    fonte = pg.inner_text("#h-fonte")
    ok("f) fonte de 1947 com ressalva", "ortofoto" in fonte.lower() and "não comparável" in fonte.lower(), fonte)
    pg.click("#h-tempo button[data-epoca='2016-17']")
    ok("f) fonte de 2016-17 sem ressalva", "não comparável" not in pg.inner_text("#h-fonte").lower())
    for e in ("1979", "1972-76"):
        pg.click(f"#h-tempo button[data-epoca='{e}']")
        ok(f"f) fonte de {e} com ressalva", "não comparável" in pg.inner_text("#h-fonte").lower())
    # g) vista=1947
    pg2 = b.new_page(viewport={"width": 1280, "height": 800})
    pg2.goto(URL + "#tema=historico&vista=1947")
    pg2.wait_for_function("window.MU && MU.historico && MU.historico.estado().epoca", timeout=60000)
    pg2.wait_for_timeout(1500)
    ok("g) vista=1947 selecciona 1947", pg2.evaluate("MU.historico.estado().epoca") == "1947")
    ok("g) vista=1947 liga a ortofoto", pg2.evaluate("MU.fundoActual") == "orto1947")
    pg2.close()
    # h) perda e ganho
    pg.click("#h-tempo button[data-epoca='2023-24']")
    pg.check("#h-mud input[type=checkbox]")
    pg.wait_for_timeout(300)
    ok("h) perda/ganho liga e esconde o par da época", pg.evaluate("MU.historico.estado().perdaGanho") and imgs(pg, "hMudPane") == 2 and imgs(pg, "hMascPane") == 0)
    pg.click("#h-tempo button[data-epoca='1985-90']")
    ok("h) escolher época desliga perda/ganho", not pg.evaluate("MU.historico.estado().perdaGanho") and imgs(pg, "hMudPane") == 0 and imgs(pg, "hMascPane") == 2)
    ok("h) o interruptor fica desmarcado", not pg.is_checked("#h-mud input[type=checkbox]"))
    # i) opacidade global
    pg.fill("#h-op", "50")
    pg.dispatch_event("#h-op", "input")
    op = pg.evaluate("[...MU.map.getPane('hMascPane').querySelectorAll('img')].map(i => i.style.opacity)")
    ok("i) opacidade global nas máscaras", op == ["0.5", "0.5"], str(op))
    pg.click("#h-tempo button[data-epoca='1947']")
    op = pg.evaluate("[...MU.map.getPane('h1947Pane').querySelectorAll('img')].map(i => i.style.opacity)")
    ok("i) opacidade global também em 1947", op == ["0.5", "0.5"], str(op))
    # 1979 detalhe
    pg.click("#h-tempo button[data-epoca='1979']")
    ok("1979) botão das 5 classes visível", pg.is_visible("#h-79"))
    pg.click("#h-79")
    pg.wait_for_timeout(300)
    ok("1979) detalhe mostra polígonos e esconde as máscaras", imgs(pg, "hMascPane") == 0 and pg.evaluate("MU.map.getPane('hCobPane').querySelectorAll('path').length") > 0)
    pg.click("#h-tempo button[data-epoca='2023-24']")
    ok("1979) o detalhe sai ao mudar de época", pg.evaluate("MU.map.getPane('hCobPane').querySelectorAll('path').length") == 0)
    pg.screenshot(path=sys.argv[1] if len(sys.argv) > 1 else "hist_pc.png")
    ok("j) sem erros na consola", not erros, str(erros[:3]))
    b.close()

print("\nFALHAS:", falhas if falhas else "nenhuma")
sys.exit(1 if falhas else 0)
