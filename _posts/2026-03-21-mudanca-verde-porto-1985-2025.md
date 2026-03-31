---
layout: post
title: "Dinâmicas de Ocupação do Solo e Cobertura Vegetal na Cidade do Porto (1985–2025)"
description: "Análise quantitativa da evolução do solo e vegetação no Porto entre 1985 e 2025, com dados Sentinel-2, Landsat e NDVI via Google Earth Engine."
date: 2026-03-21
tags: [porto, sentinel-2, landsat, ndvi, gee, vegetação, animação, deteção remota]
---

**Dinâmicas de Ocupação do Solo e Cobertura Vegetal na Cidade do Porto (1985–2025): Uma Análise Quantitativa Baseada em Deteção Remota**

---

## 1. Introdução

O espaço verde urbano desempenha um papel ecológico e social insubstituível, fornecendo serviços de ecossistema vitais — desde a mitigação do efeito de ilha de calor até à promoção da saúde pública, regulação hidrológica e manutenção da biodiversidade (Madureira *et al.*, 2018). Contudo, nas últimas décadas, a cidade do Porto tem sido palco de uma intensa transformação territorial, com a progressiva conversão de solos permeáveis em superfícies impermeabilizadas.

Monteiro *et al.* (2025) demonstraram recentemente que 32,6% do território municipal se encontra em zonas de elevado risco térmico, com a intensidade da ilha de calor urbana (UHI) particularmente pronunciada durante as noites de verão — um fenómeno agravado pela escassez de infraestrutura verde, sobretudo em áreas socioeconomicamente desfavorecidas. A quantificação rigorosa da evolução da cobertura vegetal torna-se, assim, não apenas um exercício académico mas um instrumento de planeamento urbano com implicações diretas na saúde pública e na resiliência climática.

Utilizando imagens de satélite e algoritmos processados em *Google Earth Engine*, este trabalho analisa a evolução quantitativa e espacial da vegetação no município do Porto ao longo de 40 anos. Através da conjugação de dados multitemporais de média resolução (Landsat a 30 m) e de alta resolução (Sentinel-2 a 10 m), avalia-se o ritmo da expansão do edificado à custa dos espaços verdes, o balanço líquido de perdas e ganhos, e a tipologia da vegetação afetada. Os resultados dialogam diretamente com a literatura existente, atualizando e validando os padrões documentados por Guilherme *et al.* (2022) e Madureira *et al.* (2011) através de deteção remota espectral e temporal.

- **Animação do crescimento urbano 1987–2024** — evolução bienal vectorial em 4K
- **Análise histórica 1985–2024** — Landsat a 30 m, com NDVI harmonizado entre sensores
- **Análise detalhada 2016–2025** — Sentinel-2 a 10 m, com classificação árvores/solo/edificado

---

## 2. Enquadramento e Revisão da Literatura

A evolução da estrutura verde do Porto tem sido documentada por diversos autores, que evidenciam um padrão histórico de declínio das áreas permeáveis e de forte densificação urbana. Madureira *et al.* (2011) demonstraram que, no final do século XIX (1892), cerca de 75% da superfície do concelho era ocupada por coberto verde — predominantemente agrícola e florestal. Em 2000, esse valor havia decaído para aproximadamente 30%, uma transformação impulsionada por uma redução de 92% na tipologia de verde agrícola e de 52% no verde arborizado. Os mesmos autores descrevem o processo de planeamento ao longo do século XX como "uma oportunidade perdida" para a manutenção de uma estrutura verde contínua e multifuncional, resultando numa paisagem altamente fragmentada de manchas pequenas e isoladas (Madureira & Andresen, 2014).

Estudos mais recentes e de elevada granularidade espacial confirmam esta trajetória. Guilherme *et al.* (2022), numa análise baseada em fotografia aérea e classificação supervisionada, demonstraram que a superfície de Elementos Construídos Artificiais (ABE) no Porto duplicou de 31% em 1947 para 62% em 2019. A perda de vegetação foi, no entanto, **fortemente assimétrica em termos tipológicos**: a cobertura arbórea e arbustiva (TRS) manteve-se surpreendentemente estável e resiliente, variando apenas entre 22% e 25% ao longo de sete décadas, ao passo que a vegetação herbácea e os solos agrícolas (HER) colapsaram de 40% para cerca de 10%.

