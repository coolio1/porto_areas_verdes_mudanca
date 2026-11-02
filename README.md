# Porto Verde — Espaços verdes e uso do solo

Projecto de detecção remota e análise geoespacial sobre a evolução dos espaços verdes do Porto (1947–2025).

**[portoverde.pt](https://portoverde.pt/)**

## Mapas interactivos

- [Mapas (página única, quatro temas)](https://portoverde.pt/mapa_unico/mapa_unico.html):
  - [Mapa 2016–2025](https://portoverde.pt/mapa_unico/mapa_unico.html#tema=hoje) — classificação Sentinel-2: árvores, solo, edificado e transições
  - [Acessibilidade e propostas](https://portoverde.pt/mapa_unico/mapa_unico.html#tema=acessibilidade) — acessibilidade pedonal aos espaços verdes (2SFCA) e 46 propostas de conversão
  - [Histórico 1947–2024](https://portoverde.pt/mapa_unico/mapa_unico.html#tema=historico) — ortofoto de 1947, ocupação do solo de 1979 e vegetação Landsat
  - [Verde privado](https://portoverde.pt/mapa_unico/mapa_unico.html#tema=privado) — logradouros e quintais detectados por satélite
- [Sinistralidade rodoviária](https://portoverde.pt/atropelamentos/dashboard_atropelamentos.html) — dashboard de atropelamentos no Grande Porto

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
