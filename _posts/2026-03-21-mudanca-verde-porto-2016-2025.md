---
layout: post
title: "Porto perdeu ou ganhou verde? Analise de satelite 2016-2025"
date: 2026-03-21
tags: [porto, sentinel-2, ndvi, gee, vegetacao]
---

Quanto espaco verde perdeu o Porto na ultima decada? Usando imagens Sentinel-2 e o Google Earth Engine, classifiquei cada pixel de 10 metros do municipio em tres categorias — arvores, solo e edificado — para dois periodos: **2016-17** e **2024-25**.

## Metodologia

A classificacao baseia-se em indices espectrais calculados a partir das bandas do Sentinel-2:

- **NDVI** (Normalized Difference Vegetation Index) — distingue vegetacao de areas nao-vegetadas
- **NDBI** (Normalized Difference Built-up Index) — identifica superficies construidas
- **NDMI** (Normalized Difference Moisture Index) — separa arvores de relva/herbaceas
- **Racio NIR/Green** — diferencia arvores (copa densa) de relva (reflexao mais uniforme)

### Regras de classificacao

```
Arvores:   NDVI >= 0.5  E  NIR/Green >= 5  E  B3 < 600  E  NDMI >= 0.20
Edificado: (NDVI < 0.2 E NDBI >= -0.1) OU desempate ESA WorldCover
Solo:      Tudo o resto
```

Para evitar falsos positivos, pixels classificados como edificado em 2016 so podem ser reclassificados como vegetacao em 2025 se o seu NDVI ultrapassar 0.45 — uma regra de "edificado persistente".

## Transicoes detectadas

O mapa mostra quatro tipos de transicao:

| Transicao | Significado |
|-----------|-------------|
| Arvores → Edificado | Perda de arvores por construcao |
| Arvores → Solo | Perda de arvores (abate, seca, etc.) |
| Solo → Edificado | Solo livre convertido em construcao |
| Solo → Arvores | Recuperacao ou plantacao de arvores |

## Explorar o mapa

O mapa interactivo permite alternar entre camadas, mudar cores e comparar com imagem de satelite:

**[Abrir mapa interactivo]({{ site.baseurl }}/mapa.html)**

Cada camada pode ser activada/desactivada individualmente. O mapa inclui limites de freguesia para contexto geografico.

## Validacao

A classificacao foi validada contra o **ESA WorldCover 2021** (10m) e testada numa area piloto em torno do Parque de Serralves antes de ser aplicada a todo o municipio. Utilizei tambem clustering K-means para verificar a separabilidade espectral entre classes.

## Codigo

Todo o pipeline esta disponivel no repositorio:

- [`porto_publish.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/porto_publish.py) — pipeline principal
- [`test_area.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/test_area.py) — validacao na area de teste
- [`test_clusters.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/test_clusters.py) — analise de clusters

## Proximo passo

Numa analise futura, vou explorar a serie temporal anual (2016-2025) para identificar **quando** ocorreram as maiores alteracoes, e cruzar com dados de licenciamento urbanistico da CMP.
