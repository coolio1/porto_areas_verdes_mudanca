# Detecção de Mudança via Embeddings AlphaEarth — Calibração em Área de Teste — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um script standalone `mudanca_embeddings_teste.py` que testa, na área de calibração de Serralves, a técnica de detecção de mudança do sample Google ADK `earth-engine-geospatial` (ângulo entre embeddings AlphaEarth consecutivos), para 3 thresholds, produzindo um HTML leve com as 3 camadas de "contagem de mudanças" em toggle.

**Architecture:** Script único e sequencial (mesmo estilo de `test_area.py`): setup GEE → funções de cálculo (ângulo, contagem por threshold) → download de thumbnails via `getThumbURL` → montagem de HTML standalone com Leaflet. Sem módulos separados — é um script de calibração descartável, não uma página do site.

**Tech Stack:** `ee` (Earth Engine Python API), `requests`, `PIL`, `python-dotenv`, Leaflet 1.9.4 (via CDN, no HTML gerado).

## Global Constraints

- Dataset: `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` (verificado no código-fonte do sample Google ADK, não inventado).
- Área de teste: ponto 41.188117N, -8.617633W (Serralves), buffer 1500m — mesma área de `test_area.py`.
- Thresholds a testar: π/6, π/4, π/3 (π/4 é o default do sample original).
- Anos: comparação ano-a-ano de 2018 a 2025 contra o ano anterior (2017 é o baseline do primeiro par) → **8 comparações**, logo a contagem de mudanças por pixel vai de **0 a 8** (não 0-7 — correcção face à spec, que tinha um erro de contagem).
- `get_angle()` replicado do sample sem alterações: `img1.multiply(img2).reduce(ee.Reducer.sum()).acos()` (assume embeddings já normalizados, tal como o sample original assume).
- **Fora de escopo:** sem integração com `nav.py`, `layers/` (pasta de produção), ou qualquer camada de verde existente. Sem suite de testes automatizados (nenhum script GEE deste projecto tem — validação é `python -m py_compile` + execução real, conforme `CLAUDE.md`).
- Ficheiros de saída (`layers/test/mudanca_*.png`, `mudanca_embeddings_teste.html`) são temporários — apagar depois de tomada a decisão de calibração (ver critério de decisão na spec).

---

### Task 1: Setup do script e área de teste

**Files:**
- Create: `mudanca_embeddings_teste.py`

**Interfaces:**
- Produces: variáveis de nível de módulo `GEE_PROJECT`, `area` (`ee.Geometry`), `BOUNDS` (`[[lat_min, lon_min], [lat_max, lon_max]]`), usadas por todas as tasks seguintes.

- [ ] **Step 1: Criar o ficheiro com imports, autenticação e área de teste**

```python
"""Teste de deteccao de mudanca via embeddings AlphaEarth (Serralves).

Replica a tecnica do sample Google ADK earth-engine-geospatial:
angulo entre embeddings AlphaEarth de anos consecutivos, thresholded.
Calibracao numa area pequena antes de decidir se compensa aplicar ao municipio.
"""
import ee
import os
import io
import math
import base64
import webbrowser
import requests
from PIL import Image as PILImage
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

# Mesma area de teste de test_area.py (Serralves)
LAT, LON = 41.188117, -8.617633
BUFFER = 1500  # meters

point = ee.Geometry.Point([LON, LAT])
area = point.buffer(BUFFER).bounds()

coords = area.coordinates().getInfo()[0]
lons = [c[0] for c in coords]
lats = [c[1] for c in coords]
BOUNDS = [[min(lats), min(lons)], [max(lats), max(lons)]]

print('A testar deteccao de mudanca por embeddings AlphaEarth...')
print(f'  Area: {BUFFER}m em redor de {LAT}N, {abs(LON)}W')
print(f'  Bounds: {BOUNDS}')
```

- [ ] **Step 2: Verificar sintaxe**

Run: `python -m py_compile mudanca_embeddings_teste.py`
Expected: sem output (sucesso silencioso)

- [ ] **Step 3: Correr o script**

Run: `python mudanca_embeddings_teste.py`
Expected:
```
A testar deteccao de mudanca por embeddings AlphaEarth...
  Area: 1500m em redor de 41.188117N, 8.617633W
  Bounds: [[41.1747..., -8.6311...], [41.2015..., -8.6042...]]
```
(valores exactos de bounds variam ligeiramente; confirmar que não há erro de autenticação GEE e que os 4 valores fazem sentido geograficamente — latitude ~41.17-41.20, longitude ~-8.60 a -8.63)

