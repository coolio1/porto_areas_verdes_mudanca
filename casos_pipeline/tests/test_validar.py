"""Validador dos casos: esquema, concelho (CAOP), excertos literais, fotos."""
import hashlib
from copy import deepcopy

import pytest

from casos_pipeline.validar import validar_caso

TEXTO_FONTE = "Os moradores contestaram o abate das árvores da rua."


@pytest.fixture
def caso_ok():
    return {
        "slug": "arvores-rua-x", "titulo": "Árvores da Rua X", "galeria": "horrores",
        "tipo": "arvores", "lat": 41.1480, "lon": -8.6250, "aproximada": False,
        "origem_coord": "OpenStreetMap", "ano": 2019, "estado": "abatido",
        "contestacao": "Petição de moradores.", "criterio": "documental",
        "fotos": [{"papel": "antes", "ficheiro": "01.jpg", "ano": 2015, "fonte": "Google Street View",
                   "url": "https://exemplo.pt/foto", "sha256": "x"}],
        "referencias": [{"titulo": "Notícia", "url": "https://exemplo.pt/n", "data": "2019-03-01",
                         "excerto": "contestaram o abate das árvores"}],
        "corpo": "As árvores da rua foram abatidas.",
    }


@pytest.fixture
def fontes(tmp_path):
    d = tmp_path / "fontes" / "arvores-rua-x"
    d.mkdir(parents=True)
    (d / "1.txt").write_text(TEXTO_FONTE, encoding="utf-8")
    return tmp_path / "fontes"


def test_caso_valido_sem_erros(caso_ok, fontes):
    assert validar_caso(caso_ok, fontes) == []


def test_tipo_invalido(caso_ok, fontes):
    caso_ok["tipo"] = "outra-coisa"
    assert any("tipo" in e for e in validar_caso(caso_ok, fontes))


def test_sem_referencias(caso_ok, fontes):
    caso_ok["referencias"] = []
    assert any("referência" in e for e in validar_caso(caso_ok, fontes))


def test_excerto_nao_encontrado_na_fonte(caso_ok, fontes):
    caso_ok["referencias"][0]["excerto"] = "a câmara garantiu que nenhuma árvore seria abatida"
    assert any("excerto" in e for e in validar_caso(caso_ok, fontes))


def test_fonte_sem_texto_guardado(caso_ok, tmp_path):
    assert any("texto" in e for e in validar_caso(caso_ok, tmp_path / "vazio"))


def test_fora_do_concelho(caso_ok, fontes):
    caso_ok["lat"], caso_ok["lon"] = 41.1833, -8.6900  # Matosinhos
    assert any("concelho" in e for e in validar_caso(caso_ok, fontes))


def test_foto_sem_url_de_origem(caso_ok, fontes):
    caso_ok["fotos"][0]["url"] = ""
    assert any("url" in e for e in validar_caso(caso_ok, fontes))


def test_freguesia_escrita_a_mao_e_erro(caso_ok, fontes):
    caso_ok["freguesia"] = "Cedofeita"
    assert any("freguesia" in e for e in validar_caso(caso_ok, fontes))


def test_criterio_editorial_exige_nota(caso_ok, fontes):
    caso_ok["criterio"] = "editorial"
    assert any("nota_editorial" in e for e in validar_caso(caso_ok, fontes))
    caso_ok["nota_editorial"] = "Avaliação do Porto Verde: ..."
    assert validar_caso(caso_ok, fontes) == []


def test_foto_em_falta_ou_sha256_errado(caso_ok, fontes, tmp_path):
    media = tmp_path / "media"
    (media / "arvores-rua-x").mkdir(parents=True)
    assert any("01.jpg" in e for e in validar_caso(caso_ok, fontes, raiz_media=media))
    f = media / "arvores-rua-x" / "01.jpg"
    f.write_bytes(b"jpg")
    assert any("sha256" in e for e in validar_caso(caso_ok, fontes, raiz_media=media))
    caso_ok = deepcopy(caso_ok)
    caso_ok["fotos"][0]["sha256"] = hashlib.sha256(b"jpg").hexdigest()
    assert validar_caso(caso_ok, fontes, raiz_media=media) == []
