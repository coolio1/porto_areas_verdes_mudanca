# Design: Animacao Edificado Porto — Timelapse Continuo

**Data**: 2026-03-22
**Status**: Aprovado

## Resumo

Reescrever a animacao do crescimento urbano do Porto (1985-2024) com estilo visual inspirado no mapa de crescimento de Londres: cores solidas e saturadas, tipografia bold com outline, transicoes ano-a-ano fluidas usando Signed Distance Fields (SDF). O resultado e um timelapse continuo de ~30 segundos em Full HD.

## Problema

A animacao actual tem:
- Transicoes bruscas entre 5 epocas discretas
- Pixeis visiveis na revelacao do edificado
- Estilo visual timido (transparencias, cores pouco saturadas, basemap cinzento)

## Solucao

### Dados e Interpolacao Temporal

- **Epocas reais** (com mascaras de dados): 1985-90, 1995-00, 2001-05, 2016-17, 2023-24
- **Anos de referencia**: 1987, 1997, 2003, 2016, 2024
- **Timeline continua**: 1985 a 2024 (39 anos)
- **Metodo SDF**:
  - Cada mascara binaria de edificado e convertida num signed distance field (distancia ao bordo: negativo dentro, positivo fora)
  - Para cada ano intermedio, interpola-se linearmente entre os SDFs das duas epocas adjacentes
  - O threshold zero do SDF interpolado define o contorno suave do edificado nesse ano
  - Gaussian blur final nos bordos (sigma=3 pixels a resolucao de output) para eliminar qualquer aresta dura
- **Atribuicao de cor**: pixeis que surgem durante a interpolacao entre epoca A e epoca B recebem a cor da epoca B (a epoca seguinte)
- **Resultado**: mancha urbana cresce suavemente, sem saltos nem pixeis visiveis

### Camadas de Dados

**Edificado**: 5 mascaras binarias (`layers_historico/edif_*.png`), interpoladas via SDF

**Vegetacao**: 5 mascaras binarias (`layers_historico/veg_*.png`), interpoladas via SDF tal como o edificado, cor oliva (#8A9A5B). A vegetacao varia ao longo dos anos reflectindo a mudanca real.

**Rio Douro**: mascara gerada a partir do JRC Global Surface Water (via Google Earth Engine), exportada como PNG binario para `layers_historico/rio.png`. Cor azul forte (#1565C0). Camada estatica.

**Estradas/limites**: linhas descarregadas da OpenStreetMap via Overpass API, renderizadas como PNG com linhas finas escuras sobre fundo transparente. Exportadas para `layers_historico/estradas.png`. Camada estatica.

**Limites municipio**: mascara existente (`layers_historico/municipios.png`), linha fina (#333333).

### Estilo Visual e Paleta

- **Fundo**: bege/creme quente (#E8E0D0)

**Paleta de edificado por epoca**:
| Epoca     | Cor              | Hex       |
|-----------|------------------|-----------|
| 1985-90   | Magenta/rosa     | #C2185B   |
| 1995-00   | Amarelo dourado  | #F9A825   |
| 2001-05   | Ambar/laranja    | #E65100   |
| 2016-17   | Castanho         | #5D4037   |
| 2023-24   | Vermelho coral   | #D32F2F   |

- Cada pixel mantem a cor da epoca em que "nasceu"
- Crescimento intermedio recebe a cor da epoca seguinte (ex: crescimento entre 2003 e 2016 recebe cor de 2016-17)

**Tipografia**: freguesias em maiusculas, bold, branco com outline escura (stroke_width do Pillow >= 8.0). "PORTO" grande centrado no municipio, visivel como watermark durante toda a animacao.

### Painel Lateral

- **Dimensoes**: 380px largura, fundo escuro (#1C1C20)
- **Conteudo** (de cima para baixo):
  1. Titulo: "Crescimento Urbano do Porto" — bold, branco
  2. Ano actual: numero grande animado continuamente (1985->2024)
  3. Barra de progresso: horizontal, dividida proporcionalmente ao numero de anos de cada epoca (ex: 1985-1997 = 12 anos = 31% da barra). Um marcador/preenchimento avanca com o ano actual.
  4. Legenda: quadrados coloridos com periodos, destaque na epoca actual (futuras esmaecidas)
  5. Estatisticas: area edificada (ha) e variacao desde 1985, numeros animados suavemente
  6. Rodape: fonte dos dados (Landsat USGS/NASA, 30m)

### Composicao e Output

- **Resolucao**: 1920x1080 (16:9 Full HD)
  - Mapa: ~1540px
  - Painel: 380px
- **Timing**: 30s total, 30 FPS = 900 frames
  - 1s hold em 1985 (30 frames)
  - 28s interpolacao continua 1985->2024 (840 frames, ~0.72s/ano)
  - 1s hold em 2024 (30 frames)
  - Progressao temporal linear
- **Codec**: H.264 via ffmpeg (frames escritos como raw e codificados com ffmpeg para controlo de qualidade/bitrate)

### Sequencia de Render

1. **Preparar dados**: gerar mascara do rio (GEE/JRC), descarregar estradas (OSM Overpass), exportar PNGs
2. **Pre-calcular SDFs**: converter as 5 mascaras de edificado e 5 de vegetacao em signed distance fields
3. **Para cada frame**:
   a. Calcular ano actual a partir do indice do frame
   b. Interpolar SDFs de edificado entre as duas epocas adjacentes
   c. Interpolar SDFs de vegetacao entre as duas epocas adjacentes
   d. Aplicar threshold zero para obter contornos suaves
   e. Atribuir cores por epoca ao edificado
   f. Compor camadas: fundo bege -> vegetacao oliva -> edificado colorido -> rio azul -> estradas -> limites municipio -> toponimos
   g. Compor painel lateral com ano, barra de progresso, legenda, estatisticas
   h. Escrever frame
4. **Codificar video**: ffmpeg para H.264

## Ficheiros Existentes

- `animacao_edificado.py` — script actual (a reescrever)
- `layers_historico/edif_*.png` — mascaras de edificado por epoca (5 ficheiros)
- `layers_historico/veg_*.png` — mascaras de vegetacao por epoca (5 ficheiros)
- `layers_historico/municipios.png` — limites do municipio
- `layers_historico/basemap_positron.png` — basemap CartoDB (ja nao sera usado)

## Ficheiros a Criar

- `layers_historico/rio.png` — mascara do rio Douro (via GEE JRC Global Surface Water)
- `layers_historico/estradas.png` — rede viaria (via OSM Overpass API)

## Decisoes de Design

- SDF escolhido sobre interpolacao raster por produzir bordas matematicamente suaves
- Basemap CartoDB removido em favor de fundo bege solido (mais proximo da referencia de Londres)
- Vegetacao dinamica (5 mascaras interpoladas via SDF), cor oliva unica
- Timelapse continuo em vez de epocas discretas com pausa
- Rio gerado via JRC Global Surface Water (GEE)
- Estradas descarregadas da OpenStreetMap via Overpass API
- Pixeis intermédios recebem a cor da epoca seguinte
- Encoding via ffmpeg para H.264 com controlo de qualidade
- Texto com outline usando stroke_width do Pillow
