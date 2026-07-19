# Detecção de Mudança via Embeddings AlphaEarth — Calibração em Área de Teste

## Objectivo

Testar, numa área pequena e conhecida, se a técnica de detecção de mudança usada no sample Google ADK `earth-engine-geospatial` (ângulo entre embeddings AlphaEarth de anos consecutivos) produz sinal útil no contexto urbano do Porto, antes de decidir se vale a pena construir um mapa completo para o município.

Não é (ainda) um mapa do site — é uma ferramenta de calibração descartável, ao mesmo nível de `test_area.py`.

## Contexto / origem

A técnica vem de `google/adk-samples/python/agents/earth-engine-geospatial` (`tools.py`): usa a colecção `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` (embeddings AlphaEarth, 10m/pixel, anual 2017-2025). Para cada par de anos consecutivos, trata cada pixel como um vector e calcula o ângulo entre os embeddings via `acos(dot_product)`. Pixels com ângulo > threshold são considerados "mudança significativa" nesse ano. É uma detecção de mudança genérica (não distingue tipo — construção, obras, vegetação, sazonalidade) e não-supervisionada (sem classificação prévia).

## Abordagem

Script standalone Python + GEE, reutilizando a área e convenções de `test_area.py`. Sem integração com `nav.py`, `layers/` ou qualquer camada de verde existente — mudança genérica, sem filtrar por tipo, nesta fase.

## Área de teste

Mesma área de `test_area.py`, para os resultados serem comparáveis à classificação NDVI já calibrada ali:

- Ponto: 41.188117N, -8.617633W (Serralves)
- Buffer: 1500m

## Dados de entrada

- `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` (ee.ImageCollection), mosaic anual por `ee.Filter.calendarRange(year, year, 'year')`
- Anos: 2017 (baseline) a 2025 → 8 pares de anos consecutivos, 2018-2025 como anos "de mudança possível"

## Lógica de processamento

1. `get_angle(img1, img2)`: `img1.multiply(img2).reduce(ee.Reducer.sum()).acos()` (embeddings já normalizados na colecção — replicado do sample, sem alterações)
2. Para cada threshold em `[pi/6, pi/4, pi/3]`:
   - Para cada ano 2018-2025: `angle(embed[year-1], embed[year]) > threshold` → booleano
   - Somar os 8 booleanos → imagem única, valores 0-7 = nº de anos em que o pixel "mudou significativamente" no período
3. Clip de cada imagem resultante à área de teste (buffer 1500m)
4. `getThumbURL` por threshold, paleta sequencial branco (0) → vermelho (7)

## Saída

HTML leve standalone (Leaflet), sem nav, com as 3 camadas (π/6, π/4, π/3) como overlays togglable e os bounds da área de teste. Nome sugerido: `mudanca_embeddings_teste.html` (gerado por `mudanca_embeddings_teste.py`).

## Erros e testes

Sem tratamento de erros elaborado — script de calibração descartável, falha visivelmente se o GEE falhar (consistente com `test_area.py`). Não há suite de testes automatizados; a própria execução na área de teste é a validação do método.

## Critério de decisão pós-teste

Inspecção visual das 3 camadas:
- Se a contagem de mudanças correlacionar visivelmente com estruturas conhecidas na área (edifícios, obras, vegetação) e não for dominada por ruído disperso → método promissor, avançar para desenho do mapa completo (extensão ao município, threshold escolhido, eventual cruzamento com camadas de verde)
- Se dominado por ruído (contagens altas e dispersas sem correlação visual com mudança real) → método descartado ou revisitado com pré-processamento adicional

## Fora de escopo (nesta iteração)

- Aplicação ao município inteiro do Porto
- Integração em `nav.py` / publicação no site
- Cruzamento com camadas de verde (`parques_porto.geojson`, `verde_pago.png`, `interior_subsistente.png`)
- Exportação para Drive ou assets GEE persistentes
