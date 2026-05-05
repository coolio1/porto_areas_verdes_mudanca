"""
Animacao profissional do crescimento urbano do Porto (1985-2024).
Estilo: animated cartographic timelapse (Ollie Bye / NYU Atlas).
- Basemap CartoDB Positron
- Edificado acumulado por epoca com cores frio->quente
- Vegetacao em verde claro
- Rio Douro em azul
- Toponimia principal
- Painel lateral com dados
- Transicao organica (crescimento por proximidade)
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, distance_transform_edt
import cv2
import requests
import os
import io

# ============================================================
# Configuracao
# ============================================================
EPOCHS = [
    ('1985-90', '1985\u20131990', 1987),
    ('1995-00', '1995\u20132000', 1997),
    ('2001-05', '2001\u20132005', 2003),
    ('2016-17', '2016\u20132017', 2016),
    ('2023-24', '2023\u20132024', 2024),
]

# Bounding box (mesmo que GEE)
LON_MIN, LON_MAX = -8.70, -8.54
LAT_MIN, LAT_MAX = 41.13, 41.19

# Cores edificado por epoca (RGB, castanhos do claro ao muito escuro)
EPOCH_COLORS = [
    (210, 180, 140),  # castanho claro (tan) - mais antigo
    (180, 145, 105),  # castanho medio
    (150, 110, 75),   # castanho escuro
    (115, 78, 48),    # castanho muito escuro
    (75, 45, 25),     # castanho quase chocolate - mais recente
]

VEG_COLOR = (200, 255, 200)     # verde muito claro
RIVER_COLOR = (100, 149, 237)   # azul cornflower
MUNI_LINE_COLOR = (80, 80, 80)  # cinzento escuro para limites

# Toponimia (nome, lon, lat)
TOPONYMS = [
    ("Foz do Douro", -8.678, 41.150),
    ("Nevogilde", -8.660, 41.160),
    ("Aldoar", -8.662, 41.170),
    ("Ramalde", -8.643, 41.172),
    ("Paranhos", -8.608, 41.175),
    ("Campanha", -8.568, 41.160),
    ("Bonfim", -8.590, 41.155),
    ("Cedofeita", -8.628, 41.158),
    ("Massarelos", -8.643, 41.150),
    ("Lordelo", -8.653, 41.155),
    ("Se", -8.610, 41.142),
    ("Miragaia", -8.627, 41.143),
]

# Timing
FPS = 30
HOLD_SECONDS = 2.5
TRANSITION_SECONDS = 2.5
HOLD_FRAMES = int(HOLD_SECONDS * FPS)
TRANS_FRAMES = int(TRANSITION_SECONDS * FPS)

# Output
MAP_WIDTH = 1440       # largura do mapa
PANEL_WIDTH = 380      # largura do painel lateral
OUTPUT_HEIGHT = 1080

# Pixel area (Landsat 30m)
PIXEL_AREA_HA = 30 * 30 / 10000  # 0.09 ha

# ============================================================
# Basemap: download de tiles CartoDB Positron
# ============================================================

def deg2tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    return x, y

def tile2deg(x, y, zoom):
    n = 2 ** zoom
    lon = x / n * 360 - 180
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    return math.degrees(lat_rad), lon

def download_basemap(lon_min, lat_min, lon_max, lat_max, zoom=14):
    """Download e stitch de tiles CartoDB Positron."""
    cache_path = '../layers_historico/basemap_positron.png'
    meta_path = '../layers_historico/basemap_meta.npz'

    if os.path.exists(cache_path) and os.path.exists(meta_path):
        print('  Basemap em cache, a carregar...')
        img = Image.open(cache_path)
        meta = np.load(meta_path)
        return np.array(img), float(meta['img_lon_min']), float(meta['img_lat_min']), \
               float(meta['img_lon_max']), float(meta['img_lat_max'])

    x_min, y_max_tile = deg2tile(lat_min, lon_min, zoom)
    x_max, y_min_tile = deg2tile(lat_max, lon_max, zoom)

    print(f'  Tiles: x=[{x_min},{x_max}], y=[{y_min_tile},{y_max_tile}], zoom={zoom}')
    print(f'  Total: {(x_max - x_min + 1) * (y_max_tile - y_min_tile + 1)} tiles')

    # Tiles @2x sao 512x512
    tile_size = 512
    width = (x_max - x_min + 1) * tile_size
    height = (y_max_tile - y_min_tile + 1) * tile_size
    mosaic = Image.new('RGB', (width, height), (240, 240, 240))

    servers = ['a', 'b', 'c']
    import time as _time
    for tx in range(x_min, x_max + 1):
        for ty in range(y_min_tile, y_max_tile + 1):
            s = servers[(tx + ty) % 3]
            url = f'https://{s}.basemaps.cartocdn.com/light_all/{zoom}/{tx}/{ty}@2x.png'
            success = False
            for attempt in range(3):
                try:
                    r = requests.get(url, timeout=30,
                                     headers={'User-Agent': 'PortoUrbanGrowth/1.0'})
                    r.raise_for_status()
                    tile = Image.open(io.BytesIO(r.content)).convert('RGB')
                    px = (tx - x_min) * tile_size
                    py = (ty - y_min_tile) * tile_size
                    # Redimensionar se nao for 512x512
                    if tile.size != (tile_size, tile_size):
                        tile = tile.resize((tile_size, tile_size), Image.LANCZOS)
                    mosaic.paste(tile, (px, py))
                    success = True
                    break
                except Exception as e:
                    if attempt < 2:
                        _time.sleep(1)
                    else:
                        print(f'    FALHA tile {tx},{ty}: {e}')
            if not success:
                print(f'    Tile {tx},{ty} em branco (fallback)')

    # Calcular bounds exactos do mosaico em lat/lon
    nw_lat, nw_lon = tile2deg(x_min, y_min_tile, zoom)
    se_lat, se_lon = tile2deg(x_max + 1, y_max_tile + 1, zoom)

    # Crop ao bounding box pedido (converter lon/lat para pixel)
    px_per_lon = width / (se_lon - nw_lon)
    px_per_lat = height / (nw_lat - se_lat)  # lat inverted

    crop_left = int((lon_min - nw_lon) * px_per_lon)
    crop_right = int((lon_max - nw_lon) * px_per_lon)
    crop_top = int((nw_lat - lat_max) * px_per_lat)
    crop_bottom = int((nw_lat - lat_min) * px_per_lat)

    mosaic = mosaic.crop((crop_left, crop_top, crop_right, crop_bottom))

    # Guardar cache
    mosaic.save(cache_path)
    np.savez(meta_path,
             img_lon_min=lon_min, img_lon_max=lon_max,
             img_lat_min=lat_min, img_lat_max=lat_max)

    print(f'  Basemap: {mosaic.size[0]}x{mosaic.size[1]}')
    return np.array(mosaic), lon_min, lat_min, lon_max, lat_max


# ============================================================
# Funcoes auxiliares
# ============================================================

def load_binary_mask(filepath):
    img = Image.open(filepath).convert('RGBA')
    return (np.array(img)[:, :, 3] > 30).astype(np.float32)

def lonlat_to_pixel(lon, lat, img_w, img_h):
    """Converte lon/lat para coordenadas de pixel (plate carree)."""
    px = (lon - LON_MIN) / (LON_MAX - LON_MIN) * img_w
    py = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * img_h
    return int(px), int(py)

def compute_reveal_order(new_mask, existing_mask):
    """Ordem de revelacao: pixeis mais perto do edificado existente primeiro."""
    if not np.any(new_mask):
        return np.array([]), np.array([])

    # Distancia de cada pixel ao edificado existente
    if np.any(existing_mask):
        dist = distance_transform_edt(~existing_mask.astype(bool))
    else:
        # Se nao ha edificado existente, usar distancia ao centro
        h, w = new_mask.shape
        y, x = np.mgrid[0:h, 0:w]
        dist = np.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2)

    # Coordenadas dos novos pixeis
    coords = np.argwhere(new_mask > 0.5)
    if len(coords) == 0:
        return np.array([]), np.array([])

    # Ordenar por distancia (mais perto primeiro)
    distances = dist[coords[:, 0], coords[:, 1]]
    # Adicionar pequeno ruido para nao ficar demasiado regular
    rng = np.random.default_rng(42)
    noise = rng.uniform(0, 0.3, len(distances)) * np.max(distances)
    distances_noisy = distances + noise
    order = np.argsort(distances_noisy)

    return coords, order


# ============================================================
# Main
# ============================================================
print('='*60)
print('ANIMACAO: Crescimento urbano do Porto (1985-2024)')
print('='*60)

# 1. Download basemap
print('\n1. Basemap CartoDB Positron...')
basemap_rgb, *_ = download_basemap(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, zoom=14)
basemap_h, basemap_w = basemap_rgb.shape[:2]
print(f'   Basemap: {basemap_w}x{basemap_h}')

# 2. Carregar mascaras (dimensao GEE: 2048x769)
print('\n2. A carregar mascaras...')
edif_masks = []
veg_masks = []
for epoch_id, label, year in EPOCHS:
    e = load_binary_mask(f'../layers_historico/edif_{epoch_id}.png')
    v = load_binary_mask(f'../layers_historico/veg_{epoch_id}.png')
    edif_masks.append(e)
    veg_masks.append(v)
    print(f'   {label}: edif={int(np.sum(e))} px, veg={int(np.sum(v))} px')

muni_outline = load_binary_mask('../layers_historico/municipios.png')
gee_h, gee_w = edif_masks[0].shape
print(f'   GEE: {gee_w}x{gee_h}')

# 3. Redimensionar mascaras para o tamanho do basemap
print('\n3. A alinhar mascaras com basemap...')
def resize_mask(mask, target_w, target_h):
    return cv2.resize(mask, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

edif_resized = [resize_mask(e, basemap_w, basemap_h) for e in edif_masks]
veg_resized = [resize_mask(v, basemap_w, basemap_h) for v in veg_masks]
muni_resized = resize_mask(muni_outline, basemap_w, basemap_h)

# Mascara de preenchimento do municipio (uniao de tudo)
muni_fill = np.zeros((basemap_h, basemap_w), dtype=np.float32)
for e, v in zip(edif_resized, veg_resized):
    muni_fill = np.maximum(muni_fill, np.maximum(e, v))
from scipy.ndimage import binary_dilation
muni_fill = binary_dilation(muni_fill > 0.3, iterations=5).astype(np.float32)

# 4. Calcular camadas incrementais de edificado
print('\n4. A calcular camadas incrementais...')
# Cada epoca mostra APENAS o edificado novo (nao existente na epoca anterior)
edif_incremental = []
edif_incremental.append(edif_resized[0])  # primeira epoca = tudo
for i in range(1, len(EPOCHS)):
    new = np.clip(edif_resized[i] - edif_resized[i - 1], 0, 1)
    new = (new > 0.3).astype(np.float32)
    edif_incremental.append(new)
    print(f'   {EPOCHS[i][1]}: +{int(np.sum(new))} novos pixeis')

# 5. Calcular ordens de revelacao (proximidade)
print('\n5. A calcular ordens de revelacao...')
reveal_data = []
for i in range(len(EPOCHS)):
    if i == 0:
        # Primeira epoca: revelar tudo de uma vez (ja existe)
        reveal_data.append(None)
    else:
        existing = edif_resized[i - 1]
        coords, order = compute_reveal_order(edif_incremental[i], existing > 0.3)
        reveal_data.append((coords, order))
        print(f'   {EPOCHS[i][1]}: {len(coords)} pixeis a revelar')

# 6. Recortar ao municipio e calcular dimensoes
print('\n6. A recortar ao municipio...')
rows = np.any(muni_fill > 0.5, axis=1)
cols = np.any(muni_fill > 0.5, axis=0)
rmin, rmax = np.where(rows)[0][[0, -1]]
cmin, cmax = np.where(cols)[0][[0, -1]]
margin = 30
rmin = max(0, rmin - margin)
rmax = min(basemap_h, rmax + margin)
cmin = max(0, cmin - margin)
cmax = min(basemap_w, cmax + margin)

crop_h = rmax - rmin
crop_w = cmax - cmin

# Calcular escala para output
scale = OUTPUT_HEIGHT / crop_h
map_out_w = int(crop_w * scale)
map_out_h = OUTPUT_HEIGHT
# Ajustar se mapa+painel > razoavel
if map_out_w > MAP_WIDTH:
    scale = MAP_WIDTH / crop_w
    map_out_w = MAP_WIDTH
    map_out_h = int(crop_h * scale)

total_w = map_out_w + PANEL_WIDTH
# Garantir dimensoes pares
map_out_h += map_out_h % 2
total_w += total_w % 2

print(f'   Crop: {crop_w}x{crop_h}')
print(f'   Map output: {map_out_w}x{map_out_h}')
print(f'   Total output: {total_w}x{map_out_h}')

def crop_arr(arr):
    if arr.ndim == 3:
        return arr[rmin:rmax, cmin:cmax]
    return arr[rmin:rmax, cmin:cmax]

def to_output(arr):
    if arr.ndim == 3:
        return cv2.resize(arr, (map_out_w, map_out_h), interpolation=cv2.INTER_LANCZOS4)
    return cv2.resize(arr, (map_out_w, map_out_h), interpolation=cv2.INTER_LANCZOS4)

# Crop e resize do basemap
basemap_crop = crop_arr(basemap_rgb)
basemap_out = to_output(basemap_crop).astype(np.float32) / 255.0

# Crop e resize de mascaras fixas
muni_outline_out = to_output(crop_arr(muni_resized))
muni_fill_out = to_output(crop_arr(muni_fill))

# Suavizar bordos do municipio para vinheta
muni_vignette = gaussian_filter(muni_fill_out, sigma=8)

# Crop e resize de mascaras por epoca
edif_inc_out = []
veg_out = []
edif_acc_out = []  # acumulado ate esta epoca
for i in range(len(EPOCHS)):
    edif_inc_out.append(to_output(crop_arr(edif_incremental[i])))
    veg_out.append(to_output(crop_arr(veg_resized[i])))
    edif_acc_out.append(to_output(crop_arr(edif_resized[i])))

# Recalcular ordens de revelacao no espaco de output
print('\n   A recalcular ordens de revelacao no espaco de output...')
reveal_out = []
for i in range(len(EPOCHS)):
    if i == 0:
        reveal_out.append(None)
    else:
        mask_out = (edif_inc_out[i] > 0.3).astype(np.float32)
        existing_out = (edif_acc_out[i - 1] > 0.3).astype(np.float32)
        coords, order = compute_reveal_order(mask_out, existing_out)
        reveal_out.append((coords, order))

# 7. Toponimia: converter coordenadas
print('\n7. Toponimia...')
topo_pixels = []
for name, lon, lat in TOPONYMS:
    # Converter para pixel no basemap
    px = (lon - LON_MIN) / (LON_MAX - LON_MIN) * basemap_w
    py = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * basemap_h
    # Aplicar crop e scale
    px_crop = (px - cmin) * scale
    py_crop = (py - rmin) * scale
    if 0 <= px_crop < map_out_w and 0 <= py_crop < map_out_h:
        topo_pixels.append((name, int(px_crop), int(py_crop)))
        print(f'   {name}: ({int(px_crop)}, {int(py_crop)})')

# 8. Estatisticas por epoca
# Estatisticas: usar mascaras originais GEE (resolucao 30m)
# Escala correcta: contar pixeis originais * 0.09 ha
print('\n8. Estatisticas...')
stats = []
for i, (eid, label, year) in enumerate(EPOCHS):
    edif_ha = float(np.sum(edif_masks[i] > 0.5)) * PIXEL_AREA_HA
    veg_ha = float(np.sum(veg_masks[i] > 0.5)) * PIXEL_AREA_HA
    stats.append({'edif_ha': edif_ha, 'veg_ha': veg_ha, 'year': year})
    print(f'   {label}: edif={edif_ha:.0f} ha, veg={veg_ha:.0f} ha')


# ============================================================
# Funcoes de composicao
# ============================================================

def compose_map_frame(epoch_idx, reveal_progress=1.0):
    """Compoe o frame do mapa para uma dada epoca e progresso de revelacao."""
    # Comecar com basemap
    frame = basemap_out.copy()

    # Vegetacao: interpolar se em transicao
    if reveal_progress < 1.0 and epoch_idx > 0:
        veg = veg_out[epoch_idx - 1] * (1 - reveal_progress) + \
              veg_out[epoch_idx] * reveal_progress
    else:
        veg = veg_out[epoch_idx]

    # Aplicar vegetacao (verde muito claro semi-transparente)
    veg_alpha = np.clip(veg, 0, 1)[:, :, np.newaxis] * 0.35
    veg_rgb = np.array(VEG_COLOR, dtype=np.float32) / 255.0
    frame = frame * (1 - veg_alpha) + veg_rgb.reshape(1, 1, 3) * veg_alpha

    # Edificado acumulado ate a epoca anterior
    for j in range(epoch_idx):
        if j == epoch_idx - 1 and reveal_progress < 1.0:
            # Epoca anterior: completa
            pass
        layer = edif_inc_out[j]
        layer_alpha = np.clip(layer, 0, 1)[:, :, np.newaxis] * 0.75
        color = np.array(EPOCH_COLORS[j], dtype=np.float32) / 255.0
        frame = frame * (1 - layer_alpha) + color.reshape(1, 1, 3) * layer_alpha

    # Epoca actual: revelacao parcial ou total
    if reveal_progress >= 1.0:
        # Totalmente revelada
        layer = edif_inc_out[epoch_idx]
        layer_alpha = np.clip(layer, 0, 1)[:, :, np.newaxis] * 0.75
        color = np.array(EPOCH_COLORS[epoch_idx], dtype=np.float32) / 255.0
        frame = frame * (1 - layer_alpha) + color.reshape(1, 1, 3) * layer_alpha
    elif epoch_idx > 0 and reveal_out[epoch_idx] is not None:
        coords, order = reveal_out[epoch_idx]
        if len(coords) > 0:
            n_reveal = int(reveal_progress * len(coords))
            if n_reveal > 0:
                revealed_idx = order[:n_reveal]
                revealed_coords = coords[revealed_idx]
                # Criar mascara parcial
                partial = np.zeros((map_out_h, map_out_w), dtype=np.float32)
                partial[revealed_coords[:, 0], revealed_coords[:, 1]] = 1.0
                # Suavizar para nao ver pixeis individuais
                partial = gaussian_filter(partial, sigma=2.5)
                partial_alpha = np.clip(partial, 0, 1)[:, :, np.newaxis] * 0.75
                color = np.array(EPOCH_COLORS[epoch_idx], dtype=np.float32) / 255.0
                frame = frame * (1 - partial_alpha) + color.reshape(1, 1, 3) * partial_alpha

    # Limites do municipio (linha fina escura)
    muni_alpha = np.clip(muni_outline_out, 0, 1)[:, :, np.newaxis] * 0.6
    muni_rgb = np.array(MUNI_LINE_COLOR, dtype=np.float32) / 255.0
    frame = frame * (1 - muni_alpha) + muni_rgb.reshape(1, 1, 3) * muni_alpha

    # Atenuar fora do municipio
    vignette = muni_vignette[:, :, np.newaxis]
    outside_color = np.array([0.92, 0.92, 0.92], dtype=np.float32)
    frame = frame * vignette + outside_color.reshape(1, 1, 3) * (1 - vignette)

    return np.clip(frame * 255, 0, 255).astype(np.uint8)


def draw_panel(panel_img, epoch_idx, reveal_progress=1.0):
    """Desenha painel lateral com dados."""
    draw = ImageDraw.Draw(panel_img, 'RGBA')
    pw, ph = panel_img.size

    # Fontes
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 22)
        font_year = ImageFont.truetype("arialbd.ttf", 52)
        font_label = ImageFont.truetype("arial.ttf", 15)
        font_value = ImageFont.truetype("arialbd.ttf", 20)
        font_legend = ImageFont.truetype("arial.ttf", 13)
        font_small = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        font_title = ImageFont.load_default()
        font_year = font_title
        font_label = font_title
        font_value = font_title
        font_legend = font_title
        font_small = font_title

    # Fundo do painel
    draw.rectangle([0, 0, pw, ph], fill=(28, 28, 32))

    # Linha separadora esquerda
    draw.line([(0, 0), (0, ph)], fill=(60, 60, 65), width=2)

    # Titulo
    y = 30
    title_lines = ["Crescimento", "urbano do Porto"]
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((pw - tw) // 2, y), line, fill=(230, 230, 230), font=font_title)
        y += 30
    y += 10

    # Linha
    draw.line([(30, y), (pw - 30, y)], fill=(60, 60, 65), width=1)
    y += 20

    # Ano
    if reveal_progress < 1.0 and epoch_idx > 0:
        year_a = EPOCHS[epoch_idx - 1][2]
        year_b = EPOCHS[epoch_idx][2]
        # Ease in-out
        t = reveal_progress * reveal_progress * (3 - 2 * reveal_progress)
        current_year = int(year_a + (year_b - year_a) * t)
    else:
        current_year = EPOCHS[epoch_idx][2]

    year_str = str(current_year)
    bbox = draw.textbbox((0, 0), year_str, font=font_year)
    tw = bbox[2] - bbox[0]
    draw.text(((pw - tw) // 2, y), year_str, fill=(255, 255, 255), font=font_year)
    y += 70

    # Epoca actual
    if reveal_progress < 1.0 and epoch_idx > 0:
        era_label = f"{EPOCHS[epoch_idx-1][1]}  \u2192"
        era_label2 = EPOCHS[epoch_idx][1]
    else:
        era_label = EPOCHS[epoch_idx][1]
        era_label2 = None

    bbox = draw.textbbox((0, 0), era_label, font=font_label)
    tw = bbox[2] - bbox[0]
    draw.text(((pw - tw) // 2, y), era_label, fill=(170, 170, 175), font=font_label)
    y += 20
    if era_label2:
        bbox = draw.textbbox((0, 0), era_label2, font=font_label)
        tw = bbox[2] - bbox[0]
        draw.text(((pw - tw) // 2, y), era_label2, fill=(170, 170, 175), font=font_label)
        y += 20

    y += 15
    draw.line([(30, y), (pw - 30, y)], fill=(60, 60, 65), width=1)
    y += 20

    # Legenda de cores
    draw.text((30, y), "LEGENDA", fill=(140, 140, 145), font=font_small)
    y += 20
    for j, (eid, elabel, eyear) in enumerate(EPOCHS):
        color = EPOCH_COLORS[j]
        # Destacar epoca actual
        alpha = 255 if j <= epoch_idx else 80
        rect_y = y + j * 26
        draw.rounded_rectangle(
            [30, rect_y, 48, rect_y + 16],
            radius=3, fill=(*color, alpha))
        text_color = (210, 210, 210) if j <= epoch_idx else (90, 90, 95)
        draw.text((56, rect_y), elabel, fill=text_color, font=font_legend)

    y += len(EPOCHS) * 26 + 10
    # Vegetacao na legenda
    draw.rounded_rectangle(
        [30, y, 48, y + 16],
        radius=3, fill=VEG_COLOR)
    draw.text((56, y), u"Vegeta\u00e7\u00e3o", fill=(210, 210, 210), font=font_legend)
    y += 30

    draw.line([(30, y), (pw - 30, y)], fill=(60, 60, 65), width=1)
    y += 20

    # Estatisticas
    draw.text((30, y), u"ESTAT\u00cdSTICAS", fill=(140, 140, 145), font=font_small)
    y += 22

    # Interpolar estatisticas durante transicao
    if reveal_progress < 1.0 and epoch_idx > 0:
        t = reveal_progress * reveal_progress * (3 - 2 * reveal_progress)
        edif_ha = stats[epoch_idx - 1]['edif_ha'] * (1 - t) + stats[epoch_idx]['edif_ha'] * t
        veg_ha = stats[epoch_idx - 1]['veg_ha'] * (1 - t) + stats[epoch_idx]['veg_ha'] * t
    else:
        edif_ha = stats[epoch_idx]['edif_ha']
        veg_ha = stats[epoch_idx]['veg_ha']

    # Edificado
    draw.text((30, y), u"\u00c1rea edificada", fill=(170, 170, 175), font=font_label)
    y += 20
    val_str = f"{edif_ha:,.0f} ha".replace(',', ' ')
    draw.text((30, y), val_str, fill=(230, 230, 230), font=font_value)
    y += 32

    # Vegetacao
    draw.text((30, y), u"\u00c1rea de vegeta\u00e7\u00e3o", fill=(170, 170, 175), font=font_label)
    y += 20
    val_str = f"{veg_ha:,.0f} ha".replace(',', ' ')
    draw.text((30, y), val_str, fill=(144, 238, 144), font=font_value)
    y += 32

    # Variacao desde 1985
    if epoch_idx > 0 or reveal_progress < 1.0:
        edif_change = edif_ha - stats[0]['edif_ha']
        veg_change = veg_ha - stats[0]['veg_ha']
        y += 5
        draw.text((30, y), u"Varia\u00e7\u00e3o desde 1985", fill=(140, 140, 145), font=font_small)
        y += 18
        sign_e = "+" if edif_change >= 0 else ""
        draw.text((30, y), f"Edificado: {sign_e}{edif_change:,.0f} ha".replace(',', ' '),
                  fill=(192, 57, 43) if edif_change > 0 else (100, 200, 100),
                  font=font_legend)
        y += 18
        sign_v = "+" if veg_change >= 0 else ""
        draw.text((30, y), f"Vegeta\u00e7\u00e3o: {sign_v}{veg_change:,.0f} ha".replace(',', ' '),
                  fill=(192, 57, 43) if veg_change < 0 else (100, 200, 100),
                  font=font_legend)

    # Rodape
    draw.text((20, ph - 50), "Fonte: Landsat (USGS/NASA)",
              fill=(80, 80, 85), font=font_small)
    draw.text((20, ph - 35), "NDVI \u2265 0.25 | 30m",
              fill=(80, 80, 85), font=font_small)
    draw.text((20, ph - 20), "JRC Global Surface Water",
              fill=(80, 80, 85), font=font_small)

    return panel_img


def add_toponyms_to_map(map_img):
    """Adiciona nomes de lugares ao mapa."""
    draw = ImageDraw.Draw(map_img, 'RGBA')
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        font = ImageFont.load_default()

    for name, px, py in topo_pixels:
        # Fundo semi-transparente
        bbox = draw.textbbox((0, 0), name, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rounded_rectangle(
            [px - 2, py - 1, px + tw + 2, py + th + 1],
            radius=2, fill=(255, 255, 255, 160))
        draw.text((px, py), name, fill=(40, 40, 45), font=font)

    return map_img


def compose_full_frame(epoch_idx, reveal_progress=1.0):
    """Compoe frame completo: mapa + painel."""
    # Mapa
    map_rgb = compose_map_frame(epoch_idx, reveal_progress)
    map_pil = Image.fromarray(map_rgb)
    map_pil = add_toponyms_to_map(map_pil)

    # Painel
    panel = Image.new('RGBA', (PANEL_WIDTH, map_out_h), (28, 28, 32, 255))
    panel = draw_panel(panel, epoch_idx, reveal_progress)

    # Juntar
    full = Image.new('RGB', (total_w, map_out_h), (28, 28, 32))
    full.paste(map_pil, (0, 0))
    full.paste(panel.convert('RGB'), (map_out_w, 0))

    return np.array(full)


# ============================================================
# Gerar video
# ============================================================
print('\n9. A gerar video...')
output_path = 'animacao_edificado.mp4'
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
writer = cv2.VideoWriter(output_path, fourcc, FPS, (total_w, map_out_h))

total_frames = 0

for i in range(len(EPOCHS)):
    eid, label, year = EPOCHS[i]
    print(f'   Epoca {label}...')

    # Frames de pausa (epoca estavel)
    frame = compose_full_frame(i, 1.0)
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    for _ in range(HOLD_FRAMES):
        writer.write(frame_bgr)
        total_frames += 1

    # Transicao para proxima epoca
    if i < len(EPOCHS) - 1:
        next_label = EPOCHS[i + 1][1]
        print(f'     Transicao -> {next_label}...')
        for f in range(TRANS_FRAMES):
            progress = (f + 1) / TRANS_FRAMES
            # Ease in-out
            progress_smooth = progress * progress * (3 - 2 * progress)
            frame = compose_full_frame(i + 1, progress_smooth)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)
            total_frames += 1

writer.release()

total_seconds = total_frames / FPS
file_size = os.path.getsize(output_path) / (1024 * 1024)
print(f'\n{"="*60}')
print(f'Video: {output_path}')
print(f'  {total_w}x{map_out_h}, {FPS} fps, {total_seconds:.1f}s, {file_size:.1f} MB')
print(f'{"="*60}')
