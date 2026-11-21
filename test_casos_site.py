"""Site dos casos: colecção Jekyll `casos`, layout da página do caso e índice /casos/."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((RAIZ / "_config.yml").read_text(encoding="utf-8"))


def test_config_tem_colecao_casos():
    c = CONFIG["collections"]["casos"]
    assert c["output"] is True and c["permalink"] == "/casos/:path/"
    d = [x for x in CONFIG["defaults"] if x["scope"].get("type") == "casos"]
    assert d and d[0]["values"]["layout"] == "caso"


def test_casos_nao_escondido_pelo_exclude():
    for e in CONFIG["exclude"]:
        assert e.rstrip("/*") not in ("casos", "_casos", "Horrores"), e


def test_layout_caso_liga_a_moldura():
    h = (RAIZ / "_layouts/caso.html").read_text(encoding="utf-8")
    assert h.startswith("---\nlayout: default\n---")
    assert "assets/css/casos.css" in h
    assert "page.fontes" not in h                                    # o rodapé do default já usa page.fontes
    assert "mapa_unico/mapa_unico.html' | relative_url }}#tema=casos&caso={{ page.slug }}" in h


def test_layout_caso_mostra_referencias_e_creditos():
    h = (RAIZ / "_layouts/caso.html").read_text(encoding="utf-8")
    for peca in ("page.referencias", "page.fotos", "{{ content }}", "page.contestacao"):
        assert peca in h, peca


def test_indice_lista_site_casos_com_filtros():
    h = (RAIZ / "casos/index.html").read_text(encoding="utf-8")
    assert "site.casos" in h and "casos conhecidos e documentados" in h.lower()
    assert 'data-galeria' in h and 'data-tipo' in h


def test_indice_nao_lista_rascunhos():
    gi = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert "docs/horrores/rascunhos/" in gi
    assert "docs" in CONFIG["exclude"]
