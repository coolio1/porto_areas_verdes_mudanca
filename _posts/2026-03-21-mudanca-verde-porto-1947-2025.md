---
layout: post
title: "Dinâmicas de Ocupação do Solo e Cobertura Vegetal na Cidade do Porto (1947–2025)"
description: "Análise quantitativa da vegetação no Porto entre 1947 e 2025 (ortofotomapa de 1947, Landsat e Sentinel-2), corrigida em Novembro de 2026: sem tendência detectável de perda de vegetação desde 1985."
date: 2026-03-21
tema: dados
image: /assets/images/artigo-mudanca-solo.jpg
tags: [porto, sentinel-2, landsat, ndvi, gee, vegetação, animação, deteção remota, ortofoto, 1947]
---

**Dinâmicas de Ocupação do Solo e Cobertura Vegetal na Cidade do Porto (1947–2025): Uma Análise Quantitativa Baseada em Deteção Remota**

> **Actualização de 18 de Novembro de 2026.** A primeira versão deste artigo concluía que o Porto tinha perdido cerca de um terço da vegetação desde 1985 (de 45,0 % para 30,0 % da área analisada, que era maior do que o concelho). Essa queda era em grande parte **artificial**: vinha da normalização entre sensores Landsat e de um limiar fixo de NDVI (índice de vegetação por diferença normalizada) que contava como vegetação 27 % do que já estava construído em 1979. Com a ponte de sensor corrigida, a vegetação calculada por píxel e as incertezas, a série de satélite **não mostra perda detectável entre 1985 e 2024** (32,6 % → 35,3 %, ±1,4 p.p.). Os números do concelho (e só do concelho) foram recalculados e as secções 4.2, 5 e 6 reescritas. Método e limites: [docs/historico_ponte_landsat7.md](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/docs/historico_ponte_landsat7.md).


---

## 1. Introdução

O espaço verde urbano desempenha um papel ecológico e social insubstituível, fornecendo serviços de ecossistema vitais — desde a mitigação do efeito de ilha de calor até à promoção da saúde pública, regulação hidrológica e manutenção da biodiversidade (Graça *et al.*, 2018). Contudo, nos últimos séculos, a cidade do Porto tem sido palco de uma intensa transformação territorial, ao longo do século XX, com a progressiva conversão de solos permeáveis em superfícies impermeabilizadas.

Lopes *et al.* (2025) demonstraram recentemente que 32,6% do território municipal se encontra em zonas de elevado risco térmico, com a intensidade da ilha de calor urbana (UHI) particularmente pronunciada durante as noites de verão — um fenómeno agravado pela escassez de infraestrutura verde, sobretudo em áreas socioeconomicamente desfavorecidas. A quantificação rigorosa da evolução da cobertura vegetal torna-se, assim, não apenas um exercício académico mas um instrumento de planeamento urbano com implicações diretas na saúde pública e na resiliência climática.

Utilizando fotografia aérea histórica e imagens de satélite processadas em *Google Earth Engine*, este trabalho analisa a evolução quantitativa e espacial da vegetação no município do Porto ao longo de quase 80 anos. Através da conjugação de um ortofotomapa aéreo de 1947 (0,49 m/pixel), dados multitemporais de média resolução (Landsat a 30 m) e de alta resolução (Sentinel-2 a 10 m), avalia-se o balanço de perdas e ganhos de vegetação e a tipologia da vegetação afetada. Os resultados são confrontados com Guilherme *et al.* (2022) e Madureira *et al.* (2011); onde não coincidem, o artigo di-lo.


- **Classificação do ortofoto aéreo de 1947** — Random Forest sobre textura local a 0,49 m
- **Animação do crescimento urbano 1987–2024** — evolução bienal vectorial em 4K
- **Análise histórica 1985–2024** — Landsat a 30 m, com ponte de sensor (Landsat 7), fracção de vegetação por píxel e incerteza
- **Análise detalhada 2016–2025** — Sentinel-2 a 10 m, com classificação árvores/solo/edificado

---

## 2. Enquadramento e Revisão da Literatura