Esta discrepância reflete-se geograficamente: a zona norte da cidade experienciou uma rápida expansão urbana à custa de solos agrícolas; a zona ocidental fragmentou-se mas manteve grandes manchas arbóreas em jardins privados e parques públicos; e a zona oriental viu o seu uso agrícola parcialmente substituído por vegetação arbustiva espontânea e novos loteamentos. Trabalhos subsequentes do mesmo grupo (Guilherme *et al.*, 2023; 2024) demonstraram que as manchas de vegetação mais antigas albergam maior riqueza específica, e que aves, répteis e anfíbios respondem positivamente à continuidade temporal do coberto vegetal — reforçando a importância ecológica não apenas da extensão, mas da permanência da vegetação urbana.

Do ponto de vista da expansão urbanística, o crescimento não tem sido constante, caracterizando-se por fases de expansão periférica e subsequente densificação e preenchimento de vazios urbanos. Quental (2010) quantificou a expansão urbana do município em 276 hectares na década de 1990–2000 e em 169 hectares no período de 2000–2006, apontando para um abrandamento do consumo de novos solos na viragem do milénio.

Quanto aos serviços de ecossistema prestados pela infraestrutura verde remanescente, Madureira *et al.* (2018) mapearam 95 espaços verdes urbanos de acesso público (79 parques/jardins e 16 jardins de praça), documentando os seus contributos para a purificação do ar, regulação térmica, redução de ruído, sequestro de carbono e infiltração de águas pluviais. A matriz atual de espaços verdes públicos totaliza aproximadamente 424 hectares — um rácio de 18,3 m² por habitante, valor superior ao mínimo recomendado pela OMS (9 m²/hab.), embora a sua distribuição espacial continue a ser geograficamente desigual no contexto da "cidade dos 15 minutos".

---

## 3. Animação: 37 anos de crescimento urbano

<video controls width="100%" poster="{{ site.baseurl }}/animacao/frame_2024.png">
  <source src="{{ site.baseurl }}/animacao/animacao_cairo.mp4" type="video/mp4">
</video>

A animação mostra a evolução bienal do Porto entre 1987 e 2024, com dados interpolados a partir das cinco épocas de classificação Landsat. Cada cor representa uma era de construção diferente — do castanho escuro (pré-1990) ao magenta (2023–24) — enquanto o verde recua progressivamente.

---

## 4. Metodologia

Para garantir rigor na avaliação de uma série temporal de 40 anos e contornar os desafios inerentes à variabilidade de sensores, a metodologia foi estruturada em duas abordagens complementares.

### 4.1. Análise Histórica (1985–2024) com Landsat (30 m)

A comparação direta entre os sensores *Thematic Mapper* (TM, Landsat 5) e *Operational Land Imager* (OLI, Landsat 8/9) requer correção radiométrica, visto que as diferentes respostas espectrais inflacionam sistematicamente o NDVI no Landsat 8. Para mitigar este enviesamento, aplicou-se um duplo nível de harmonização:

1. **Transformação linear das bandas Red e NIR** através dos coeficientes de Roy *et al.* (2016), convertendo as reflectâncias OLI para o espaço espectral do TM.
2. **Normalização por Alvos Pseudo-Invariantes (PIF)**, utilizando 6 pontos de calibração empiricamente estáveis ao longo de 40 anos:
   - **Água** (Douro e Oceano Atlântico) — NDVI ≈ 0
   - **Solo nu** — NDVI intermédio
   - **Manchas florestais maduras** (Serralves e Parque da Cidade) — NDVI elevado

Para cada época, extraiu-se o NDVI nestes pontos de referência e calculou-se uma regressão linear que alinha os valores com a época de referência (1985–90), corrigindo simultaneamente diferenças de sensor, atmosfera e calibração. A vegetação foi classificada com um limiar de **NDVI ≥ 0,25** aplicado à mediana de verão (Junho–Setembro), agregando entre 54 e 70 cenas por época.

### 4.2. Análise Detalhada (2016–2025) com Sentinel-2 (10 m)

A classificação granular exigiu a separação entre estrato arbóreo e estrato herbáceo/solo — um problema clássico em deteção remota a 10 metros de resolução. O algoritmo explorou as **assinaturas sazonais divergentes** destas tipologias: enquanto as árvores mantêm NDVI elevado (> 0,7) no final de Maio/início de Junho, o estrato herbáceo (frequentemente não regado ou cortado) apresenta uma quebra acentuada no sinal (NDVI < 0,3).

