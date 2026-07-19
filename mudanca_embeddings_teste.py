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
