---
layout: post
title: "Porto perdeu ou ganhou verde? Analise de satelite 2016-2025"
date: 2026-03-21
tags: [porto, sentinel-2, ndvi, gee, vegetacao]
---

Quanto espaco verde perdeu o Porto na ultima decada? Usando imagens Sentinel-2 e o Google Earth Engine, classifiquei cada pixel de 10 metros do municipio em tres categorias — arvores, solo/relva e edificado — para dois periodos: **2016-17** e **2024-25**.

## Resultados

| Classe | 2016-17 (ha) | 2024-25 (ha) | Mudanca | % |
|--------|-------------|-------------|---------|---|
| **Arvores** | 1 254 | 1 229 | **-25 ha** | -2,0% |
| Solo/Relva | 2 298 | 2 005 | -293 ha | -12,7% |
| Edificado | 5 395 | 5 714 | +319 ha | +5,9% |

O Porto perdeu 25 hectares de arvores e 293 hectares de solo/relva em menos de uma decada. O edificado cresceu 319 hectares (+5,9%).

### Transicoes detectadas

| Transicao | Area (ha) |
|-----------|-----------|
| Arvores &rarr; Edificado | 49 |
| Arvores &rarr; Solo | 126 |
| Solo &rarr; Edificado | 221 |
| Solo &rarr; Arvores | 127 |

A maior perda vem da conversao de solo em edificado (221 ha). A perda de arvores para construcao (49 ha) e menor mas irreversivel. Nota positiva: 127 ha de solo foram convertidos em arvores, quase compensando as perdas.

## Metodologia

### Abordagem multi-sazonal

A classificacao combina analise **temporal** e **espectral** para distinguir arvores de relva — um problema classico em deteccao remota a 10 metros.

A chave e que arvores e relva tem comportamentos sazonais opostos:
- **Final de Maio/Junho**: arvores tem copa completa (NDVI alto), relva esta tipicamente seca ou cortada (NDVI baixo)
- **Verao (Julho-Setembro)**: ambas podem ter NDVI alto (relva regada)
- **Inverno**: arvores caducifolias perdem folha, relva de inverno pode ser muito verde

Ao comparar o NDVI em diferentes epocas do ano, conseguimos separar as duas classes com muito mais precisao do que usando apenas indices espectrais.

### Regras de classificacao

```
Arvores:
  NDVI verao (mediana Mai-Out) >= 0.5
  NDVI primavera (percentil 15, Mai-Jun) >= 0.7   [relva seca, arvores com folha]
  NDVI minimo (percentil 10, anual) >= 0.3         [tolerante para caducifolias]
  NIR/Green >= 4                                    [filtra relva regada]
  B3 < 600, ou B3 < 800 se NDVI_min >= 0.5         [arvores claras com NDVI estavel]

Verde urbano (arvores mistas, ruas arborizadas):
  NDVI verao >= 0.5
  NDVI primavera >= 0.5
  NDVI minimo >= 0.2
  B3 < 600, ou B3 < 800 se NDVI_min >= 0.5

Edificado:
  (NDVI < 0.2 E NDBI >= -0.1) OU desempate ESA WorldCover

Solo/Relva: tudo o resto
```

Para evitar falsos positivos nas transicoes, pixels classificados como edificado em 2016 so podem ser reclassificados como vegetacao em 2025 se o NDVI ultrapassar 0.45.

### Processo de calibracao

Os limiares foram calibrados iterativamente:

1. **Area de teste** (1500m em redor de Serralves) para ajuste rapido
2. **Analise pixel-a-pixel** comparando pixeis de relva conhecida vs arvores conhecidas
3. **Serie temporal** de 81 cenas Sentinel-2 para descobrir a janela sazonal ideal
4. **Clustering K-means** (k=2 a 10) com bandas Red Edge para validar separabilidade
5. **Validacao contra ESA WorldCover 2021**: precisao de 90,4% na identificacao de arvores

A analise temporal revelou que o melhor discriminador e o **NDVI de final de Maio/inicio de Junho** — nessa janela, arvores mantem NDVI > 0.7 enquanto relva cai para < 0.3.

## Explorar o mapa

O mapa interactivo permite activar/desactivar cada camada, mudar cores e comparar com imagem de satelite:

**[Abrir mapa interactivo]({{ site.baseurl }}/mapa.html)**

## Codigo

Todo o pipeline esta disponivel no repositorio:

- [`porto_publish.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/porto_publish.py) — pipeline principal (classificacao + mapa)
- [`test_area.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/test_area.py) — calibracao na area de teste
- [`porto_stats.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/porto_stats.py) — calculo de estatisticas

## Proximo passo

Numa analise futura, vou explorar a serie temporal anual (2016-2025) para identificar **quando** ocorreram as maiores alteracoes, e cruzar com dados de licenciamento urbanistico da CMP.