**Regras de classificação:**

```
Árvores:
  NDVI verão (mediana Mai–Out) ≥ 0,5
  NDVI primavera (percentil 15, Mai–Jun) ≥ 0,7   [relva seca, árvores com folha]
  NDVI mínimo (percentil 10, anual) ≥ 0,3         [tolerante para caducifólias]
  NIR/Green ≥ 4                                    [filtra relva regada]
  B3 < 600, ou B3 < 800 se NDVI_min ≥ 0,5         [árvores claras com NDVI estável]

Verde urbano (árvores mistas, ruas arborizadas):
  NDVI verão ≥ 0,5
  NDVI primavera ≥ 0,5
  NDVI mínimo ≥ 0,2
  B3 < 600, ou B3 < 800 se NDVI_min ≥ 0,5

Edificado:
  (NDVI < 0,2 E NDBI ≥ −0,1) OU desempate ESA WorldCover

Solo/Relva: tudo o resto
```

O *pipeline* incluiu a análise de **81 cenas Sentinel-2**, validação de separabilidade via *clustering K-means* (k=2 a 10) nas bandas *Red Edge*, e filtragem do edificado conjugando o NDBI (Índice de Diferença Normalizada do Edificado) com a máscara *ESA WorldCover 2021*. A análise temporal revelou que o melhor discriminador é o NDVI de final de Maio/início de Junho — nessa janela, árvores mantêm NDVI > 0,7 enquanto a relva cai para < 0,3. A validação cruzada com o *ESA WorldCover 2021* atingiu uma precisão de **90,4%** na identificação de árvores.

---

## 5. Resultados e Discussão

### 5.1. Evolução Histórica e Ritmos de Perda (1985–2024)

A análise longitudinal da série Landsat revela que a cidade do Porto passou de uma cobertura vegetal (NDVI ≥ 0,25) de **45,0% (5 352 ha)** no final da década de 1980 para **30,0% (3 567 ha)** em 2024. Este decréscimo representa uma **perda líquida de 1 785 hectares** — um valor altamente congruente com a evidência de Guilherme *et al.* (2022), que aponta para 62% de ocupação artificial do solo em 2019 (deixando cerca de 38% para solos permeáveis e verdes).

| Época | Satélite | Área verde (ha) | % do município |
|-------|----------|----------------|----------------|
| 1985–90 | Landsat 5 | 5 352 | **45,0%** |
| 1995–00 | Landsat 5 | 4 240 | 35,6% |
| 2001–05 | Landsat 5 | 3 572 | 30,0% |
| 2016–17 | Landsat 8 | 3 732 | 31,4% |
| 2023–24 | Landsat 8 | 3 567 | **30,0%** |

O balanço bruto entre 1987 e 2024 quantifica-se em **2 266 hectares de vegetação destruída** contra **481 hectares de vegetação ganha**. A dinâmica desta perda balizou-se em três fases cronológicas distintas:

#### Fase I — 1987–2003: Expansão Acelerada

Perda de 1 780 hectares a uma taxa de **111 ha/ano**. Este período reflete o pico da expansão urbana sobre as antigas periferias agrícolas do concelho — Paranhos, Ramalde e Campanhã. Estes dados corroboram as estatísticas de Quental (2010), que identificou a década de 1990 como o período de maior e mais intenso crescimento do edificado no Porto (276 ha de nova expansão urbana).

#### Fase II — 2003–2016: Estabilização e Recuperação

Observou-se uma ténue recuperação (+160 ha, +12 ha/ano). Este abrandamento espelha a confluência de múltiplos fatores: a exaustão dos solos limpos disponíveis para urbanização; a crise económica do setor imobiliário (2008–2013); a maturação de novas infraestruturas verdes públicas construídas no fim dos anos 90; e a colonização espontânea de terrenos agrícolas abandonados por vegetação arbustiva — fenómeno também documentado na zona oriental da cidade por Guilherme *et al.* (2022). Relaciona-se igualmente com os ritmos decrescentes de expansão bruta medidos por Quental para o início dos anos 2000 (redução de 276 ha para 169 ha de nova urbanização).

#### Fase III — 2017–2024: Nova Pressão Urbana e Densificação

