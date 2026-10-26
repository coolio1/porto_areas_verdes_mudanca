import json

import pytest

from espacos_pipeline.gerar import gerar
from espacos_pipeline.modelo import Espaco


def _e(titulo="Quinta X", **kw):
    base = dict(titulo=titulo, concelho="Porto", seleccionado=True, selecao="2009-04", texto="Texto fundido.",
                freguesia="Campanhã", lat=41.16, lon=-8.57, origem_coord="ficha 2006–2008", fontes=["Ficha 2006–2008"])
    base.update(kw)
    return Espaco(**base)


def test_gerar_escreve_front_matter_e_corpo(tmp_path):
    gerar([_e()], tmp_path)
    md = (tmp_path / "_espacos" / "porto" / "quinta-x.md").read_text(encoding="utf-8")
    assert md.startswith("---\n") and "title: Quinta X" in md and "titulo: Quinta X" in md
    assert "freguesia: Campanhã" in md and md.rstrip().endswith("Texto fundido.")


def test_gerar_e_idempotente(tmp_path):
    gerar([_e()], tmp_path)
    antes = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    gerar([_e()], tmp_path)
    assert antes == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_titulo_publico_sem_sigla_mantem_o_slug(tmp_path):
    gerar([_e("Barrinha de Esmoriz e Lagoa de Paramos (BELP)", concelho="Espinho")], tmp_path)
    md = (tmp_path / "_espacos" / "espinho" / "barrinha-de-esmoriz-e-lagoa-de-paramos-belp.md").read_text(encoding="utf-8")
    assert "title: Barrinha de Esmoriz e Lagoa de Paramos\n" in md and "titulo: Barrinha de Esmoriz e Lagoa de Paramos\n" in md
    assert "BELP" not in md
    pontos = json.loads((tmp_path / "_data" / "espacos_mapa.json").read_text(encoding="utf-8"))
    assert pontos[0]["titulo"] == "Barrinha de Esmoriz e Lagoa de Paramos"


def test_espaco_sem_coordenadas_nao_entra_no_mapa(tmp_path):
    gerar([_e(), _e("Sem Mapa", lat=None, lon=None, origem_coord=None)], tmp_path)
    pontos = json.loads((tmp_path / "_data" / "espacos_mapa.json").read_text(encoding="utf-8"))
    assert [p["slug"] for p in pontos] == ["quinta-x"]
    assert set(pontos[0]) == {"slug", "titulo", "lat", "lon", "origem_coord", "seleccionado", "concelho"}


def test_erro_de_validacao_nao_escreve_nada(tmp_path):
    with pytest.raises(ValueError):
        gerar([_e(), _e("Mau", lat=0.0, lon=0.0)], tmp_path)
    assert list(tmp_path.rglob("*")) == []


def test_nao_publica_fusao_sem_revisto(tmp_path):
    from espacos_pipeline.gerar import ler_fusao
    f = tmp_path / "x.md"
    f.write_text("---\nslug: x\nrevisto: false\n---\nCorpo.\n", encoding="utf-8")
    assert ler_fusao(f) is None
    f.write_text("---\nslug: x\nrevisto: true\n---\nCorpo.\n", encoding="utf-8")
    assert ler_fusao(f) == "Corpo."


def test_listar_media_separa_fotos_e_anexos(tmp_path):
    from espacos_pipeline.gerar import listar_media
    d = tmp_path / "50espacos" / "media" / "quinta-x"
    d.mkdir(parents=True)
    for n in ("01.jpg", "02.jpg", "mapa.pdf"):
        (d / n).write_bytes(b"x")
    fotos, anexos = listar_media("quinta-x", tmp_path)
    assert [f["src"] for f in fotos] == ["/50espacos/media/quinta-x/01.jpg", "/50espacos/media/quinta-x/02.jpg"]
    assert anexos == [{"src": "/50espacos/media/quinta-x/mapa.pdf", "titulo": "mapa"}]
    assert listar_media("inexistente", tmp_path) == ([], [])


def test_titulo_com_dois_pontos_fica_entre_aspas(tmp_path):
    import yaml
    gerar([_e("Quinta: a velha")], tmp_path)
    fm = (tmp_path / "_espacos" / "porto" / "quinta-a-velha.md").read_text(encoding="utf-8").split("---")[1]
    assert yaml.safe_load(fm)["titulo"] == "Quinta: a velha"
