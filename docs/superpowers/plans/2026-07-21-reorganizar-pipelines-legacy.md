# Reorganizar Pipelines Legacy (mapa, histórico, interiores) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mover os três pipelines "legacy" que ainda vivem soltos na raiz do projecto (`porto_publish.py`/`mapa.html`, `ndvi_historico.py`/`ndvi_historico.html`, `interiores_quarteiroes.py`/`interiores_quarteiroes.html`) para pastas próprias — `mapa/`, `ndvi_historico/`, `interiores/` — replicando o padrão já usado em `acessibilidade/`, `atropelamentos/`, `1947/` e `animacao/`. Corrigir todos os caminhos internos (`.env`, `layers/`, `layers_historico/`, imports cruzados) para serem independentes do directório de trabalho (CWD), e actualizar todos os consumidores (`nav.py`, `patch_nav.py`, `index.html`, `capture_cards.py`).

**Architecture:** Cada pasta nova segue o padrão `SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))` / `ROOT_DIR = os.path.dirname(SCRIPT_DIR)` já usado em `acessibilidade/acessibilidade_verde.py` e `1947/orto_1947.py`. As pastas de cache (`layers/`, `layers_historico/`) **continuam na raiz** — são partilhadas entre pipelines (`layers/` serve tanto `mapa/` como `interiores/`) — só os scripts e HTMLs gerados se movem.

**Tech Stack:** Python (`ee`, `requests`, `PIL`, `python-dotenv`), Jekyll (site estático), Leaflet (HTMLs standalone).

## Global Constraints

