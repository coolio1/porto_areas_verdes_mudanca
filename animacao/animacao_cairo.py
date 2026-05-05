"""
Animacao vectorial do crescimento urbano do Porto (1987-2024).
Interpolacao bienal, Cairo sf=5, downscale Lanczos 4K.
"""
import numpy as np
import cairo
import cv2
import os
import time
import subprocess
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from scipy.ndimage import gaussian_filter
from scipy.interpolate import splprep, splev
import imageio_ffmpeg

t0 = time.time()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# Configuracao
# ============================================================
EPOCHS = [
    ('1985-90', 1987),
    ('1995-00', 1997),
    ('2001-05', 2003),
    ('2016-17', 2016),
    ('2023-24', 2024),
]

# Anos a renderizar (cada 2 anos)
YEARS = list(range(1987, 2025, 2)) + [2024]
YEARS = sorted(set(YEARS))

LON_MIN, LON_MAX = -8.70, -8.54
LAT_MIN, LAT_MAX = 41.13, 41.19
COS_LAT = np.cos(np.radians((LAT_MIN + LAT_MAX) / 2))

EPOCH_COLORS = [
    (101, 67, 33), (160, 110, 45), (230, 175, 0),
    (240, 90, 0), (210, 16, 100),
]

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

LAYERS_DIR = os.path.join(SCRIPT_DIR, '..', 'layers_historico')

SF = 5
VIDEO_SF = 2

FPS = 30
HOLD_SECONDS = 1.5    # menos hold por estado (mais estados)
TRANS_SECONDS = 1.0   # transicao rapida entre bienios
HOLD_FRAMES = int(HOLD_SECONDS * FPS)
TRANS_FRAMES = int(TRANS_SECONDS * FPS)


# ============================================================
# Funcoes vectoriais
# ============================================================
def load_mask(fp):
    return (np.array(Image.open(fp).convert('RGBA'))[:, :, 3] > 30).astype(bool)


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


# ============================================================
# Carregar dados
# ============================================================
print('A carregar mascaras...')
muni = load_mask(os.path.join(LAYERS_DIR, 'porto_mask.png'))
muni_out_mask = load_mask(os.path.join(LAYERS_DIR, 'municipios.png'))
rio_mask = load_mask(os.path.join(LAYERS_DIR, 'rio.png')) & muni

edif_masks = []
veg_masks = []
epoch_years = []
for eid, year in EPOCHS:
    edif_masks.append(load_mask(os.path.join(LAYERS_DIR, f'edif_{eid}.png')) & muni)
    veg_masks.append(load_mask(os.path.join(LAYERS_DIR, f'veg_{eid}.png')) & muni)
    epoch_years.append(year)

gee_h, gee_w = edif_masks[0].shape

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

scale_x = 1540 * SF / crop_w
scale_y = scale_x / COS_LAT
if int(crop_h * scale_y) > 1080 * SF:
    scale_y = 1080 * SF / crop_h
    scale_x = scale_y * COS_LAT
map_w = int(crop_w * scale_x)
map_h = int(crop_h * scale_y)
map_w += map_w % 2
map_h += map_h % 2
print(f'  Render: {map_w}x{map_h}')


# ============================================================
# Interpolar mascaras para cada 2 anos
# ============================================================
print('\nA interpolar mascaras bienais...')
rng = np.random.default_rng(42)

# Pre-gerar mascaras aleatorias para revelacao gradual (por segmento entre epocas)
reveal_masks = []
for i in range(len(EPOCHS) - 1):
    rm = rng.uniform(0, 1, (gee_h, gee_w)).astype(np.float32)
    reveal_masks.append(rm)


def get_epoch_idx(year):
    """Encontra o indice da epoca e fraccao de interpolacao."""
    if year <= epoch_years[0]:
        return 0, 0.0
    if year >= epoch_years[-1]:
        return len(EPOCHS) - 2, 1.0
    for i in range(len(EPOCHS) - 1):
        if epoch_years[i] <= year <= epoch_years[i + 1]:
            t = (year - epoch_years[i]) / (epoch_years[i + 1] - epoch_years[i])
            return i, t
    return len(EPOCHS) - 2, 1.0


