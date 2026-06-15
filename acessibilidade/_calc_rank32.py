"""
Script descartável — calcular pop_delta/pct_antes/pct_depois para rank=32 (Aguas Ferreas)
Usa simulação cumulativa na ordem dos ranks.
"""
import json
import numpy as np
from scipy import ndimage
from shapely.geometry import shape
from rasterio.features import rasterize
from rasterio.transform import Affine
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAYERS_DIR = os.path.join(SCRIPT_DIR, "layers")

LON_MIN, LON_MAX = -8.70, -8.54
LAT_MIN, LAT_MAX = 41.13, 41.19
PARK_MIN_AREA_M2 = 4_000

pop_corrected = np.load(os.path.join(LAYERS_DIR, "pop_corrected.npy"))
porto_mask    = np.load(os.path.join(LAYERS_DIR, "porto_mask.npy"))
kernel_300    = np.load(os.path.join(LAYERS_DIR, "kernel_300.npy"))
reach_300     = np.load(os.path.join(LAYERS_DIR, "reach_300.npy"))
pop_500m      = np.load(os.path.join(LAYERS_DIR, "pop_500m.npy"))
params        = np.load(os.path.join(LAYERS_DIR, "calc_params.npz"))
pixel_area_m2 = float(params["pixel_area_m2"])
POP_500M_MIN  = float(params["POP_500M_MIN"])
calc_h, calc_w = int(params["calc_h"]), int(params["calc_w"])

transform = Affine(
    (LON_MAX - LON_MIN) / calc_w, 0, LON_MIN,
    0, -(LAT_MAX - LAT_MIN) / calc_h, LAT_MAX,
)
kernel_300_bool = kernel_300 > 0
habitado = porto_mask & (pop_500m >= POP_500M_MIN)
total_pop = pop_corrected[porto_mask].sum()

coberto = reach_300 & porto_mask
pop_coberta_actual = pop_corrected[coberto & habitado].sum()
pct_actual = pop_coberta_actual / total_pop * 100
print(f"Baseline: {pct_actual:.1f}%")

with open(os.path.join(SCRIPT_DIR, "candidatos_conversao.geojson"), encoding="utf-8") as f:
    geojson = json.load(f)

feats = sorted(geojson["features"], key=lambda f: f["properties"]["rank"])

# Simular cumulativamente todos os ranks em ordem
coberto_sim = coberto.copy()
for feat in feats:
    p = feat["properties"]
    rank = p["rank"]
    if rank == 32:
        break
    area_m2 = p.get("area_ha", 0) * 10000
    if area_m2 < PARK_MIN_AREA_M2:
        continue
    try:
        geom = shape(feat["geometry"])
        mask = rasterize([(geom, 1)], out_shape=(calc_h, calc_w),
                         transform=transform, fill=0, dtype=np.uint8).astype(bool)
        reach_new = ndimage.binary_dilation(mask, structure=kernel_300_bool)
        coberto_sim |= reach_new & porto_mask
    except Exception as e:
        print(f"  rank={rank} erro: {e}")

pop_coberta_antes = pop_corrected[coberto_sim & habitado].sum()
pct_antes = round(pop_coberta_antes / total_pop * 100, 1)
print(f"Depois de ranks 1-31: {pct_antes}%")

# Agora aplicar rank=32
feat32 = next(f for f in feats if f["properties"]["rank"] == 32)
geom32 = shape(feat32["geometry"])
mask32 = rasterize([(geom32, 1)], out_shape=(calc_h, calc_w),
                   transform=transform, fill=0, dtype=np.uint8).astype(bool)
reach32 = ndimage.binary_dilation(mask32, structure=kernel_300_bool)
coberto_depois = coberto_sim | (reach32 & porto_mask)
pop_coberta_depois = pop_corrected[coberto_depois & habitado].sum()
pct_depois = round(pop_coberta_depois / total_pop * 100, 1)
pop_delta = int(round(pop_coberta_depois - pop_coberta_antes))
print(f"Depois de rank=32: {pct_depois}%  pop_delta={pop_delta}")

# Escrever no GeoJSON
for feat in geojson["features"]:
    if feat["properties"]["rank"] == 32:
        feat["properties"]["pop_delta"] = pop_delta
        feat["properties"]["pct_antes"] = pct_antes
        feat["properties"]["pct_depois"] = pct_depois
        break

with open(os.path.join(SCRIPT_DIR, "candidatos_conversao.geojson"), "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

print("GeoJSON actualizado.")
