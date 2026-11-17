"""3-30-300 · o «30»: % de copa arbórea à volta de cada edifício (círculo de 500 m; 400 e 600 para sensibilidade).

Parte das máscaras de copa de copa.py (50 cm), agrega em células de CELULA_M (5 m) e faz a convolução com um
disco por FFT. % = copa / área válida do disco (só o concelho com folha fiável conta: folhas «más» e o exterior do
Porto não entram nem no numerador nem no denominador). `cobertura` = área válida / área do disco: junto à
fronteira do concelho o círculo sai do Porto e a % assenta numa parte do disco; cobertura < COB_MIN fica
assinalada (o mapa mostra o valor com aviso, não o esconde).

Saída: <DADOS>\\copa500_edificios.csv (idx, copa400, copa500, copa600, cobertura500).
"""
import csv
import os
import sys
from pathlib import Path

import numpy as np

CELULA_M = 5.0
PIXEL_M = 0.5
RAIOS = (400, 500, 600)
COB_MIN = 0.7
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
COPA_DIR = DADOS / "copa"


def agregar(mascara, bloco):
    """uint8 (0 sem copa, 1 copa, 2 edifício, 255 nodata) → (copa, válidas) somadas por blocos bloco×bloco."""
    h, w = (s // bloco * bloco for s in mascara.shape)
    m = mascara[:h, :w]
    valida = (m != 255).reshape(h // bloco, bloco, w // bloco, bloco).sum((1, 3)).astype(np.float32)
    copa = (m == 1).reshape(h // bloco, bloco, w // bloco, bloco).sum((1, 3)).astype(np.float32)
    return copa, valida


def disco(raio_m, celula=CELULA_M):
    r = raio_m / celula
    n = int(np.ceil(r))
    y, x = np.mgrid[-n: n + 1, -n: n + 1]
    return (np.hypot(y, x) <= r).astype(np.float32)


def convolucao(copa, valida, raio_m, celula=CELULA_M):
    """Devolve (% de copa, cobertura) em cada célula: copa/válidas e válidas/área do disco, em [0, 1]."""
    from scipy.signal import fftconvolve
    k = disco(raio_m, celula)
    c = fftconvolve(copa, k, mode="same")
    v = fftconvolve(valida, k, mode="same")
    area = k.sum() * (celula / PIXEL_M) ** 2
    with np.errstate(invalid="ignore", divide="ignore"):
        pct = np.where(v > 1, c / v, np.nan)
    return pct, np.clip(v / area, 0, 1)


def mosaico(pasta=COPA_DIR, ma=frozenset()):
    """Mosaico das folhas (menos as `ma`): devolve copa, válidas (grelha de CELULA_M) e (x0, y0) do canto superior esquerdo."""
    import rasterio
    bloco = int(CELULA_M / PIXEL_M)
    folhas = []
    for p in sorted(pasta.glob("copa-*.tif")):
        with rasterio.open(p) as d:
            folhas.append((p, d.bounds))
    x0 = min(b.left for _, b in folhas)
    y0 = max(b.top for _, b in folhas)
    W = int(round((max(b.right for _, b in folhas) - x0) / CELULA_M))
    H = int(round((y0 - min(b.bottom for _, b in folhas)) / CELULA_M))
    copa = np.zeros((H, W), np.float32)
    val = np.zeros((H, W), np.float32)
    for p, b in folhas:
        if p.stem.replace("copa-", "") in ma:
            continue
        with rasterio.open(p) as d:
            c, v = agregar(d.read(1), bloco)
        r0, c0 = int(round((y0 - b.top) / CELULA_M)), int(round((b.left - x0) / CELULA_M))
        copa[r0: r0 + c.shape[0], c0: c0 + c.shape[1]] += c
        val[r0: r0 + v.shape[0], c0: c0 + v.shape[1]] += v
    return copa, val, (x0, y0)


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from edificios import carregar
    ma = {r["folha"].replace("MDS-50cm-", "") for r in csv.DictReader(open(DADOS / "copa_folhas.csv", encoding="utf-8")) if int(r["ma"])}
    copa, val, (x0, y0) = mosaico(ma=ma)
    print("grelha", copa.shape, "| folhas más ignoradas:", sorted(ma))
    ed = carregar()
    pt = ed.geometry.representative_point()
    col = np.clip(((pt.x.values - x0) // CELULA_M).astype(int), 0, copa.shape[1] - 1)
    lin = np.clip(((y0 - pt.y.values) // CELULA_M).astype(int), 0, copa.shape[0] - 1)
    out = {"idx": np.arange(len(ed))}
    for r in RAIOS:
        pct, cob = convolucao(copa, val, r)
        out[f"copa{r}"] = np.round(100 * pct[lin, col], 2)
        if r == 500:
            out["cobertura500"] = np.round(cob[lin, col], 3)
    import pandas as pd
    df = pd.DataFrame(out)
    df.to_csv(DADOS / "copa500_edificios.csv", index=False)
    print("copa500: mediana %.1f %% | média %.1f %% | edifícios com ≥30 %%: %.1f %%" % (df.copa500.median(), df.copa500.mean(), 100 * (df.copa500 >= 30).mean()))
    print("cobertura <%.0f %% (junto à fronteira ou a folha má): %.1f %% dos edifícios | sem valor: %d" % (100 * COB_MIN, 100 * (df.cobertura500 < COB_MIN).mean(), df.copa500.isna().sum()))


if __name__ == "__main__":
    main()