A evolução da estrutura verde do Porto tem sido documentada por diversos autores, que evidenciam um padrão histórico de declínio das áreas permeáveis e de forte densificação urbana. Madureira *et al.* (2011) demonstraram que, no final do século XIX (1892), cerca de 75% da superfície do concelho era ocupada por coberto verde — predominantemente agrícola e florestal. Em 2000, esse valor havia decaído para aproximadamente 30%, uma transformação impulsionada por uma redução de 92% na tipologia de verde agrícola e de 52% no verde arborizado. Os mesmos autores descrevem o processo de planeamento ao longo do século XX como "uma oportunidade perdida" para a manutenção de uma estrutura verde contínua e multifuncional, resultando numa paisagem altamente fragmentada de manchas pequenas e isoladas (Madureira & Andresen, 2014).

Estudos mais recentes e de elevada granularidade espacial confirmam esta trajetória. Guilherme *et al.* (2022), numa análise baseada em fotografia aérea e classificação supervisionada, demonstraram que a superfície de Elementos Construídos Artificiais (ABE) no Porto duplicou de 31% em 1947 para 62% em 2019. A análise da época de 1947 — tanto nesse estudo como no presente trabalho — assenta nos ortofotomapas históricos georreferenciados e ortorrectificados por Gonçalves, Pinhal & Lino (s.d.) a partir das 24 fotografias aéreas do voo SPLAL de 1947, disponibilizados online pela Faculdade de Ciências da Universidade do Porto. A perda de vegetação foi, no entanto, **fortemente assimétrica em termos tipológicos**: a cobertura arbórea e arbustiva (TRS) manteve-se surpreendentemente estável e resiliente, variando apenas entre 22% e 25% ao longo de sete décadas, ao passo que a vegetação herbácea e os solos agrícolas (HER) colapsaram de 40% para cerca de 10%.

Esta discrepância reflete-se geograficamente: a zona norte da cidade experienciou uma rápida expansão urbana à custa de solos agrícolas; a zona ocidental fragmentou-se mas manteve grandes manchas arbóreas em jardins privados e parques públicos; e a zona oriental viu o seu uso agrícola parcialmente substituído por vegetação arbustiva espontânea e novos loteamentos. Trabalhos subsequentes do mesmo grupo (Guilherme *et al.*, 2024a; 2024b) demonstraram que as manchas de vegetação mais antigas albergam maior riqueza específica, e que aves, répteis e anfíbios respondem positivamente à continuidade temporal do coberto vegetal — reforçando a importância ecológica não apenas da extensão, mas da permanência da vegetação urbana.

Do ponto de vista da expansão urbanística, o crescimento não tem sido constante, caracterizando-se por fases de expansão periférica e subsequente densificação e preenchimento de vazios urbanos. Quental (2010) quantificou a expansão urbana do município em 276 hectares na década de 1990–2000 e em 169 hectares no período de 2000–2006, apontando para um abrandamento do consumo de novos solos na viragem do milénio.

Quanto aos serviços de ecossistema prestados pela infraestrutura verde remanescente, Graça *et al.* (2018) mapearam 95 espaços verdes urbanos de acesso público (79 parques/jardins e 16 jardins de praça), documentando os seus contributos para a purificação do ar, regulação térmica, redução de ruído, sequestro de carbono e infiltração de águas pluviais. A matriz atual de espaços verdes públicos totaliza aproximadamente 424 hectares — um rácio de 18,3 m² por habitante, valor superior ao mínimo recomendado pela OMS (9 m²/hab.), embora a sua distribuição espacial continue a ser geograficamente desigual no contexto da "cidade dos 15 minutos".

---

## 3. Animação: 37 anos de crescimento urbano

<video controls width="100%" poster="{{ site.baseurl }}/animacao/frame_2024.png">
  <source src="{{ site.baseurl }}/animacao/animacao_cairo.mp4" type="video/mp4">
</video>


A animação mostra a evolução bienal do Porto entre 1987 e 2024, interpolada a partir das cinco épocas de classificação Landsat. **Atenção:** foi construída com a série anterior (limiar NDVI ≥ 0,25 e normalização por alvos pseudo-invariantes), que exagerava a perda de vegetação. Não corresponde à série corrigida da secção 5.2 e serve só de ilustração da expansão do edificado; está por refazer.

---


## 4. Metodologia

Para garantir rigor na avaliação de uma série temporal de quase 80 anos e contornar os desafios inerentes à variabilidade de sensores e fontes, a metodologia foi estruturada em três abordagens complementares.

