"""dados_casos(): lê `_casos/`, valida e prepara `dados/casos.js` do tema Casos."""
import math
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "mapa_unico"))
sys.path.insert(0, str(RAIZ))

import mapa_unico  # noqa: E402

FONTE = "Os moradores contestaram o abate das árvores da rua."


def _caso(raiz, fontes, slug, tipo="arvores", lat=41.1480, lon=-8.6250, corpo="Descrição.", fotos="", titulo=None):
    (raiz / "_casos").mkdir(exist_ok=True)
    (raiz / "_casos" / f"{slug}.md").write_text(
        f"---\ntitulo: {titulo or slug}\ngaleria: horrores\ntipo: {tipo}\nlat: {lat}\nlon: {lon}\n"
        f"aproximada: false\norigem_coord: OSM\nano: 2019\nestado: abatido\ncontestacao: Petição.\n"
        f"criterio: documental\n{fotos}"
        f"referencias:\n  - {{titulo: Notícia, url: 'https://exemplo.pt/n', data: 2019-03-01, "
        f"excerto: contestaram o abate}}\n---\n{corpo}\n", encoding="utf-8")
    (fontes / slug).mkdir(parents=True, exist_ok=True)
    (fontes / slug / "1.txt").write_text(FONTE, encoding="utf-8")


@pytest.fixture
def ambiente(tmp_path):
    fontes = tmp_path / "fontes"
    fontes.mkdir()
    return tmp_path, fontes


def _dados(raiz, fontes):
    return mapa_unico.dados_casos(raiz, fontes, None)


def _metros(a, b):
    dy = (a["lat"] - b["lat"]) * 111320
    dx = (a["lon"] - b["lon"]) * 111320 * math.cos(math.radians(a["lat"]))
    return math.hypot(dx, dy)


def test_dados_casos_contagens(ambiente):
    raiz, fontes = ambiente
    _caso(raiz, fontes, "a", tipo="arvores", lat=41.1480)
    _caso(raiz, fontes, "b", tipo="arvores", lat=41.1500)
    _caso(raiz, fontes, "c", tipo="demolicao", lat=41.1520)
    n = _dados(raiz, fontes)["numeros"]
    assert n["total"] == 3 and n["por_tipo"]["arvores"] == 2 and n["por_tipo"]["demolicao"] == 1
    assert n["por_galeria"] == {"horrores": 3, "sucessos": 0}


def test_so_casos_revistos(ambiente):
    raiz, fontes = ambiente
    _caso(raiz, fontes, "a")
    rasc = raiz / "docs" / "horrores" / "rascunhos"
    rasc.mkdir(parents=True)
    (rasc / "b.md").write_text("---\ntitulo: B\n---\nx\n", encoding="utf-8")
    assert [c["slug"] for c in _dados(raiz, fontes)["casos"]] == ["a"]


def test_coordenadas_repetidas_ficam_distintas(ambiente):
    raiz, fontes = ambiente
    _caso(raiz, fontes, "a")
    _caso(raiz, fontes, "b")
    a, b = _dados(raiz, fontes)["casos"]
    assert 0 < _metros(a, b) <= 8
    assert _metros(a, {"lat": 41.1480, "lon": -8.6250}) <= 5 and _metros(b, {"lat": 41.1480, "lon": -8.6250}) <= 5


def test_caso_invalido_aborta(ambiente):
    raiz, fontes = ambiente
    _caso(raiz, fontes, "mau", tipo="invalido")
    with pytest.raises(ValueError, match="mau"):
        _dados(raiz, fontes)


def test_foto_src_relativo_e_freguesia_derivada(ambiente):
    raiz, fontes = ambiente
    _caso(raiz, fontes, "a", fotos="fotos:\n  - {papel: antes, ficheiro: 01.jpg, ano: 2015, fonte: Arquivo, url: 'https://x.pt/f', sha256: abc}\n")
    c = _dados(raiz, fontes)["casos"][0]
    assert c["fotos"][0]["src"] == "../Horrores/media/a/01.jpg"
    assert c["freguesia"] and c["url"] == "../casos/a/"


def test_escapa_html_no_corpo_e_no_titulo(ambiente):
    raiz, fontes = ambiente
    _caso(raiz, fontes, "a", corpo="Linha <script>x</script> & mais.\n\nSegundo parágrafo.", titulo="'<b>x</b>'")
    c = _dados(raiz, fontes)["casos"][0]
    assert "<script>" not in c["corpo_html"] and "&lt;script&gt;" in c["corpo_html"]
    assert c["corpo_html"].count("<p>") == 2
    assert "<b>" not in c["titulo"] and "&lt;b&gt;" in c["titulo"]


def test_sem_casos_devolve_zeros(ambiente):
    raiz, fontes = ambiente
    d = _dados(raiz, fontes)
    assert d["casos"] == [] and d["numeros"]["total"] == 0
