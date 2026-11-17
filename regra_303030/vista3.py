"""3-30-300 · o «3»: árvores visíveis a ≤ 30 m de uma janela do edifício.

Janelas simuladas a cada PASSO_M (5 m) ao longo de todos os contornos (exterior e pátios), deslocadas
OFFSET_M (0,3 m) para fora. Uma árvore é «visível» se o segmento janela → árvore não cruza nenhum edifício
(o próprio incluído) e a distância é ≤ RAIO_M. Visão 2D: ignora a altura dos edifícios que bloqueiam e a
das copas (limitação declarada: sobrestima o bloqueio por edifícios baixos e o desbloqueio por copas altas).

`calcular` devolve os pares únicos (edifício, árvore) com a distância mínima entre as janelas que a vêem;
chega para qualquer raio ≤ RAIO_M (sensibilidade) sem repetir o cálculo.

Árvores usadas: arvores.gpkg (LiDAR + CMP). Do inventário saem as que o LiDAR não vê com ≥ 3 m (detectado == 0:
jovens, abatidas), porque o «3» só conta árvores com copa; `detectado == -1` (sem nDSM) mantêm-se.

Saída: <DADOS>\\vista3_pares.npz (b, t, d) e <DADOS>\\vista3_edificios.csv (idx, osm_id, n3, n30_sem_bloqueio).
"""
import os
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely import STRtree

RAIO_M = 30.0
PASSO_M = 5.0
OFFSET_M = 0.3
LOTE = 400_000
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))


def janelas(geoms, passo=PASSO_M, offset=OFFSET_M):
    """Pontos-janela por edifício: devolve (idx_edifício, x, y) com os pontos deslocados para fora."""
    bi, xs, ys = [], [], []
    for i, g in enumerate(geoms):
        for poly in getattr(g, "geoms", [g]):
            poly = shapely.geometry.polygon.orient(poly, 1.0)  # exterior anti-horário, pátios horários: o edifício fica à esquerda
            for ring in [poly.exterior, *poly.interiors]:
                L = ring.length
                if L < 1:
                    continue
                n = max(1, int(L // passo))
                s = (np.arange(n) + 0.5) * L / n
                p = shapely.line_interpolate_point(ring, s)
                a = shapely.line_interpolate_point(ring, np.clip(s - 0.5, 0, L))
                b = shapely.line_interpolate_point(ring, np.clip(s + 0.5, 0, L))
                px, py = shapely.get_x(p), shapely.get_y(p)
                tx, ty = shapely.get_x(b) - shapely.get_x(a), shapely.get_y(b) - shapely.get_y(a)
                norm = np.hypot(tx, ty)
                norm[norm == 0] = 1
                xs.append(px + offset * ty / norm)   # normal à direita da direcção = para fora do edifício
                ys.append(py - offset * tx / norm)
                bi.append(np.full(n, i))
    return np.concatenate(bi), np.concatenate(xs), np.concatenate(ys)


def calcular(geoms, arv_xy, raio=RAIO_M, passo=PASSO_M, offset=OFFSET_M, lote=LOTE):
    """Pares únicos (edifício, árvore) visíveis: arrays b, t, d (distância mínima, m) e contagem sem bloqueio por edifício."""
    arv_xy = np.asarray(arv_xy, float)
    bi, wx, wy = janelas(geoms, passo, offset)
    arv_pts = shapely.points(arv_xy[:, 0], arv_xy[:, 1])
    arv_tree = STRtree(arv_pts)
    ed_tree = STRtree(np.asarray(geoms, dtype=object))
    jan_pts = shapely.points(wx, wy)
    wi, ti = arv_tree.query(jan_pts, predicate="dwithin", distance=raio)  # candidatos (janela, árvore) a ≤ raio
    dist = np.hypot(wx[wi] - arv_xy[ti, 0], wy[wi] - arv_xy[ti, 1])
    ok = dist <= raio
    wi, ti, dist = wi[ok], ti[ok], dist[ok]
    n_edif = len(geoms)
    sem_bloq = np.bincount(np.unique(np.stack([bi[wi], ti], 1), axis=0)[:, 0], minlength=n_edif)
    visivel = np.zeros(len(wi), bool)
    for ini in range(0, len(wi), lote):
        sl = slice(ini, ini + lote)
        linhas = shapely.linestrings(np.stack([np.stack([wx[wi[sl]], wy[wi[sl]]], 1), arv_xy[ti[sl]]], 1))
        li, _ = ed_tree.query(linhas, predicate="intersects")
        bloq = np.zeros(len(linhas), bool)
        bloq[np.unique(li)] = True
        visivel[sl] = ~bloq
    b, t, d = bi[wi][visivel], ti[visivel], dist[visivel]
    ordem = np.lexsort((d, t, b))
    b, t, d = b[ordem], t[ordem], d[ordem]
    primeiro = np.ones(len(b), bool)
    primeiro[1:] = (b[1:] != b[:-1]) | (t[1:] != t[:-1])  # menor distância de cada par
    return b[primeiro], t[primeiro], d[primeiro], sem_bloq


def n3(b, d, n_edif, raio=RAIO_M):
    """Nº de árvores visíveis a ≤ raio por edifício."""
    return np.bincount(b[d <= raio], minlength=n_edif)


def carregar_arvores():
    """Árvores que contam no «3» (ver docstring); o índice 0..N-1 é o `t` dos pares gravados."""
    import geopandas as gpd
    arv = gpd.read_file(DADOS / "arvores.gpkg")
    return arv[~((arv.origem == "cmp") & (arv.detectado == 0))].reset_index(drop=True)


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from edificios import carregar
    ed = carregar()
    arv = carregar_arvores()
    xy = np.stack([arv.geometry.x, arv.geometry.y], 1)
    print("edifícios:", len(ed), "| árvores:", len(arv))
    b, t, d, sem = calcular(list(ed.geometry), xy)
    np.savez_compressed(DADOS / "vista3_pares.npz", b=b, t=t, d=d.astype("float32"))
    c = n3(b, d, len(ed))
    import pandas as pd
    pd.DataFrame({"idx": np.arange(len(ed)), "osm_id": ed.osm_id, "n3": c, "n30_sem_bloqueio": sem}).to_csv(DADOS / "vista3_edificios.csv", index=False)
    print("pares visíveis:", len(b))
    print("edifícios com ≥3 árvores visíveis a ≤30 m: %.1f %% (sem bloqueio: %.1f %%)" % (100 * (c >= 3).mean(), 100 * (sem >= 3).mean()))
    print("n3: mediana %d | média %.1f | máx %d" % (np.median(c), c.mean(), c.max()))


if __name__ == "__main__":
    main()