- [ ] **Step 4: Commit**

```bash
git add mudanca_embeddings_teste.py
git commit -m "feat(gee-teste): setup do script de calibracao mudanca-embeddings AlphaEarth"
```

---

### Task 2: Colecção de embeddings e função de ângulo

**Files:**
- Modify: `mudanca_embeddings_teste.py` (adicionar ao fim)

**Interfaces:**
- Consumes: `area` (Task 1)
- Produces: `EMBEDDINGS` (`ee.ImageCollection`), `year_embedding(year: int) -> ee.Image`, `get_angle(img1: ee.Image, img2: ee.Image) -> ee.Image` — usados pela Task 3.

- [ ] **Step 1: Adicionar a colecção e as funções de embedding/ângulo**

```python
# ============================================================
# Embeddings AlphaEarth (GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL)
# Replica a logica de earth-engine-geospatial/earth_engine_geospatial/tools.py
# ============================================================
EMBEDDINGS = ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL')

def year_embedding(year):
    """Mosaic do embedding anual, recortado a area de teste."""
    return (EMBEDDINGS
        .filterBounds(area)
        .filter(ee.Filter.calendarRange(year, year, 'year'))
        .mosaic()
        .clip(area))

def get_angle(img1, img2):
    """Angulo entre dois embeddings (assume-os ja normalizados, tal como o sample original)."""
    return img1.multiply(img2).reduce(ee.Reducer.sum()).acos().rename('angle')

# --- Verificacao rapida: confirmar que o dataset responde para a area de teste ---
print('\nA verificar acesso ao dataset de embeddings...')
img_2020 = year_embedding(2020)
band_names = img_2020.bandNames().getInfo()
print(f'  Bandas do embedding 2020: {len(band_names)} bandas ({band_names[0]}...{band_names[-1]})')
n_images_2020 = (EMBEDDINGS.filterBounds(area)
    .filter(ee.Filter.calendarRange(2020, 2020, 'year')).size().getInfo())
print(f'  Imagens 2020 cobrindo a area de teste: {n_images_2020}')
```

- [ ] **Step 2: Correr o script**

Run: `python mudanca_embeddings_teste.py`
Expected: as linhas da Task 1 seguidas de:
```
A verificar acesso ao dataset de embeddings...
  Bandas do embedding 2020: <N> bandas (<primeira>...<ultima>)
  Imagens 2020 cobrindo a area de teste: <n >= 1>
```
Se `n_images_2020` for 0 ou o pedido falhar com erro de asset/permissão — **parar aqui**: significa que o dataset não está acessível com o `GEE_PROJECT` actual (não é bug de código, confirmar com a documentação do dataset antes de continuar).

- [ ] **Step 3: Commit**

```bash
git add mudanca_embeddings_teste.py
git commit -m "feat(gee-teste): funcoes de embedding anual e angulo entre anos"
```

---

### Task 3: Contagem de mudanças por threshold (validação numérica)

**Files:**
- Modify: `mudanca_embeddings_teste.py` (adicionar ao fim)

**Interfaces:**
- Consumes: `year_embedding()`, `get_angle()` (Task 2), `area` (Task 1)
- Produces: `get_change_count_image(threshold: float) -> ee.Image` (banda única `'count'`, valores 0-8) — usada pela Task 4.

- [ ] **Step 1: Adicionar a função de contagem de mudanças e um teste numérico com o threshold default (π/4)**

```python
# ============================================================
# Contagem de mudancas 2018-2025 (8 comparacoes ano-a-ano)
# ============================================================
def get_change_count_image(threshold):
    """Numero de anos (2018-2025) em que o pixel mudou significativamente.

    Compara cada ano ao anterior (2017 e o baseline do primeiro par).
    Retorna imagem de banda unica 'count', valores 0-8.
    """
    count = ee.Image.constant(0).rename('count')
    for year in range(2018, 2026):
        prev = year_embedding(year - 1)
        cur = year_embedding(year)
        changed = get_angle(prev, cur).gt(threshold).rename('count')
        count = count.add(changed)
    return count.clip(area).rename('count')

# --- Validacao numerica antes de gerar visuais (threshold default pi/4) ---
print('\nA validar contagem de mudancas (threshold pi/4, area de teste)...')
default_count = get_change_count_image(math.pi / 4)
stats = default_count.reduceRegion(
    reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
    geometry=area, scale=10, maxPixels=1e8
).getInfo()
print(f'  Media de mudancas/pixel: {stats.get("count_mean"):.2f}')
print(f'  Maximo de mudancas/pixel: {stats.get("count_max")}')
```

