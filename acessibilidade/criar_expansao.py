"""
Construção do GeoJSON dos espaços verdes da Estratégia de Expansão (CMP).
Fonte: ambiente.cm-porto.pt/estrutura-verde/estrategia-de-expansao

Output: expansao_verde.geojson (EPSG:4326)
"""

import json
import math
import os
import time

import geopandas as gpd
import requests
from shapely import affinity
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import unary_union

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(SCRIPT_DIR, "expansao_verde.geojson")
OSM_API = "https://api.openstreetmap.org/api/0.6"

CAOP_PATH = os.path.join(
    os.path.dirname(SCRIPT_DIR),
    "CAOP_Continente_2025-gpkg",
    "CAOP2025_municipios.shp",
)

# Espaços da estratégia de expansão CMP
EXPANSAO = [
    {
        "nome": "Ampliação do Parque de Requesende",
        "area_ha": 12,
        "centroid_lat": 41.1600,
        "centroid_lon": -8.6310,
        "buffer_m": 196,
    },
    {
        "nome": "Parque Urbano da Lapa",
        "area_ha": 4,
        "centroid_lat": 41.1510,
        "centroid_lon": -8.6260,
        "buffer_m": 113,
    },
    {
        "nome": "Jardim de Sobreiras",
        "area_ha": 1.8,
        "centroid_lat": 41.1475,
        "centroid_lon": -8.6598,
        "buffer_m": 76,
    },
    {
        "nome": "Parque da Prelada",
        "area_ha": 21,
        "osm_type": "relation",
        "osm_id": 9491850,
    },
    {
        "nome": "Parque das Fontainhas/Carquejeiras",
        "area_ha": 14,
        "centroid_lat": 41.1445,
        "centroid_lon": -8.6020,
        "buffer_m": 211,
    },
    {
        "nome": "Parque das Antas",
        "area_ha": 5,
        "centroid_lat": 41.1620,
        "centroid_lon": -8.5880,
        "buffer_m": 126,
    },
    {
        "nome": "Parque de Noeda",
        "area_ha": 8,
        "centroid_lat": 41.1580,
        "centroid_lon": -8.5820,
        "buffer_m": 160,
    },
    {
        "nome": "Parque de Contumil",
        "area_ha": 7,
        "centroid_lat": 41.1630,
        "centroid_lon": -8.5800,
        "buffer_m": 149,
    },
    {
        "nome": "Parque da Ervilha",
        "area_ha": 6,
        "centroid_lat": 41.1590,
        "centroid_lon": -8.6710,
        "buffer_m": 138,
    },
    {
        "nome": "Parque Desportivo de Ramalde",
        "area_ha": 5,
        "osm_type": "way",
        "osm_id": 753557660,
    },
    {
        "nome": "Parque de Cartes",
        "area_ha": 5,
        "osm_type": "way",
        "osm_id": 1252966415,
    },
    {
        "nome": "Parque Urbano de Aldoar",
        "area_ha": 4,
        "centroid_lat": 41.1680,
        "centroid_lon": -8.6570,
        "buffer_m": 113,
    },
    {
        "nome": "Corredor Verde da Charca de Salgueiros",
        "area_ha": 4,
        "osm_type": "way",
        "osm_id": 448812133,
    },
    {
        "nome": "Jardim frontal à Escola Nicolau Nasoni",
        "area_ha": 4,
        "centroid_lat": 41.1650,
        "centroid_lon": -8.5850,
        "buffer_m": 113,
    },
    {
        "nome": "Jardim da R. de D. Pedro de Meneses",
        "area_ha": 4,
        "centroid_lat": 41.1500,
        "centroid_lon": -8.6380,
        "buffer_m": 113,
    },
    {
        "nome": "Jardim Nun'Alvares",
        "area_ha": 2,
        "centroid_lat": 41.1500,
        "centroid_lon": -8.6350,
        "buffer_m": 80,
    },
    {
        "nome": "Jardim da Vilarinha",
        "area_ha": 2,
        "centroid_lat": 41.1650,
        "centroid_lon": -8.6500,
        "buffer_m": 80,
    },
    {
        "nome": "Jardim Monte da Bela",
        "area_ha": 2,
        "centroid_lat": 41.1548,
        "centroid_lon": -8.5775,
        "buffer_m": 80,
    },
    {
        "nome": "Corredor ribeirinho do Aleixo",
        "area_ha": 1.8,
        # Buffer em vez de polígono OSM (brownfield até à margem do rio)
        "centroid_lat": 41.1515,
        "centroid_lon": -8.6475,
        "buffer_m": 76,
    },
]


