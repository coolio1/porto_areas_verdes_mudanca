"""Indicador «300» do 3-30-300: distância a PÉ (rede pedonal OSM) de cada edifício ao espaço verde público.

Entradas (de obter_pbf.py, em S:\\3 30 300\\dados): edificios_osm.gpkg, rede_pedonal.pkl.
Parques: acessibilidade/parques_porto.geojson (fonte autoritativa do projecto; só verde público gratuito).
Variantes: parque ≥ 0,5 ha (principal, Browning 2024) e ≥ 1 ha (OMS, Konijnendijk 2023); rede e linha recta.

Saída: edificios_300.gpkg (ponto dentro da pegada + d_rede_05, d_rede_1, d_euc_05, d_euc_1, em metros;
NaN = sem parque a ≤ 1000 m).

Limites assumidos (escritos no mapa): só parques do concelho (não conta os dos concelhos vizinhos);
acesso aproximado = qualquer nó pedonal dentro do parque ou a ≤ 10 m do contorno (sem portas OSM; parques
vedados ficam optimistas).
"""
import os
import pickle
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
from scipy.spatial import cKDTree
from shapely.strtree import STRtree

RAIZ = Path(__file__).resolve().parents[1]
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
CRS = "EPSG:3763"
CORTE = 1000.0       # m; além disto NaN
TOL_CONTORNO = 10.0  # m: nó fora do parque mas a ≤ 10 m do contorno conta como acesso
EXCLUIR = {"roof", "shed", "garage", "garages", "ruins", "construction", "carport", "service", "hut", "kiosk"}


def parques():
    g = gpd.read_file(RAIZ / "acessibilidade" / "parques_porto.geojson").to_crs(CRS)
    g["ha"] = g.geometry.area / 1e4  # área recalculada em ETRS89/PT-TM06, não a do ficheiro
    return g


def main():
    with open(DADOS / "rede_pedonal.pkl", "rb") as f:
        G = pickle.load(f)
    ids = np.array(list(G.nodes))
    xy = np.array([(G.nodes[n]["x"], G.nodes[n]["y"]) for n in ids])
    arvore_nos = cKDTree(xy)

    ed = gpd.read_file(DADOS / "edificios_osm.gpkg")
    ed = ed[~ed["building"].isin(EXCLUIR)].reset_index(drop=True)
    pt = ed.geometry.representative_point()  # dentro da pegada (o centróide pode cair fora em L/U)
    d_lig, k = arvore_nos.query(np.c_[pt.x.values, pt.y.values])
    nn = ids[k]

    P = parques()
    nos_gdf = gpd.GeoDataFrame({"id": ids}, geometry=gpd.points_from_xy(xy[:, 0], xy[:, 1]), crs=CRS)
    arv_pts = STRtree(nos_gdf.geometry.values)
    out = gpd.GeoDataFrame({"building": ed["building"]}, geometry=pt, crs=CRS)
    out["d_lig"] = d_lig  # edifício → nó mais próximo (somada à distância pela rede)
    for rot, minimo in (("05", 0.5), ("1", 1.0)):
        sel = P[P["ha"] >= minimo]
        fontes = set()
        for geom in sel.geometry:
            # predicate obrigatório: sem ele o STRtree devolve os nós da CAIXA ENVOLVENTE do parque
            fontes.update(ids[i] for i in arv_pts.query(geom.buffer(TOL_CONTORNO), predicate="intersects"))
        dist = nx.multi_source_dijkstra_path_length(G, list(fontes), cutoff=CORTE, weight="length")
        out["d_rede_" + rot] = [dist[n] + l if n in dist else np.nan for n, l in zip(nn, d_lig)]
        arv_parq = STRtree(sel.geometry.values)
        out["d_euc_" + rot] = [sel.geometry.values[arv_parq.nearest(p)].distance(p) for p in pt.values]
        print(f"parques ≥{minimo} ha: {len(sel)} | nós de acesso: {len(fontes)}")
    out.to_file(DADOS / "edificios_300.gpkg", driver="GPKG")
    print(f"edifícios: {len(out)}")
    for rot in ("05", "1"):
        print(f"≥{rot} ha: rede ≤300 m {np.mean(out['d_rede_' + rot] <= 300):.1%} | "
              f"linha recta ≤300 m {np.mean(out['d_euc_' + rot] <= 300):.1%} dos edifícios")


if __name__ == "__main__":
    main()