### 4.1. Classificação do Ortofoto Aéreo de 1947 (0,49 m)

A análise do período pré-satélite baseou-se nos ortofotomapas históricos georreferenciados e ortorrectificados por Gonçalves, Pinhal & Lino (s.d.) a partir das 24 fotografias aéreas do voo SPLAL de 1947, servidos via WMS pelo CIIMAR/FCUP. O ortofoto, em escala de cinzentos, foi processado por *tiles* de 1 km × 1 km a 2048 × 2048 pixels (resolução efetiva de 0,49 m/pixel), cobrindo toda a área do município com uma grelha de 18 × 9 *tiles*.

A classificação em duas classes — **vegetação** e **edificado** — utilizou um modelo *Random Forest* (100 árvores) treinado sobre quatro *features* de textura local extraídas de cada pixel: intensidade média, média local (janela), desvio-padrão local e gradiente. Os pontos de treino foram selecionados manualmente a partir de coordenadas fornecidas pelo utilizador, abrangendo 13 amostras de vegetação e 5 de edificado em zonas diversas do município. A máscara do limite municipal foi obtida via GEE (CAOP 2025), e fragmentos classificados inferiores a um limiar mínimo de pixels foram removidos por filtragem morfológica.

Após a classificação inicial, um segundo *pipeline* de limpeza cruzou os resultados com camadas independentes — a vegetação Landsat de 1985, as árvores e solo Sentinel-2 actuais — para remover falsos positivos de edificado em zonas comprovadamente verdes. Um filtro de maioria (15 × 15 pixels) suavizou o ruído residual. A máscara do rio Douro foi excluída (transparente) para não contaminar as estatísticas.


### 4.2. Análise Histórica (1985–2024) com Landsat (30 m)

A primeira versão harmonizava os sensores com os coeficientes de Roy *et al.* (2016) e uma regressão em alvos pseudo-invariantes (PIF), e contava como vegetação todo o píxel com NDVI ≥ 0,25. Os dois passos foram abandonados, por três razões medidas:

- **Salto de sensor, não de paisagem.** Landsat 5 e Landsat 7 dão o mesmo resultado (49,8 e 49,5 % em 1999–2011, com o limiar antigo), mas Landsat 8/9 dá +7 a +9 p.p. sobre o 7 na sobreposição 2013–2021. A normalização PIF absorvia esse salto na série e criava uma queda artificial da ordem de 15 p.p. entre 1985–90 e 2023–24.
- **Limiar demasiado baixo.** A 30 m, NDVI ≥ 0,25 corresponde a só ~16 % de vegetação no píxel; 27 % do construído de 1979 contava como vegetação em 1985–90.
- **Sem incerteza.** Uma diferença de 1 a 3 p.p. de vegetação entre épocas não se distingue do ruído sem a medir.

O método actual:

1. **Controlo por cena e ponte de sensor.** Cada cena Landsat (Junho–Setembro) é medida em áreas que não mudaram — construído em 1979 e ainda construído em 2024, e árvores em 1979 e ainda árvores em 2024. Uma cena cujo NDVI nessas áreas foge ao resto do seu sensor é névoa ou nuvem não mascarada, não paisagem: 102 de 721 cenas (14 %) foram excluídas (em 2002, todas as do Landsat 5). O Landsat 5 fica em reflectância de superfície sem correcção e, a partir de 1999, junta-se-lhe o Landsat 7 (mesmas bandas), o que duplica as cenas de cada época. O Landsat 8/9 passa à escala do Landsat 7 por uma recta (NDVI₇ = −0,020 + 0,959·NDVI₈) calculada nessas duas áreas na sobreposição de 2013 a 2021, porque o desvio entre sensores não é constante (0,026 no construído, 0,051 nas árvores). Compósitos de mediana de Junho a Setembro.
2. **Fracção de vegetação por píxel.** Uma curva monótona NDVI → fracção (regressão isotónica) calibrada em 2023–24 contra as classes «árvores» e «solo/relva» do Sentinel-2 (secção 4.3), e aplicada a todas as épocas. O píxel passa a contar pela fracção (não por 0 ou 1) e a fracção de 50 % corresponde a NDVI ≈ 0,36.
3. **Só o concelho.** Percentagens e hectares contam apenas píxeis dentro do Porto (CAOP 2025, 4 142 ha), sem água permanente.
4. **Incerteza (1σ).** Erro-padrão da percentagem anual dentro de cada época, somado em quadratura ao erro da ponte (resíduo +0,6 ± 0,5 p.p.).
5. **Perda e ganho.** Variação da fracção ≥ 0,30 entre o início (média de 1985–90 e 1995–00) e o fim (média de 2016–17 e 2023–24), em manchas contínuas ≥ 0,5 ha.

