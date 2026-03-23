---
layout: post
title: "Porto perdeu ou ganhou verde? Análise de satélite 1985–2025"
date: 2026-03-21
tags: [porto, sentinel-2, landsat, ndvi, gee, vegetação, animação]
---

Quanto espaço verde perdeu o Porto nas últimas décadas? Usando imagens de satélite e o Google Earth Engine, analisei a evolução da vegetação do município em duas escalas temporais — e criei uma animação vectorial que mostra, a cada dois anos, como a cidade cresceu à custa dos espaços verdes.

- **Animação do crescimento urbano 1987–2024** — evolução bienal vectorial em 4K
- **Análise histórica 1985–2024** — Landsat a 30 m, com NDVI normalizado entre sensores
- **Análise detalhada 2016–2025** — Sentinel-2 a 10 m, com classificação árvores/solo/edificado

---

## Animação: 37 anos de crescimento urbano

<video controls width="100%" poster="{{ site.baseurl }}/animacao/frame_2024.png">
  <source src="{{ site.baseurl }}/animacao/animacao_cairo.mp4" type="video/mp4">
</video>

A animação mostra a evolução bienal do Porto entre 1987 e 2024, com dados interpolados a partir das cinco épocas de classificação Landsat. Cada cor representa uma era de construção diferente — do castanho escuro (pré-1990) ao magenta (2023–24) — enquanto o verde recua progressivamente.

Três fases são visíveis:

1. **1987–2003: expansão acelerada.** O Porto perdeu 1 780 ha de vegetação em apenas 16 anos — uma taxa de 111 ha/ano. A mancha urbana expandiu-se rapidamente nas freguesias periféricas (Ramalde, Paranhos, Campanhã), preenchendo vazios e quintas.

2. **2003–2016: estabilização e ligeira recuperação.** A vegetação recuperou 160 ha, possivelmente reflectindo o amadurecimento de plantações e a crise económica de 2008–2013 que travou a construção. O balanço líquido neste período foi positivo.

3. **2017–2024: nova pressão urbana.** Com o boom turístico e imobiliário pós-2015, o Porto voltou a perder vegetação — 165 ha em 8 anos. A construção concentrou-se na densificação do tecido existente, visível nas manchas laranja e magenta dispersas por toda a cidade.

### Evolução bienal da vegetação

| Ano | Vegetação (ha) | % do município | Variação vs 1987 |
|-----|---------------|----------------|------------------|
| 1987 | 5 352 | **45,0%** | — |
| 1991 | 4 907 | 41,3% | −445 ha |
| 1997 | 4 240 | 35,6% | −1 112 ha |
| 2003 | 3 572 | **30,0%** | −1 780 ha |
| 2009 | 3 646 | 30,7% | −1 706 ha |
| 2016 | 3 732 | 31,4% | −1 620 ha |
| 2024 | 3 567 | **30,0%** | **−1 785 ha** |

O ritmo de perda não foi constante. Entre 1987 e 1997, o Porto perdeu vegetação ao ritmo mais intenso de toda a série — **111 ha por ano**. Na década seguinte (1997–2003), o ritmo manteve-se elevado (111 ha/ano). Mas entre 2003 e 2016, houve uma inversão notável: a vegetação cresceu ligeiramente (+12 ha/ano), sugerindo que a expansão urbana abrandou e que áreas anteriormente classificadas como solo foram recolonizadas por vegetação espontânea ou plantada.

### Distribuição espacial

A análise espacial revela padrões geográficos claros:

- **Zona Ocidental (Foz, Nevogilde, Aldoar):** manteve a maior cobertura verde ao longo de todo o período, graças ao Parque da Cidade e às áreas residenciais de baixa densidade. Mesmo em 2024, esta zona permanece maioritariamente verde.

- **Centro histórico (Sé, Miragaia, Cedofeita):** já densamente edificado em 1987, com muito pouca vegetação. As alterações foram mínimas — não havia verde para perder.