A cidade regressa a uma trajetória de **perda acelerada (−165 ha em 8 anos)**, refletindo a retoma do mercado imobiliário e o *boom* turístico pós-2015. O padrão de crescimento alterou-se qualitativamente: já não se trata de expansão centrífuga sobre periferias rurais, mas de **densificação e preenchimento de vazios intraurbanos** — o que explica a dispersão espacial das novas construções por todo o tecido urbano existente.

#### Evolução bienal interpolada

| Ano | Vegetação (ha) | % do município | Variação vs 1987 |
|-----|---------------|----------------|------------------|
| 1987 | 5 352 | **45,0%** | — |
| 1991 | 4 907 | 41,3% | −445 ha |
| 1997 | 4 240 | 35,6% | −1 112 ha |
| 2003 | 3 572 | **30,0%** | −1 780 ha |
| 2009 | 3 646 | 30,7% | −1 706 ha |
| 2016 | 3 732 | 31,4% | −1 620 ha |
| 2024 | 3 567 | **30,0%** | **−1 785 ha** |

### 5.2. Padrões Espaciais de Transformação

A distribuição geográfica da perda de vegetação confirma a evolução assimétrica documentada na literatura:

- **Zona Ocidental (Foz, Nevogilde, Aldoar):** demonstrou ser a mais resiliente, mantendo elevados níveis de cobertura vegetal não apenas graças ao Parque da Cidade (80 ha), mas ao tecido residencial de baixa densidade com jardins privados significativos. Mesmo em 2024, esta zona permanece maioritariamente verde.

- **Centro Histórico (Sé, Miragaia, Cedofeita):** sofreu alterações marginais por já se encontrar profundamente impermeabilizado no arranque da série temporal (década de 1980). Não havia verde para perder.

- **Periferias Norte e Este (Paranhos, Ramalde, Campanhã):** sofreram a maior transformação. As grandes quintas e áreas agrícolas visíveis em 1987 foram inteiramente reconfiguradas ao longo dos eixos viários, dando lugar a um *continuum* edificado. Esta distribuição valida a tese de que a **acessibilidade viária foi o vetor primordial do crescimento urbano**, um padrão consistente com a dinâmica observada por Guilherme *et al.* (2022) para a zona norte da cidade.

### 5.3. Análise Granular e Tipológica (2016–2025)

A dissecação da última década com recurso ao Sentinel-2 (10 m) introduz uma camada analítica crítica, permitindo distinguir entre cobertura arbórea e herbácea.

| Classe | 2016–17 (ha) | 2024–25 (ha) | Mudança | % |
|--------|-------------|-------------|---------|---|
| **Árvores** | 1 254 | 1 229 | **−25 ha** | −2,0% |
| Solo/Relva | 2 298 | 2 005 | −293 ha | −12,7% |
| Edificado | 5 395 | 5 714 | +319 ha | +5,9% |

Entre 2016 e 2025, a cidade perdeu 25 hectares de cobertura arbórea (−2,0%) mas **293 hectares de cobertura herbácea e solos permeáveis** (−12,7%). Concomitantemente, o edificado cresceu 319 hectares (+5,9%).

#### Transições de uso do solo

| Transição | Área (ha) |
|-----------|-----------|
| Árvores → Edificado | 49 |
| Árvores → Solo | 126 |
| Solo → Edificado | **221** |
| Solo → Árvores | 127 |

Da análise de transições, sobressai que a **força motriz do crescimento urbano atual é a conversão de solo/relva em edificado** (221 ha), enquanto a conversão direta de áreas florestadas em edificado se limitou a 49 ha. Estes resultados empíricos validam a tese central de Guilherme *et al.* (2022): perante a urbanização, a cobertura arbórea (TRS) tende a ser preservada — protegida por dinâmicas de planeamento, parques públicos e propriedades privadas — enquanto as áreas herbáceas e agrícolas (HER) são sumariamente suprimidas pelo avanço da impermeabilização.

Nota positiva: o algoritmo detetou **127 hectares de solo/relva que transitaram para a classe arbórea**, indicando esforços recentes de arborização — potencialmente associados ao programa *FUN Porto* (Florestas Urbanas Nativas), que distribuiu cerca de 10 000 árvores a residentes desde 2016 — e o crescimento natural do dossel das copas. Este ganho compensa parcialmente as perdas ecológicas estruturais, embora a substituição funcional de solo permeável por copa arbórea não seja equivalente em termos de serviços hidrológicos.

