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
    veg = np.array(Image.open(RAIZ / "layers_historico" / "veg_2023-24.png"))[..., 3] / 255.0  # alfa = fracção
    esperado = 100 * veg[mask].sum() / mask.sum()
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

    ha = c79.recortar_ao_porto(c79.carregar()).groupby("LC_1979_ab")["ha"].sum()
    total = float(ha.sum())
    assert abs(nums["1979"]["veg"] - 100 * (ha["TRS"] + ha["HER"]) / total) < 0.1
    assert abs(nums["1979"]["edif"] - 100 * ha["ABE"] / total) < 0.1


def test_1979_recortado_nao_passa_o_concelho():
    """Os números de 1979 só contam o que está dentro do concelho (o ficheiro original passa o limite)."""
    import cobertura_1979 as c79

    g = c79.carregar()
    s = c79.recortar_ao_porto(g)
    assert s.ha.sum() < g.ha.sum() - 20          # o original tem >20 ha fora do concelho
    assert s.ha.sum() <= 4142.1                   # ≤ área do concelho (CAOP)


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


def test_incerteza_so_nas_epocas_landsat(nums):
    import mapa_unico as mu

    inc = mu.incerteza_epocas(RAIZ / "layers_historico" / "incerteza.json")
    assert set(inc) == {"2023-24", "2016-17", "2001-05", "1995-00", "1985-90"}
    assert all(0 < s < 5 for s in inc.values())
    assert inc["2016-17"] >= 0.4  # inclui o erro da ponte L8-L7


def test_perda_ganho_sem_manchas_abaixo_de_meio_hectare():
    from scipy import ndimage as ndi

    mask = np.array(Image.open(RAIZ / "layers_historico" / "porto_mask.png"))[..., 3] > 0
    ha_px = 4142.1 / mask.sum()
    for n in ("veg_perda", "veg_ganho"):
        a = (np.array(Image.open(RAIZ / "layers_historico" / f"{n}.png"))[..., 3] > 0) & mask
        lab, k = ndi.label(a, np.ones((3, 3)))
        areas = np.bincount(lab.ravel())[1:] * ha_px
        assert k > 0 and areas.min() >= 0.5, f"{n}: menor mancha {areas.min():.2f} ha"


def test_contar_binaria_ignora_o_valor_do_alfa():
    """1947 tem alfa 200 (não 255): binária conta píxeis, ponderada daria 78 %."""
    concelho = np.ones((2, 2), bool)
    m = np.array([[200, 0], [0, 0]], np.uint8)
    assert contar(m, concelho, binaria=True) == 25.0
    assert abs(contar(m, concelho) - 100 * (200 / 255) / 4) < 1e-9


def test_1947_nao_mudou_com_a_fase_2(nums):
    assert abs(nums["1947"]["veg"] - 74.5) < 0.1 and abs(nums["1947"]["edif"] - 21.2) < 0.1
