# Porto Verde — Espaços verdes e uso do solo

Projecto de detecção remota e análise geoespacial sobre a evolução dos espaços verdes do Porto (1947–2025).

**[coolio1.github.io/porto_areas_verdes_mudanca](https://coolio1.github.io/porto_areas_verdes_mudanca/)**

## Mapas interactivos

- [Mapa actual](https://coolio1.github.io/porto_areas_verdes_mudanca/mapa.html) — classificação Sentinel-2 (2016–2025): verde público, verde pago, verde privado
- [Mapa histórico](https://coolio1.github.io/porto_areas_verdes_mudanca/ndvi_historico.html) — evolução NDVI via Landsat (1984–2024)
- [Verde privado](https://coolio1.github.io/porto_areas_verdes_mudanca/interiores_quarteiroes.html) — logradouros e quintais detectados por satélite
- [Acessibilidade](https://coolio1.github.io/porto_areas_verdes_mudanca/acessibilidade/acessibilidade_verde.html) — acessibilidade pedonal aos espaços verdes (2SFCA)
- [Conversão urbanística](https://coolio1.github.io/porto_areas_verdes_mudanca/acessibilidade/conversao_verde.html) — áreas verdes perdidas para construção
- [Sinistralidade rodoviária](https://coolio1.github.io/porto_areas_verdes_mudanca/atropelamentos/dashboard_atropelamentos.html) — dashboard de atropelamentos no Grande Porto

## Fontes de dados

- **Sentinel-2** (Copernicus) — imagens multiespectrais 10m, 2016–2025
- **Landsat 5/7/8/9** (USGS) — série temporal NDVI, 1984–2024
- **Ortofoto 1947** (DGT) — classificação pixel com Random Forest
- **PDM do Porto** — polígonos de espaços verdes de fruição colectiva
- **OpenStreetMap** — rede viária e limites de parques
- **ANSR** — dados de sinistralidade rodoviária

## Stack

Python, Google Earth Engine, Leaflet, Jekyll (GitHub Pages)

## Licença

Os conteúdos deste site estão protegidos pela licença [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/).