**Limite principal:** a referência de calibração é uma classificação de satélite (Sentinel-2), não verdade de terreno. A ortofoto DGT de 2025 foi tentada e não serve (só RGB: as copas escuras ficam cinzentas).


### 4.3. Análise Detalhada (2016–2025) com Sentinel-2 (10 m)

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

O *pipeline* incluiu a análise de **81 cenas Sentinel-2**, validação de separabilidade via *clustering K-means* (k=2 a 10) nas bandas *Red Edge*, e filtragem do edificado conjugando o NDBI (Índice de Diferença Normalizada do Edificado) com a máscara *ESA WorldCover 2021*. A análise temporal revelou que o melhor discriminador é o NDVI de final de Maio/início de Junho — nessa janela, árvores mantêm NDVI > 0,7 enquanto a relva cai para < 0,3. A concordância com o mapa *ESA WorldCover 2021* (outro mapa de satélite, que também entra nas regras acima) foi de **90,4%** na identificação de árvores.


A tabela da secção 5.4 conta apenas o concelho do Porto (4 142 ha), não o rectângulo do mapa (≈ 8 900 ha) que a primeira versão usava por engano.

---



## 5. Resultados e Discussão

### 5.1. O Ponto de Partida: Porto em 1947

A classificação do ortofoto de 1947 (*Random Forest* sobre textura) deu 59,7 % de vegetação (2 473 ha) e 40,3 % de edificado (1 669 ha). Esse resultado bruto sobrestima o edificado, porque caminhos de terra, muros e afloramentos ficam classificados como edificado. A limpeza com camadas independentes (`1947/clean_1947.py`) converte edificado em vegetação onde as outras fontes mostram verde e dá **74,5 % de vegetação e 21,2 % de edificado** (os 4,3 % restantes ficam sem classe, como o rio), os valores que o mapa mostra. A limpeza só converte num sentido (edificado → vegetação): 74,5 % é um valor máximo, não uma medida.

Guilherme *et al.* (2022) obtiveram 31 % de elementos construídos artificiais (ABE) em 1947 por fotointerpretação, entre os 21 % (limpo) e os 40 % (bruto) daqui. Independentemente do número exacto, ambas as fontes coincidem no essencial: **em 1947 a maioria do concelho era permeável e vegetada**, com uma matriz de quintas, hortas e terrenos agrícolas pelas periferias de Paranhos, Ramalde e Campanhã, e a cidade densa restrita ao centro histórico e aos eixos oitocentistas.

### 5.2. Evolução Histórica (1985–2024)

| Época | Fonte | Vegetação (% do concelho) |
|-------|-------|---------------------------|
| 1947 | Ortofoto SPLAL, Random Forest + limpeza | 74,5 (não comparável) |
| 1979 | Cartografia de ocupação do solo de 1979 (árvores, arbustos e herbáceas) | 50,0 (não comparável) |
| 1985–90 | Landsat 5 | 32,6 ± 1,3 |
| 1995–00 | Landsat 5 e 7 | 33,1 ± 0,4 |
| 2001–05 | Landsat 5 e 7 | 30,8 ± 0,5 |
| 2016–17 | Landsat 8 (com ponte) | 34,7 ± 1,4 |
| 2023–24 | Landsat 8/9 (com ponte) | 35,3 ± 0,5 |

**1947 e 1979 não se comparam com a série Landsat nem entre si:** usam outras definições (contam herbáceas e campos como vegetação; 1947 tem a limpeza assimétrica da secção 5.1). A série Landsat é uma só fonte, um só método, e é essa que se pode ler como evolução.

Nessa série:

