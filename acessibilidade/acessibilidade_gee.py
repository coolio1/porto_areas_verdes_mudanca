"""Funções GEE partilhadas — Sentinel-2 e download helpers."""

import ee
import requests
import os
import io
import time
import numpy as np
from PIL import Image

BANDS = ["B3", "B4", "B8", "B11", "SCL"]


def getS2col(start, end, porto):
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(porto)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .select(BANDS)
    )

    def process(img):
        scl = img.select("SCL")
        clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(2)).Or(scl.eq(11))
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
        ndbi = img.normalizedDifference(["B11", "B8"]).rename("ndbi")
        nir_green = img.select("B8").divide(img.select("B3").max(1)).rename("nir_green")
        green = img.select("B3").rename("green")
        return ndvi.addBands(ndbi).addBands(nir_green).addBands(green).updateMask(clear)

    return s2.map(process)


def getComposite(years, porto):
    all_col = ee.ImageCollection([])
    spring_col = ee.ImageCollection([])
    for year in years:
        full = getS2col(f"{year}-05-01", f"{year}-10-31", porto)
        all_col = all_col.merge(full)
        spring = getS2col(f"{year}-05-15", f"{year}-06-30", porto)
        spring_col = spring_col.merge(spring)
    median = all_col.median().clip(porto)
    spring_ndvi = (
        spring_col.select("ndvi")
        .reduce(ee.Reducer.percentile([15]))
        .rename("spring_ndvi")
        .clip(porto)
    )
    ndvi_min = (
        all_col.select("ndvi")
        .reduce(ee.Reducer.percentile([10]))
        .rename("ndvi_min")
        .clip(porto)
    )
    return median.addBands(spring_ndvi).addBands(ndvi_min)


def classify(ndvi, ndbi, nirgreen, green, spring_ndvi, ndvi_min, esaBuilt):
    b3_ok = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isTreeStrict = (
        ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.7))
        .And(ndvi_min.gte(0.3))
        .And(nirgreen.gte(4))
        .And(b3_ok)
    )
    b3_ok_mixed = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isMixed = (
        ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.5))
        .And(ndvi_min.gte(0.2))
        .And(b3_ok_mixed)
        .And(isTreeStrict.Not())
    )
    isTree = isTreeStrict.Or(isMixed)
    clear_built = ndvi.lt(0.2).And(ndbi.gte(-0.1))
    esa_tiebreak = ndvi.gte(0.2).And(ndvi.lt(0.35)).And(esaBuilt)
    isBuilt = clear_built.Or(esa_tiebreak)
    isSolo = isTree.Not().And(isBuilt.Not())
    return isTree, isBuilt, isSolo


def download_mono_layer(image, color_hex, filename, porto, dim, layers_dir):
    """Download camada monocromática com transparência."""
    filepath = os.path.join(layers_dir, filename)
    if os.path.exists(filepath):
        print(f"  {filename} já existe, a saltar...")
        return filepath
    vis = image.visualize(palette=[color_hex], min=0, max=1)
    for attempt in range(3):
        url = vis.getThumbURL({"region": porto, "dimensions": dim, "format": "png"})
        print(f"  A descarregar {filename}...")
        r = requests.get(url)
        try:
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            break
        except Exception as e:
            print(f"  Tentativa {attempt + 1} falhou: {e}")
            if attempt < 2:
                time.sleep(3)
            else:
                return None
    arr = np.array(img)
    dark = (arr[:, :, 0] < 10) & (arr[:, :, 1] < 10) & (arr[:, :, 2] < 10)
    arr[dark, 3] = 0
    Image.fromarray(arr).save(filepath)
    print(f"  {filename} guardado ({os.path.getsize(filepath) // 1024} KB)")
    return filepath


def download_greyscale(image, dim, min_val, max_val, label, porto):
    """Download imagem GEE como array numpy float via greyscale PNG."""
    vis = image.unmask(0).visualize(
        min=min_val, max=max_val, palette=["000000", "FFFFFF"]
    )
    for attempt in range(3):
        url = vis.getThumbURL({"region": porto, "dimensions": dim, "format": "png"})
        print(f"  A descarregar {label} ({dim}px)...")
        r = requests.get(url)
        try:
            img = Image.open(io.BytesIO(r.content)).convert("L")
            arr = np.array(img).astype(np.float64) / 255.0 * max_val
            print(f"  {label}: {arr.shape}, min={arr.min():.1f}, max={arr.max():.1f}")
            return arr
        except Exception as e:
            print(f"  Tentativa {attempt + 1} falhou: {e}")
            if attempt < 2:
                time.sleep(3)
    return None
