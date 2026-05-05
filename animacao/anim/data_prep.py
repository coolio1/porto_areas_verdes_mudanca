"""Data preparation: generate river mask (GEE) and road lines (OSM)."""
import ee
import os
import io
import requests
import numpy as np
from PIL import Image, ImageDraw
from dotenv import load_dotenv
from .config import LON_MIN, LON_MAX, LAT_MIN, LAT_MAX, LAYERS_DIR, ROAD_COLOR


def export_river_mask():
    """Export JRC Global Surface Water river mask as PNG."""
    output_path = os.path.join(LAYERS_DIR, 'rio.png')
    if os.path.exists(output_path):
        print(f'  Rio mask already exists: {output_path}')
        return output_path

    load_dotenv(os.path.join(os.path.dirname(LAYERS_DIR), '.env'))
    GEE_PROJECT = os.environ["GEE_PROJECT"]
    ee.Initialize(project=GEE_PROJECT)

    porto = ee.Geometry.Rectangle([LON_MIN, LAT_MIN, LON_MAX, LAT_MAX])

    # JRC Global Surface Water - occurrence > 50% = permanent water
    jrc_water = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence')
    water_mask = jrc_water.unmask(0).gt(50).clip(porto)

    # Export as PNG matching existing mask dimensions (2048x769)
    url = water_mask.getThumbURL({
        'min': 0, 'max': 1,
        'dimensions': '2048x769',
        'region': porto,
        'format': 'png',
        'palette': ['00000000', '000000FF'],
    })

    print(f'  Downloading river mask...')
    r = requests.get(url, timeout=60)
    r.raise_for_status()

    img = Image.open(io.BytesIO(r.content)).convert('RGBA')
    img.save(output_path)
    print(f'  Saved: {output_path} ({img.size[0]}x{img.size[1]})')
    return output_path


def download_roads():
    """Download road network from OSM Overpass API and render as PNG."""
    output_path = os.path.join(LAYERS_DIR, 'estradas.png')
    if os.path.exists(output_path):
        print(f'  Roads mask already exists: {output_path}')
        return output_path

    bbox = f"{LAT_MIN},{LON_MIN},{LAT_MAX},{LON_MAX}"
    query = f"""
    [out:json][timeout:60];
    (
      way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]({bbox});
    );
    out geom;
    """

    print(f'  Querying OSM Overpass for roads...')
    r = requests.post(
        'https://overpass-api.de/api/interpreter',
        data={'data': query},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()

    W, H = 2048, 769
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def lonlat_to_px(lon, lat):
        x = (lon - LON_MIN) / (LON_MAX - LON_MIN) * W
        y = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * H
        return int(x), int(y)

    road_widths = {
        'motorway': 3, 'trunk': 3,
        'primary': 2, 'secondary': 2,
        'tertiary': 1,
    }

    n_roads = 0
    for element in data.get('elements', []):
        if element['type'] != 'way' or 'geometry' not in element:
            continue
        highway = element.get('tags', {}).get('highway', 'tertiary')
        width = road_widths.get(highway, 1)
        points = [lonlat_to_px(n['lon'], n['lat']) for n in element['geometry']]
        if len(points) >= 2:
            draw.line(points, fill=(*ROAD_COLOR, 200), width=width)
            n_roads += 1

    img.save(output_path)
    print(f'  Saved: {output_path} ({n_roads} roads)')
    return output_path


if __name__ == '__main__':
    print('Data preparation:')
    print('\n1. River mask (GEE)...')
    export_river_mask()
    print('\n2. Roads (OSM)...')
    download_roads()
    print('\nDone!')
