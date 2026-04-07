"""
Script pontual para adicionar 9 micro-jardins ao parques_porto.geojson
usando a OSM API v0.6 (mais estável que o Overpass).
"""

import json
import math
import os
import time

import geopandas as gpd
import requests
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import unary_union

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_PATH = os.path.join(SCRIPT_DIR, "parques_porto.geojson")
OSM_API = "https://api.openstreetmap.org/api/0.6"

# CAOP para clipar ao Porto
CAOP_PATH = os.path.join(
    os.path.dirname(SCRIPT_DIR),
    "CAOP_Continente_2025-gpkg",
    "CAOP2025_municipios.shp",
)

NOVOS_JARDINS = [
    {"nome": "Jardim de Belém", "tipo": "jardim", "osm_id": 1308725143},
    {"nome": "Jardim Palmira Milheiro", "tipo": "jardim", "osm_id": 1456129791},
    {"nome": "Jardim da Praça de Liège", "tipo": "jardim", "osm_id": 115999890},
    {"nome": "Jardim de Fradelos", "tipo": "jardim", "osm_id": 290578113},
    {"nome": "Jardim do Campo 24 de Agosto", "tipo": "jardim", "osm_id": 27293329},
    {
        "nome": "Jardim de Antero de Quental",
        "tipo": "jardim",
        "centroid_lat": 41.1490,
        "centroid_lon": -8.6175,
        "buffer_m": 30,
    },
    {
        "nome": "Jardim da Praça de Francisco Sá Carneiro",
        "tipo": "jardim",
        "osm_id": 13715723,
    },
    {"nome": "Jardim de Sarah Afonso", "tipo": "jardim", "osm_id": 447731781},
    {"nome": "Jardim do Largo da Paz", "tipo": "jardim", "osm_id": 571754719},
]


def fetch_way_geometry(osm_id):
    """Buscar geometria de um way via OSM API v0.6/way/{id}/full."""
    url = f"{OSM_API}/way/{osm_id}/full.json"
    print(f"    GET {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Extrair nós e construir polígono
    nodes = {}
    way_node_ids = []
    for el in data["elements"]:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
        elif el["type"] == "way" and el["id"] == osm_id:
            way_node_ids = el.get("nodes", [])

    coords = [nodes[nid] for nid in way_node_ids if nid in nodes]
    if len(coords) >= 4 and coords[0] == coords[-1]:
        return Polygon(coords)
    elif len(coords) >= 4:
        coords.append(coords[0])
        return Polygon(coords)
    return None


def make_buffer(lat, lon, radius_m):
    """Buffer circular simples."""
    from shapely import affinity

    deg_lat = radius_m / 111320
    deg_lon = radius_m / (111320 * math.cos(math.radians(lat)))
    return affinity.scale(
        Point(lon, lat).buffer(deg_lat),
        xfact=deg_lon / deg_lat,
        yfact=1.0,
        origin=(lon, lat),
    )


def calc_area_ha(geom):
    """Área em hectares (UTM 29N)."""
    gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
    return gdf.to_crs(epsg=32629).geometry.area.iloc[0] / 10000


def main():
    print("=== Adicionar micro-jardins ao GeoJSON ===\n")

    # Carregar GeoJSON existente
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    nomes_existentes = {ft["properties"]["nome"] for ft in geojson["features"]}
    print(f"  GeoJSON actual: {len(geojson['features'])} parques")

    # Limites do Porto
    print("  A carregar limites do Porto (CAOP)...")
    caop = gpd.read_file(CAOP_PATH).to_crs(epsg=4326)
    porto_boundary = caop[caop["dtmn"] == "1312"].geometry.union_all()

    added = 0
    for j in NOVOS_JARDINS:
        nome = j["nome"]
        if nome in nomes_existentes:
            print(f"  {nome}: já existe, a saltar")
            continue

        print(f"  {nome}:")
        geom = None
        fonte = None

        if "osm_id" in j:
            try:
                geom = fetch_way_geometry(j["osm_id"])
                fonte = "osm"
            except Exception as e:
                print(f"    ERRO OSM API: {e}")
        else:
            geom = make_buffer(j["centroid_lat"], j["centroid_lon"], j["buffer_m"])
            fonte = "manual"

        if geom is None:
            print("    Sem geometria, a saltar")
            continue

        # Clipar ao Porto
        geom = geom.intersection(porto_boundary)
        if geom.is_empty:
            print("    Fora do Porto, a saltar")
            continue
        if geom.geom_type == "GeometryCollection":
            polys = [
                g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")
            ]
            geom = unary_union(polys) if polys else geom

        area_ha = calc_area_ha(geom)
        props = {
            "nome": nome,
            "tipo": j["tipo"],
            "area_calc_ha": round(area_ha, 2),
            "fonte": fonte,
        }
        geojson["features"].append(
            {"type": "Feature", "geometry": mapping(geom), "properties": props}
        )
        print(f"    {area_ha:.2f} ha ({fonte})")
        added += 1
        time.sleep(1)  # Rate limit

    # Gravar
    with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"\n+{added} jardins adicionados → {len(geojson['features'])} parques total")
    total_ha = sum(
        ft["properties"].get("area_calc_ha", 0) for ft in geojson["features"]
    )
    print(f"Área total: {total_ha:.1f} ha")


if __name__ == "__main__":
    main()
