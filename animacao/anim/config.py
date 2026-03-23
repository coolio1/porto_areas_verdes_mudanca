"""Configuration for Porto urban growth animation."""
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
LAYERS_DIR = os.path.join(PROJECT_ROOT, 'layers_historico')

# Bounding box (same as GEE exports)
LON_MIN, LON_MAX = -8.70, -8.54
LAT_MIN, LAT_MAX = 41.13, 41.19

# Epochs: (file_id, display_label, reference_year)
EPOCHS = [
    ('1985-90', '1985–1990', 1987),
    ('1995-00', '1995–2000', 1997),
    ('2001-05', '2001–2005', 2003),
    ('2016-17', '2016–2017', 2016),
    ('2023-24', '2023–2024', 2024),
]

# Year range for continuous timelapse
YEAR_START = 1985
YEAR_END = 2024

# Epoch colors (RGB) - London-inspired bold palette
EPOCH_COLORS = [
    (194, 24, 91),    # #C2185B magenta/rosa - 1985-90
    (249, 168, 37),   # #F9A825 amarelo dourado - 1995-00
    (230, 81, 0),     # #E65100 ambar/laranja - 2001-05
    (93, 64, 55),     # #5D4037 castanho - 2016-17
    (211, 47, 47),    # #D32F2F vermelho coral - 2023-24
]

# Other layer colors
VEG_COLOR = (138, 154, 91)       # #8A9A5B oliva
RIVER_COLOR = (21, 101, 192)     # #1565C0 azul forte
BG_COLOR = (232, 224, 208)       # #E8E0D0 bege/creme
MUNI_LINE_COLOR = (51, 51, 51)   # #333333
ROAD_COLOR = (80, 80, 80)        # cinzento escuro
PANEL_BG = (28, 28, 32)          # #1C1C20

# Typography
TOPO_COLOR = (255, 255, 255)
TOPO_OUTLINE_COLOR = (30, 30, 30)

# Toponyms (name, lon, lat)
TOPONYMS = [
    ("FOZ DO DOURO", -8.678, 41.150),
    ("NEVOGILDE", -8.660, 41.160),
    ("ALDOAR", -8.662, 41.170),
    ("RAMALDE", -8.643, 41.172),
    ("PARANHOS", -8.608, 41.175),
    ("CAMPANHA", -8.568, 41.160),
    ("BONFIM", -8.590, 41.155),
    ("CEDOFEITA", -8.628, 41.158),
    ("MASSARELOS", -8.643, 41.150),
    ("LORDELO", -8.653, 41.155),
    ("SÉ", -8.610, 41.142),
    ("MIRAGAIA", -8.627, 41.143),
]

# Video output
FPS = 30
TOTAL_DURATION = 30  # seconds
HOLD_START = 1.0     # seconds hold at 1985
HOLD_END = 1.0       # seconds hold at 2024
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
PANEL_WIDTH = 380
MAP_WIDTH = OUTPUT_WIDTH - PANEL_WIDTH  # 1540

# SDF
SDF_BLUR_SIGMA = 3.0

# Pixel area for statistics (Landsat 30m)
PIXEL_AREA_HA = 30 * 30 / 10000  # 0.09 ha
