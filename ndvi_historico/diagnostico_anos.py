"""Diagnóstico: % de vegetação (NDVI >= limiar) do concelho do Porto ANO A ANO (Jun-Set, mediana),
para ver quanto da série por épocas é variação de ano (seca/sensor) e não mudança real.
Mesmo método do ndvi_historico.py (L5; L8/L9 harmonizados a TM por Roy 2016), sem normalização PIF."""
import json
import os

import ee
from dotenv import load_dotenv

load_dotenv(r"C:\Users\quent\OneDrive\Claude\.env")
ee.Initialize(project=os.environ["GEE_PROJECT"])
GP = os.environ["GEE_PROJECT"]
porto = ee.FeatureCollection(f"projects/{GP}/assets/CAOP2025_municipios").filter(ee.Filter.eq("municipio", "Porto")).geometry()


def mask_l(img, nuvem=3, sombra=4):
    qa = img.select("QA_PIXEL")
    return img.updateMask(qa.bitwiseAnd(1 << nuvem).eq(0)).updateMask(qa.bitwiseAnd(1 << sombra).eq(0))


def ndvi_l5(img):
    img = mask_l(img)
    nir = img.select("SR_B4").multiply(0.0000275).add(-0.2)
    red = img.select("SR_B3").multiply(0.0000275).add(-0.2)
    return nir.subtract(red).divide(nir.add(red)).rename("ndvi").clamp(-1, 1)


def ndvi_l8(img):
    img = mask_l(img)
    nir = img.select("SR_B5").multiply(0.0000275).add(-0.2).multiply(0.9785).add(-0.0010)
    red = img.select("SR_B4").multiply(0.0000275).add(-0.2).multiply(0.9585).add(-0.0002)
    return nir.subtract(red).divide(nir.add(red)).rename("ndvi").clamp(-1, 1)


def ano(y):
    ini, fim = f"{y}-06-01", f"{y}-09-30"
    if y <= 2011:
        col = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").filterBounds(porto).filterDate(ini, fim).filter(ee.Filter.lt("CLOUD_COVER", 40)).map(ndvi_l5)
        sensor = "L5"
    else:
        c8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(porto).filterDate(ini, fim).filter(ee.Filter.lt("CLOUD_COVER", 40))
        c9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(porto).filterDate(ini, fim).filter(ee.Filter.lt("CLOUD_COVER", 40))
        col = c8.merge(c9).map(ndvi_l8)
        sensor = "L8/9"
    n = col.size().getInfo()
    if n == 0:
        return {"ano": y, "sensor": sensor, "cenas": 0}
    m = col.median()
    out = {"ano": y, "sensor": sensor, "cenas": n}
    r = ee.Image.cat([m.gte(0.20).rename("v20"), m.gte(0.25).rename("v25"), m.gte(0.30).rename("v30"), m.rename("ndvi")]) \
        .reduceRegion(ee.Reducer.mean(), porto, 30, maxPixels=1e9).getInfo()
    out.update({k: round(100 * v, 1) if k.startswith("v") else round(v, 3) for k, v in r.items() if v is not None})
    return out


res = []
for y in list(range(1985, 2012)) + list(range(2013, 2025)):
    try:
        res.append(ano(y))
    except Exception as e:  # noqa: BLE001
        res.append({"ano": y, "erro": str(e)[:80]})
    print(res[-1], flush=True)
open(r"C:\Users\quent\AppData\Local\Temp\claude\d5c9edcf14c0610a\92e77ca8-9abe-4a35-a2f7-46b5de3f5266\scratchpad\diag_anos.json", "w").write(json.dumps(res))