- [ ] **Step 2: Correr o script**

Run: `python mudanca_embeddings_teste.py`
Expected: linhas anteriores seguidas de:
```
A validar contagem de mudancas (threshold pi/4, area de teste)...
  Media de mudancas/pixel: <valor entre 0 e 8>
  Maximo de mudancas/pixel: <inteiro entre 0 e 8>
```
Se a média for 0 (nenhuma mudança detectada) ou 8 (tudo mudou todos os anos) em toda a área — sinal de que o threshold ou a lógica estão errados; não avançar para a Task 4 sem perceber porquê.

- [ ] **Step 3: Commit**

```bash
git add mudanca_embeddings_teste.py
git commit -m "feat(gee-teste): contagem de mudancas por threshold com validacao numerica"
```

---

### Task 4: Thumbnails para os 3 thresholds

**Files:**
- Modify: `mudanca_embeddings_teste.py` (adicionar ao fim)

**Interfaces:**
- Consumes: `get_change_count_image()` (Task 3), `area`, `BOUNDS` (Task 1)
- Produces: `download_change_layer(threshold: float, label: str) -> str` (caminho do ficheiro PNG gravado) — usada pela Task 5. Ficheiros gravados em `layers/test/mudanca_<label>.png`.

- [ ] **Step 1: Adicionar a paleta, a função de download e o loop pelos 3 thresholds**

```python
# ============================================================
# Thumbnails: contagem de mudancas visualizada, 3 thresholds
# ============================================================
# Paleta sequencial branco -> vermelho escuro, 9 niveis (contagem 0 a 8)
PALETTE = ['ffffff', 'ffe0b2', 'ffcc80', 'ffab91', 'ff8a65',
           'ff7043', 'f4511e', 'd84315', '7f0000']
DIM = 1024

THRESHOLDS = [
    ('pi6', math.pi / 6, 'Threshold pi/6 (mais sensivel)'),
    ('pi4', math.pi / 4, 'Threshold pi/4 (default do sample)'),
    ('pi3', math.pi / 3, 'Threshold pi/3 (mais conservador)'),
]

def download_change_layer(threshold, label):
    """Descarrega a contagem de mudancas visualizada (paleta 0-8) como PNG."""
    img = get_change_count_image(threshold)
    vis = img.visualize(min=0, max=8, palette=PALETTE)
    url = vis.getThumbURL({'region': area, 'dimensions': DIM, 'format': 'png'})
    print(f'  A descarregar mudanca_{label}...')
    r = requests.get(url)
    r.raise_for_status()
    os.makedirs('layers/test', exist_ok=True)
    filepath = f'layers/test/mudanca_{label}.png'
    with open(filepath, 'wb') as f:
        f.write(r.content)
    return filepath

print('\nA descarregar camadas de contagem de mudancas (3 thresholds)...')
layer_paths = {}
for label, threshold, _desc in THRESHOLDS:
    layer_paths[label] = download_change_layer(threshold, label)
print(f'  Ficheiros gerados: {list(layer_paths.values())}')
```

- [ ] **Step 2: Correr o script**

Run: `python mudanca_embeddings_teste.py`
Expected: linhas anteriores seguidas de 3 linhas "A descarregar mudanca_...", terminando em:
```
  Ficheiros gerados: ['layers/test/mudanca_pi6.png', 'layers/test/mudanca_pi4.png', 'layers/test/mudanca_pi3.png']
```

- [ ] **Step 3: Confirmar que os 3 ficheiros existem e não estão vazios**

Run: `python -c "import os; [print(f, os.path.getsize(f), 'bytes') for f in ['layers/test/mudanca_pi6.png','layers/test/mudanca_pi4.png','layers/test/mudanca_pi3.png']]"`
Expected: 3 linhas, cada uma com tamanho > 1000 bytes (um PNG 1024x1024 vazio/só-branco já tem alguns KB; se algum ficheiro tiver poucas dezenas de bytes, o download falhou silenciosamente)

- [ ] **Step 4: Commit**

```bash
git add mudanca_embeddings_teste.py
git commit -m "feat(gee-teste): download de thumbnails para os 3 thresholds"
```

---

### Task 5: HTML standalone com as 3 camadas em toggle

**Files:**
- Modify: `mudanca_embeddings_teste.py` (adicionar ao fim)
- Create (gerado pela execução, não editado à mão): `mudanca_embeddings_teste.html`