---

## 6. Conclusões

A integração de dados de satélite de média e alta resolução espacial permite afirmar, com elevada precisão quantitativa, que o Porto perdeu **um terço da sua matriz verde histórica** ao longo dos últimos 40 anos (−1 785 hectares). O trabalho demonstra que esta perda foi de natureza fortemente tipológica: vitimou sobretudo os solos outrora agrícolas e prados abertos (cobertura herbácea), enquanto a estrutura arbórea manteve uma **resiliência notável** perante a pressão urbanística — um padrão consistente ao longo de múltiplas escalas temporais e espaciais, e convergente com as conclusões independentes de Guilherme *et al.* (2022) baseadas em fotointerpretação.

Ao melhorar a metodologia de calibração espectral multitemporal (PIF) e a filtragem fenológica sazonal, esta análise oferece um diagnóstico reprodutível e atualizado. A ausência de estudos publicados que analisem a série temporal NDVI do Porto a partir de Landsat para o período 1985–2024 confere originalidade a este contributo.

Os resultados acarretam implicações diretas para o planeamento urbano. Dado que 32,6% do município se encontra em zonas de elevado risco térmico (Monteiro *et al.*, 2025), e que a perda de vegetação se concentra nos solos permeáveis herbáceos — fundamentais para a regulação hidrológica e a mitigação do escoamento superficial —, torna-se imperativo que as futuras políticas urbanísticas foquem não apenas na proteção do estrato arbóreo, mas também na **fixação e permeabilidade dos últimos redutos de solo e cobertura herbácea**. A resiliência da cobertura arbórea, embora encorajadora, não deve obscurecer o colapso silencioso dos solos permeáveis — o substrato ecológico que sustenta a capacidade de infiltração, a recarga de aquíferos e a regulação microclimática à escala do bairro.

---

## 7. Referências

- Guilherme, F., Garcia Moreno, E., Gonçalves, J.A., Carretero, M.A. & Farinha-Marques, P. (2022). Looking Closer at the Patterns of Land Cover in the City of Porto, Portugal, between 1947 and 2019. *Land*, 11(10), 1828.
- Guilherme, F. *et al.* (2023). Assessment of land cover trajectories as an indicator of urban habitat temporal continuity. *Landscape and Urban Planning*.
- Guilherme, F. *et al.* (2024). Mapping multigroup responses to land cover legacy for urban biodiversity conservation. *Biological Conservation*.
- Madureira, H., Andresen, T. & Monteiro, A. (2011). Green structure and planning evolution in Porto. *Urban Forestry & Urban Greening*, 10(2), 141–149.
- Madureira, H. & Andresen, T. (2014). Planning for multifunctional urban green infrastructures: Promises and challenges. *Urban Design International*, 19, 38–49.
- Madureira, H. *et al.* (2018). Assessing how green space types affect ecosystem services delivery in Porto, Portugal. *Landscape and Urban Planning*, 170, 286–297.
- Monteiro, A. *et al.* (2025). Green infrastructure and its influence on urban heat island, heat risk, and air pollution: A case study of Porto. *Journal of Environmental Management*, 376, 124446.
- Quental, N. (2010). Expansão urbana no município do Porto. *Relatório técnico*.
- Roy, D.P. *et al.* (2016). Characterization of Landsat-7 to Landsat-8 reflective wavelength and normalized difference vegetation index continuity. *Remote Sensing of Environment*, 185, 57–70.

---

## Mapas interativos

- **[Mapa histórico (1985–2024)]({{ site.baseurl }}/ndvi_historico.html)** — alternância entre épocas, máscaras de vegetação, zonas de perda e ganho
- **[Mapa detalhado (2016–2025)]({{ site.baseurl }}/mapa.html)** — classificação árvores/solo/edificado a 10 m

---

## Código

Todo o *pipeline* está disponível no repositório:

- [`ndvi_historico.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/ndvi_historico.py) — análise histórica 1985–2024 (Landsat + normalização PIF)
- [`porto_publish.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/porto_publish.py) — pipeline Sentinel-2 (classificação + mapa)
- [`test_area.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/test_area.py) — calibração na área de teste
- [`porto_stats.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/porto_stats.py) — cálculo de estatísticas
- [`animacao/animacao_cairo.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/animacao/animacao_cairo.py) — animação vectorial Cairo com interpolação bienal