def interpolate_masks(year):
    """Interpola edificado e vegetacao para um dado ano."""
    idx, t = get_epoch_idx(year)

    if t == 0.0:
        return edif_masks[idx].copy(), veg_masks[idx].copy(), idx
    if t >= 1.0:
        return edif_masks[idx + 1].copy(), veg_masks[idx + 1].copy(), idx + 1

    rm = reveal_masks[idx]

    # Edificado: so cresce. Novos pixels aparecem gradualmente
    edif_a = edif_masks[idx]
    edif_b = edif_masks[idx + 1]
    edif_new = edif_b & ~edif_a
    edif_interp = edif_a | (edif_new & (rm < t))

    # Vegetacao: pode crescer ou diminuir
    veg_a = veg_masks[idx]
    veg_b = veg_masks[idx + 1]
    veg_stay = veg_a & veg_b
    veg_lost = veg_a & ~veg_b
    veg_gained = ~veg_a & veg_b
    veg_interp = veg_stay | (veg_lost & (rm > t)) | (veg_gained & (rm < t))

    # Determinar cor da epoca para o edificado novo
    # Edificado ate epoca idx ja existe; novo pertence a epoca idx+1
    return edif_interp, veg_interp, idx

# Gerar mascaras interpoladas para cada ano
year_edif = {}
year_veg = {}
year_epoch = {}
for year in YEARS:
    edif, veg, eidx = interpolate_masks(year)
    year_edif[year] = edif & muni
    year_veg[year] = veg & muni
    year_epoch[year] = eidx
    print(f'  {year}: edif={edif.sum():,} veg={veg.sum():,} (entre epoca {eidx} e {eidx+1 if eidx<4 else eidx})')


# ============================================================
# Vectorizar fixos + por ano
# ============================================================
print('\nA vectorizar...')
t1 = time.time()
muni_poly = mask_to_polys(muni, 3.0)
muni_out_poly = mask_to_polys(muni_out_mask, 1.0)
rio_poly = mask_to_polys(rio_mask, 1.5)

muni_bool = cv2.resize(
    muni[rmin:rmax, cmin:cmax].astype(np.float32),
    (map_w, map_h), interpolation=cv2.INTER_LINEAR) > 0.5

try:
    font_topo = ImageFont.truetype("GILB____.TTF", 16 * SF)
except OSError:
    font_topo = ImageFont.load_default()

# Vectorizar edificado e vegetacao para cada ano
year_edif_polys = {}  # lista de polys incrementais por epoca
year_veg_polys = {}

for year in YEARS:
    t2 = time.time()
    # Edificado: atribuir cada pixel a epoca MAIS ANTIGA onde aparece
    edif = year_edif[year]
    edif_inc_list = []
    assigned = np.zeros_like(edif, dtype=bool)
    for i in range(len(EPOCHS)):
        layer = edif & edif_masks[i] & ~assigned
        edif_inc_list.append(layer)
        assigned = assigned | layer

    # Vectorizar cada camada incremental
    edif_polys = []
    for layer in edif_inc_list:
        if layer.any():
            edif_polys.append(mask_to_polys_upscale(layer, stol=1.5, upscale=8, sigma=2.0))
        else:
            edif_polys.append(MultiPolygon())
    year_edif_polys[year] = edif_polys

    # Vegetacao
    veg = year_veg[year]
    year_veg_polys[year] = mask_to_polys_upscale(veg, stol=0.5, upscale=8, sigma=2.0)

    nv = len(year_veg_polys[year].geoms) if hasattr(year_veg_polys[year], 'geoms') else 0
    print(f'  {year}: veg={nv} polys ({time.time()-t2:.1f}s)')

print(f'  Total vectorizacao: {time.time() - t1:.1f}s')


# ============================================================
# Pre-renderizar estados (Cairo sf=5, downscale 4K)
# ============================================================
vid_map_w = int(map_w * VIDEO_SF / SF)
vid_map_h = int(map_h * VIDEO_SF / SF)
vid_map_w += vid_map_w % 2
vid_map_h += vid_map_h % 2
vid_panel_w = 380 * VIDEO_SF
vid_map_area_w = 1540 * VIDEO_SF
vid_h = 1080 * VIDEO_SF
vid_total_w = vid_map_area_w + vid_panel_w
print(f'\n  Video: {vid_total_w}x{vid_h}')


