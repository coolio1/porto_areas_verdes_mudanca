"""Passo 2 do mapa 3-30-300: edifícios e rede pedonal do Porto a partir do extracto OSM da Geofabrik.

Porque não o Overpass: o serviço público dava 502/timeouts constantes (4 h para 8 blocos de 9).
O extracto completo de Portugal (~430 MB) descarrega-se em segundos e lê-se localmente.

Descarregar (uma vez; actualiza-se diariamente):
  https://download.geofabrik.de/europe/portugal-latest.osm.pbf  ->  S:\\3 30 300\\dados\\portugal-latest.osm.pbf

Saídas (em S:\\3 30 300\\dados, variável PV_REGRA_DADOS):
  edificios_osm.gpkg   edifícios (EPSG:3763) dentro do concelho
  rede_pedonal.pkl     grafo pedonal não dirigido (networkx; nós com x,y em EPSG:3763; aresta 'length' em m)

Correr com o venv %LOCALAPPDATA%\\PortoVerde\\venv (geopandas, pyogrio, osmium, networkx, pyproj).
Idempotente: não refaz o que já existe.
"""
import os
import pickle
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import osmium
from pyproj import Transformer
from shapely.geometry import box

RAIZ = Path(__file__).resolve().parents[1]
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
PBF = DADOS / "portugal-latest.osm.pbf"
CAOP = RAIZ / "CAOP_Continente_2025-gpkg" / "CAOP2025_municipios.shp"
CRS = "EPSG:3763"

# rede «a pé»: exclui o que não é para peões (como o filtro «walk» do osmnx, sem ciclovias e auto-estradas)
EXCLUIR_HIGHWAY = {"motorway", "motorway_link", "abandoned", "bridleway", "bus_guideway", "construction",
                   "corridor", "cycleway", "elevator", "escalator", "motor", "no", "planned", "platform", "proposed",
                   "raceway", "razed"}


def concelho():
    m = gpd.read_file(CAOP)
    return m[m["dtmn"] == "1312"].to_crs(CRS).geometry.iloc[0]  # 1312 = Porto


def edificios(poly):
    destino = DADOS / "edificios_osm.gpkg"
    if destino.exists():
        print("já existe:", destino)
        return
    wgs = gpd.GeoSeries([poly], crs=CRS).to_crs(4326)
    bbox = tuple(wgs.total_bounds)
    g = gpd.read_file(PBF, layer="multipolygons", bbox=bbox, where="building IS NOT NULL", engine="pyogrio")
    g = g[g.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs(CRS)
    g = g[g.intersects(poly)]
    g = g[["osm_id", "osm_way_id", "building", "name", "other_tags", "geometry"]].reset_index(drop=True)
    g.to_file(destino, driver="GPKG")
    print("edifícios:", len(g), "->", destino)


class _Vias(osmium.SimpleHandler):
    def __init__(self, bbox_wgs):
        super().__init__()
        self.b = bbox_wgs
        self.vias = []  # (lista de (id, lon, lat), highway)

    def way(self, w):
        t = w.tags
        h = t.get("highway")
        if not h or h in EXCLUIR_HIGHWAY:
            return
        if t.get("foot") == "no" or t.get("access") in ("private", "no") and t.get("foot") not in ("yes", "designated", "permissive"):
            return
        if t.get("service") == "private" or t.get("area") == "yes":
            return
        pts = []
        for n in w.nodes:
            if not n.location.valid():
                return
            pts.append((n.ref, n.location.lon, n.location.lat))
        x0, y0, x1, y1 = self.b
        if any(x0 <= lo <= x1 and y0 <= la <= y1 for _, lo, la in pts):
            self.vias.append((pts, h))


def rede(poly):
    destino = DADOS / "rede_pedonal.pkl"
    if destino.exists():
        print("já existe:", destino)
        return
    grande = gpd.GeoSeries([poly.buffer(1000)], crs=CRS).to_crs(4326)
    h = _Vias(tuple(grande.total_bounds))
    h.apply_file(str(PBF), locations=True)  # locations=True resolve as coordenadas dos nós das vias
    print("vias pedonais na caixa:", len(h.vias))
    tr = Transformer.from_crs(4326, 3763, always_xy=True)
    G = nx.Graph()
    for pts, hw in h.vias:
        xs, ys = tr.transform([p[1] for p in pts], [p[2] for p in pts])
        for (nid, _, _), x, y in zip(pts, xs, ys):
            if nid not in G:
                G.add_node(nid, x=float(x), y=float(y))
        for a, b, (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:], zip(xs[:-1], ys[:-1]), zip(xs[1:], ys[1:])):
            L = float(np.hypot(xb - xa, yb - ya))
            if a[0] != b[0] and (not G.has_edge(a[0], b[0]) or G[a[0]][b[0]]["length"] > L):
                G.add_edge(a[0], b[0], length=L, highway=hw)
    # só a maior componente ligada; o resto são ilhas (pátios, vias cortadas pela caixa)
    maior = max(nx.connected_components(G), key=len)
    print("nós:", G.number_of_nodes(), "-> maior componente:", len(maior))
    G = G.subgraph(maior).copy()
    with open(destino, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
    print("rede: nós", G.number_of_nodes(), "arestas", G.number_of_edges(), "->", destino)


if __name__ == "__main__":
    if not PBF.exists():
        raise SystemExit(f"falta {PBF} (ver docstring)")
    p = concelho()
    print("área do concelho (km²):", round(p.area / 1e6, 2))
    edificios(p)
    rede(p)
