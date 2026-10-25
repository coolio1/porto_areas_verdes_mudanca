import pytest
from espacos_pipeline.modelo import Espaco, ESTADOS, slugify, validar, validar_lote


def _e(**kw):
    base = dict(titulo="Parque Exemplo", concelho="Porto", seleccionado=False, texto="Texto limpo de 2007.")
    base.update(kw)
    return Espaco(**base)


def test_slug_ignora_caixa_acentos_espacos():
    assert slugify("Quinta dos Ananases") == "quinta-dos-ananases"
    assert slugify("  quinta dos ananases ") == "quinta-dos-ananases"
    assert slugify("Arboreto — Escola EB2 de Canelas") == "arboreto-escola-eb2-de-canelas"


def test_espaco_valido_nao_tem_erros():
    assert validar(_e()) == []


def test_seleccionado_sem_selecao_falha():
    assert any("selecao" in m for m in validar(_e(seleccionado=True)))
    assert validar(_e(seleccionado=True, selecao="2009-04")) == []
    assert validar(_e(seleccionado=True, selecao="posterior")) == []


def test_nao_seleccionado_com_selecao_falha():
    assert any("selecao" in m for m in validar(_e(selecao="2009-04")))


def test_slug_repetido_no_mesmo_concelho_falha():
    lote = [_e(titulo="Parque X"), _e(titulo="parque x ")]
    assert any("slug" in m for m in validar_lote(lote))


def test_lat_lon_sem_origem_falha():
    assert any("origem_coord" in m for m in validar(_e(lat=41.15, lon=-8.61)))


def test_lat_lon_zero_falha():
    assert any("coordenadas" in m for m in validar(_e(lat=0.0, lon=0.0, origem_coord="Webnode")))


def test_so_uma_coordenada_falha():
    assert any("coordenadas" in m for m in validar(_e(lat=41.15, origem_coord="Webnode")))


def test_estado_fora_da_lista_falha():
    assert any("estado_actual" in m for m in validar(_e(estado_actual="inventado")))
    assert "por verificar" in ESTADOS


@pytest.mark.parametrize("texto", ["Ligue 912345678", "escreva para a@b.pt", "tel +351 22 000 00 00"])
def test_texto_com_contactos_falha(texto):
    assert any("contacto" in m for m in validar(_e(texto=texto)))


def test_coordenadas_fora_da_amp_falham():
    assert any("fora da AMP" in m for m in validar(_e(lat=41.17, lon=-8.17, origem_coord="Webnode")))
    assert any("fora da AMP" in m for m in validar(_e(lat=41.16, lon=8.57, origem_coord="Webnode")))
    assert validar(_e(lat=41.16, lon=-8.57, origem_coord="Webnode")) == []