def render_map_state(year):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, map_w, map_h)
    ctx = cairo.Context(surface)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    ctx.set_source_rgb(*[c / 255 for c in BG_COLOR])
    ctx.paint()

    # Base municipio
    draw_mp(ctx, muni_poly, EPOCH_COLORS[0])

    # Edificado incremental por epoca
    edif_polys = year_edif_polys[year]
    for j in range(1, len(edif_polys)):
        if not edif_polys[j].is_empty:
            draw_mp(ctx, edif_polys[j], EPOCH_COLORS[j])

    # Vegetacao
    draw_mp_veg(ctx, year_veg_polys[year], VEG_COLOR)

    # Rio + contornos
    draw_mp(ctx, rio_poly, RIVER_COLOR)
    stroke_mp(ctx, muni_out_poly, MUNI_LINE_COLOR, 3.0 * SF)
    stroke_mp(ctx, muni_poly, MUNI_LINE_COLOR, 4.0 * SF)

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

    hires = np.array(pil)
    return cv2.resize(hires, (vid_map_w, vid_map_h),
                      interpolation=cv2.INTER_LANCZOS4)


print('\nA pre-renderizar...')
map_states = {}
for year in YEARS:
    t2 = time.time()
    map_states[year] = render_map_state(year)
    print(f'  {year}: {time.time()-t2:.1f}s')


# ============================================================
# Painel lateral
# ============================================================
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


