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
    assert "'/casos/' | relative_url }}#tema=casos&caso={{ page.slug }}" in h


def test_layout_caso_mostra_referencias_e_creditos():
    h = (RAIZ / "_layouts/caso.html").read_text(encoding="utf-8")
    for peca in ("page.referencias", "page.fotos", "{{ content }}", "page.contestacao"):
        assert peca in h, peca


def test_layout_e_indice_escapam_texto_e_mostram_nota_editorial():
    h = (RAIZ / "_layouts/caso.html").read_text(encoding="utf-8")
    for campo in ("page.titulo", "page.contestacao", "f.fonte", "r.titulo", "page.nota_editorial", "page.estado", "f.ano"):
        assert "{{ " + campo + " | escape }}" in h, campo
    i = (RAIZ / "casos/lista/index.html").read_text(encoding="utf-8")
    assert "{{ c.titulo | escape }}" in i and "{{ c.estado | escape }}" in i and "c.estado != 'alterado'" in i


def test_indice_lista_site_casos_com_filtros():
    h = (RAIZ / "casos/lista/index.html").read_text(encoding="utf-8")
    assert "site.casos" in h and "casos conhecidos e documentados" in h.lower()
    assert 'data-galeria' in h and 'data-tipo' in h and 'data-grupo' in h


def test_menu_tem_casos_e_fontes():
    js = (RAIZ / "assets/js/moldura.js").read_text(encoding="utf-8")
    assert "['casos/', 'Horrores e sucessos']" in js
    assert "'casos/':" in js                                          # fontes da página /casos/
    assert (RAIZ / "docs/horrores.md").exists()
    assert "docs/horrores.md" in (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")


def test_indice_nao_lista_rascunhos():
    gi = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert "docs/horrores/rascunhos/" in gi
    assert "docs" in CONFIG["exclude"]


def test_paginas_de_caso_tem_fontes_proprias():
    d = [x for x in CONFIG["defaults"] if x["scope"].get("type") == "casos"][0]
    assert d["values"].get("fontes")


def test_layout_nao_mostra_estado_outro():
    h = (RAIZ / "_layouts/caso.html").read_text(encoding="utf-8")
    assert "page.estado != 'outro' and page.estado != 'alterado'" in h


def test_layout_mostra_fotos_ligadas_sem_as_copiar():
    h = (RAIZ / "_layouts/caso.html").read_text(encoding="utf-8")
    assert "page.fotos_ligadas" in h and "noopener" in h


def test_front_matter_da_lista_e_yaml_valido_com_layout():
    t = (RAIZ / "casos/lista/index.html").read_text(encoding="utf-8")
    fm = yaml.safe_load(t.split("---", 2)[1])     # YAML inválido (ex.: «: » sem aspas) faz o Jekyll servir a página sem layout
    assert fm["layout"] == "default" and fm["permalink"] == "/casos/lista/" and fm["wide"] is True


def test_mapa_dos_casos_e_pagina_propria_com_positron():
    h = (RAIZ / "casos/index.html").read_text(encoding="utf-8")
    assert "MU.URL_DADOS = '../mapa_unico/dados/'" in h and "MU.LIGACOES" in h
    assert "fundo: 'positron'" in h                                      # fundo por defeito deste mapa
    assert "id: 'casos'" not in (RAIZ / "mapa_unico/mapa_unico.html").read_text(encoding="utf-8")


def test_paginas_folha_usam_o_template_comum():
    for f in ("artigos/index.html", "casos/lista/index.html", "50espacos/index.md"):
        t = (RAIZ / f).read_text(encoding="utf-8")
        assert "folha: true" in t and "folha-abre.html" in t and "folha-fecha.html" in t, f
    assert "italic" in (RAIZ / "assets/css/folha.css").read_text(encoding="utf-8")


def test_layout_campanha_usa_o_template_comum():
    h = (RAIZ / "_layouts/campanha.html").read_text(encoding="utf-8")
    assert "folha-abre.html" in h and "folha-fecha.html" in h
    for f in ("campanha", "imprensa", "estudos"):
        t = (RAIZ / f"50espacos/{f}.md").read_text(encoding="utf-8")
        assert "folha: true" in t and "folha_em:" in t and "folha_texto:" in t, f
