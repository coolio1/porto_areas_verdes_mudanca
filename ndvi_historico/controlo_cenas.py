"""NDVI de cada cena Landsat (Jun-Set) nos alvos estáveis: construído 1979∩2024 e árvores 1979∩2024.

Uma cena cujo NDVI no construído/árvores se afasta do resto do sensor é atmosfera/névoa/nuvem não mascarada,
não paisagem. Saída: layers_historico/controlo_cenas.csv (uma linha por cena). Corre-se uma vez; a mediana dos
compósitos usa depois só as cenas aprovadas (ver ndvi_historico.py).
"""
import csv
import io
import os
import sys

import ee
import numpy as np
from dotenv import load_dotenv
from PIL import Image
from scipy import ndimage as ndi

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, 'mapa_unico'))
import cobertura_1979 as c79  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(RAIZ), '.env'))
ee.Initialize(project=os.environ['GEE_PROJECT'])
porto = ee.Geometry.Polygon([[[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]])
S, O, N, E = 41.13, -8.70, 41.19, -8.54
W, H = 2048, 769

alfa = lambda p: np.array(Image.open(p))[..., 3] > 0
concelho = alfa(os.path.join(RAIZ, 'layers_historico', 'porto_mask.png'))
g79 = c79.carregar()
m79 = lambda s: np.array(Image.open(io.BytesIO(c79.mascara_png(g79, s, c79.COR_VEG))))[..., 3] > 0
ero = lambda a: ndi.binary_erosion(a, np.ones((3, 3)), iterations=3)
CONSTR = ero(m79(['ABE']) & alfa(os.path.join(RAIZ, 'layers', 'uso_edificado.png'))) & concelho
ARV = ero(m79(['TRS']) & alfa(os.path.join(RAIZ, 'layers', 'uso_arvores.png'))) & concelho


def pontos(mask, passo=5):
    r, c = np.where(mask)
    k = (r % passo == 0) & (c % passo == 0)
    lat = N - (r[k] + 0.5) / H * (N - S)
    lon = O + (c[k] + 0.5) / W * (E - O)
    return ee.FeatureCollection([ee.Feature(ee.Geometry.Point([float(x), float(y)])) for x, y in zip(lon, lat)])


PC, PA = pontos(CONSTR), pontos(ARV, 3)
print('pontos construido', PC.size().getInfo(), 'arvores', PA.size().getInfo(), flush=True)

SENS = {'L5': ('LANDSAT/LT05/C02/T1_L2', 'SR_B4', 'SR_B3'), 'L7': ('LANDSAT/LE07/C02/T1_L2', 'SR_B4', 'SR_B3'),
        'L8': ('LANDSAT/LC08/C02/T1_L2', 'SR_B5', 'SR_B4'), 'L9': ('LANDSAT/LC09/C02/T1_L2', 'SR_B5', 'SR_B4')}
ANOS = {'L5': range(1985, 2012), 'L7': range(1999, 2022), 'L8': range(2013, 2025), 'L9': range(2022, 2025)}


def por_cena(sens, ano):
    col, nir, red = SENS[sens]
    c = ee.ImageCollection(col).filterBounds(porto).filterDate(f'{ano}-06-01', f'{ano}-09-30').filter(ee.Filter.lt('CLOUD_COVER', 40))

    def f(i):
        qa = i.select('QA_PIXEL')
        i = i.updateMask(qa.bitwiseAnd(24).eq(0))
        n = i.select(nir).multiply(0.0000275).add(-0.2)
        r = i.select(red).multiply(0.0000275).add(-0.2)
        v = n.subtract(r).divide(n.add(r)).rename('v')
        mc = v.reduceRegion(ee.Reducer.mean(), PC, 30).get('v')
        ma = v.reduceRegion(ee.Reducer.mean(), PA, 30).get('v')
        nc = v.reduceRegion(ee.Reducer.count(), PC, 30).get('v')
        return ee.Feature(None, {'id': i.get('system:index'), 'data': i.date().format('YYYY-MM-dd'), 'cc': i.get('CLOUD_COVER'),
                                 'construido': mc, 'arvores': ma, 'n_constr': nc})
    return [x['properties'] for x in c.map(f).getInfo()['features']]


# Uso: sem argumentos refaz tudo; `controlo_cenas.py L7:1999:2012` mede so esse sensor e intervalo e ANEXA ao CSV.
ANEXAR = len(sys.argv) > 1
if ANEXAR:
    _s, _a, _b = sys.argv[1].split(':')
    SENS = {_s: SENS[_s]}
    ANOS = {_s: range(int(_a), int(_b) + 1)}

linhas = []
for s in SENS:
    for a in ANOS[s]:
        try:
            r = por_cena(s, a)
        except Exception as e:
            print('falhou', s, a, str(e)[:100], flush=True)
            continue
        for x in r:
            x['sensor'] = s
        linhas += r
        print(s, a, len(r), flush=True)
cols = ['sensor', 'data', 'id', 'cc', 'construido', 'arvores', 'n_constr']
with open(os.path.join(RAIZ, 'layers_historico', 'controlo_cenas.csv'), 'a' if ANEXAR else 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, cols, extrasaction='ignore')
    if not ANEXAR:
        w.writeheader()
    w.writerows(linhas)
print('guardado', len(linhas))
