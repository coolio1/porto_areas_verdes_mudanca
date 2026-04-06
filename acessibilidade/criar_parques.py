"""
Construção do GeoJSON dos 20 parques/jardins públicos oficiais do Porto.

Fonte primária: OpenStreetMap (Overpass API) — contornos nomeados
Fallback: PDM (GeoPackage) para Frente Atlântica; centróide+buffer para parques sem OSM
Metadados: ambiente.cm-porto.pt/estrutura-verde/parques-jardins

Output: parques_porto.geojson (EPSG:4326)
"""

import json
import math
import os
import time
import requests
import geopandas as gpd
from shapely.geometry import mapping, Polygon, Point
from shapely.ops import unary_union

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(SCRIPT_DIR, "parques_porto.geojson")
PDM_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "CLC", "po_cqs.gpkg")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ===== Definição dos 20 parques oficiais (CMP) =====
# osm_type: 'way' ou 'relation'
# osm_id: ID no OpenStreetMap (verificado 2026-04-06)
# Para parques sem OSM: centroid_lat/lon para buffer circular
PARQUES = [
    {
        "nome": "Parque da Cidade",
        "tipo": "parque",
        "osm_type": "way",
        "osm_id": 559610396,
        "area_ha": 80,
        "horario_verao": "07:00–00:00",
        "horario_inverno": "07:00–22:00",
    },
    {
        "nome": "Parque Oriental",
        "tipo": "parque",
        "osm_type": "relation",
        "osm_id": 14227800,
        "area_ha": 16,
    },
    {
        "nome": "Parque do Covelo",
        "tipo": "parque",
        "osm_type": "way",
        "osm_id": 35540964,
        "area_ha": 7,
        "horario_verao": "07:00–20:00",
        "horario_inverno": "07:00–20:00",
    },
    {
        "nome": "Parque de São Roque",
        "tipo": "parque",
        "osm_type": "way",
        "osm_id": 621569208,
    },
    {
        "nome": "Parque da Pasteleira",
        "tipo": "parque",
        "osm_type": "way",
        "osm_id": 40651360,
        "area_ha": 7,
        "horario_verao": "08:00–23:00",
        "horario_inverno": "08:00–20:00",
    },
    {
        "nome": "Parque das Águas",
        "tipo": "parque",
        "osm_type": "way",
        "osm_id": 474858417,
    },
    {
        "nome": "Parque das Virtudes",
        "tipo": "parque",
        "osm_type": "relation",
        "osm_id": 3251867,
    },
    {
        "nome": "Jardim do Passeio Alegre",
        "tipo": "jardim",
        "osm_type": "relation",
        "osm_id": 8521873,
    },
    {
        "nome": "Jardim do Palácio de Cristal",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 244599647,
        "area_ha": 11,
        "horario_verao": "08:00–21:00",
        "horario_inverno": "08:00–19:00",
    },
    {
        "nome": "Jardim da Cordoaria",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 215304932,
        # Nome OSM: "Jardim de João Chagas"
    },
    {
        "nome": "Jardim do Marquês",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 13716207,
        # Nome OSM: "Jardim da Praça do Marquês de Pombal"
    },
    {
        "nome": "Jardim do Carregal",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 233012813,
        # Nome OSM: "Parque do Carregal" (sem tag leisure)
    },
    {
        "nome": "Jardim de Arca d'Água",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 13797641,
    },
    {
        "nome": "Jardim de São Lázaro",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 466224857,
    },
    {
        "nome": "Jardim da Praça da República",
        "tipo": "jardim",
        # Não encontrado no OSM — usar centróide
        "centroid_lat": 41.1492,
        "centroid_lon": -8.6105,
        "buffer_m": 55,
    },
    {
        "nome": "Viveiro Municipal",
        "tipo": "quinta",
        "osm_type": "way",
        "osm_id": 381421687,
        # Tag OSM: landuse=plant_nursery
    },
    {
        "nome": "Quinta de Bonjóia",
        "tipo": "quinta",
        "osm_type": "way",
        "osm_id": 500315125,
    },
    {
        "nome": "Rotunda da Boavista",
        "tipo": "praça",
        "osm_type": "way",
        "osm_id": 13531471,
        # Nome OSM: "Jardim da Praça de Mouzinho de Albuquerque"
    },
    {
        "nome": "Praça da Galiza",
        "tipo": "praça",
        "osm_type": "way",
        "osm_id": 262802860,
    },
    {
        "nome": "Frente Atlântica",
        "tipo": "frente",
        # Zona linear — usar polígonos PDM "Área de frente atlântica e ribeirinha"
        "pdm_category": "frente",
    },
    # --- Parques adicionais (ausentes do site CMP) ---
    {
        "nome": "Parque Central da Asprela",
        "tipo": "parque",
        # 34 ways leisure=park fragmentados no OSM — buscar por bbox
        "osm_bbox_park": (41.175, -8.615, 41.182, -8.60),
        "area_ha": 6,
    },
    {
        "nome": "Parque Urbano da Lapa",
        "tipo": "parque",
        "osm_type": "way",
        "osm_id": 1452005414,
        "area_ha": 1.7,
        # Parque Urbano Dr. Mário Soares, Dez 2024
    },
    {
        "nome": "Jardim Botânico do Porto",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 450874936,
        "area_ha": 4,
    },
    {
        "nome": "Jardim Paulo Vallada",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 35731231,
        # Jardim das Antas
    },
    {
        "nome": "Jardim da Praça do Império",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 165495635,
    },
    {
        "nome": "Alameda das Fontainhas",
        "tipo": "jardim",
        # Miradouro público, não indexado no OSM como leisure
        "centroid_lat": 41.1413,
        "centroid_lon": -8.6040,
        "buffer_m": 60,
    },
    {
        "nome": "Jardim do Homem do Leme",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 478335004,
        # Jardim marítimo na Foz
    },
    {
        "nome": "Jardim da Avenida de Montevideu",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 370626234,
    },
    {
        "nome": "Jardins da Praia de Gondarém",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 551666215,
        # Jardim marítimo (incluído na "Frente Atlântica" no site CMP)
    },
    {
        "nome": "Jardins da Praia do Molhe",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 551666213,
    },
    # --- Espaços gratuitos adicionais ---
    {
        "nome": "Parque da Fundação Eng. António de Almeida",
        "tipo": "parque",
        "osm_type": "way",
        "osm_id": 1019590397,
        # Acesso livre em horário administrativo (dias úteis 09:30-18:30)
    },
    {
        "nome": "Jardins da Casa Allen",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 549960061,
        # Casa e Quinta de Vilar D'Allen — património de interesse público
    },
    {
        "nome": "Parque da Quinta de Lamas",
        "tipo": "parque",
        "osm_type": "way",
        "osm_id": 455315123,
        # Espaço universitário de acesso livre
    },
    {
        "nome": "Jardins da FLUP",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 891088478,
        # Faculdade de Letras — acesso livre sem barreiras
    },
    {
        "nome": "Parque de Requesende",
        "tipo": "parque",
        # 6 ways fragmentados no OSM — buscar por bbox
        "osm_bbox_park": (41.158, -8.642, 41.167, -8.630),
    },
    {
        "nome": "Jardim do Calém e das Sobreiras",
        "tipo": "jardim",
        "osm_ids": [("way", 555827193), ("way", 615952628)],
        # Calém + Sobreiras (marginal fluvial)
    },
    {
        "nome": "Jardim da Corujeira",
        "tipo": "jardim",
        "osm_type": "way",
        "osm_id": 35413298,
    },
    {
        "nome": "Jardim de Teodoro de Sousa",
        "tipo": "jardim",
        # Monte Aventino/Antas — não encontrado no OSM
        "centroid_lat": 41.1565,
        "centroid_lon": -8.588,
        "buffer_m": 50,
    },
]


