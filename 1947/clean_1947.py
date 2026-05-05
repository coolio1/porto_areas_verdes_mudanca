"""Limpar classificacao 1947 usando mascaras Sentinel e Landsat 1985."""
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import numpy as np
from scipy.ndimage import uniform_filter
import math, os, time

# Bounds
S_LAT = (41.13, 41.19); S_LON = (-8.70, -8.54)

BBOX_3857 = {'xmin': -968578.0, 'ymin': 5031536.0, 'xmax': -950671.0, 'ymax': 5040407.0}
ntx = math.ceil((BBOX_3857['xmax'] - BBOX_3857['xmin']) / 1000)
nty = math.ceil((BBOX_3857['ymax'] - BBOX_3857['ymin']) / 1000)
mx = BBOX_3857['xmin'] + ntx * 1000
my = BBOX_3857['ymax'] - nty * 1000

def m2w(x, y):
    lon = x / 20037508.34 * 180.0
    lat = math.degrees(2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lat, lon

T_LAT = (m2w(0, my)[0], m2w(0, BBOX_3857['ymax'])[0])
T_LON = (m2w(BBOX_3857['xmin'], 0)[1], m2w(mx, 0)[1])

# 1. Carregar 1947 original
print('1. Classificacao 1947 original')
veg_img = np.array(Image.open('layers/uso_1947_vegetacao.png'))
edif_img = np.array(Image.open('layers/uso_1947_edificado.png'))
t_h, t_w = veg_img.shape[:2]
veg_mask = veg_img[:, :, 3] > 0
edif_mask = edif_img[:, :, 3] > 0
muni_mask = veg_mask | edif_mask
print(f'   Veg: {veg_mask.sum():,} ({veg_mask.sum()/muni_mask.sum()*100:.1f}%)')
print(f'   Edif: {edif_mask.sum():,} ({edif_mask.sum()/muni_mask.sum()*100:.1f}%)')

# 2. Reprojectar mask para grid 1947
def reproject(src_mask):
    src_h, src_w = src_mask.shape
    rows = np.arange(t_h)
    cols = np.arange(t_w)
    lats = T_LAT[1] - (rows + 0.5) / t_h * (T_LAT[1] - T_LAT[0])
    lons = T_LON[0] + (cols + 0.5) / t_w * (T_LON[1] - T_LON[0])
    sr = np.clip(((S_LAT[1] - lats) / (S_LAT[1] - S_LAT[0]) * src_h).astype(int), 0, src_h - 1)
    sc = np.clip(((lons - S_LON[0]) / (S_LON[1] - S_LON[0]) * src_w).astype(int), 0, src_w - 1)
    return src_mask[np.ix_(sr, sc)]

# 3. Mascaras de exclusao
print('\n2. Mascaras de exclusao')
veg85 = np.array(Image.open(os.path.join('..', 'layers_historico', 'veg_1985-90.png')).convert('RGBA'))
veg85_r = reproject(veg85[:, :, 3] > 0)
print(f'   Landsat 1985 veg -> {veg85_r.sum():,} px')

arv = np.array(Image.open(os.path.join('..', 'layers', 'uso_arvores.png')))
arv_r = reproject(arv[:, :, 3] > 0)
print(f'   Sentinel arvores -> {arv_r.sum():,} px')

solo = np.array(Image.open(os.path.join('..', 'layers', 'uso_solo.png')))
solo_r = reproject(solo[:, :, 3] > 0)
print(f'   Sentinel solo -> {solo_r.sum():,} px')

rio = np.array(Image.open(os.path.join('..', 'layers_historico', 'rio.png')).convert('RGBA'))
rio_r = reproject(rio[:, :, 3] > 0)
print(f'   Rio -> {rio_r.sum():,} px')

exclusion = veg85_r | arv_r | solo_r
print(f'   Total exclusao: {exclusion.sum():,} px')

# 4. Aplicar
print('\n3. Aplicar exclusao + rio')
edif_clean = edif_mask & ~exclusion & ~rio_r
veg_clean = muni_mask & ~edif_clean & ~rio_r

# 5. Filtro de maioria
print('\n4. Filtro de maioria 15x15')
t0 = time.time()
edif_f = uniform_filter(edif_clean.astype(np.float32), size=15)
edif_final = (edif_f > 0.5) & muni_mask & ~rio_r
veg_final = muni_mask & ~edif_final & ~rio_r

total_valid = veg_final.sum() + edif_final.sum()
print(f'   Veg: {veg_final.sum():,} ({veg_final.sum()/total_valid*100:.1f}%)')
print(f'   Edif: {edif_final.sum():,} ({edif_final.sum()/total_valid*100:.1f}%)')
print(f'   Rio (transparente): {(rio_r & muni_mask).sum():,}')
print(f'   {time.time()-t0:.1f}s')

# 6. Verificacoes
print('\n5. Verificacoes')
valid_area = muni_mask & ~rio_r
gaps = valid_area & ~veg_final & ~edif_final
overlap = veg_final & edif_final
rio_leak = rio_r & (veg_final | edif_final)
print(f'   Buracos: {gaps.sum()}')
print(f'   Sobreposicao: {overlap.sum()}')
print(f'   Rio com cor: {rio_leak.sum()}')
if gaps.sum() > 0 or overlap.sum() > 0 or rio_leak.sum() > 0:
    print('   ERRO - ha problemas!')
else:
    print('   OK - tudo limpo')

# 7. Guardar
print('\n6. Guardar')
for mask, name, color in [(veg_final, 'uso_1947_vegetacao', (34, 139, 34)),
                           (edif_final, 'uso_1947_edificado', (136, 136, 136))]:
    rgba = np.zeros((t_h, t_w, 4), dtype=np.uint8)
    rgba[mask] = [color[0], color[1], color[2], 200]
    path = f'layers/{name}.png'
    Image.fromarray(rgba).save(path, optimize=True)
    print(f'   {name}: {os.path.getsize(path)//1024} KB')

print('\nDONE')
