"""
Gerar frame estatica de 1947 para a animacao.
Converte a classificacao 1947 para o grid das mascaras historicas (2048x769)
e renderiza usando o mesmo pipeline Cairo da animacao.
"""
import numpy as np
import cairo
import cv2
import os
import math
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from scipy.ndimage import gaussian_filter
from scipy.interpolate import splprep, splev

Image.MAX_IMAGE_PIXELS = None
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAYERS_DIR = os.path.join(SCRIPT_DIR, '..', 'layers_historico')
LAYERS_1947 = os.path.join(SCRIPT_DIR, '..', '1947', 'layers')

# ============================================================
# Converter classificacao 1947 para o grid das mascaras GEE
# ============================================================
# Grid GEE (animacao)
GEE_LON_MIN, GEE_LON_MAX = -8.70, -8.54
GEE_LAT_MIN, GEE_LAT_MAX = 41.13, 41.19
GEE_W, GEE_H = 2048, 769

# Grid 1947 (mosaic bounds em WGS84)
def m3857_to_wgs84(x, y):
    lon = x / 20037508.34 * 180.0
    lat = math.degrees(2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lat, lon

BBOX_3857 = {'xmin': -968578.0, 'ymin': 5031536.0, 'xmax': -950671.0, 'ymax': 5040407.0}
N_TX, N_TY = 18, 9
mosaic_xmax = BBOX_3857['xmin'] + N_TX * 1000
mosaic_ymin = BBOX_3857['ymax'] - N_TY * 1000
M47_LAT_S, M47_LON_W = m3857_to_wgs84(BBOX_3857['xmin'], mosaic_ymin)
M47_LAT_N, M47_LON_E = m3857_to_wgs84(mosaic_xmax, BBOX_3857['ymax'])

print('A converter classificacao 1947 para grid GEE...')

def convert_1947_to_gee(class_name):
    """Converte uma camada 1947 (18432x9216) para o grid GEE (2048x769)."""
    src = np.array(Image.open(os.path.join(LAYERS_1947, f'uso_1947_{class_name}.png')).convert('RGBA'))
    src_mask = src[:, :, 3] > 30  # alpha > 30 = classe presente
    src_h, src_w = src_mask.shape

    # Criar mascara no grid GEE
    gee_mask = np.zeros((GEE_H, GEE_W), dtype=bool)

    for gy in range(GEE_H):
        # Latitude deste pixel GEE
        lat = GEE_LAT_MAX - (gy + 0.5) / GEE_H * (GEE_LAT_MAX - GEE_LAT_MIN)
        # Pixel correspondente no mosaic 1947
        sy = (M47_LAT_N - lat) / (M47_LAT_N - M47_LAT_S) * src_h
        sy = int(np.clip(sy, 0, src_h - 1))

        for gx in range(GEE_W):
            lon = GEE_LON_MIN + (gx + 0.5) / GEE_W * (GEE_LON_MAX - GEE_LON_MIN)
            sx = (lon - M47_LON_W) / (M47_LON_E - M47_LON_W) * src_w
            sx = int(np.clip(sx, 0, src_w - 1))
            gee_mask[gy, gx] = src_mask[sy, sx]

    return gee_mask

edif_mask = convert_1947_to_gee('edificado')
veg_mask = convert_1947_to_gee('vegetacao')
print(f'  Edificado: {edif_mask.sum():,} pixels')
print(f'  Vegetacao: {veg_mask.sum():,} pixels')

# Guardar como RGBA (mesmo formato das mascaras existentes)
for name, mask, color in [('edif_1947', edif_mask, (136, 136, 136)),
                            ('veg_1947', veg_mask, (34, 139, 34))]:
    rgba = np.zeros((GEE_H, GEE_W, 4), dtype=np.uint8)
    rgba[mask] = [color[0], color[1], color[2], 200]
    path = os.path.join(LAYERS_DIR, f'{name}.png')
    Image.fromarray(rgba).save(path)
    print(f'  {path} ({os.path.getsize(path)//1024} KB)')

# ============================================================
# Renderizar frame 1947 (mesmo estilo da animacao)
# ============================================================
print('\nA renderizar frame...')

# Carregar mascaras fixas
def load_mask(fp):
    return (np.array(Image.open(fp).convert('RGBA'))[:, :, 3] > 30).astype(bool)

muni = load_mask(os.path.join(LAYERS_DIR, 'porto_mask.png'))
muni_out_mask = load_mask(os.path.join(LAYERS_DIR, 'municipios.png'))
rio_mask = load_mask(os.path.join(LAYERS_DIR, 'rio.png')) & muni

# Aplicar mascara do municipio
edif_mask = edif_mask & muni
veg_mask = veg_mask & muni

LON_MIN, LON_MAX = GEE_LON_MIN, GEE_LON_MAX
LAT_MIN, LAT_MAX = GEE_LAT_MIN, GEE_LAT_MAX
COS_LAT = np.cos(np.radians((LAT_MIN + LAT_MAX) / 2))

EDIF_1947_COLOR = (60, 42, 24)  # castanho muito escuro (pre-1947)
VEG_COLOR = (34, 140, 34)
RIVER_COLOR = (25, 60, 200)
BG_COLOR = (222, 216, 198)
MUNI_LINE_COLOR = (20, 20, 20)

TOPONYMS = [
    ("FOZ DO DOURO", -8.678, 41.150), ("NEVOGILDE", -8.660, 41.163),
    ("ALDOAR", -8.662, 41.173), ("RAMALDE", -8.643, 41.175),
    ("PARANHOS", -8.608, 41.178), ("CAMPANHA", -8.568, 41.162),
    ("BONFIM", -8.590, 41.157), ("CEDOFEITA", -8.628, 41.160),
    ("MASSARELOS", -8.643, 41.148), ("LORDELO", -8.653, 41.157),
    ("SE", -8.610, 41.142), ("MIRAGAIA", -8.627, 41.143),
]

gee_h, gee_w = GEE_H, GEE_W

# Crop ao municipio
rows = np.any(muni, axis=1)
cols = np.any(muni, axis=0)
rmin, rmax = np.where(rows)[0][[0, -1]]
cmin, cmax = np.where(cols)[0][[0, -1]]
mg = 20
rmin = max(0, rmin - mg)
rmax = min(gee_h, rmax + mg + 1)
cmin = max(0, cmin - mg)
cmax = min(gee_w, cmax + mg + 1)
crop_h = rmax - rmin
crop_w = cmax - cmin

SF = 5
scale_x = 1540 * SF / crop_w
scale_y = scale_x / COS_LAT
if int(crop_h * scale_y) > 1080 * SF:
    scale_y = 1080 * SF / crop_h
    scale_x = scale_y * COS_LAT
map_w = int(crop_w * scale_x)
map_h = int(crop_h * scale_y)
map_w += map_w % 2
map_h += map_h % 2

# Vectorizar
def smooth_ring(coords):
    pts = np.array(coords)
    if len(pts) < 6:
        return pts
    if np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    if len(pts) < 6:
        return np.vstack([pts, pts[0:1]])
    perim = np.sum(np.sqrt(np.sum(np.diff(pts, axis=0)**2, axis=1)))
    n = max(20, min(200, int(perim / 3)))
    s = max(0, len(pts) * 0.5)
    try:
        tck, u = splprep([pts[:, 0], pts[:, 1]], s=s, per=True, k=3)
        x, y = splev(np.linspace(0, 1, n), tck)
        r = np.column_stack([x, y])
        return np.vstack([r, r[0:1]])
    except Exception:
        return np.vstack([pts, pts[0:1]])

def smooth_ring_light(coords):
    pts = np.array(coords)
    if len(pts) < 6:
        return pts
    if np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    if len(pts) < 6:
        return np.vstack([pts, pts[0:1]])
    perim = np.sum(np.sqrt(np.sum(np.diff(pts, axis=0)**2, axis=1)))
    n = max(20, min(300, int(perim / 2)))
    s = max(0, len(pts) * 0.05)
    try:
        tck, u = splprep([pts[:, 0], pts[:, 1]], s=s, per=True, k=3)
        x, y = splev(np.linspace(0, 1, n), tck)
        r = np.column_stack([x, y])
        return np.vstack([r, r[0:1]])
    except Exception:
        return np.vstack([pts, pts[0:1]])

def mask_to_polys(mask, stol=1.5):
    cr = mask[rmin:rmax, cmin:cmax].astype(np.float32)
    cr = gaussian_filter(cr, sigma=1.0)
    b = (cr > 0.35).astype(np.uint8) * 255
    cs, hi = cv2.findContours(b, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if not cs or hi is None:
        return MultiPolygon()
    hi = hi[0]
    polys = []
    for i, c in enumerate(cs):
        if hi[i][3] != -1 or len(c) < 4:
            continue
        p = c.squeeze().astype(np.float64)
        if p.ndim != 2 or p.shape[0] < 4:
            continue
        p[:, 0] *= scale_x
        p[:, 1] *= scale_y
        hs = []
        ch = hi[i][2]
        while ch != -1:
            h = cs[ch].squeeze().astype(np.float64)
            if h.ndim == 2 and h.shape[0] >= 4:
                h[:, 0] *= scale_x
                h[:, 1] *= scale_y
                hs.append(h.tolist())
            ch = hi[ch][0]
        try:
            pg = Polygon(p.tolist(), hs)
            if pg.is_valid and pg.area > 10:
                pg = pg.simplify(stol, preserve_topology=True)
                if not pg.is_empty:
                    polys.append(pg)
        except Exception:
            continue
    if not polys:
        return MultiPolygon()
    m = unary_union(polys)
    if isinstance(m, Polygon):
        m = MultiPolygon([m])
    elif not isinstance(m, MultiPolygon):
        return MultiPolygon()
    return m

def mask_to_polys_upscale(mask, stol=1.5, upscale=8, sigma=None):
    cr = mask[rmin:rmax, cmin:cmax].astype(np.uint8)
    up = cv2.resize(cr, (cr.shape[1] * upscale, cr.shape[0] * upscale),
                    interpolation=cv2.INTER_NEAREST)
    if sigma is None:
        sigma = upscale * 0.3
    up_f = gaussian_filter(up.astype(np.float32), sigma=sigma)
    binary = (up_f > 0.4).astype(np.uint8) * 255
    contours, hier = cv2.findContours(binary, cv2.RETR_CCOMP,
                                      cv2.CHAIN_APPROX_SIMPLE)
    if not contours or hier is None:
        return MultiPolygon()
    hier = hier[0]
    polys = []
    asx = scale_x / upscale
    asy = scale_y / upscale
    for i, cnt in enumerate(contours):
        if hier[i][3] != -1 or len(cnt) < 4:
            continue
        pts = cnt.squeeze().astype(np.float64)
        if pts.ndim != 2 or pts.shape[0] < 4:
            continue
        pts[:, 0] *= asx
        pts[:, 1] *= asy
        holes = []
        ch = hier[i][2]
        while ch != -1:
            h = contours[ch].squeeze().astype(np.float64)
            if h.ndim == 2 and h.shape[0] >= 4:
                h[:, 0] *= asx
                h[:, 1] *= asy
                holes.append(h.tolist())
            ch = hier[ch][0]
        try:
            pg = Polygon(pts.tolist(), holes)
            if pg.is_valid and pg.area > 5:
                pg = pg.simplify(stol, preserve_topology=True)
                if not pg.is_empty:
                    polys.append(pg)
        except Exception:
            continue
    return MultiPolygon(polys) if polys else MultiPolygon()

def draw_sp(ctx, poly):
    if poly.is_empty:
        return
    se = smooth_ring(list(poly.exterior.coords))
    if len(se) < 3:
        return
    ctx.move_to(se[0][0], se[0][1])
    for x, y in se[1:]:
        ctx.line_to(x, y)
    ctx.close_path()
    for hole in poly.interiors:
        sh = smooth_ring(list(hole.coords))
        if len(sh) < 3:
            continue
        ctx.move_to(sh[0][0], sh[0][1])
        for x, y in sh[1:]:
            ctx.line_to(x, y)
        ctx.close_path()

def draw_sp_light(ctx, poly):
    if poly.is_empty:
        return
    se = smooth_ring_light(list(poly.exterior.coords))
    if len(se) < 3:
        return
    ctx.move_to(se[0][0], se[0][1])
    for x, y in se[1:]:
        ctx.line_to(x, y)
    ctx.close_path()
    for hole in poly.interiors:
        sh = smooth_ring_light(list(hole.coords))
        if len(sh) < 3:
            continue
        ctx.move_to(sh[0][0], sh[0][1])
        for x, y in sh[1:]:
            ctx.line_to(x, y)
        ctx.close_path()

def draw_mp(ctx, mp, color):
    ctx.set_source_rgb(color[0] / 255, color[1] / 255, color[2] / 255)
    for p in (list(mp.geoms) if hasattr(mp, 'geoms') else [mp]):
        draw_sp(ctx, p)
    ctx.fill()

def draw_mp_veg(ctx, mp, color):
    ctx.set_source_rgb(color[0] / 255, color[1] / 255, color[2] / 255)
    for p in (list(mp.geoms) if hasattr(mp, 'geoms') else [mp]):
        draw_sp_light(ctx, p)
    ctx.fill()

def stroke_mp(ctx, mp, color, lw):
    ctx.set_source_rgb(color[0] / 255, color[1] / 255, color[2] / 255)
    ctx.set_line_width(lw)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for p in (list(mp.geoms) if hasattr(mp, 'geoms') else [mp]):
        if p.is_empty:
            continue
        se = smooth_ring(list(p.exterior.coords))
        if len(se) < 3:
            continue
        ctx.move_to(se[0][0], se[0][1])
        for x, y in se[1:]:
            ctx.line_to(x, y)
        ctx.close_path()
    ctx.stroke()

# Vectorizar
print('  Vectorizar fixos...')
muni_poly = mask_to_polys(muni, 3.0)
muni_out_poly = mask_to_polys(muni_out_mask, 1.0)
rio_poly = mask_to_polys(rio_mask, 1.5)

muni_bool = cv2.resize(
    muni[rmin:rmax, cmin:cmax].astype(np.float32),
    (map_w, map_h), interpolation=cv2.INTER_LINEAR) > 0.5

print('  Vectorizar 1947...')
edif_poly = mask_to_polys_upscale(edif_mask, stol=1.5, upscale=8, sigma=2.0)
veg_poly = mask_to_polys_upscale(veg_mask, stol=0.5, upscale=8, sigma=2.0)

ne = len(edif_poly.geoms) if hasattr(edif_poly, 'geoms') else 0
nv = len(veg_poly.geoms) if hasattr(veg_poly, 'geoms') else 0
print(f'  Edificado: {ne} polys, Vegetacao: {nv} polys')

# Renderizar
print('  Renderizar...')
try:
    font_topo = ImageFont.truetype("GILB____.TTF", 16 * SF)
except OSError:
    font_topo = ImageFont.load_default()

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, map_w, map_h)
ctx = cairo.Context(surface)
ctx.set_antialias(cairo.ANTIALIAS_BEST)
ctx.set_source_rgb(*[c / 255 for c in BG_COLOR])
ctx.paint()

# Municipio como fundo (cor neutra)
draw_mp(ctx, muni_poly, BG_COLOR)

# Edificado 1947
draw_mp(ctx, edif_poly, EDIF_1947_COLOR)

# Vegetacao 1947
draw_mp_veg(ctx, veg_poly, VEG_COLOR)

# Rio + contornos
draw_mp(ctx, rio_poly, RIVER_COLOR)
stroke_mp(ctx, muni_out_poly, MUNI_LINE_COLOR, 3.0 * SF)
stroke_mp(ctx, muni_poly, MUNI_LINE_COLOR, 4.0 * SF)

# Cairo -> PIL
buf = surface.get_data()
arr = np.frombuffer(buf, dtype=np.uint8).reshape(map_h, map_w, 4)
rgb = np.stack([arr[:, :, 2], arr[:, :, 1], arr[:, :, 0]], axis=-1).copy()
rgb[~muni_bool] = np.array(BG_COLOR, dtype=np.uint8)

pil = Image.fromarray(rgb)
draw = ImageDraw.Draw(pil)
for name, lon, lat in TOPONYMS:
    px = int(((lon - LON_MIN) / (LON_MAX - LON_MIN) * gee_w - cmin) * scale_x)
    py = int(((LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * gee_h - rmin) * scale_y)
    if 0 <= px < map_w and 0 <= py < map_h:
        draw.text((px, py), name, font=font_topo, fill=(255, 255, 255),
                  stroke_width=3 * SF, stroke_fill=(20, 20, 20))

# Downscale para tamanho de video (2x)
VIDEO_SF = 2
vid_map_w = int(map_w * VIDEO_SF / SF)
vid_map_h = int(map_h * VIDEO_SF / SF)
final = pil.resize((vid_map_w, vid_map_h), Image.LANCZOS)

# Compor com painel lateral
vid_panel_w = 380 * VIDEO_SF
vid_map_area_w = 1540 * VIDEO_SF
vid_h = 1080 * VIDEO_SF

vs = VIDEO_SF
try:
    font_title = ImageFont.truetype("GILB____.TTF", 24 * vs)
    font_year_f = ImageFont.truetype("GILB____.TTF", 56 * vs)
    font_leg_title = ImageFont.truetype("GILB____.TTF", 16 * vs)
    font_leg_item = ImageFont.truetype("GIL_____.TTF", 18 * vs)
except OSError:
    font_title = ImageFont.load_default()
    font_year_f = font_title
    font_leg_title = font_title
    font_leg_item = font_title

pw = vid_panel_w
ph = vid_h
s = vs
panel = Image.new('RGB', (pw, ph), (28, 28, 32))
pdraw = ImageDraw.Draw(panel, 'RGBA')

pdraw.line([(0, 0), (0, ph)], fill=(60, 60, 65), width=2 * s)
y = 30 * s
for line in ["CRESCIMENTO", "URBANO DO PORTO"]:
    bbox = pdraw.textbbox((0, 0), line, font=font_title)
    tw = bbox[2] - bbox[0]
    pdraw.text(((pw - tw) // 2, y), line, fill=(230, 230, 230), font=font_title)
    y += 32 * s
y += 10 * s
pdraw.line([(30 * s, y), (pw - 30 * s, y)], fill=(60, 60, 65), width=s)
y += 20 * s

year_str = "1947"
bbox = pdraw.textbbox((0, 0), year_str, font=font_year_f)
tw = bbox[2] - bbox[0]
pdraw.text(((pw - tw) // 2, y), year_str, fill=(255, 255, 255), font=font_year_f)
y += 75 * s

# Barra de progresso (vazia, antes da serie temporal)
bar_x = 30 * s
bar_w = pw - 60 * s
bar_h = 8 * s
pdraw.rounded_rectangle([bar_x, y, bar_x + bar_w, y + bar_h],
                         radius=4 * s, fill=(50, 50, 55))
pdraw.ellipse([bar_x - 5 * s, y - 3 * s, bar_x + 5 * s, y + bar_h + 3 * s],
              fill=(255, 255, 255))
y += bar_h + 25 * s

pdraw.line([(30 * s, y), (pw - 30 * s, y)], fill=(60, 60, 65), width=s)
y += 20 * s

pdraw.text((30 * s, y), "LEGENDA", fill=(160, 160, 165), font=font_leg_title)
y += 30 * s
box_size = 26 * s
spacing = 38 * s

pdraw.rounded_rectangle([30 * s, y, 30 * s + box_size, y + box_size],
                         radius=4 * s, fill=EDIF_1947_COLOR)
pdraw.text((30 * s + box_size + 14 * s, y + 2 * s), "Pre-1947",
           fill=(220, 220, 220), font=font_leg_item)
y += spacing

pdraw.rounded_rectangle([30 * s, y, 30 * s + box_size, y + box_size],
                         radius=4 * s, fill=VEG_COLOR)
pdraw.text((30 * s + box_size + 14 * s, y + 2 * s), "Vegetacao",
           fill=(220, 220, 220), font=font_leg_item)
y += spacing
pdraw.rounded_rectangle([30 * s, y, 30 * s + box_size, y + box_size],
                         radius=4 * s, fill=RIVER_COLOR)
pdraw.text((30 * s + box_size + 14 * s, y + 2 * s), "Rio Douro",
           fill=(220, 220, 220), font=font_leg_item)

# Composicao final
vid_total_w = vid_map_area_w + vid_panel_w
full = Image.new('RGB', (vid_total_w, vid_h), BG_COLOR)
pad_left = (vid_map_area_w - vid_map_w) // 2
pad_top = (vid_h - vid_map_h) // 2
full.paste(final, (pad_left, pad_top))
full.paste(panel, (vid_map_area_w, 0))

output = os.path.join(SCRIPT_DIR, 'frame_1947.png')
full.save(output)
print(f'\nFrame: {output} ({os.path.getsize(output)//1024} KB)')
print(f'  {vid_total_w}x{vid_h}')
