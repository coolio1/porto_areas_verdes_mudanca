"""Percentagens de vegetação e edificado por época (Histórico), calculadas das próprias máscaras.

Denominador: o concelho do Porto (alfa de layers_historico/porto_mask.png, grelha 2048x769).
A grelha de 1947 é outra (BOUNDS_1947, 18432x9216): o concelho é reamostrado para ela.
"""

import io
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

EPOCAS = ["2023-24", "2016-17", "2001-05", "1995-00", "1985-90", "1979", "1972-76", "1947"]
GRELHA = (41.13, -8.7, 41.19, -8.54)  # lat_s, lon_o, lat_n, lon_e (épocas Landsat e 1979)
BOUNDS_1947 = (41.12912995365261, -8.700884213830351, 41.189999037480554, -8.539187462666328)


def contar(mascara_alfa: np.ndarray, concelho: np.ndarray) -> float:
    """% de píxeis com alfa > 0 dentro do concelho (bool, mesma forma)."""
    return 100.0 * float(((mascara_alfa > 0) & concelho).sum()) / float(concelho.sum())


def _alfa(origem) -> np.ndarray:
    im = Image.open(origem)
    return np.asarray(im.getchannel("A") if "A" in im.getbands() else im.convert("RGBA").getchannel("A"))


def _concelho_na_grelha_1947(concelho: np.ndarray, w: int, h: int):
    """Reamostra o concelho (grelha Landsat) para a grelha 1947 (w x h); devolve (bool h x w, cobertura %)."""
    s, o, n, e = BOUNDS_1947
    gs, go, gn, ge = GRELHA
    lat = n - (np.arange(h) + 0.5) / h * (n - s)
    lon = o + (np.arange(w) + 0.5) / w * (e - o)
    hc, wc = concelho.shape
    r = np.floor((gn - lat) / (gn - gs) * hc).astype(int)
    c = np.floor((lon - go) / (ge - go) * wc).astype(int)
    rv, cv = (r >= 0) & (r < hc), (c >= 0) & (c < wc)
    out = concelho[np.ix_(np.clip(r, 0, hc - 1), np.clip(c, 0, wc - 1))] & rv[:, None] & cv[None, :]
    # cobertura: fracção do concelho (centros dos píxeis Landsat) que cai dentro de BOUNDS_1947
    la = gn - (np.arange(hc) + 0.5) / hc * (gn - gs)
    lo = go + (np.arange(wc) + 0.5) / wc * (ge - go)
    dentro = ((la >= s) & (la <= n))[:, None] & ((lo >= o) & (lo <= e))[None, :]
    return out, 100.0 * float((concelho & dentro).sum()) / float(concelho.sum())


def percentagens(raiz: Path) -> dict:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cobertura_1979 as c79

    hist = raiz / "layers_historico"
    concelho = _alfa(hist / "porto_mask.png") > 0
    r = lambda x: round(x, 1)
    out = {}
    for e in EPOCAS:
        if e == "1979":
            g = c79.carregar()
            veg = _alfa(io.BytesIO(c79.mascara_png(g, ["TRS", "HER"], c79.COR_VEG)))
            edif = _alfa(io.BytesIO(c79.mascara_png(g, ["ABE"], c79.COR_EDIF)))
            out[e] = {"veg": r(contar(veg, concelho)), "edif": r(contar(edif, concelho)), "cobertura": 100.0}
        elif e == "1947":
            veg = _alfa(raiz / "1947" / "layers" / "uso_1947_vegetacao.png")
            h, w = veg.shape
            c47, cob = _concelho_na_grelha_1947(concelho, w, h)
            v = contar(veg, c47)
            del veg
            edif = _alfa(raiz / "1947" / "layers" / "uso_1947_edificado.png")
            out[e] = {"veg": r(v), "edif": r(contar(edif, c47)), "cobertura": r(cob)}
        else:
            veg = _alfa(hist / f"veg_{e}.png")
            edif = _alfa(hist / f"edif_{e}.png")
            out[e] = {"veg": r(contar(veg, concelho)), "edif": r(contar(edif, concelho)), "cobertura": 100.0}
    return out