def fetch_osm_geometries(parques):
    """Buscar geometrias de todos os parques com OSM ID numa única query Overpass."""
    # Recolher todos os IDs (single e multi)
    all_ids = set()
    for p in parques:
        if "osm_ids" in p:
            for osm_type, osm_id in p["osm_ids"]:
                all_ids.add((osm_type, osm_id))
        elif "osm_id" in p:
            all_ids.add((p["osm_type"], p["osm_id"]))

    parts = []
    for osm_type, osm_id in all_ids:
        parts.append(f"{osm_type}({osm_id});")

    if not parts:
        return {}

    query = f"[out:json][timeout:60];({' '.join(parts)});out geom;"
    print(f"  A consultar Overpass API ({len(parts)} elementos)...")

    for attempt in range(3):
        try:
            resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            print(f"  Tentativa {attempt + 1} falhou: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                raise

    # Mapear osm_type/osm_id → geometria Shapely
    geom_map = {}
    for el in data.get("elements", []):
        key = f"{el['type']}/{el['id']}"
        geom = _overpass_element_to_geometry(el)
        if geom is not None:
            geom_map[key] = geom

    print(f"  Obtidas {len(geom_map)} geometrias")
    return geom_map


def _overpass_element_to_geometry(el):
    """Converter um elemento Overpass (com geom) para Shapely Polygon/MultiPolygon."""
    if el["type"] == "way":
        coords = [(n["lon"], n["lat"]) for n in el.get("geometry", [])]
        if len(coords) >= 4 and coords[0] == coords[-1]:
            return Polygon(coords)
        elif len(coords) >= 4:
            # Fechar o polígono
            coords.append(coords[0])
            return Polygon(coords)
        return None

    elif el["type"] == "relation":
        # Extrair outer e inner rings dos members
        outers = []
        inners = []
        for member in el.get("members", []):
            if member.get("type") != "way":
                continue
            coords = [(n["lon"], n["lat"]) for n in member.get("geometry", [])]
            if len(coords) < 3:
                continue
            role = member.get("role", "outer")
            if role == "outer":
                outers.append(coords)
            elif role == "inner":
                inners.append(coords)

        if not outers:
            return None

        # Tentar unir outer rings (podem estar fragmentados)
        from shapely.ops import linemerge, polygonize
        from shapely.geometry import LineString

        # Converter cada outer ring: se fechado, é polígono; senão, tentar merge
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

        if not polygons:
            return None

        # Subtrair inner rings
        result = unary_union(polygons)
        if inners:
            holes = []
            for ring in inners:
                if len(ring) >= 4:
                    if ring[0] != ring[-1]:
                        ring.append(ring[0])
                    holes.append(Polygon(ring))
            if holes:
                result = result.difference(unary_union(holes))

        return result

    return None


def make_buffer_polygon(lat, lon, radius_m):
    """Criar polígono circular a partir de centróide (aproximação em graus)."""
    deg_lat = radius_m / 111320
    deg_lon = radius_m / (111320 * math.cos(math.radians(lat)))
    return (
        Point(lon, lat)
        .buffer(1)
        .affine_transform(
            [deg_lon, 0, 0, deg_lat, lon - deg_lon * lon, lat - deg_lat * lat]
        )
    )


def get_pdm_frente_atlantica():
    """Extrair polígonos PDM da frente atlântica (apenas costa oceânica)."""
    print("  A carregar PDM para Frente Atlântica...")
    gdf = gpd.read_file(PDM_PATH, layer="PO_QSFUNCIONAL_PL").to_crs(epsg=4326)
    # Filtrar APENAS a categoria correcta (não "frente urbana contínua")
    mask = gdf["sc_espaco"].str.contains(
        "frente atlântica", case=False, na=False
    ) | gdf["sc_espaco"].str.contains("frente atlantica", case=False, na=False)
    if mask.sum() == 0:
        print("  AVISO: nenhum polígono PDM de frente atlântica encontrado")
        return None
    frente = gdf[mask]
    # Filtrar para a zona costeira (oeste de -8.63) excluindo zona ribeirinha do Douro
    frente = frente[frente.geometry.representative_point().x < -8.63]
    print(f"  {len(frente)} polígonos PDM de frente atlântica (costa)")
    return unary_union(frente.geometry)


def fetch_osm_bbox_parks(bbox):
    """Buscar todos os ways leisure=park numa bbox e unir."""
    s, w, n, e = bbox
    query = f'[out:json][timeout:30];way["leisure"="park"]({s},{w},{n},{e});out geom;'
    print(f"  A consultar Overpass (parks em bbox {bbox})...")
    time.sleep(5)  # Evitar rate limit após query anterior
    for attempt in range(3):
        try:
            resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=60)
            resp.raise_for_status()
            break
        except Exception as e:
            print(f"  Tentativa {attempt + 1} falhou: {e}")
            if attempt < 2:
                time.sleep(10)
            else:
                raise
    data = resp.json()
    polys = []
    for el in data.get("elements", []):
        g = _overpass_element_to_geometry(el)
        if g:
            polys.append(g)
    if polys:
        print(f"  {len(polys)} fragmentos encontrados")
        merged = unary_union(polys)
        # Buffer+debuffer para fundir fragmentos com pequenos gaps (~5m)
        buf_deg = 5 / 111320  # ~5m em graus
        merged = merged.buffer(buf_deg).buffer(-buf_deg)
        if merged.geom_type == "MultiPolygon":
            # Manter apenas o polígono maior (o parque principal)
            parts = list(merged.geoms)
            merged = max(parts, key=lambda p: p.area)
        return merged
    return None


