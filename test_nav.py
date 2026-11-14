"""Os includes Jekyll gerados têm de coincidir com nav.py (fonte única)."""
from pathlib import Path

import nav

RAIZ = Path(__file__).resolve().parent


def _ler(p):
    return (RAIZ / p).read_text(encoding="utf-8").strip()


def test_include_nav_coincide():
    assert _ler("_includes/nav.html") == nav.get_jekyll_nav().strip()


def test_include_rodape_coincide():
    assert _ler("_includes/rodape.html") == nav.get_rodape_jekyll().strip()


def test_rodape_mapa_tem_fontes_por_pagina():
    assert "corredores BUS" in nav.get_rodape("Mobilidade/analise.html", 1)
    assert nav.FONTES_PADRAO in nav.get_rodape("mapa_unico/mapa_unico.html", 1, "mapa")