def render_panel(current_year):
    pw = vid_panel_w
    ph = vid_h
    s = vs
    panel = Image.new('RGB', (pw, ph), (28, 28, 32))
    draw = ImageDraw.Draw(panel, 'RGBA')

    draw.line([(0, 0), (0, ph)], fill=(60, 60, 65), width=2 * s)
    y = 30 * s
    for line in ["CRESCIMENTO", "URBANO DO PORTO"]:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((pw - tw) // 2, y), line, fill=(230, 230, 230), font=font_title)
        y += 32 * s
    y += 10 * s
    draw.line([(30 * s, y), (pw - 30 * s, y)], fill=(60, 60, 65), width=s)
    y += 20 * s

    year_str = str(current_year)
    bbox = draw.textbbox((0, 0), year_str, font=font_year_f)
    tw = bbox[2] - bbox[0]
    draw.text(((pw - tw) // 2, y), year_str, fill=(255, 255, 255), font=font_year_f)
    y += 75 * s

    # Barra de progresso
    bar_x = 30 * s
    bar_w = pw - 60 * s
    bar_h = 8 * s
    total_span = epoch_years[-1] - epoch_years[0]
    draw.rounded_rectangle([bar_x, y, bar_x + bar_w, y + bar_h],
                           radius=4 * s, fill=(50, 50, 55))
    x_pos = bar_x
    for i in range(len(EPOCHS) - 1):
        seg_frac = (epoch_years[i + 1] - epoch_years[i]) / total_span
        seg_w = int(seg_frac * bar_w)
        if current_year >= epoch_years[i + 1]:
            draw.rectangle([x_pos, y, x_pos + seg_w, y + bar_h], fill=EPOCH_COLORS[i + 1])
        elif current_year > epoch_years[i]:
            fill_frac = (current_year - epoch_years[i]) / (epoch_years[i + 1] - epoch_years[i])
            draw.rectangle([x_pos, y, x_pos + int(fill_frac * seg_w), y + bar_h],
                           fill=EPOCH_COLORS[i + 1])
        x_pos += seg_w
    marker_frac = min(max((current_year - epoch_years[0]) / total_span, 0), 1.0)
    marker_x = bar_x + int(marker_frac * bar_w)
    draw.ellipse([marker_x - 5 * s, y - 3 * s, marker_x + 5 * s, y + bar_h + 3 * s],
                 fill=(255, 255, 255))
    y += bar_h + 25 * s

    draw.line([(30 * s, y), (pw - 30 * s, y)], fill=(60, 60, 65), width=s)
    y += 20 * s

    draw.text((30 * s, y), "LEGENDA", fill=(160, 160, 165), font=font_leg_title)
    y += 30 * s
    legend_labels = ["Pre-1990", "1995-2000", "2001-2005", "2016-2017", "2023-2024"]
    box_size = 26 * s
    spacing = 38 * s
    for j in range(len(EPOCHS)):
        rect_y = y + j * spacing
        draw.rounded_rectangle([30 * s, rect_y, 30 * s + box_size, rect_y + box_size],
                               radius=4 * s, fill=EPOCH_COLORS[j])
        draw.text((30 * s + box_size + 14 * s, rect_y + 2 * s), legend_labels[j],
                  fill=(220, 220, 220), font=font_leg_item)
    y += len(EPOCHS) * spacing + 15 * s

    draw.rounded_rectangle([30 * s, y, 30 * s + box_size, y + box_size],
                           radius=4 * s, fill=VEG_COLOR)
    draw.text((30 * s + box_size + 14 * s, y + 2 * s), "Vegetacao",
              fill=(220, 220, 220), font=font_leg_item)
    y += spacing
    draw.rounded_rectangle([30 * s, y, 30 * s + box_size, y + box_size],
                           radius=4 * s, fill=RIVER_COLOR)
    draw.text((30 * s + box_size + 14 * s, y + 2 * s), "Rio Douro",
              fill=(220, 220, 220), font=font_leg_item)

    return np.array(panel)


# ============================================================
# Composicao e video
# ============================================================
def compose_frame(map_rgb, panel_rgb):
    full = np.empty((vid_h, vid_total_w, 3), dtype=np.uint8)
    full[:, :vid_map_area_w] = BG_COLOR
    pad_left = (vid_map_area_w - vid_map_w) // 2
    pad_top = (vid_h - vid_map_h) // 2
    full[pad_top:pad_top + vid_map_h, pad_left:pad_left + vid_map_w] = map_rgb
    full[:, vid_map_area_w:] = panel_rgb
    return full


def blend_maps(a, b, t):
    if t <= 0:
        return a
    if t >= 1:
        return b
    diff = np.any(a != b, axis=2)
    r = a.copy()
    r[diff] = (a[diff].astype(np.float32) * (1 - t) +
               b[diff].astype(np.float32) * t + 0.5).astype(np.uint8)
    return r


def ease_inout(t):
    return t * t * (3 - 2 * t)


# Gerar video
print('\nA gerar video...')
output_path = os.path.join(SCRIPT_DIR, 'animacao_cairo.mp4')
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_cmd = [
    ffmpeg_exe, '-y',
    '-f', 'rawvideo', '-vcodec', 'rawvideo',
    '-s', f'{vid_total_w}x{vid_h}',
    '-pix_fmt', 'rgb24', '-r', str(FPS),
    '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
    '-pix_fmt', 'yuv420p',
    output_path,
]
ffproc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

frame_count = 0


def write_frame(frame_rgb):
    global frame_count
    ffproc.stdin.write(frame_rgb.tobytes())
    frame_count += 1


for yi in range(len(YEARS)):
    year = YEARS[yi]
    print(f'  {year}...')

    panel_rgb = render_panel(year)
    hold_frame = compose_frame(map_states[year], panel_rgb)
    for _ in range(HOLD_FRAMES):
        write_frame(hold_frame)

    if yi < len(YEARS) - 1:
        next_year = YEARS[yi + 1]
        for f in range(TRANS_FRAMES):
            t = ease_inout((f + 1) / TRANS_FRAMES)
            blended = blend_maps(map_states[year], map_states[next_year], t)
            cy = int(year + (next_year - year) * t)
            panel_rgb = render_panel(cy)
            write_frame(compose_frame(blended, panel_rgb))

ffproc.stdin.close()
ffproc.wait()

total_seconds = frame_count / FPS
file_size = os.path.getsize(output_path) / (1024 * 1024)
print(f'\n{"=" * 60}')
print(f'Video: {output_path}')
print(f'  {vid_total_w}x{vid_h}, {FPS} fps, {total_seconds:.1f}s, {file_size:.1f} MB')
print(f'  Frames: {frame_count}, Anos: {YEARS[0]}-{YEARS[-1]}')
print(f'Tempo total: {time.time() - t0:.1f}s')
print(f'{"=" * 60}')