- **Periferia Norte e Este (Paranhos, Ramalde, Campanhã):** sofreram a maior transformação. Grandes áreas verdes visíveis em 1987 foram progressivamente convertidas em tecido urbano, particularmente ao longo dos eixos viários principais.

---

## Análise histórica: 40 anos de mudança (1985–2024)

### O problema da comparação inter-sensor

Comparar imagens Landsat 5 (anos 80–2000) com Landsat 8 (2013–presente) não é trivial: os sensores TM e OLI têm respostas espectrais diferentes, o que inflaciona sistematicamente o NDVI do Landsat 8. Para corrigir isto, apliquei dois níveis de harmonização:

1. **Coeficientes de Roy et al. (2016)** — transformação linear das bandas Red e NIR do OLI para o nível do TM
2. **Normalização por alvos pseudo-invariantes (PIF)** — calibração empírica usando pontos de referência estáveis ao longo de 40 anos:
   - **Água** (Douro e Oceano Atlântico) — NDVI ≈ 0
   - **Solo/relva** (zonas sem árvores) — NDVI intermédio
   - **Floresta estável** (Serralves e Parque da Cidade) — NDVI alto

Para cada época, extraí o NDVI nestes 6 pontos de referência e calculei uma regressão linear que alinha os valores com a época de referência (1985–90). Isto corrige simultaneamente diferenças de sensor, atmosfera e calibração.

### Resultados históricos

Área com NDVI ≥ 0,3 (vegetação), por época:

| Época | Satélite | Área verde (ha) | % do município |
|-------|----------|----------------|----------------|
| 1985–90 | Landsat 5 | 5 352 | **45,0%** |
| 1995–00 | Landsat 5 | 4 240 | 35,6% |
| 2001–05 | Landsat 5 | 3 572 | 30,0% |
| 2016–17 | Landsat 8 | 3 732 | 31,4% |
| 2023–24 | Landsat 8 | 3 567 | **30,0%** |

**Balanço: −1 785 ha de vegetação perdida.** O Porto passou de quase metade verde para menos de um terço em 40 anos. A maior perda ocorreu nos anos 90 (expansão urbana intensa), estabilizando a partir de 2005.

| Métrica | Valor |
|---------|-------|
| Vegetação perdida | 2 266 ha |
| Vegetação ganha | 481 ha |
| **Balanço líquido** | **−1 785 ha** |

### Mapa histórico interativo

O mapa permite alternar entre épocas e visualizar as máscaras de vegetação e zonas de perda/ganho:

**[Abrir mapa histórico (1985–2024)]({{ site.baseurl }}/ndvi_historico.html)**

---

## Análise detalhada: última década (2016–2025)

Com imagens Sentinel-2 a 10 metros de resolução, é possível uma classificação mais granular — distinguindo árvores, solo/relva e edificado.

### Resultados

| Classe | 2016–17 (ha) | 2024–25 (ha) | Mudança | % |
|--------|-------------|-------------|---------|---|
| **Árvores** | 1 254 | 1 229 | **−25 ha** | −2,0% |
| Solo/Relva | 2 298 | 2 005 | −293 ha | −12,7% |
| Edificado | 5 395 | 5 714 | +319 ha | +5,9% |

O Porto perdeu 25 hectares de árvores e 293 hectares de solo/relva em menos de uma década. O edificado cresceu 319 hectares (+5,9%).

### Transições detectadas

| Transição | Área (ha) |
|-----------|-----------|
| Árvores → Edificado | 49 |
| Árvores → Solo | 126 |
| Solo → Edificado | 221 |
| Solo → Árvores | 127 |

A maior perda vem da conversão de solo em edificado (221 ha). A perda de árvores para construção (49 ha) é menor mas irreversível. Nota positiva: 127 ha de solo foram convertidos em árvores, quase compensando as perdas directas.

