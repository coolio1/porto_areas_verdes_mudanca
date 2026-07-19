"""Teste de deteccao de mudanca via embeddings AlphaEarth (Serralves).

Replica a tecnica do sample Google ADK earth-engine-geospatial:
angulo entre embeddings AlphaEarth de anos consecutivos, thresholded.
Calibracao numa area pequena antes de decidir se compensa aplicar ao municipio.
"""
import ee
import os
import io
import math
import base64
import webbrowser
import requests
from PIL import Image as PILImage
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

# Mesma area de teste de test_area.py (Serralves)
LAT, LON = 41.188117, -8.617633
BUFFER = 1500  # meters

point = ee.Geometry.Point([LON, LAT])
area = point.buffer(BUFFER).bounds()

coords = area.coordinates().getInfo()[0]
lons = [c[0] for c in coords]
lats = [c[1] for c in coords]
BOUNDS = [[min(lats), min(lons)], [max(lats), max(lons)]]

print('A testar deteccao de mudanca por embeddings AlphaEarth...')
print(f'  Area: {BUFFER}m em redor de {LAT}N, {abs(LON)}W')
print(f'  Bounds: {BOUNDS}')

# ============================================================
# Embeddings AlphaEarth (GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL)
# Replica a logica de earth-engine-geospatial/earth_engine_geospatial/tools.py
# ============================================================
EMBEDDINGS = ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL')

def year_embedding(year):
    """Mosaic do embedding anual, recortado a area de teste."""
    return (EMBEDDINGS
        .filterBounds(area)
        .filter(ee.Filter.calendarRange(year, year, 'year'))
        .mosaic()
        .clip(area))

def get_angle(img1, img2):
    """Angulo entre dois embeddings (assume-os ja normalizados, tal como o sample original)."""
    return img1.multiply(img2).reduce(ee.Reducer.sum()).acos().rename('angle')

# --- Verificacao rapida: confirmar que o dataset responde para a area de teste ---
print('\nA verificar acesso ao dataset de embeddings...')
img_2020 = year_embedding(2020)
band_names = img_2020.bandNames().getInfo()
print(f'  Bandas do embedding 2020: {len(band_names)} bandas ({band_names[0]}...{band_names[-1]})')
n_images_2020 = (EMBEDDINGS.filterBounds(area)
    .filter(ee.Filter.calendarRange(2020, 2020, 'year')).size().getInfo())
print(f'  Imagens 2020 cobrindo a area de teste: {n_images_2020}')