- **De 1985–90 a 2000 não há variação** (32,6 → 33,1 %).
- **2001–05 é o mínimo** (30,8 %), 2,3 p.p. abaixo de 1995–00. É frágil: com só o Landsat 5 dava 30,2 %, e nos mesmos anos o Landsat 7 dá valores mais altos; entre sensores, um mesmo ano difere até ±2 p.p., mais do que o erro indicado (±0,5). O ano mais baixo é 2005 (29,7 %), de seca extrema. A causa não foi apurada: pode ser clima, paisagem ou ruído de amostragem.
- **Entre 2001–05 e 2016–17 há recuperação** (+3,9 p.p.), que se mantém em 2023–24.
- **1985–90 → 2023–24: +2,7 p.p. (≈ +110 ha), com σ combinado de 1,4 p.p.**, ou seja, um aumento ligeiro, no limite do que a série distingue. **Não há tendência detectável de perda de vegetação nos satélites.**

O resultado é coerente com o tema «Hoje» do mapa (35,6 % de vegetação em 2024–25, que serviu de referência à calibração), pelo que a coincidência vem da construção e não é uma confirmação independente e com Guilherme *et al.* (2022): ~38 % do concelho sem elementos construídos em 2019 (100 − 62 %). **Não reproduz**, porém, a expansão urbana de 276 ha em 1990–2000 e 169 ha em 2000–2006 de Quental (2010): essa discrepância fica por esclarecer (as definições diferem: expansão do edificado e não fracção de vegetação, e 30 m não vê o preenchimento de logradouros).

Quanto a perda e ganho entre o início (1985–2000) e o fim (2016–2024) da série, em manchas ≥ 0,5 ha dentro do concelho: **cerca de 226 ha de perda e 286 ha de ganho** (saldo +59 ha, ≈ +1,4 p.p.). Este saldo é menor que a diferença das médias da série (+2,7 p.p., ≈ +110 ha) porque só conta manchas ≥ 0,5 ha com variação ≥ 0,30; os dois são do mesmo tamanho que a incerteza da série (±1,4 p.p., ≈ ±58 ha). A perda é uma realidade local, mas compensada por ganhos noutros sítios.

### 5.3. Padrões Espaciais de Transformação

Perda e ganho por freguesia (ha, manchas ≥ 0,5 ha; valores arredondados, a soma pode diferir do total em 1 ha; Cedofeita, Santo Ildefonso, Sé, Miragaia, São Nicolau e Vitória formam uma só união de freguesias):

| Freguesia | Perda | Ganho |
|-----------|-------|-------|
| Paranhos | 79 | 40 |
| Campanhã | 51 | 53 |
| Ramalde | 36 | 64 |
| Aldoar, Foz do Douro e Nevogilde | 35 | 51 |
| Lordelo do Ouro e Massarelos | 16 | 48 |
| Bonfim | 4 | 19 |
| Cedofeita, Santo Ildefonso, Sé, Miragaia, São Nicolau e Vitória | 6 | 11 |

- **Paranhos concentra a perda** (79 ha, 35 % do total) e é a única freguesia onde a perda supera o ganho com margem. Compatível com a conversão de terrenos agrícolas em edificado documentada por Guilherme *et al.* (2022) para o norte da cidade.
- **Campanhã** perde (50 ha) e ganha (56 ha) quase o mesmo: reconfiguração, não recuo.
- **Ramalde, Aldoar–Foz–Nevogilde e Lordelo–Massarelos** ganham mais do que perdem (novas arborizações, parques e maturação de copas), o que a série de satélite não separa de crescimento espontâneo de vegetação.
- **O centro histórico e Bonfim** têm pouca variação, por já estarem impermeabilizados no início da série.

A afirmação anterior de que a «acessibilidade viária foi o vector primordial do crescimento» **não foi testada** nesta análise e foi retirada.

### 5.4. Análise Granular e Tipológica (2016–2025)

O Sentinel-2 (10 m) separa cobertura arbórea de herbácea. Resultados dentro do concelho:

| Classe | 2016–17 (ha) | 2024–25 (ha) | Mudança | % |
|--------|-------------|-------------|---------|---|
| **Árvores** | 587 | 571 | −16 ha | −2,7 % |
| Solo/Relva | 1 059 | 900 | −159 ha | −15,1 % |
| Edificado | 2 496 | 2 671 | +175 ha | +7,0 % |

