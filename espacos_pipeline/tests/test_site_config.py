"""Task 1: configuração Jekyll da secção 50espacos (sem Ruby local: verifica ficheiros, não o build)."""
from pathlib import Path
import re
import yaml

RAIZ = Path(__file__).resolve().parents[2]


def _config():
    return yaml.safe_load((RAIZ / "_config.yml").read_text(encoding="utf-8"))


def test_colecao_espacos_com_permalink():
    c = _config()["collections"]["espacos"]
    assert c["output"] is True
    assert c["permalink"] == "/50espacos/espacos/:path/"


def test_defaults_aplicam_layout_espaco():
    defaults = _config()["defaults"]
    assert any(
        d["scope"].get("type") == "espacos" and d["values"].get("layout") == "espaco"
        for d in defaults
    )


def test_pipeline_excluida_do_jekyll():
    assert "espacos_pipeline" in _config()["exclude"]


def test_layout_espaco_usa_campos_da_spec():
    html = (RAIZ / "_layouts" / "espaco.html").read_text(encoding="utf-8")
    for campo in ("titulo", "concelho", "freguesia", "seleccionado", "selecao",
                  "area_ha", "estado_actual", "data_verificacao", "fontes", "fotos", "anexos"):
        assert f"page.{campo}" in html, campo


def test_layout_espaco_so_mostra_mapa_com_coordenadas():
    html = (RAIZ / "_layouts" / "espaco.html").read_text(encoding="utf-8")
    assert re.search(r"if\s+page\.lat", html)


def test_pagina_da_campanha_existe_para_a_nav():
    assert (RAIZ / "50espacos" / "index.md").exists()


def test_default_suporta_pagina_larga():
    assert "page.wide" in (RAIZ / "_layouts" / "default.html").read_text(encoding="utf-8")


def test_paginas_da_seccao_sao_largas_por_defeito():
    # page.wide (lido por default.html) vem dos defaults, não do front matter dos layouts
    defaults = _config()["defaults"]
    assert any(d["scope"].get("path") == "50espacos" and d["values"].get("wide") is True for d in defaults)
    assert any(d["scope"].get("type") == "espacos" and d["values"].get("wide") is True for d in defaults)