### Mapa interativo (2016–2025)

**[Abrir mapa detalhado (2016–2025)]({{ site.baseurl }}/mapa.html)**

---

## Metodologia

### Análise histórica (Landsat, 30 m)

- **Dados:** Landsat 5 TM (1985–2005) e Landsat 8/9 OLI (2016–2024), Collection 2 Level 2
- **Composição:** mediana do NDVI de verão (Junho–Setembro), agregando 5–6 anos por época
- **Harmonização:** coeficientes OLI→TM de Roy et al. (2016) + normalização PIF com regressão linear
- **Classificação:** limiar de NDVI ≥ 0,3 para vegetação
- **Cenas utilizadas:** 54 a 70 por época

### Análise detalhada (Sentinel-2, 10 m)

A classificação combina análise **temporal** e **espectral** para distinguir árvores de relva — um problema clássico em deteção remota a 10 metros.

A chave é que árvores e relva têm comportamentos sazonais opostos:
- **Final de Maio/Junho:** árvores têm copa completa (NDVI alto), relva está tipicamente seca ou cortada (NDVI baixo)
- **Verão (Julho–Setembro):** ambas podem ter NDVI alto (relva regada)
- **Inverno:** árvores caducifólias perdem folha, relva de inverno pode ser muito verde

#### Regras de classificação

```
Árvores:
  NDVI verão (mediana Mai–Out) >= 0,5
  NDVI primavera (percentil 15, Mai–Jun) >= 0,7   [relva seca, árvores com folha]
  NDVI mínimo (percentil 10, anual) >= 0,3         [tolerante para caducifólias]
  NIR/Green >= 4                                    [filtra relva regada]
  B3 < 600, ou B3 < 800 se NDVI_min >= 0,5         [árvores claras com NDVI estável]

Verde urbano (árvores mistas, ruas arborizadas):
  NDVI verão >= 0,5
  NDVI primavera >= 0,5
  NDVI mínimo >= 0,2
  B3 < 600, ou B3 < 800 se NDVI_min >= 0,5

Edificado:
  (NDVI < 0,2 E NDBI >= −0,1) OU desempate ESA WorldCover

Solo/Relva: tudo o resto
```

#### Calibração

Os limiares foram calibrados iterativamente:

1. **Área de teste** — 1 500 m em redor de Serralves para ajuste rápido
2. **Análise pixel-a-pixel** — comparação de píxeis de relva conhecida vs árvores conhecidas
3. **Série temporal** — 81 cenas Sentinel-2 para descobrir a janela sazonal ideal
4. **Clustering K-means** (k=2 a 10) com bandas Red Edge para validar separabilidade
5. **Validação contra ESA WorldCover 2021** — precisão de 90,4% na identificação de árvores

A análise temporal revelou que o melhor discriminador é o **NDVI de final de Maio/início de Junho** — nessa janela, árvores mantêm NDVI > 0,7 enquanto relva cai para < 0,3.

---

## Código

Todo o pipeline está disponível no repositório:

- [`ndvi_historico.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/ndvi_historico.py) — análise histórica 1985–2024 (Landsat + normalização PIF)
- [`porto_publish.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/porto_publish.py) — pipeline Sentinel-2 (classificação + mapa)
- [`test_area.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/test_area.py) — calibração na área de teste
- [`porto_stats.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/porto_stats.py) — cálculo de estatísticas
- [`animacao/animacao_cairo.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/animacao/animacao_cairo.py) — animação vectorial Cairo com interpolação bienal

---

## Próximos passos

- Cruzar com dados de licenciamento urbanístico da CMP para correlacionar picos de construção com perda de vegetação
- Analisar a distribuição espacial da perda por freguesia, identificando quais sofreram maior pressão
- Comparar com a ortofotografia de 1947 para contextualizar a escala da transformação urbana do Porto ao longo de quase 80 anos