**Interfaces:**
- Consumes: `layer_paths` (Task 4), `BOUNDS`, `LAT`, `LON` (Task 1), `THRESHOLDS` (Task 4)

- [ ] **Step 1: Adicionar a geração do HTML**

```python
# ============================================================
# HTML standalone de inspeccao (Leaflet, sem nav — nao e pagina do site)
# ============================================================
def to_b64(filepath):
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode()

test_layers = [
    (label, desc, label == 'pi4', to_b64(layer_paths[label]))
    for label, _threshold, desc in THRESHOLDS
]

layer_js = ',\n'.join([
    f'  {{id:"{lid}", label:"{desc}", show:{str(show).lower()}, '
    f'src:"data:image/png;base64,{b64}"}}'
    for lid, desc, show, b64 in test_layers
])

center_lat = (BOUNDS[0][0] + BOUNDS[1][0]) / 2
center_lon = (BOUNDS[0][1] + BOUNDS[1][1]) / 2

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Teste mudanca embeddings AlphaEarth - Serralves</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; }} #map {{ position:absolute; top:0; bottom:0; width:100%; }}
  #panel {{ position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(30,30,30,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',sans-serif; color:#eee; line-height:2.0; max-width:320px; }}
  .row {{ display:flex; align-items:center; gap:8px; }}
  .row input[type=checkbox] {{ width:15px; height:15px; cursor:pointer; }}
  .row input[type=range] {{ width:70px; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <b>Teste: mudanca via embeddings AlphaEarth</b><br>
  <span style="color:#aaa;font-size:10px;">Contagem de mudancas 2018-2025 (0-8) | Serralves 1500m</span>
  <div id="rows"></div>
</div>
<script>
var map = L.map('map').setView([{center_lat}, {center_lon}], 15);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
  maxZoom:19, attribution:'Esri'
}}).addTo(map);
var bounds = {BOUNDS};
var layers = [{layer_js}];
var state = [];
function init(){{
  var div = document.getElementById('rows');
  for (var i = 0; i < layers.length; i++) {{
    var L_ = layers[i];
    var ov = L.imageOverlay(L_.src, bounds, {{opacity: 0.75}});
    if (L_.show) ov.addTo(map);
    state.push({{overlay: ov}});
    var row = document.createElement('div'); row.className = 'row';
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function(){{
      var idx = +this.dataset.idx;
      if (this.checked) state[idx].overlay.addTo(map); else map.removeLayer(state[idx].overlay);
    }});
    var lb = document.createElement('label'); lb.textContent = L_.label;
    row.appendChild(cb); row.appendChild(lb); div.appendChild(row);
  }}
}}
init();
</script>
</body>
</html>'''

with open('mudanca_embeddings_teste.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('\nmudanca_embeddings_teste.html gerado')

webbrowser.open('mudanca_embeddings_teste.html')
```

- [ ] **Step 2: Correr o script completo**

Run: `python mudanca_embeddings_teste.py`
Expected: todas as linhas das tasks anteriores, terminando em:
```
mudanca_embeddings_teste.html gerado
```
e o browser abre automaticamente com o mapa.

- [ ] **Step 3: Verificação visual manual**

No browser aberto, confirmar:
- O mapa mostra imagens de satélite Esri centradas em Serralves
- Por defeito, só a camada "Threshold pi/4 (default do sample)" está visível, sobreposta à área de teste
- Marcar/desmarcar as checkboxes das 3 camadas mostra/esconde cada uma independentemente
- As áreas com contagem alta (vermelho escuro) correspondem visualmente a zonas com mudança real reconhecível (obras, construção nova) e não estão dispersas aleatoriamente por toda a área — se estiverem dispersas sem padrão, é ruído e fica registado como resultado do teste, não como bug a corrigir aqui

- [ ] **Step 4: Commit**

```bash
git add mudanca_embeddings_teste.py
git commit -m "feat(gee-teste): HTML standalone com as 3 camadas de contagem de mudancas em toggle"
```

---

## Depois de correr o teste

Este plano termina com o script funcional e o HTML gerado. A decisão de avançar (mapa completo para o município) ou descartar o método é humana, com base na inspecção visual do Step 3 da Task 5 — conforme o critério definido na spec (`docs/superpowers/specs/2026-07-19-mudanca-embeddings-teste-design.md`). Não apagar `layers/test/mudanca_*.png` nem `mudanca_embeddings_teste.html` antes dessa decisão ser tomada.