- Este projecto **não usa pytest** para os scripts GEE — validação documentada em `CLAUDE.md`: `python -m py_compile <script>.py` + execução real. Os passos de verificação abaixo seguem esta convenção, não TDD clássico.
- **Não re-executar os pipelines GEE completos** como parte da verificação automática (custam minutos, requerem `ee.Initialize()` autenticado, e escrevem PNGs de produção). A verificação de paths é feita por um script auxiliar descartável que confirma resolução de caminhos sem chamar GEE. Recomenda-se ao utilizador correr cada pipeline uma vez manualmente depois, para confirmação end-to-end.
- `layers/` e `layers_historico/` **não se movem** — ficam na raiz (regra do `CLAUDE.md`: "Layers ficam na pasta do seu pipeline: layers/ (actual)... — mas `layers/` é partilhada entre `mapa/` e `interiores/`, por isso fica na raiz, não dentro de uma única pasta de pipeline).
- Decisões já confirmadas com o utilizador:
  - `porto_publish.py` tem um bug pré-existente (`output = 'index.html'` em vez de `'mapa.html'`) — corrigir como parte deste plano.
  - `porto_stats.py` vai para `mapa/` (partilha `GEE_PROJECT`/classificação com `porto_publish.py`).
  - `ndvi_historico_remote.html` (órfão, sem referências) move-se para `ndvi_historico/` sem apagar.
- Ficheiros que **ficam na raiz** (ferramentas cross-cutting, não pipelines): `nav.py`, `patch_nav.py` (referenciado por caminho relativo no hook git), `check_leaflet_init.py` (referenciado por `.pre-commit-config.yaml` como `python check_leaflet_init.py`), `capture_cards.py`, `test_area.py`.
- `GEE/server.py` (servidor MCP) e `mudanca_embeddings_teste.py`/`.html` (calibração AlphaEarth, explicitamente marcada como descartável no seu próprio plano) **não fazem parte deste plano** — fora de escopo.

---

### Task 1: Mover ficheiros para as novas pastas

**Files:**
- Create dirs: `mapa/`, `ndvi_historico/`, `interiores/`
- Move: `porto_publish.py` → `mapa/porto_publish.py`
- Move: `porto_stats.py` → `mapa/porto_stats.py`
- Move: `mapa.html` → `mapa/mapa.html`
- Move: `ndvi_historico.py` → `ndvi_historico/ndvi_historico.py`
- Move: `ndvi_historico_html.py` → `ndvi_historico/ndvi_historico_html.py`
- Move: `ndvi_historico.html` → `ndvi_historico/ndvi_historico.html`
- Move: `ndvi_historico_remote.html` → `ndvi_historico/ndvi_historico_remote.html`
- Move: `interiores_quarteiroes.py` → `interiores/interiores_quarteiroes.py`
- Move: `interiores_html.py` → `interiores/interiores_html.py`
- Move: `interiores_quarteiroes.html` → `interiores/interiores_quarteiroes.html`

- [ ] **Step 1: Mover com `git mv` (preserva histórico)**

```bash
cd "C:\Users\quent\OneDrive\Claude\Porto Verde"
mkdir -p mapa ndvi_historico interiores
git mv porto_publish.py mapa/porto_publish.py
git mv porto_stats.py mapa/porto_stats.py
git mv mapa.html mapa/mapa.html
git mv ndvi_historico.py ndvi_historico/ndvi_historico.py
git mv ndvi_historico_html.py ndvi_historico/ndvi_historico_html.py
git mv ndvi_historico.html ndvi_historico/ndvi_historico.html
git mv ndvi_historico_remote.html ndvi_historico/ndvi_historico_remote.html
git mv interiores_quarteiroes.py interiores/interiores_quarteiroes.py
git mv interiores_html.py interiores/interiores_html.py
git mv interiores_quarteiroes.html interiores/interiores_quarteiroes.html
```

- [ ] **Step 2: Confirmar que o root já não tem estes ficheiros**

Run: `ls *.py *.html 2>/dev/null`
Expected: apenas `capture_cards.py`, `check_leaflet_init.py`, `nav.py`, `patch_nav.py`, `test_area.py`, `googlec78d03be03954350.html`, `index.html` (mais os ficheiros `mudanca_embeddings_teste.*`, fora de escopo).

- [ ] **Step 3: Commit**

`git mv` already staged the renames. Do **not** run `git add -A` — the working tree has unrelated untracked files out of scope for this plan (`layers/test/`, `mudanca_embeddings_teste.html`, `docs/superpowers/plans/2026-07-19-mudanca-embeddings-teste.md`). Verify the staged set before committing:

```bash
git status --short
```

Expected: only `R` (renamed) lines for the 10 moved files — nothing else staged. If anything else appears staged, `git reset` it before committing.

```bash
git commit -m "chore: mover pipelines mapa/histórico/interiores para pastas próprias"
```

---

### Task 2: Corrigir `mapa/porto_publish.py`

**Files:**
- Modify: `mapa/porto_publish.py`

**Interfaces:**
- Produces: script executável com `python mapa/porto_publish.py` a partir da raiz (ou de qualquer CWD), escreve `mapa/mapa.html`.

- [ ] **Step 1: Corrigir `.env` e definir `SCRIPT_DIR`/`ROOT_DIR`/`LAYERS_DIR`**

Old:
```python
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
```

New:
```python
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
LAYERS_DIR = os.path.join(ROOT_DIR, 'layers')

load_dotenv(os.path.join(ROOT_DIR, '.env'))
```

- [ ] **Step 2: Corrigir `os.makedirs('layers', ...)`**

Old:
```python
os.makedirs('layers', exist_ok=True)
```

New:
```python
os.makedirs(LAYERS_DIR, exist_ok=True)
```

- [ ] **Step 3: Corrigir as duas ocorrências de `filepath = f'layers/{filename}'` (linhas ~134 e ~192)**

Old (ambas as ocorrências, idênticas):
```python
    filepath = f'layers/{filename}'
```

New:
```python
    filepath = os.path.join(LAYERS_DIR, filename)
```

- [ ] **Step 4: Corrigir `to_base64(f'layers/{lid}.png')`**

Old:
```python
    b64 = to_base64(f'layers/{lid}.png')
```

New:
```python
    b64 = to_base64(os.path.join(LAYERS_DIR, f'{lid}.png'))
```

- [ ] **Step 5: Corrigir o bug `output = 'index.html'` e escrever para `SCRIPT_DIR`**

Old:
```python
output = 'index.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\nMapa guardado em {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open(output)
```

New:
```python
output = os.path.join(SCRIPT_DIR, 'mapa.html')
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\nMapa guardado em {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open(output)
```

- [ ] **Step 6: Corrigir URLs canónicas SEO**

Old:
```python
<link rel="canonical" href="https://portoverde.pt/mapa.html">
<meta property="og:title" content="Espaço verde do Porto — Mudança 2016-2025">
<meta property="og:description" content="Mapa interactivo da mudança de uso do solo no Porto entre 2016 e 2025, com classificação Sentinel-2.">
<meta property="og:url" content="https://portoverde.pt/mapa.html">
```

New:
```python
<link rel="canonical" href="https://portoverde.pt/mapa/mapa.html">
<meta property="og:title" content="Espaço verde do Porto — Mudança 2016-2025">
<meta property="og:description" content="Mapa interactivo da mudança de uso do solo no Porto entre 2016 e 2025, com classificação Sentinel-2.">
<meta property="og:url" content="https://portoverde.pt/mapa/mapa.html">
```

- [ ] **Step 7: Verificar sintaxe**

Run: `python -m py_compile mapa/porto_publish.py`
Expected: sem output, sem erro.

---

### Task 3: Corrigir `mapa/porto_stats.py`

**Files:**
- Modify: `mapa/porto_stats.py`

- [ ] **Step 1: Corrigir `.env`**

Old:
```python
import ee
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
```

New:
```python
import ee
import os
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, '.env'))
```

- [ ] **Step 2: Verificar sintaxe**

Run: `python -m py_compile mapa/porto_stats.py`
Expected: sem output, sem erro.

---

### Task 4: Corrigir `ndvi_historico/ndvi_historico.py`

**Files:**
- Modify: `ndvi_historico/ndvi_historico.py`

**Interfaces:**
- Consumes: `build_html(script_dir, layers_dir, bounds, bounds_1947, epochs, layers_1947, wms_url, wms_layer)` de `ndvi_historico_html.py` (mesma pasta após a Task 1 — import sem alterações).
- Produces: `ndvi_historico/ndvi_historico.html`.

- [ ] **Step 1: Corrigir `.env` e definir `SCRIPT_DIR`/`ROOT_DIR`/`LAYERS_DIR`**

Old:
```python
from dotenv import load_dotenv
from ndvi_historico_html import build_html
```
(linha seguinte, mais abaixo no ficheiro)
```python
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
```

New:
```python
from dotenv import load_dotenv
from ndvi_historico_html import build_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
LAYERS_DIR = os.path.join(ROOT_DIR, 'layers_historico')
```
(substituir a linha `load_dotenv(...)` original por)
```python
load_dotenv(os.path.join(ROOT_DIR, '.env'))
```

- [ ] **Step 2: Corrigir `os.makedirs('layers_historico', ...)`**

Old:
```python
os.makedirs('layers_historico', exist_ok=True)
```

New:
```python
os.makedirs(LAYERS_DIR, exist_ok=True)
```

- [ ] **Step 3: Corrigir as duas chamadas a `_robust_download` com `f'layers_historico/{filename}'`**

Old:
```python
    return _robust_download(vis, f'layers_historico/{filename}', label)
```
```python
    return _robust_download(vis, f'layers_historico/{filename}', filename, transparent_black=True)
```

New:
```python
    return _robust_download(vis, os.path.join(LAYERS_DIR, filename), label)
```
```python
    return _robust_download(vis, os.path.join(LAYERS_DIR, filename), filename, transparent_black=True)
```

- [ ] **Step 4: Corrigir a chamada a `build_html`**

Old:
```python
build_html(
    os.path.dirname(os.path.abspath(__file__)),
    'layers_historico',
    BOUNDS,
    BOUNDS_1947,
    EPOCHS,
    LAYERS_1947,
    WMS_1947_URL,
    WMS_1947_LAYER,
)
```

New:
```python
build_html(
    SCRIPT_DIR,
    LAYERS_DIR,
    BOUNDS,
    BOUNDS_1947,
    EPOCHS,
    LAYERS_1947,
    WMS_1947_URL,
    WMS_1947_LAYER,
)
```

- [ ] **Step 5: Verificar sintaxe**

Run: `python -m py_compile ndvi_historico/ndvi_historico.py`
Expected: sem output, sem erro.

---

### Task 5: Corrigir `ndvi_historico/ndvi_historico_html.py`

**Files:**
- Modify: `ndvi_historico/ndvi_historico_html.py`

- [ ] **Step 1: Corrigir URLs canónicas SEO**

Old:
```python
<link rel="canonical" href="https://portoverde.pt/ndvi_historico.html">
<meta property="og:title" content="Vegetação do Porto 1947-2024">
<meta property="og:description" content="Mapa histórico da vegetação do Porto de 1947 a 2024, com ortofoto aérea e dados Landsat.">
<meta property="og:url" content="https://portoverde.pt/ndvi_historico.html">
```

New:
```python
<link rel="canonical" href="https://portoverde.pt/ndvi_historico/ndvi_historico.html">
<meta property="og:title" content="Vegetação do Porto 1947-2024">
<meta property="og:description" content="Mapa histórico da vegetação do Porto de 1947 a 2024, com ortofoto aérea e dados Landsat.">
<meta property="og:url" content="https://portoverde.pt/ndvi_historico/ndvi_historico.html">
```

- [ ] **Step 2: Verificar sintaxe**

Run: `python -m py_compile ndvi_historico/ndvi_historico_html.py`
Expected: sem output, sem erro.

---

### Task 6: Corrigir `interiores/interiores_quarteiroes.py`

**Files:**
- Modify: `interiores/interiores_quarteiroes.py`

**Interfaces:**
- Consumes: `getS2col, getComposite, classify` de `acessibilidade/acessibilidade_gee.py` (agora tio, não irmão — precisa de `ROOT_DIR`); `build_html(script_dir, layers_dir, bounds)` de `interiores_html.py` (mesma pasta — import sem alterações).
- Produces: `interiores/interiores_quarteiroes.html`.

- [ ] **Step 1: Corrigir `.env`, `sys.path` e definir `SCRIPT_DIR`/`ROOT_DIR`/`LAYERS_DIR`**

Old:
```python
import ee
import requests
import os
import io
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "acessibilidade"))
from acessibilidade_gee import getS2col, getComposite, classify
from interiores_html import build_html

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
```

New:
```python
import ee
import requests
import os
import io
import sys
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
LAYERS_DIR = os.path.join(ROOT_DIR, "layers")

sys.path.insert(0, os.path.join(ROOT_DIR, "acessibilidade"))
from acessibilidade_gee import getS2col, getComposite, classify
from interiores_html import build_html

load_dotenv(os.path.join(ROOT_DIR, ".env"))
```

- [ ] **Step 2: Corrigir `os.makedirs("layers", ...)`**

Old:
```python
os.makedirs("layers", exist_ok=True)
```

New:
```python
os.makedirs(LAYERS_DIR, exist_ok=True)
```

- [ ] **Step 3: Corrigir as duas ocorrências de `filepath = f"layers/{filename}"` (linhas ~163 e ~192)**

Old (ambas idênticas):
```python
    filepath = f"layers/{filename}"
```

New:
```python
    filepath = os.path.join(LAYERS_DIR, filename)
```

- [ ] **Step 4: Corrigir `centro_path`**

Old:
```python
centro_path = "layers/centro_alargado.png"
```

New:
```python
centro_path = os.path.join(LAYERS_DIR, "centro_alargado.png")
```

- [ ] **Step 5: Corrigir `Image.open("layers/interior_subsistente.png")` (linha ~226)**

Old:
```python
    ref_img = Image.open("layers/interior_subsistente.png")
```

New:
```python
    ref_img = Image.open(os.path.join(LAYERS_DIR, "interior_subsistente.png"))
```

- [ ] **Step 6: Corrigir as chamadas a `apply_geom_mask` (linhas ~303-304)**

Old:
```python
    apply_geom_mask("layers/interior_subsistente.png", parques_union, "parques")
    apply_geom_mask("layers/interior_perdido.png", parques_union, "parques")
```

New:
```python
    apply_geom_mask(os.path.join(LAYERS_DIR, "interior_subsistente.png"), parques_union, "parques")
    apply_geom_mask(os.path.join(LAYERS_DIR, "interior_perdido.png"), parques_union, "parques")
```

- [ ] **Step 7: Corrigir `verde_pago_path` e as chamadas a `apply_raster_mask` (linhas ~308, ~311-312)**

Old:
```python
verde_pago_path = os.path.join("acessibilidade", "layers", "verde_pago.png")
```
```python
    apply_raster_mask("layers/interior_subsistente.png", verde_pago_path, "verde pago")
    apply_raster_mask("layers/interior_perdido.png", verde_pago_path, "verde pago")
```

New:
```python
verde_pago_path = os.path.join(ROOT_DIR, "acessibilidade", "layers", "verde_pago.png")
```
```python
    apply_raster_mask(os.path.join(LAYERS_DIR, "interior_subsistente.png"), verde_pago_path, "verde pago")
    apply_raster_mask(os.path.join(LAYERS_DIR, "interior_perdido.png"), verde_pago_path, "verde pago")
```

- [ ] **Step 8: Corrigir as chamadas a `apply_roads_mask` (linhas ~385-386)**

Old:
```python
    apply_roads_mask("layers/interior_subsistente.png", roads_buffered)
    apply_roads_mask("layers/interior_perdido.png", roads_buffered)
```

New:
```python
    apply_roads_mask(os.path.join(LAYERS_DIR, "interior_subsistente.png"), roads_buffered)
    apply_roads_mask(os.path.join(LAYERS_DIR, "interior_perdido.png"), roads_buffered)
```

- [ ] **Step 9: Corrigir `ref_img = Image.open("layers/interior_subsistente.png")` (linha ~396)**

Old:
```python
ref_img = Image.open("layers/interior_subsistente.png")
```

New:
```python
ref_img = Image.open(os.path.join(LAYERS_DIR, "interior_subsistente.png"))
```

- [ ] **Step 10: Corrigir `filter_by_vector` (linhas ~464-465)**

Old:
```python
filter_by_vector("layers/interior_subsistente.png")
filter_by_vector("layers/interior_perdido.png")
```

New:
```python
filter_by_vector(os.path.join(LAYERS_DIR, "interior_subsistente.png"))
filter_by_vector(os.path.join(LAYERS_DIR, "interior_perdido.png"))
```

- [ ] **Step 11: Corrigir a chamada a `build_html`**

Old:
```python
build_html(os.path.dirname(os.path.abspath(__file__)), "layers", BOUNDS)
```

New:
```python
build_html(SCRIPT_DIR, LAYERS_DIR, BOUNDS)
```

- [ ] **Step 12: Verificar sintaxe**

Run: `python -m py_compile interiores/interiores_quarteiroes.py`
Expected: sem output, sem erro.

- [ ] **Step 13 (adenda pós-revisão): Corrigir `parques_path`**

Encontrado pelo task reviewer da Task 6 — não fazia parte do grep original (só procurava `"layers/`), mas é a mesma classe de bug: literal relativo que só resolve com CWD=raiz. Como a leitura está atrás de `if os.path.exists(parques_path):`, falha **silenciosamente** (sem erro), saltando a subtracção de parques — parques públicos ficariam incorrectamente contados como verde privado.

Old:
```python
parques_path = os.path.join("acessibilidade", "parques_porto.geojson")
```

New:
```python
parques_path = os.path.join(ROOT_DIR, "acessibilidade", "parques_porto.geojson")
```

Run: `python -m py_compile interiores/interiores_quarteiroes.py`
Expected: sem output, sem erro.

---

### Task 7: Corrigir `interiores/interiores_html.py`

**Files:**
- Modify: `interiores/interiores_html.py`

- [ ] **Step 1: Corrigir URLs canónicas SEO**

Old:
```python
<link rel="canonical" href="https://portoverde.pt/interiores_quarteiroes.html">
<meta property="og:url" content="https://portoverde.pt/interiores_quarteiroes.html">
```

New:
```python
<link rel="canonical" href="https://portoverde.pt/interiores/interiores_quarteiroes.html">
<meta property="og:url" content="https://portoverde.pt/interiores/interiores_quarteiroes.html">
```

- [ ] **Step 2: Verificar sintaxe**

Run: `python -m py_compile interiores/interiores_html.py`
Expected: sem output, sem erro.

---

### Task 8: Actualizar `nav.py` e `patch_nav.py`

**Files:**
- Modify: `nav.py`
- Modify: `patch_nav.py`

**Interfaces:**
- Produces: `get_nav()`/`get_jekyll_nav()` com os novos caminhos canónicos; `patch_nav.py` volta a escrever a nav correcta em todos os HTMLs (incluindo os movidos) na Task 10.

- [ ] **Step 1: Actualizar `PAGES` em `nav.py`**

Old:
```python
PAGES = [
    ("index.html",                                    "Início"),
    ("mapa.html",                                     "Mapa 2016-2025"),
    ("ndvi_historico.html",                           "Histórico 1947-2024"),
    ("interiores_quarteiroes.html",                   "Verde Privado"),
    ("acessibilidade/acessibilidade_verde.html",      "Acessibilidade"),
    ("acessibilidade/conversao_verde.html",           "Propostas"),
    ("atropelamentos/dashboard_atropelamentos.html",  "Atropelamentos"),
]
```

New:
```python
PAGES = [
    ("index.html",                                    "Início"),
    ("mapa/mapa.html",                                "Mapa 2016-2025"),
    ("ndvi_historico/ndvi_historico.html",            "Histórico 1947-2024"),
    ("interiores/interiores_quarteiroes.html",        "Verde Privado"),
    ("acessibilidade/acessibilidade_verde.html",      "Acessibilidade"),
    ("acessibilidade/conversao_verde.html",           "Propostas"),
    ("atropelamentos/dashboard_atropelamentos.html",  "Atropelamentos"),
]
```

- [ ] **Step 2: Actualizar `TARGETS` em `patch_nav.py`**

Old:
```python
TARGETS = [
    ("mapa.html",                                     "mapa.html",                                    0),
    ("ndvi_historico.html",                           "ndvi_historico.html",                          0),
    ("interiores_quarteiroes.html",                   "interiores_quarteiroes.html",                  0),
    ("acessibilidade/acessibilidade_verde.html",      "acessibilidade/acessibilidade_verde.html",     1),
    ("acessibilidade/conversao_verde.html",           "acessibilidade/conversao_verde.html",          1),
    ("atropelamentos/dashboard_atropelamentos.html",  "atropelamentos/dashboard_atropelamentos.html", 1),
    ("1947/orto_1947.html",                           "1947/orto_1947.html",                          1),
]
```

New:
```python
TARGETS = [
    ("mapa/mapa.html",                                 "mapa/mapa.html",                                1),
    ("ndvi_historico/ndvi_historico.html",             "ndvi_historico/ndvi_historico.html",            1),
    ("interiores/interiores_quarteiroes.html",         "interiores/interiores_quarteiroes.html",        1),
    ("acessibilidade/acessibilidade_verde.html",       "acessibilidade/acessibilidade_verde.html",      1),
    ("acessibilidade/conversao_verde.html",            "acessibilidade/conversao_verde.html",           1),
    ("atropelamentos/dashboard_atropelamentos.html",   "atropelamentos/dashboard_atropelamentos.html",  1),
    ("1947/orto_1947.html",                            "1947/orto_1947.html",                           1),
]
```

- [ ] **Step 3: Verificar sintaxe**

Run: `python -m py_compile nav.py patch_nav.py`
Expected: sem output, sem erro.

---

### Task 9: Actualizar `index.html` e `capture_cards.py`

**Files:**
- Modify: `index.html`
- Modify: `capture_cards.py`

- [ ] **Step 1: Actualizar os 3 links em `index.html`**

Old:
```html
      <a href="{{ site.baseurl }}/mapa.html" class="map-card">
```
```html
      <a href="{{ site.baseurl }}/ndvi_historico.html" class="map-card">
```
```html
      <a href="{{ site.baseurl }}/interiores_quarteiroes.html" class="map-card">
```

New:
```html
      <a href="{{ site.baseurl }}/mapa/mapa.html" class="map-card">
```
```html
      <a href="{{ site.baseurl }}/ndvi_historico/ndvi_historico.html" class="map-card">
```
```html
      <a href="{{ site.baseurl }}/interiores/interiores_quarteiroes.html" class="map-card">
```

- [ ] **Step 2: Actualizar `MAPS` em `capture_cards.py`**

Old:
```python
    {
        "slug": "mudancas",
        "url": f"{BASE_URL}/mapa.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
    {
        "slug": "historico",
        "url": f"{BASE_URL}/ndvi_historico.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
    {
        "slug": "verde_privado",
        "url": f"{BASE_URL}/interiores_quarteiroes.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
```

New:
```python
    {
        "slug": "mudancas",
        "url": f"{BASE_URL}/mapa/mapa.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
    {
        "slug": "historico",
        "url": f"{BASE_URL}/ndvi_historico/ndvi_historico.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
    {
        "slug": "verde_privado",
        "url": f"{BASE_URL}/interiores/interiores_quarteiroes.html",
        "wait_for": ".leaflet-tile-loaded",
        "extra_wait": 5,
    },
```

- [ ] **Step 3: Verificar sintaxe**

Run: `python -m py_compile capture_cards.py`
Expected: sem output, sem erro.

---

### Task 10: Verificação final

**Files:**
- None (apenas verificação)

- [ ] **Step 1: `py_compile` de todos os ficheiros tocados**

Run:
```bash
python -m py_compile mapa/porto_publish.py mapa/porto_stats.py ndvi_historico/ndvi_historico.py ndvi_historico/ndvi_historico_html.py interiores/interiores_quarteiroes.py interiores/interiores_html.py nav.py patch_nav.py capture_cards.py
```
Expected: sem output, sem erro (código de saída 0).

- [ ] **Step 2: Grep por referências residuais aos caminhos antigos (sem GEE, rápido)**

Run:
```bash
grep -rn "href=\"mapa\.html\"\|href=\"ndvi_historico\.html\"\|href=\"interiores_quarteiroes\.html\"" index.html nav.py patch_nav.py capture_cards.py
```
Expected: nenhuma correspondência (todas as referências foram actualizadas nas Tasks 8-9).

- [ ] **Step 3: Smoke-check dos caminhos sem chamar GEE**

Criar um script descartável `_smoke_paths.py` na raiz que confirma que `LAYERS_DIR`/`ROOT_DIR` resolvem para os locais certos, sem importar `ee` nem chamar `ee.Initialize()`:

```python
import os

checks = [
    ("mapa/porto_publish.py -> layers/",       os.path.join("mapa", "..", "layers")),
    ("ndvi_historico/... -> layers_historico/", os.path.join("ndvi_historico", "..", "layers_historico")),
    ("interiores/... -> layers/",               os.path.join("interiores", "..", "layers")),
    ("interiores/... -> acessibilidade/layers/", os.path.join("interiores", "..", "acessibilidade", "layers")),
]
for label, path in checks:
    resolved = os.path.abspath(path)
    exists = os.path.isdir(resolved)
    print(f"{'OK ' if exists else 'FALTA'} {label}: {resolved}")
```

Run: `python _smoke_paths.py`
Expected: todas as linhas `OK` (as pastas `layers/`, `layers_historico/`, `acessibilidade/layers/` já existem hoje na raiz).

- [ ] **Step 4: Apagar o script de smoke-check**

```bash
rm _smoke_paths.py
```

- [ ] **Step 5: Correr `patch_nav.py` para repatchar a nav dos HTMLs movidos**

Run: `python patch_nav.py`
Expected: lista `[patch] mapa/mapa.html`, `[patch] ndvi_historico/ndvi_historico.html`, `[patch] interiores/interiores_quarteiroes.html` (e possivelmente `_includes/nav.html`) — confirma que a nav com os novos caminhos (`../`) foi escrita correctamente nos HTMLs já existentes.

- [ ] **Step 6: Abrir os 3 HTMLs movidos no browser e confirmar visualmente**

Run: `start mapa/mapa.html && start ndvi_historico/ndvi_historico.html && start interiores/interiores_quarteiroes.html`
Expected: cada página abre, mostra o mapa Leaflet com tiles, e a nav no topo direito tem o link da própria página a "active" e os restantes links funcionam (apontam para `../mapa.html` no formato correcto a partir da nova profundidade).

- [ ] **Step 7: Commit final**

`patch_nav.py` (Step 5) already `git add`-ed the HTML/nav files it patched. Stage only the remaining edited `.py` files explicitly — do **not** run `git add -A` (same unrelated untracked files as Task 1 Step 3 are still present):

```bash
git add mapa/porto_publish.py mapa/porto_stats.py \
        ndvi_historico/ndvi_historico.py ndvi_historico/ndvi_historico_html.py \
        interiores/interiores_quarteiroes.py interiores/interiores_html.py \
        nav.py patch_nav.py index.html capture_cards.py
git status --short
```

Expected: only the files above plus whatever `patch_nav.py` already staged (`mapa/mapa.html`, `ndvi_historico/ndvi_historico.html`, `interiores/interiores_quarteiroes.html`, possibly `_includes/nav.html`) show as staged. Nothing from `layers/test/`, `mudanca_embeddings_teste.*`, or the unrelated docs plan should appear.

```bash
git commit -m "fix: corrigir caminhos internos e referencias apos mover pipelines para pastas proprias"
```

**Nota para o utilizador:** este plano não volta a correr `porto_publish.py`, `ndvi_historico.py` nem `interiores_quarteiroes.py` de ponta a ponta (exigem GEE autenticado e demoram minutos). Depois de mergeado, recomenda-se correr cada um manualmente pelo menos uma vez para confirmar que a regeneração completa (não só a abertura do HTML já em cache) funciona a partir da nova localização.
