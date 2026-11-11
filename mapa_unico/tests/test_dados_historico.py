import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "mapa_unico"))
sys.path.insert(0, str(RAIZ))

import mapa_unico  # noqa: E402

LANDSAT = ["1985-90", "1995-00", "2001-05", "2016-17", "2023-24"]


@pytest.fixture(scope="module")
def d():
    return mapa_unico.dados_historico()  # ~2 min (máscaras 1947)


def test_sem_ndvi(d):
    assert not [k for k in d if k.startswith("ndvi_")]


def test_numeros_presente(d):
    assert list(d["numeros"]) == ["2023-24", "2016-17", "2001-05", "1995-00", "1985-90", "1979", "1947"]


def test_chaves_mantidas(d):
    esperadas = {"uso_1947_vegetacao", "uso_1947_edificado", "veg_1979", "edif_1979", "veg_perda",
                 "veg_ganho", "cobertura_1979", "cobertura_1979_ha"}
    esperadas |= {f"{p}_{e}" for p in ("veg", "edif") for e in LANDSAT}
    assert esperadas <= set(d)
