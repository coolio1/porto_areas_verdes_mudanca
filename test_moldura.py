"""moldura.js é a única fonte do menu/abas/rodapé: as páginas só a ligam, com um data-pagina válido."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
JS = (RAIZ / "assets/js/moldura.js").read_text(encoding="utf-8")


def _lista(nome):
    bloco = re.search(rf"var {nome} = \[(.*?)\n  \];", JS, re.S).group(1)
    return re.findall(r"\['([^']+)', '([^']+)'\]", bloco)


def test_destinos_do_menu_e_abas_existem():
    for caminho, _ in _lista("PAGINAS") + _lista("ABAS"):
        assert (RAIZ / caminho).exists() or (RAIZ / (caminho.rstrip("/") + ".md")).exists(), caminho


def test_paginas_geradas_ligam_a_moldura():
    paginas = ["mapa_unico/mapa_unico.html", "Mobilidade/autocarros.html",
               "Mobilidade/analise.html", "atropelamentos/dashboard_atropelamentos.html"]
    for p in paginas:
        h = (RAIZ / p).read_text(encoding="utf-8")
        assert f'assets/js/moldura.js" data-pagina="{p}"' in h, p
        assert '<div id="nav"' not in h and '<footer class="pv-rodape' not in h, p      # nada de menu escrito à mão


def test_layout_jekyll_liga_a_moldura():
    h = (RAIZ / "_layouts/default.html").read_text(encoding="utf-8")
    assert "assets/js/moldura.js" in h and "include nav.html" not in h and "include rodape.html" not in h
