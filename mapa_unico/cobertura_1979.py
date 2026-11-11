"""Converte o shapefile Land cover 1979 (Filipa Guilherme) para o tema Histórico.

Entrada : Land_cover_1979 - dados de Filipa Guilherme/Land_cover_1979.shp (EPSG:3763)
Saída   : (1) GeoJSON compacto em WGS84 (polígonos reparados e simplificados);
          (2) duas máscaras raster na grelha das épocas Landsat (vegetação, edificado).
O .shp.xml nunca é lido nem publicado (contém caminhos pessoais).
"""

import io
from pathlib import Path

import geopandas as gpd
import numpy as np
from PIL import Image
from shapely.validation import make_valid

RAIZ = Path(__file__).resolve().parent.parent
SHP = RAIZ / "Land_cover_1979 - dados de Filipa Guilherme" / "Land_cover_1979.shp"

# sigla -> (nome em português, nome original no ficheiro)
CLASSES = {
    "ABE": "Elementos artificiais (construído)",
    "TRS": "Árvores e arbustos",
    "HER": "Herbáceas",
    "SPV": "Vegetação esparsa (terrestre)",
    "AQU": "Vegetação esparsa (aquática)",
}
TOLERANCIA_M = 8.0  # simplificação em metros (EPSG:3763); 3 m = 2,5 MB, 8 m = 1,4 MB
CASAS = 5  # casas decimais das coordenadas (~1 m)

# grelha das épocas Landsat (layers_historico): 2048 x 769 sobre estes limites
GRELHA_BOUNDS = (41.13, -8.7, 41.19, -8.54)  # lat_s, lon_o, lat_n, lon_e
GRELHA_WH = (2048, 769)
COR_VEG = (0, 255, 0, 255)
COR_EDIF = (196, 168, 130, 255)


def _poligonos(geom):
    return [geom] if geom.geom_type == "Polygon" else list(geom.geoms)


def carregar() -> gpd.GeoDataFrame:
    g = gpd.read_file(SHP, encoding="utf-8")
    g["geometry"] = g.geometry.apply(lambda x: make_valid(x) if not x.is_valid else x)
    g["ha"] = g.geometry.area / 1e4
    return g


def geojson(g: gpd.GeoDataFrame) -> dict:
    s = g.copy()
    s["geometry"] = s.geometry.simplify(TOLERANCIA_M, preserve_topology=True)
    s = s.to_crs(4326)
    feats = []
    for _, r in s.iterrows():
        polis = [
            p
            for p in _poligonos(r.geometry)
            if p.geom_type == "Polygon" and not p.is_empty
        ]
        if not polis:
            continue
        coords = [
            [
                [[round(x, CASAS), round(y, CASAS)] for x, y in a.coords]
                for a in [p.exterior, *p.interiors]
            ]
            for p in polis
        ]
        feats.append(
            {
                "type": "Feature",
                "properties": {"c": r["LC_1979_ab"], "ha": round(float(r["ha"]), 2)},
                "geometry": {"type": "MultiPolygon", "coordinates": coords},
            }
        )
    return {"type": "FeatureCollection", "features": feats}


def mascara_png(g: gpd.GeoDataFrame, siglas, cor) -> bytes:
    """Rasteriza as classes `siglas` na grelha das épocas (alfa 255 onde há classe)."""
    lat_s, lon_o, lat_n, lon_e = GRELHA_BOUNDS
    w, h = GRELHA_WH
    # rasterio.rasterize (all_touched=False): sem o contorno que o contorno do polígono que o PIL acrescenta e com
    # os buracos de cada polígono tratados na própria geometria (sem apagar polígonos vizinhos)
    from rasterio.features import rasterize
    from rasterio.transform import from_bounds

    w84 = g[g["LC_1979_ab"].isin(siglas)].to_crs(4326)
    a = rasterize(
        [(geom, 255) for geom in w84.geometry if not geom.is_empty],
        out_shape=(h, w),
        transform=from_bounds(lon_o, lat_s, lon_e, lat_n, w, h),
        fill=0,
        all_touched=False,
        dtype="uint8",
    )
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[a > 0] = cor
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


if __name__ == "__main__":
    import json

    g = carregar()
    gj = geojson(g)
    n = len(json.dumps(gj, separators=(",", ":")))
    print("polígonos:", len(gj["features"]), "| GeoJSON:", n // 1024, "KB")
    print(
        "área por classe (ha):", g.groupby("LC_1979_ab")["ha"].sum().round(1).to_dict()
    )
    print("veg PNG:", len(mascara_png(g, ["TRS", "HER"], COR_VEG)) // 1024, "KB")
    print("edif PNG:", len(mascara_png(g, ["ABE"], COR_EDIF)) // 1024, "KB")
