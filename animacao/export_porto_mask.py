"""Exporta mascara preenchida do municipio do Porto via GEE."""
import ee
import os
import requests
import io
import numpy as np
from PIL import Image
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

LON_MIN, LON_MAX = -8.70, -8.54
LAT_MIN, LAT_MAX = 41.13, 41.19
porto_bbox = ee.Geometry.Rectangle([LON_MIN, LAT_MIN, LON_MAX, LAT_MAX])

# CAOP 2025 - municipio do Porto
municipios = ee.FeatureCollection(f'projects/{GEE_PROJECT}/assets/CAOP2025_municipios')
porto_muni = municipios.filter(ee.Filter.eq('municipio', 'Porto'))

# Pintar: 1 dentro do Porto, 0 fora
porto_raster = ee.Image.constant(0).paint(porto_muni, 1).clip(porto_bbox)

# Exportar como PNG — branco dentro, preto fora
url = porto_raster.getThumbURL({
    'min': 0, 'max': 1,
    'dimensions': '2048x769',
    'region': porto_bbox,
    'format': 'png',
    'palette': ['000000', 'FFFFFF'],
})

print('A descarregar mascara do Porto...')
r = requests.get(url, timeout=60)
r.raise_for_status()

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'layers_historico', 'porto_mask.png')
img = Image.open(io.BytesIO(r.content)).convert('RGB')
arr = np.array(img)

# Mascara: pixels brancos = dentro do Porto
mask = arr[:, :, 0] > 127
print(f'Pixels dentro do Porto: {mask.sum()} / {mask.size} ({mask.sum()/mask.size*100:.1f}%)')

# Converter para RGBA: branco opaco dentro, transparente fora
rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
rgba[mask] = [0, 0, 0, 255]  # preto opaco dentro
img_out = Image.fromarray(rgba, 'RGBA')
img_out.save(output_path)
print(f'Guardado: {output_path} ({img_out.size[0]}x{img_out.size[1]})')