def calc_area_ha(geom):
    """Calcular área em hectares (projecção UTM 29N para Porto)."""
    gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")
    gdf_utm = gdf.to_crs(epsg=32629)  # UTM 29N
    return gdf_utm.geometry.area.iloc[0] / 10000


def main():
    print("=== Construção da base de parques públicos do Porto ===\n")

    # 1. Buscar geometrias OSM
    osm_parques = [p for p in PARQUES if "osm_id" in p or "osm_ids" in p]
    geom_map = fetch_osm_geometries(osm_parques)

    # 2. Construir features
    features = []
    for p in PARQUES:
        nome = p["nome"]
        geom = None
        fonte = None

        if "osm_bbox_park" in p:
            geom = fetch_osm_bbox_parks(p["osm_bbox_park"])
            if geom:
                fonte = "osm"
            else:
                print(f"  AVISO: {nome} — nenhum park encontrado na bbox")
        elif "osm_ids" in p:
            # Múltiplos ways/relations — unir geometrias
            parts = []
            for osm_type, osm_id in p["osm_ids"]:
                key = f"{osm_type}/{osm_id}"
                g = geom_map.get(key)
                if g:
                    parts.append(g)
            if parts:
                geom = unary_union(parts)
                fonte = "osm"
            else:
                print(f"  AVISO: {nome} — nenhuma geometria OSM encontrada")
        elif "osm_id" in p:
            key = f"{p['osm_type']}/{p['osm_id']}"
            geom = geom_map.get(key)
            if geom:
                fonte = "osm"
            else:
                print(f"  AVISO: {nome} — geometria OSM não encontrada ({key})")

        elif "pdm_category" in p:
            geom = get_pdm_frente_atlantica()
            fonte = "pdm"

        elif "centroid_lat" in p:
            lat, lon = p["centroid_lat"], p["centroid_lon"]
            radius = p.get("buffer_m", 50)
            # Buffer circular simples em graus
            deg_lat = radius / 111320
            deg_lon = radius / (111320 * math.cos(math.radians(lat)))
            geom = Point(lon, lat).buffer(1)
            # Escalar para metros reais
            from shapely import affinity

            geom = affinity.scale(
                Point(lon, lat).buffer(deg_lat),
                xfact=deg_lon / deg_lat,
                yfact=1.0,
                origin=(lon, lat),
            )
            fonte = "manual"

        if geom is None:
            print(f"  ERRO: {nome} — sem geometria, a saltar")
            continue

        # Garantir que é Polygon ou MultiPolygon
        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            print(f"  AVISO: {nome} — tipo inesperado {geom.geom_type}")

        area_calc = calc_area_ha(geom)

        props = {
            "nome": nome,
            "tipo": p["tipo"],
            "area_ha": p.get("area_ha"),
            "area_calc_ha": round(area_calc, 2),
            "fonte": fonte,
            "horario_verao": p.get("horario_verao"),
            "horario_inverno": p.get("horario_inverno"),
        }
        # Remover None
        props = {k: v for k, v in props.items() if v is not None}

        features.append(
            {
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": props,
            }
        )
        print(f"  {nome}: {area_calc:.2f} ha ({fonte})")

    # 3. Gravar GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"\n{len(features)} parques gravados em {OUTPUT}")
    total_ha = sum(f["properties"].get("area_calc_ha", 0) for f in features)
    print(f"Área total calculada: {total_ha:.1f} ha")


if __name__ == "__main__":
    main()