Em oito anos o concelho perdeu 16 ha de cobertura arbórea (−2,7 %) e 159 ha de solo permeável e relva (−15,1 %), enquanto o edificado cresceu 175 ha (+7,0 %). Dentro das árvores, as «puras» recuam (398 → 335 ha) e o «verde urbano» (árvores mistas, ruas arborizadas) sobe (189 → 237 ha): a divisão entre as duas é sensível às regras de classificação e não deve ser lida isoladamente.

#### Transições de uso do solo

| Transição | Área (ha) |
|-----------|-----------|
| Árvores → Edificado | 29 |
| Árvores → Solo | 61 |
| Solo → Edificado | **124** |
| Solo → Árvores | 59 |

A **conversão de solo/relva em edificado** (124 ha) é a transição dominante; a de árvores em edificado limita-se a 29 ha. Isto vai no sentido da tese de Guilherme *et al.* (2022): a cobertura arbórea é mais resiliente do que a herbácea e agrícola. 59 ha de solo passaram a árvores, o que pode reflectir arborização (como o programa *FUN Porto*) e crescimento natural das copas. As quatro transições são as únicas calculadas (não as inversas, como edificado → solo), por isso não somam às variações por classe da tabela anterior. Cada ano é uma classificação independente: diferenças de poucas dezenas de hectares podem ser ruído de classificação.

Nota de coerência: árvores mais solo/relva em 2024–25 somam 1 471 ha (35,5 % do concelho), próximo da série Landsat de 2023–24 (35,3 %), por construção da calibração.

**Duas séries que não concordam.** Em 2016–17 o Sentinel-2 dá 1 646 ha de árvores e solo/relva (39,7 %) e o Landsat 34,7 %; de 2016–17 a 2024–25 o Sentinel-2 desce 4,2 p.p. (−175 ha) e o Landsat sobe 0,6 p.p. (dentro do ruído). Não sabemos qual acerta: a calibração do Landsat usa o Sentinel-2 de 2024–25 como referência e não o de 2016–17, e as regras do Sentinel-2 são limiares fixos aplicados a cada ano. A descida do Sentinel-2 é portanto um indício a confirmar, não um facto.

---

## 6. Conclusões

1. **Entre 1985 e 2024 não há perda líquida de vegetação detectável por satélite no Porto** (houve um mínimo frágil em 2001–05, depois recuperado). A série corrigida vai de 32,6 % (1985–90) a 35,3 % (2023–24), com mínimo de 30,8 % em 2001–05. A queda de 45,0 % para 30,0 % da primeira versão era um artefacto de sensor e de limiar.
2. **A perda de espaço livre é real, mas localizada**: cerca de 226 ha de perda (concentrados em Paranhos) contra 286 ha de ganho em manchas ≥ 0,5 ha. No Sentinel-2 (2016–2025), o solo permeável encolheu 159 ha (−15,1 %) e o edificado cresceu 175 ha (+7,0 %), enquanto as árvores quase não variaram (−2,7 %).
3. **O que satélite a 30 m não mede**: a transformação mais profunda do século XX (agricultura → cidade) ocorreu sobretudo antes de 1985 e não é quantificável com esta série. Guilherme *et al.* (2022) documentam a duplicação do edificado entre 1947 e 2019 (31 % → 62 %); os valores de 1947 e 1979 deste trabalho vêm de outras fontes e métodos e não se somam à série Landsat.
4. **Para o planeamento** (32,6 % do concelho em risco térmico elevado, Lopes *et al.*, 2025): o que a análise sustenta é proteger o solo permeável e a vegetação herbácea que resta, não alegar uma perda geral de vegetação. As árvores têm sido mais resilientes do que o solo permeável.

**Limites:** a calibração usa uma classificação de satélite, não verdade de terreno; a ponte entre sensores é uma recta calculada em dois tipos de alvo (resíduo +0,6 p.p.); as árvores estáveis sobem de NDVI ao longo do tempo (0,56 → 0,71), o que pode ser maturação das copas e não sensor; a série Landsat a 30 m não distingue relva regada de árvores; e a discrepância com Quental (2010) não está resolvida. Para uma série longa de uma só fonte, faltam as camadas de Guilherme *et al.* (1947/1979/2019), a pedir à autora.

---


## 7. Referências

