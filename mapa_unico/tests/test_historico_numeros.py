import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "mapa_unico"))
sys.path.insert(0, str(RAIZ))

from historico_numeros import contar, percentagens  # noqa: E402

ORDEM = ["2023-24", "2016-17", "2001-05", "1995-00", "1985-90", "1979", "1947"]


@pytest.fixture(scope="module")
def nums():
    return percentagens(RAIZ)


def test_contar_conta_so_dentro_do_concelho():
    concelho = np.zeros((4, 4), bool)
    concelho[:2, :] = True  # 8 pixeis
    m = np.zeros((4, 4), np.uint8)
    m[0, 0] = m[1, 3] = 255  # 2 dentro
    m[3, 0] = m[3, 1] = m[2, 2] = 255  # 3 fora
    assert contar(m, concelho) == 25.0


def test_sete_epocas_do_mais_recente_ao_mais_antigo(nums):
    assert list(nums) == ORDEM


def test_conferem_com_contagem_independente(nums):
    mask = np.array(Image.open(RAIZ / "layers_historico" / "porto_mask.png"))[..., 3] > 0
    veg = np.array(Image.open(RAIZ / "layers_historico" / "veg_2023-24.png"))[..., 3] > 0
    esperado = 100 * (veg & mask).sum() / mask.sum()
    assert abs(nums["2023-24"]["veg"] - esperado) < 0.1


def test_valores_plausiveis(nums):
    for e, v in nums.items():
        assert 0 <= v["veg"] + v["edif"] <= 100, e
        assert 0 < v["cobertura"] <= 100, e
    assert nums["2023-24"]["veg"] > 0


def test_cobertura_minima_95(nums):
    for e, v in nums.items():
        assert v["cobertura"] >= 95, f"{e}: cobertura {v['cobertura']} %"


def test_1979_confere_com_as_areas_vectoriais(nums):
    """1979 vem das áreas vectoriais (as mesmas ha da legenda das 5 classes), não de píxeis rasterizados."""
    import cobertura_1979 as c79

    ha = c79.carregar().groupby("LC_1979_ab")["ha"].sum()
    total = float(ha.sum())
    assert abs(nums["1979"]["veg"] - 100 * (ha["TRS"] + ha["HER"]) / total) < 0.1
    assert abs(nums["1979"]["edif"] - 100 * ha["ABE"] / total) < 0.1


def test_mascara_visual_1979_confere_com_as_areas_vectoriais():
    """O que se vê no mapa (máscara rasterizada) tem de bater com os números (áreas vectoriais)."""
    import io

    import cobertura_1979 as c79

    g = c79.carregar()
    ha = g.groupby("LC_1979_ab")["ha"].sum()
    total = float(ha.sum())
    mask = np.array(Image.open(RAIZ / "layers_historico" / "porto_mask.png"))[..., 3] > 0

    def pct(png):
        a = np.array(Image.open(io.BytesIO(png)))[..., 3] > 0
        return 100 * (a & mask).sum() / mask.sum()

    veg = pct(c79.mascara_png(g, ["TRS", "HER"], c79.COR_VEG))
    edif = pct(c79.mascara_png(g, ["ABE"], c79.COR_EDIF))
    assert abs(veg - 100 * (ha["TRS"] + ha["HER"]) / total) < 1.0, veg
    assert abs(edif - 100 * ha["ABE"] / total) < 1.0, edif
