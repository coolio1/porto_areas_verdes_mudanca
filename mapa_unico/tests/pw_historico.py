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
    pg.click("#h-tempo button[data-epoca='1947']")
    pg.check("#h-mud input[type=checkbox]")
    f = pg.inner_text("#h-fonte")
    ok("h) com perda/ganho a fonte descreve a diferença Landsat, não a época escolhida", "Perda e ganho" in f and "1947" not in f and "Landsat" in f and pg.inner_text("#h-nums").strip() == "", f)
    pg.click("#h-tempo button[data-epoca='1985-90']")
    ok("fonte) 2023-24 cita Landsat 8/9 e não atribui Roy et al. ao Landsat 5", "8/9" in (pg.click("#h-tempo button[data-epoca='2023-24']") or pg.inner_text("#h-fonte")) and "Roy" not in (pg.click("#h-tempo button[data-epoca='2001-05']") or pg.inner_text("#h-fonte")))
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
    # ---- cortina de comparação ----
    import io
    from PIL import Image

    def cores(img_bytes, caixa):
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB").crop(caixa)
        px = im.getdata()
        bege = sum(1 for c in px if abs(c[0] - 196) < 4 and abs(c[1] - 168) < 4 and abs(c[2] - 130) < 4)
        return bege

    pg.fill("#h-op", "100")
    pg.dispatch_event("#h-op", "input")
    pg.evaluate("MU.historico.comparar(true)")
    pg.wait_for_timeout(600)
    est = pg.evaluate("MU.historico.estado()")
    ok("cortina a) comparar liga com 2023-24 contra 1947", est["comparar"] and pg.input_value("#h-esq") == "2023-24" and pg.input_value("#h-dir") == "1947", str(est))
    pg.evaluate("MU.historico.cortina(0.62)")
    pg.wait_for_timeout(400)
    mapa = pg.evaluate("(() => { const r = document.getElementById('map').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
    x = mapa[0] + 0.62 * mapa[2]
    cy = int(mapa[1] + mapa[3] / 2)
    img = pg.screenshot()
    esq = cores(img, (int(x) - 220, cy - 120, int(x) - 10, cy + 120))
    dire = cores(img, (int(x) + 10, cy - 120, int(x) + 220, cy + 120))
    ok("cortina b) esquerda mostra 2023-24 (bege) e direita não", esq > 1000 and dire < 50, f"esq={esq} dir={dire}")
    pg.select_option("#h-esq", "1947")
    pg.select_option("#h-dir", "2023-24")
    pg.wait_for_timeout(600)
    img = pg.screenshot()
    esq = cores(img, (int(x) - 220, cy - 120, int(x) - 10, cy + 120))
    dire = cores(img, (int(x) + 10, cy - 120, int(x) + 220, cy + 120))
    ok("cortina b) trocar as épocas troca os lados", dire > 1000 and esq < 50, f"esq={esq} dir={dire}")
    for a, c in (("1979", "2023-24"), ("1947", "1972-76"), ("1972-76", "1979")):
        pg.select_option("#h-esq", a)
        pg.select_option("#h-dir", c)
        pg.wait_for_timeout(300)
        ok(f"cortina c) {a} contra {c} sem erro", not erros, str(erros[:2]))
    ok("cortina d) perda/ganho inactivo na cortina", pg.is_disabled("#h-mud input[type=checkbox]"))
    # e) arrastar com o rato
    bx = pg.evaluate("(() => { const r = document.querySelector('#h-cortina .h-asa').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
    pg.mouse.move(bx[0], bx[1]); pg.mouse.down(); pg.mouse.move(bx[0] + 120, bx[1], steps=6); pg.mouse.up()
    nx = pg.evaluate("document.querySelector('#h-cortina .h-asa').getBoundingClientRect().left + 0")
    ok("cortina e) arrastar com o rato move o separador", abs(nx - bx[0] - 120) < 25, f"antes={bx[0]:.0f} depois={nx:.0f}")
    pg.evaluate("MU.historico.comparar(false)")
    est = pg.evaluate("MU.historico.estado()")
    ok("cortina d) sair repõe a época da esquerda", (not est["comparar"]) and est["epoca"] == "1972-76", str(est))
    ok("cortina d) sem separador depois de sair", not pg.is_visible("#h-cortina"))
    # e) toque a 375 px
    ctx = b.new_context(viewport={"width": 375, "height": 700}, has_touch=True, is_mobile=True)
    pt = ctx.new_page()
    pt.goto(URL + "#tema=historico")
    pt.wait_for_function("window.MU && MU.historico && MU.historico.estado().epoca", timeout=60000)
    pt.evaluate("MU.historico.comparar(true)")
    pt.wait_for_timeout(500)
    r0 = pt.evaluate("(() => { const r = document.querySelector('#h-cortina .h-asa').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
    cdp = ctx.new_cdp_session(pt)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": r0[0], "y": r0[1]}]})
    for dx in (20, 50, 80):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": r0[0] + dx, "y": r0[1]}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    pt.wait_for_timeout(300)
    r1 = pt.evaluate("document.querySelector('#h-cortina .h-asa').getBoundingClientRect().left")
    ok("cortina e) arrastar com o dedo (375 px)", abs(r1 - r0[0] - 80) < 25 or r1 > r0[0] + 40, f"antes={r0[0]:.0f} depois={r1:.0f}")
    pt.screenshot(path=(sys.argv[1].replace(".png", "_mv.png") if len(sys.argv) > 1 else "hist_mv.png"))
    ctx.close()
    pg.screenshot(path=sys.argv[1] if len(sys.argv) > 1 else "hist_pc.png")
    ok("j) sem erros na consola", not erros, str(erros[:3]))
    b.close()

print("\nFALHAS:", falhas if falhas else "nenhuma")
sys.exit(1 if falhas else 0)
