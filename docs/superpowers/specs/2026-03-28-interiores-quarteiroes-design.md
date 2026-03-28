# Interiores de Quarteirão — Mapa de Espaços Verdes Privados Encravados

## Objectivo

Criar um mapa interactivo que identifique interiores de quarteirão (espaços verdes privados com árvores ou solo permeável, encravados no tecido urbano) no Porto, distinguindo os que subsistem dos que foram perdidos entre 2016 e 2024.

## Abordagem

Pipeline GEE + Python local, reutilizando as classificações Sentinel-2 do `porto_publish.py`.

Detecção raster pura: manchas de verde/solo onde a vizinhança é maioritariamente edificada. Sem dependência de shapefiles cadastrais. Espaços verdes públicos (parques, jardins) excluídos via dados OpenStreetMap.

## Dados de entrada

### Classificações Sentinel-2 (reutilizadas)

- **Época 1 (2016-17)**: composite Sentinel-2 Mai-Out, classes: árvores, solo, edificado
- **Época 2 (2024-25)**: idem
- Mesmas regras de classificação do `porto_publish.py`:
  - Árvores: NDVI >= 0.5, spring_NDVI >= 0.7, ndvi_min >= 0.3, NIR/Green >= 4, B3 < 600
  - Edificado: (NDVI < 0.2 AND NDBI >= -0.1) OR (NDVI 0.2-0.35 AND ESA WorldCover = built)
  - Solo: restante

### Filtro de vizinhança

- Kernel circular de ~50m raio (5 pixels a 10m de resolução)
- Fracção de edificado (2024-25) na vizinhança >= 60%
- Implementado com `ee.Image.reduceNeighborhood(ee.Reducer.mean(), ee.Kernel.circle(50, 'meters'))`

### Máscara de espaços verdes públicos (OSM)

- Overpass API: `leisure=park`, `leisure=garden`, `landuse=recreation_ground` dentro do bbox do Porto
- Rasterizada a 10m na mesma grelha/bounds dos PNGs
- Subtraída aos resultados (pixels dentro de parques tornam-se transparentes)

## Camadas derivadas

- **Perdido**: pixel era árvores OR solo em 2016-17 AND é edificado em 2024-25 AND fracção edificado vizinhança >= 0.6 AND fora de parques OSM
- **Subsistente**: pixel é árvores OR solo em 2024-25 AND fracção edificado vizinhança >= 0.6 AND fora de parques OSM

## Pipeline de processamento

### Script: `interiores_quarteiroes.py`

#### Fase 1 — GEE

1. Autenticar e inicializar GEE com `GEE_PROJECT` do `.env`
2. Construir composites Sentinel-2 2016-17 e 2024-25 (mesmas datas/filtros do `porto_publish.py`)
3. Classificar ambas as épocas (mesmas regras)
4. Calcular fracção de edificado na vizinhança com `reduceNeighborhood`
5. Filtrar: manter só pixels onde fracção >= 0.6
6. Gerar imagens "perdido" e "subsistente"
7. Exportar ambas como PNGs (mesmos bounds e resolução: 2048px, [41.13, -8.70] a [41.19, -8.54])

#### Fase 2 — Python local (máscara OSM)

1. Query Overpass API para polígonos de espaços verdes públicos
2. Rasterizar polígonos com mesma resolução/bounds dos PNGs
3. Aplicar máscara: remover pixels dentro de parques
4. Guardar PNGs finais:
   - `layers/interior_subsistente.png`
   - `layers/interior_perdido.png`

#### Fase 3 — HTML

1. Gerar `interiores_quarteiroes.html` com Leaflet 1.9.4
2. Imagens embebidas em base64
3. Painel lateral com checkboxes e selector de basemap

## Mapa e apresentação visual

### Layout

- Leaflet 1.9.4, fullscreen
- Mesmos bounds do projecto: [41.13, -8.70] a [41.19, -8.54]
- Zoom inicial centrado no Porto (~13)

### Basemaps (4, com selector dropdown)

1. CartoDB Positron (defeito)
2. CartoDB Dark
3. OpenStreetMap
4. Esri Satellite

### Camadas overlay

| Camada | Cor | Visível por defeito |
|--------|-----|---------------------|
| Subsistente | #2E7D32 (verde) | Sim |
| Perdido | #D7263D (vermelho) | Sim |
| Limites municipais | reutilizar `municipios.png` | Sim |

### Painel lateral

- Titulo: "Interiores de Quarteirão — Porto"
- Subtitulo: "Espaços verdes privados encravados no tecido urbano"
- Checkboxes para as 2 camadas + limites municipais
- Selector de basemap
- Sem color picker

## Ficheiros gerados

- `interiores_quarteiroes.py` — script principal (GEE + OSM + HTML)
- `layers/interior_subsistente.png` — camada de interiores que persistem
- `layers/interior_perdido.png` — camada de interiores perdidos
- `interiores_quarteiroes.html` — mapa interactivo final