def fetch_way_geometry(osm_id):
    """Buscar geometria de um way via OSM API v0.6."""
    url = f"{OSM_API}/way/{osm_id}/full.json"
    print(f"    GET {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    nodes = {}
    way_node_ids = []
    for el in data["elements"]:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
        elif el["type"] == "way" and el["id"] == osm_id:
            way_node_ids = el.get("nodes", [])
    coords = [nodes[nid] for nid in way_node_ids if nid in nodes]
    if len(coords) >= 4:
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        return Polygon(coords)
    return None


def fetch_relation_geometry(osm_id):
    """Buscar geometria de uma relation via OSM API v0.6."""
    url = f"{OSM_API}/relation/{osm_id}/full.json"
    print(f"    GET {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    nodes = {}
    ways = {}
    for el in data["elements"]:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
        elif el["type"] == "way":
            coords = [nodes[nid] for nid in el.get("nodes", []) if nid in nodes]
            ways[el["id"]] = coords
    # Extrair outer rings da relation
    rel = [
        el for el in data["elements"] if el["type"] == "relation" and el["id"] == osm_id
    ]
    if not rel:
        return None
    outers = []
    for member in rel[0].get("members", []):
        if member.get("type") == "way" and member.get("role", "outer") == "outer":
            coords = ways.get(member["ref"], [])
            if coords:
                outers.append(coords)
    if not outers:
        return None
    from shapely.ops import linemerge, polygonize
    from shapely.geometry import LineString

    polygons = []
    open_lines = []
    for ring in outers:
        if len(ring) >= 4 and ring[0] == ring[-1]:
            polygons.append(Polygon(ring))
        elif len(ring) >= 2:
            open_lines.append(LineString(ring))
    if open_lines:
        merged = linemerge(open_lines)
        for poly in polygonize(merged):
            polygons.append(poly)
    return unary_union(polygons) if polygons else None


def make_buffer(lat, lon, radius_m):
    """Buffer circular."""
    deg_lat = radius_m / 111320
    deg_lon = radius_m / (111320 * math.cos(math.radians(lat)))
    return affinity.scale(
        Point(lon, lat).buffer(deg_lat),
        xfact=deg_lon / deg_lat,
        yfact=1.0,
        origin=(lon, lat),
    )


def calc_area_ha(geom):
    gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
    return gdf.to_crs(epsg=32629).geometry.area.iloc[0] / 10000


def main():
    print("=== Estratégia de Expansão — GeoJSON ===\n")

    # Limites do Porto
    print("  A carregar limites do Porto (CAOP)...")
    caop = gpd.read_file(CAOP_PATH).to_crs(epsg=4326)
    porto_boundary = caop[caop["dtmn"] == "1312"].geometry.union_all()

    features = []
    for e in EXPANSAO:
        nome = e["nome"]
        print(f"  {nome}:")
        geom = None
        fonte = None

        if "osm_id" in e:
            try:
                if e["osm_type"] == "relation":
                    geom = fetch_relation_geometry(e["osm_id"])
                else:
                    geom = fetch_way_geometry(e["osm_id"])
                fonte = "osm"
            except Exception as exc:
                print(f"    ERRO: {exc}")
            time.sleep(1)

        if geom is None and "centroid_lat" in e:
            geom = make_buffer(e["centroid_lat"], e["centroid_lon"], e["buffer_m"])
            fonte = "manual"

        if geom is None:
            print("    Sem geometria, a saltar")
            continue

        # Clipar ao Porto
        geom = geom.intersection(porto_boundary)
        if geom.is_empty:
            print("    Fora do Porto")
            continue
        if geom.geom_type == "GeometryCollection":
            polys = [
                g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")
            ]
            geom = unary_union(polys) if polys else geom

        area_ha = calc_area_ha(geom)
        props = {
            "nome": nome,
            "area_ha_planeada": e["area_ha"],
            "area_calc_ha": round(area_ha, 2),
            "fonte": fonte,
        }
        features.append(
            {"type": "Feature", "geometry": mapping(geom), "properties": props}
        )
        print(f"    {area_ha:.2f} ha ({fonte})")

    geojson = {"type": "FeatureCollection", "features": features}
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"\n{len(features)} espaços gravados em {OUTPUT}")
    total = sum(f["properties"]["area_calc_ha"] for f in features)
    print(f"Área total calculada: {total:.1f} ha")


if __name__ == "__main__":
    main()