- Gonçalves, J.A., Pinhal, A. & Lino, R.S. (s.d.). *Mapas e fotografias aéreas históricas do Porto*. FCUP / CMP / CIGeoE. [https://www.fc.up.pt/pessoas/jagoncal/porto/](https://www.fc.up.pt/pessoas/jagoncal/porto/)
- Graça, M., Alves, P., Gonçalves, J., Nowak, D.J., Hoehn, R., Farinha-Marques, P. & Cunha, M. (2018). Assessing how green space types affect ecosystem services delivery in Porto, Portugal. *Landscape and Urban Planning*, 170, 195–208. [doi:10.1016/j.landurbplan.2017.11.007](https://doi.org/10.1016/j.landurbplan.2017.11.007)
- Guilherme, F., Garcia Moreno, E., Gonçalves, J.A., Carretero, M.A. & Farinha-Marques, P. (2022). Looking Closer at the Patterns of Land Cover in the City of Porto, Portugal, between 1947 and 2019. *Land*, 11(10), 1828. [doi:10.3390/land11101828](https://doi.org/10.3390/land11101828)
- Guilherme, F., Gonçalves, J.A., Carretero, M.A. & Farinha-Marques, P. (2024a). Assessment of land cover trajectories as an indicator of urban habitat temporal continuity. *Landscape and Urban Planning*, 242. [doi:10.1016/j.landurbplan.2023.104952](https://doi.org/10.1016/j.landurbplan.2023.104952)
- Guilherme, F., Vicente, J.R., Carretero, M.A. & Farinha-Marques, P. (2024b). Mapping multigroup responses to land cover legacy for urban biodiversity conservation. *Biological Conservation*, 291, 110489. [doi:10.1016/j.biocon.2024.110489](https://doi.org/10.1016/j.biocon.2024.110489)
- Lopes, H.S., Vidal, D.G., Cherif, N., Silva, L. & Remoaldo, P.C. (2025). Green infrastructure and its influence on urban heat island, heat risk, and air pollution: A case study of Porto (Portugal). *Journal of Environmental Management*, 376, 124446. [doi:10.1016/j.jenvman.2025.124446](https://doi.org/10.1016/j.jenvman.2025.124446)
- Madureira, H., Andresen, T. & Monteiro, A. (2011). Green structure and planning evolution in Porto. *Urban Forestry & Urban Greening*, 10(2), 141–149. [doi:10.1016/j.ufug.2010.12.004](https://doi.org/10.1016/j.ufug.2010.12.004)
- Madureira, H. & Andresen, T. (2014). Planning for multifunctional urban green infrastructures: Promises and challenges. *Urban Design International*, 19, 38–49. [doi:10.1057/udi.2013.11](https://doi.org/10.1057/udi.2013.11)
- Quental, N. (2010). *Modeling a sustainable urban structure: An application to the Metropolitan Area of Porto*. Tese de Doutoramento em Engenharia do Território, Instituto Superior Técnico, Universidade Técnica de Lisboa. [PDF](https://coolio1.github.io/pdfs/2010-08-02%20-%20Tese%20de%20doutoramento.pdf)


---

## Mapas interativos

- **[Mapa histórico (1985–2024)]({{ site.baseurl }}/mapa_unico/mapa_unico.html#tema=historico)** — alternância entre épocas, vegetação por píxel, zonas de perda e ganho
- **[Mapa detalhado (2016–2025)]({{ site.baseurl }}/mapa.html)** — classificação árvores/solo/edificado a 10 m

---

## Código

Todo o *pipeline* está disponível no repositório:

- [`1947/orto_1947.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/1947/orto_1947.py) — classificação do ortofoto 1947 (tiles WMS + Random Forest)
- [`1947/clean_1947.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/1947/clean_1947.py) — limpeza/pós-processamento com máscaras Sentinel e Landsat
- [`ndvi_historico/ndvi_historico.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/ndvi_historico/ndvi_historico.py) — análise histórica 1985–2024 (ponte Landsat 7, fracção de vegetação, incerteza)
- [`mapa/porto_publish.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/mapa/porto_publish.py) — pipeline Sentinel-2 (classificação + mapa)
- [`test_area.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/test_area.py) — calibração na área de teste
- [`mapa/porto_stats.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/mapa/porto_stats.py) — cálculo de estatísticas
- [`animacao/animacao_cairo.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/animacao/animacao_cairo.py) — animação vectorial Cairo com interpolação bienal
