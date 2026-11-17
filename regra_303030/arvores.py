"""3-30-300 · árvores individuais: picos do LiDAR dentro de manchas de copa + inventário da Câmara (CMP).

Para o «3» (3 árvores à vista a ≤30 m) conta-se por árvore, não por píxel:
  · LiDAR: máximos locais do nDSM suavizado (σ = 1 m) dentro de manchas de copa ≥ MIN_COPA_M2 (25 m²),
    altura entre ALTURA_COPA (3 m) e ALTURA_MAX (45 m); folhas «más» (copa.py) ficam de fora;
  · CMP: todas as árvores do inventário (71 634), com a marca `detectado` (nDSM ≥ 3 m a ≤ 2 m); um pico LiDAR a
    ≤ DEDUP_M de uma árvore da CMP é descartado (o inventário prevalece). Nenhum espaço é excluído (Serralves,
    quintas, praças: decisão do utilizador, 2026-11-17).

Saída: <DADOS>\\arvores.gpkg (EPSG:3763): origem (lidar|cmp), altura_m, mancha_m2, detectado (1/0, -1 = sem dados).
"""
import csv
import os
import sys
from pathlib import Path

import numpy as np

ALTURA_COPA = 3.0
ALTURA_MAX = 45.0    # m: acima disto é grua, mastro ou edifício por mapear, não árvore (Porto: eucaliptos ≤ ~40 m)
MIN_COPA_M2 = 25.0
PIXEL_M = 0.5
SIGMA_M = 1.0
JANELA_M = 3.0      # raio mínimo entre picos
DEDUP_M = 3.0       # pico LiDAR a ≤ isto de uma árvore da CMP = a mesma árvore
RAIO_DET_M = 2.0
RAIZ = Path(__file__).resolve().parents[1]
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
LIDAR = Path(os.environ.get("PV_LIDAR_DADOS", DADOS / "lidar"))
COPA_DIR = DADOS / "copa"


def picos(ndsm, copa, min_m2=MIN_COPA_M2, altura=ALTURA_COPA, pixel=PIXEL_M, altura_max=ALTURA_MAX):
    """Árvores de um raster: devolve (linhas, colunas, alturas, área da mancha em m²).

    `copa` = máscara booleana de copa. Manchas (8-vizinhança) < min_m2 são ruído (arbustos, carros, postes).
    """
    from scipy import ndimage
    lab, n = ndimage.label(copa, structure=np.ones((3, 3)))
    if n == 0:
        return (np.array([], int),) * 2 + (np.array([], float),) * 2
    area = np.bincount(lab.ravel(), minlength=n + 1) * pixel * pixel
    liso = ndimage.gaussian_filter(np.where(np.isfinite(ndsm), ndsm, 0), SIGMA_M / pixel)
    k = max(int(round(2 * JANELA_M / pixel)) | 1, 3)
    max_local = ndimage.maximum_filter(liso, size=k)
    cand = copa & (liso == max_local) & (np.nan_to_num(ndsm, nan=0) >= altura) & (np.nan_to_num(ndsm, nan=0) <= altura_max) & (area[lab] >= min_m2)
    r, c = np.nonzero(cand)
    return r, c, ndsm[r, c], area[lab[r, c]]


def le_cmp(caminho=DADOS / "arvoredo_cmp.csv"):
    """Inventário da CMP: [(x, y, classe de idade)] em EPSG:3763."""
    out = []
    with open(caminho, encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh, quotechar="'")
        next(rd)
        for row in rd:
            x, y = (float(v) for v in row[4].split(","))
            out.append((x, y, row[3]))
    return out


def deduplicar(pontos_lidar, pontos_cmp, dist=DEDUP_M):
    """Máscara booleana dos picos LiDAR a manter (≥ `dist` m de qualquer árvore da CMP)."""
    from scipy.spatial import cKDTree
    if not len(pontos_cmp) or not len(pontos_lidar):
        return np.ones(len(pontos_lidar), bool)
    d, _ = cKDTree(np.asarray(pontos_cmp)).query(np.asarray(pontos_lidar), k=1)
    return d > dist


def main():
    import geopandas as gpd
    import pandas as pd
    import rasterio
    from shapely.geometry import Point

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    folhas = {r["folha"]: r for r in csv.DictReader(open(DADOS / "copa_folhas.csv", encoding="utf-8"))}
    cmp_ = le_cmp()
    mdt_por_caixa = {}
    for p in LIDAR.glob("MDT-50cm-*.tif"):
        with rasterio.open(p) as d:
            mdt_por_caixa[tuple(round(v) for v in d.bounds)] = p
    lidar_pts, det = [], {}
    k = int(RAIO_DET_M / PIXEL_M)
    for nome, f in sorted(folhas.items()):
        mds_p = LIDAR / (nome + ".tif")
        with rasterio.open(mds_p) as d:
            caixa = tuple(round(v) for v in d.bounds)
            mds = d.read(1, masked=True).astype("float32")
            tr, b = d.transform, d.bounds
        with rasterio.open(mdt_por_caixa[caixa]) as d2:
            mdt = d2.read(1, masked=True).astype("float32")
        ndsm = np.ma.filled(mds - mdt, np.nan)
        # detecção do inventário nesta folha (vale também nas folhas más: só serve de indicador)
        for i, (x, y, _) in enumerate(cmp_):
            if b.left <= x < b.right and b.bottom <= y < b.top:
                c, r_ = ~tr * (x, y)
                w = ndsm[max(int(r_) - k, 0): int(r_) + k + 1, max(int(c) - k, 0): int(c) + k + 1]
                if np.isfinite(w).any():
                    det[i] = int(np.nanmax(w) >= ALTURA_COPA)
        if int(f["ma"]):
            continue
        with rasterio.open(COPA_DIR / (nome.replace("MDS-50cm-", "copa-") + ".tif")) as dc:
            copa = dc.read(1) == 1
        r, c, h, a = picos(ndsm, copa)
        xs, ys = tr * (c + 0.5, r + 0.5)
        lidar_pts += list(zip(xs, ys, h, a))
        print(nome[-17:], len(r), "picos")
    manter = deduplicar([(x, y) for x, y, *_ in lidar_pts], [(x, y) for x, y, _ in cmp_])
    linhas = [("lidar", Point(x, y), float(h), float(a), None) for (x, y, h, a), m in zip(lidar_pts, manter) if m]
    linhas += [("cmp", Point(x, y), None, None, det.get(i, -1)) for i, (x, y, _) in enumerate(cmp_)]
    g = gpd.GeoDataFrame(pd.DataFrame([(o, h, a, d) for o, _, h, a, d in linhas], columns=["origem", "altura_m", "mancha_m2", "detectado"]),
                         geometry=[p for _, p, *_ in linhas], crs=3763)
    g.to_file(DADOS / "arvores.gpkg", driver="GPKG")
    ava = g[(g.origem == "cmp") & (g.detectado >= 0)].detectado  # -1 = sem nDSM válido (não avaliável)
    print("árvores:", g.origem.value_counts().to_dict(), "| CMP avaliáveis: %d, detectadas %.1f %%" % (len(ava), 100 * ava.mean()))


if __name__ == "__main__":
    main()
