---
layout: post
title: "Acessibilidade a Espaços Verdes Públicos no Porto: Uma Análise Espacial pelo Método 2SFCA"
description: "Mapa de acessibilidade da população do Porto a espaços verdes públicos (m²/hab, raio 500m), usando o método Two-Step Floating Catchment Area com dados GHS-POP e inventário de 47 parques e jardins."
date: 2026-03-30
tags: [porto, acessibilidade, verde público, 2sfca, gee, ghs-pop, osm, sentinel-2]
---

**Acessibilidade a Espaços Verdes Públicos no Porto: Uma Análise Espacial pelo Método Two-Step Floating Catchment Area**

---

## 1. Introdução

O Porto dispõe de 19,3 m² de espaço verde público por habitante — um valor que excede confortavelmente o limiar de 9 m²/hab recomendado pela Organização Mundial de Saúde (OMS). Porém, esta métrica agregada esconde uma realidade espacialmente desigual: quem vive junto ao Parque da Cidade beneficia de uma dotação generosa, enquanto quem habita na Sé, em Campanhã ou no interior de Paranhos pode não ter nenhum espaço verde público acessível a pé.

A questão da acessibilidade — distinta da mera existência — tornou-se central na literatura de planeamento urbano. Não basta que uma cidade tenha parques; importa que a população consiga alcançá-los em poucos minutos a pé, e que esses espaços não estejam saturados por uma procura excessiva. Este trabalho aplica o método *Two-Step Floating Catchment Area* (2SFCA) ao município do Porto, cruzando um inventário de 47 parques e jardins de acesso público gratuito (construído a partir do directório municipal e de levantamento complementar), a classificação de uso do solo por satélite Sentinel-2, e a grelha de população GHS-POP do *Joint Research Centre*.

O resultado é um mapa pixel a pixel da acessibilidade efectiva a verde público, expresso em m² por habitante dentro de um raio pedonal de 500 metros — uma análise que, tanto quanto se apura, não foi anteriormente publicada para o Porto com este nível de granularidade espacial e metodológica.

---

## 2. Enquadramento e Revisão da Literatura

### 2.1. Verde público no Porto

Madureira *et al.* (2018) mapearam 95 espaços verdes urbanos de acesso público no Porto, totalizando cerca de 424 hectares. A presente análise, baseada na intersecção entre classificação Sentinel-2 e os polígonos do PDM 2021, identifica **448 hectares de verde público classificado** — um valor coerente com a estimativa anterior e que reflecte a estabilidade estrutural da rede de parques municipais ao longo da última década.

Contudo, a distribuição destes espaços é marcadamente assimétrica. A faixa ocidental (Foz–Nevogilde–Aldoar), que alberga o Parque da Cidade (80 ha), Serralves (18 ha) e os Jardins do Palácio de Cristal (8 ha), concentra uma proporção desmesurada do verde público total. Em contraste, as freguesias de alta densidade do centro e leste — Cedofeita, Bonfim, Campanhã — apresentam uma malha verde residual e fragmentada, onde a maior "mancha" pode não ultrapassar um pequeno largo arborizado.

### 2.2. O problema da equidade espacial

Wolch *et al.* (2014), na sua influente revisão sobre justiça ambiental urbana, sintetizaram a evidência de que as populações de menor rendimento e as minorias étnicas tendem a residir em bairros com menor acesso a espaços verdes — fenómeno que designaram *green gentrification paradox*. Monteiro *et al.* (2025) demonstraram que, no Porto, 32,6% do território se encontra em zonas de elevado risco térmico, com a ilha de calor urbana mais intensa precisamente nas áreas de maior densidade habitacional e menor cobertura vegetal.

### 2.3. Limitações das métricas tradicionais

As abordagens clássicas de avaliação de verde urbano apresentam limitações bem documentadas:

- **Área per capita** (m²/hab por freguesia): dilui a informação numa média administrativa, ignorando a distribuição interna. Uma freguesia pode ter um parque enorme num extremo e zero verde no resto.
- **Buffer de proximidade** (população a ≤300 m de um espaço verde): trata todos os espaços como iguais, sem distinguir um canteiro de 500 m² de um parque de 50 hectares.
- **Índices de cobertura vegetal** (NDVI médio): não separam verde público de privado, nem consideram a acessibilidade pedonal.

### 2.4. O método 2SFCA

O método *Two-Step Floating Catchment Area*, proposto por Luo & Wang (2003) para a análise de acessibilidade a serviços de saúde, tornou-se referência para a avaliação espacial de espaços verdes urbanos. O seu mérito reside na consideração simultânea da oferta (área verde) e da procura (população), num raio de acesso definido:

1. **Passo da oferta**: para cada unidade de verde, calcular o rácio entre a sua área e a população total que a ela acede num raio *d*.
2. **Passo da procura**: para cada unidade de população, somar os rácios de todos os espaços verdes acessíveis no mesmo raio.

O resultado — em m² de verde por habitante, ponderado pela competição — é conceptualmente superior às métricas agregadas porque captura o efeito de saturação: um parque pequeno rodeado por muita gente vale menos, por pessoa, do que um parque grande com pouca população na envolvente.

Dai (2011) aplicou o 2SFCA a espaços verdes em Atlanta, demonstrando disparidades significativas de acessibilidade ao longo de linhas raciais e socioeconómicas. Rigolon (2016) evidenciou que a qualidade dos parques — e não apenas a sua proximidade — explica parte da desigualdade no seu uso. Luo & Qi (2009) propuseram a variante *Enhanced 2SFCA* (E2SFCA), incorporando uma função de decaimento gaussiano com a distância; porém, para raios pedonais curtos (≤500 m), a diferença prática entre o modelo uniforme e o gaussiano tende a ser marginal (Langford *et al.*, 2012).

---

## 3. Dados e Metodologia

### 3.1. Fontes de dados

| Dado | Fonte | Resolução | Período |
|------|-------|-----------|---------|
| Parques e jardins públicos | Inventário próprio (CMP + OSM + levantamento) | vectorial (47 polígonos) | 2026 |
| Classificação verde | Sentinel-2 (ESA) | 10 m | 2024–2025 |
| Verde não usufruível | PDM Porto 2021 (CMP) | vectorial (132 polígonos) | 2021 |
| População | GHS-POP (JRC/EC) | 100 m | 2020 |
| Limites municipais | CAOP 2025 (DGT) | vectorial | 2025 |

### 3.2. Identificação do verde público

#### Inventário de parques e jardins

A definição de "verde público" adoptou uma abordagem de inventário explícito, em vez da classificação funcional genérica do PDM. Compilou-se uma lista de **47 parques e jardins de acesso público e gratuito**, partindo do directório oficial da CMP ([ambiente.cm-porto.pt/estrutura-verde/parques-jardins](https://ambiente.cm-porto.pt/estrutura-verde/parques-jardins), 20 espaços) e complementando com espaços omitidos desse directório mas de acesso comprovadamente livre:

- **Gestão municipal directa** (21 espaços): Parque da Cidade, Parque Oriental, Parque do Covelo, Parque de S. Roque, Parque da Pasteleira, Parque das Águas, Parque das Virtudes, Jardim do Passeio Alegre, Jardins do Palácio de Cristal, Jardim da Cordoaria, Jardim do Marquês, Jardim do Carregal, Jardim de Arca d'Água, Jardim de S. Lázaro, Jardim da Praça da República, Quinta de Bonjóia, Rotunda da Boavista, Praça da Galiza, Frente Atlântica (incluindo jardins do Homem do Leme e da Av. de Montevideu), Jardim da Corujeira, Jardim de Teodoro de Sousa.
- **Gestão institucional ou privada com acesso gratuito** (8 espaços): Parque Central da Asprela, Parque Urbano da Lapa (Dr. Mário Soares), Jardim Botânico do Porto, Parque da Quinta de Lamas, Jardins da Casa Allen, Fundação Eng. António de Almeida, Jardins da FLUP, Parque de Requesende.
- **Espaços adicionais identificados** (9 espaços): Viveiro Municipal, Jardim Paulo Vallada, Jardim da Praça do Império, Alameda das Fontainhas, Jardins da Praia de Gondarém, Jardins da Praia do Molhe, Jardim do Calém e das Sobreiras, e outros jardins marítimos.
- **Micro-jardins e praças ajardinadas** (9 espaços): Jardim de Belém, Jardim Palmira Milheiro, Jardim da Praça de Liège, Jardim de Fradelos, Jardim do Campo 24 de Agosto, Jardim de Antero de Quental, Jardim da Praça de Francisco Sá Carneiro, Jardim de Sarah Afonso, Jardim do Largo da Paz.

Os contornos de cada espaço foram obtidos primariamente via OpenStreetMap (Overpass API e API v0.6), com recurso a polígonos do PDM para a Frente Atlântica e a centróides georreferenciados com buffer para os espaços sem polígono no OSM. A área total dos 47 parques inventariados é de **~202 hectares**.

#### Classificação Sentinel-2 (camada visual)

A classificação da cobertura verde seguiu a metodologia multi-sazonal descrita em Quental (2026), utilizando compósitos Sentinel-2 de 2024–2025 com regras de decisão baseadas em NDVI de verão, NDVI de primavera, NDVI mínimo anual, rácio NIR/Green e banda B3 — um esquema que demonstrou 90,4% de concordância com o ESA WorldCover 2021 para a classe arbórea. Esta classificação é utilizada para a **camada visual** do mapa (pixels verdes dentro dos parques), mas o cálculo de acessibilidade utiliza a área total dos polígonos dos parques, não a classificação por satélite.

#### Verde pago ou não usufruível

Os polígonos do PDM 2021 classificados como verde público (132 polígonos em 4 subcategorias: fruição colectiva, lúdico-produtiva, associada a equipamento e frente atlântica/ribeirinha) mas que **não correspondem a nenhum dos 38 parques inventariados** são apresentados numa camada separada ("Verde pago ou não usufruível") como áreas sólidas. Estes espaços incluem jardins de escolas, hortas urbanas com acesso restrito, jardins de equipamentos hospitalares e outras zonas verdes formalmente públicas mas sem usufruto livre pela população.

### 3.3. Dados de população

A grelha GHS-POP 2020 (Schiavina *et al.*, 2023) fornece estimativas de contagem populacional a uma resolução de ~100 m, produzidas pelo *Joint Research Centre* da Comissão Europeia a partir de recenseamentos desagregados e classificação de povoamento (*built-up*). Para o Porto, os valores por célula variam entre 0 (espaços não habitados) e ~708 habitantes (blocos residenciais de alta densidade).

Uma nota técnica importante: ao renderizar a grelha GHS-POP na resolução de cálculo (~6,5 m/pixel), o método de reamostragem por vizinho mais próximo (*nearest neighbour*) do Google Earth Engine replica o valor de cada célula nativa em ~175 sub-pixels. Para evitar inflacionar a soma focal de população, aplicou-se um factor de correcção proporcional ao rácio entre a área do pixel de cálculo e a área da célula nativa (57 m² / 10 000 m² ≈ 1/175).

### 3.4. Cálculo do 2SFCA

O cálculo foi implementado em versão raster contínua, dispensando a discretização em pontos de oferta e procura:

1. **Área verde por pixel**: máscara binária dos polígonos dos 47 parques × área do pixel (57 m²). Toda a área dentro dos contornos dos parques conta como verde (não apenas os pixels classificados como vegetação pelo Sentinel-2), reflectindo que caminhos, lagos e clareiras fazem parte integrante da experiência do espaço verde.
2. **Soma focal do verde** (*green_500m*): convolução com kernel circular elíptico de raio 500 m (76×58 pixels), contabilizando ~13 800 pixels por vizinhança.
3. **Soma focal da população** (*pop_500m*): mesma operação sobre a grelha de população corrigida.
4. **Filtro de densidade**: exclui-se do cálculo os pixels cuja soma de população no raio de 500 m seja inferior a 50 habitantes. Isto remove zonas verdadeiramente desabitadas (rio, oceano, margens) sem esconder parques e jardins cujo pixel local tem população zero mas que servem residentes nas imediações.
5. **Acessibilidade**: *green_500m* / *pop_500m* (m²/hab), apenas para pixels que passam o filtro de densidade.

Este procedimento equivale ao 2SFCA clássico na sua versão de campo contínuo, onde cada pixel é simultaneamente potencial consumidor e potencial vizinho de espaços verdes. A escolha de 500 m como raio de captação reflecte um compromisso entre o limiar europeu frequente de 300 m (norma EN 16798) e a realidade topográfica do Porto — cidade de colinas onde 300 m em linha recta podem corresponder a um percurso pedonal significativamente mais longo.

---

## 4. Resultados

### 4.1. Verde público: inventário e distribuição

O inventário identifica **47 parques e jardins de acesso público gratuito** no concelho do Porto, totalizando **~202 hectares**. Este valor é inferior aos 448 ha de verde funcional classificado no PDM porque exclui deliberadamente espaços formalmente "públicos" mas sem usufruto livre (jardins de escolas, hortas com acesso restrito, separadores viários). Os 202 ha correspondem a **~8,7 m² por habitante** — um valor ligeiramente abaixo do limiar da OMS em termos agregados.

A tabela seguinte lista os 47 espaços inventariados e a respectiva área calculada:

| Parque / Jardim | Área (m²) |
|---|---:|
| Parque da Cidade | 714 300 |
| Parque Oriental | 193 200 |
| Frente Atlântica | 170 500 |
| Parque da Pasteleira | 91 500 |
| Jardim do Palácio de Cristal | 88 400 |
| Parque do Covelo | 75 700 |
| Viveiro Municipal | 66 500 |
| Parque Central da Asprela | 56 600 |
| Parque de São Roque | 52 200 |
| Quinta de Bonjóia | 47 800 |
| Jardim Botânico do Porto | 43 000 |
| Jardim do Passeio Alegre | 38 700 |
| Rotunda da Boavista | 30 800 |
| Parque de Requesende | 30 800 |
| Parque das Águas | 27 600 |
| Jardim da Avenida de Montevideu | 27 300 |
| Jardim do Calém e das Sobreiras | 25 100 |
| Jardim de Arca d'Água | 22 700 |
| Jardim da Praça da República | 20 000 |
| Jardim da Corujeira | 19 800 |
| Jardim da Cordoaria | 16 500 |
| Jardim da Praça de Francisco Sá Carneiro | 15 000 |
| Jardim do Homem do Leme | 14 800 |
| Parque da Fundação Eng. António de Almeida | 13 700 |
| Jardim Paulo Vallada | 13 600 |
| Parque das Virtudes | 12 400 |
| Jardim de Sarah Afonso | 10 400 |
| Alameda das Fontainhas | 10 000 |
| Jardim de Teodoro de Sousa | 7 800 |
| Parque Urbano da Lapa | 7 000 |
| Jardim do Marquês | 6 800 |
| Jardim de São Lázaro | 5 700 |
| Jardim Palmira Milheiro | 5 200 |
| Jardim da Praça de Liège | 4 800 |
| Jardim da Praça do Império | 4 000 |
| Parque da Quinta de Lamas | 3 800 |
| Jardins da Praia do Molhe | 3 700 |
| Jardim do Campo 24 de Agosto | 3 700 |
| Jardim de Fradelos | 3 000 |
| Jardim de Antero de Quental | 2 800 |
| Jardim de Belém | 1 900 |
| Jardim do Carregal | 1 900 |
| Jardins da Casa Allen | 1 500 |
| Jardim do Largo da Paz | 1 200 |
| Jardins da Praia de Gondarém | 900 |
| Praça da Galiza | 800 |
| Jardins da FLUP | 500 |
| **Total** | **2 015 900** |

Os restantes ~246 ha de verde do PDM que não integram o inventário de parques são apresentados na camada "Verde pago ou não usufruível". Esta distinção — entre verde formalmente público e verde efectivamente usufruível — é central para a análise de acessibilidade.

### 4.2. Acessibilidade 2SFCA: a desigualdade revelada

A distribuição espacial da acessibilidade a verde público no raio de 500 m é fortemente assimétrica. Considerando apenas os pixels com densidade populacional suficiente (≥10 hab/célula GHS-POP, ~56% da área do concelho), **83,4% do território habitado do Porto apresenta uma acessibilidade efectiva inferior ao limiar da OMS de 9 m²/hab**.

Este resultado contrasta drasticamente com a métrica agregada (~8,7 m²/hab) e revela a profunda desigualdade espacial no acesso a verde público.

A distribuição geográfica das classes de acessibilidade revela um padrão espacial claro:

- **Zona ocidental (Foz, Nevogilde, Aldoar)**: acessibilidade consistentemente elevada (>15 m²/hab), beneficiando da proximidade ao Parque da Cidade (80 ha), à Frente Atlântica e ao corredor de jardins marítimos. É a única zona do concelho onde a acessibilidade excede largamente o limiar.

- **Eixo Boavista–Palácio de Cristal**: acessibilidade adequada (9–15 m²/hab), sustentada pelos Jardins do Palácio de Cristal (11 ha) e pela Fundação Eng. António de Almeida.

- **Centro histórico e Baixa (Sé, Miragaia, Vitória, Cedofeita)**: défice severo (0–3 m²/hab). O tecido urbano densíssimo e a escassez de espaços verdes de dimensão significativa produzem valores de acessibilidade próximos de zero — agravados pela elevada densidade populacional. Os pequenos jardins existentes (Cordoaria, Praça da República, S. Lázaro) são insuficientes para a população envolvente.

- **Interior de Paranhos e Ramalde**: valores heterogéneos, com o Parque Central da Asprela (6 ha) e o Parque de Requesende a beneficiar as zonas universitárias, mas bolsas de défice severo nos bairros residenciais intermédios.

- **Campanhã**: o Parque Oriental (16 ha) e a Quinta de Bonjóia melhoram pontualmente a acessibilidade, mas a estrutura verde pública permanece fragmentada. A zona industrial apresenta valores nulos.

### 4.4. O papel do verde privado

Um resultado notável desta análise é a magnitude do verde privado: os 1 678 hectares de espaços verdes encravados em quarteirões, logradouros e jardins de moradias representam uma "infraestrutura verde oculta" que — embora não acessível ao público — presta serviços ecossistémicos locais críticos: infiltração pluvial, regulação microclimática, habitat para fauna urbana e valor estético.

Se se incluísse o verde privado no cálculo de acessibilidade (o que não é conceptualmente correcto para uma análise de equidade no acesso público, mas é relevante para uma análise de serviços ecossistémicos), os valores de acessibilidade subiriam substancialmente em zonas residenciais de baixa densidade — precisamente as áreas que já beneficiam de maior dotação pública. Este resultado sublinha um paradoxo de equidade: as zonas com mais verde privado tendem a ter também mais verde público, enquanto as zonas densas carecem de ambos.

---

## 5. Discussão

### 5.1. Concordância com a literatura

O rácio agregado de 19,3 m²/hab de verde público é coerente com os 18,3 m²/hab reportados por Madureira *et al.* (2018) — a pequena diferença pode dever-se ao crescimento da arborização em espaços existentes e a diferenças de delimitação e de classificação.

A forte heterogeneidade espacial revelada pelo 2SFCA confirma as preocupações de Monteiro *et al.* (2025) sobre a desigualdade térmica no Porto: as zonas identificadas como de maior risco térmico (centro e leste) coincidem com as de menor acessibilidade a verde público. Esta sobreposição sugere um mecanismo de reforço mútuo: a ausência de verde agrava o calor urbano, que por sua vez torna mais urgente a necessidade de espaços verdes para refúgio.

### 5.2. Limitações

1. **Completude do inventário**: embora o inventário de 47 parques cubra os espaços principais, podem existir pequenos jardins ou espaços verdes de acesso livre não contemplados. A utilização de contornos OpenStreetMap — complementados por polígonos PDM e buffers georreferenciados — introduz uma precisão variável nos limites dos parques.

2. **Distância euclidiana vs. distância de rede**: o raio de 500 m é medido em linha recta, não pela rede viária. Em áreas com barreiras topográficas (encostas íngremes, viadutos, linhas de comboio), a distância real percorrida é significativamente superior. Uma análise futura com distância de rede (baseada em dados OpenStreetMap) aumentaria a precisão do modelo.

3. **Resolução temporal**: os dados populacionais (GHS-POP 2020) podem não reflectir alterações demográficas recentes — nomeadamente o crescimento do alojamento local turístico, que reduz a população residente efectiva em certas zonas (Baixa, Cedofeita) sem alterar a contagem censitária.

4. **Qualidade do verde**: o método trata todos os metros quadrados de verde como equivalentes. Na realidade, um relvado degradado junto a uma via rápida não presta os mesmos serviços que um parque arborizado com equipamento de lazer. A incorporação de indicadores de qualidade (dimensão das manchas, presença de arvoredo, equipamento) enriqueceria a análise.

### 5.3. Implicações para o planeamento

Os resultados sugerem que a estratégia municipal de verde público deveria priorizar investimentos no **eixo central e oriental** — as zonas onde o défice ponderado pela população é mais elevado. Intervenções como a abertura de logradouros e interiores de quarteirão ao uso público, a conversão de terrenos expectantes em jardins de bolso (*pocket parks*), e a arborização intensiva de praças e arruamentos poderiam melhorar significativamente a acessibilidade nas zonas mais carenciadas.

O contraste entre a abundância de verde privado (1 678 ha) e a escassez de verde público acessível (448 ha) levanta uma questão de política urbanística: até que ponto podem ser criados mecanismos de permeabilização do verde privado — por exemplo, incentivos à abertura parcial de logradouros, servidões de passagem em interiores de quarteirão, ou a obrigação de cedências verdes em operações urbanísticas — para complementar a rede de espaços verdes formalmente públicos?

---

## 6. Conclusões

A aplicação do método 2SFCA ao Porto, baseada num inventário de 47 parques e jardins de acesso gratuito (~202 ha), revela que **83,4% do território habitado da cidade apresenta uma acessibilidade efectiva inferior a 9 m²/hab** num raio pedonal de 500 m — apesar de a dotação agregada (~8,7 m²/hab) estar próxima do limiar OMS. O défice concentra-se no eixo central e oriental (Cedofeita, Bonfim, Paranhos interior, Campanhã), precisamente as zonas de maior densidade habitacional e, segundo a literatura, de maior vulnerabilidade térmica.

A distinção entre verde formalmente público (PDM) e verde efectivamente usufruível (inventário de parques) é particularmente reveladora: dos ~448 ha classificados pelo PDM como verde público, apenas ~202 ha correspondem a espaços que a população pode efectivamente utilizar sem restrições.

Esta análise demonstra que a métrica agregada per capita é insuficiente para avaliar a equidade no acesso a verde urbano. A acessibilidade espacial — que pondera simultaneamente a oferta, a procura e a distância — oferece um diagnóstico mais fiel da experiência real dos residentes e constitui um instrumento de planeamento mais rigoroso para a priorização de investimentos na criação e melhoria de espaços verdes urbanos.

---

## 7. Nota Metodológica

Todo o processamento foi realizado em Python com *Google Earth Engine*, *scipy*, *NumPy* e *Shapely*. O código é aberto e reproduzível:

- [`acessibilidade/acessibilidade_verde.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/acessibilidade/acessibilidade_verde.py) — *pipeline* completo (classificação + 2SFCA + HTML)
- [`acessibilidade/criar_parques.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/acessibilidade/criar_parques.py) — construção do inventário de 47 parques (Overpass API + PDM)

---

## 8. Referências

- Dai, D. (2011). Racial/ethnic and socioeconomic disparities in urban green space accessibility: Where to intervene? *Landscape and Urban Planning*, 102(4), 234–244.
- Langford, M., Higgs, G., Radcliffe, J. & White, S. (2012). Urban population distribution models and service accessibility estimation. *Computers, Environment and Urban Systems*, 36(1), 66–80.
- Luo, W. & Qi, Y. (2009). An enhanced two-step floating catchment area (E2SFCA) method for measuring spatial accessibility to primary care physicians. *Health & Place*, 15(4), 1100–1107.
- Luo, W. & Wang, F. (2003). Measures of spatial accessibility to health care in a GIS environment: Synthesis and a case study in the Chicago region. *Environment and Planning B*, 30(6), 865–884.
- Madureira, H. *et al.* (2018). Assessing how green space types affect ecosystem services delivery in Porto, Portugal. *Landscape and Urban Planning*, 170, 286–297.
- Madureira, H., Andresen, T. & Monteiro, A. (2011). Green structure and planning evolution in Porto. *Urban Forestry & Urban Greening*, 10(2), 141–149.
- Monteiro, A. *et al.* (2025). Green infrastructure and its influence on urban heat island, heat risk, and air pollution: A case study of Porto. *Journal of Environmental Management*, 376, 124446.
- Quental, N. (2026). Dinâmicas de Ocupação do Solo e Cobertura Vegetal na Cidade do Porto (1985–2025). *Relatório técnico*.
- Rigolon, A. (2016). A complex landscape of inequity in access to urban parks: A literature review. *Landscape and Urban Planning*, 153, 160–169.
- Schiavina, M., Freire, S. & MacManus, K. (2023). GHS-POP R2023A — GHS population grid multitemporal (1975–2030). *European Commission, Joint Research Centre*.
- Wolch, J.R., Byrne, J. & Newell, J.P. (2014). Urban green space, public health, and environmental justice: The challenge of making cities 'just green enough'. *Landscape and Urban Planning*, 125, 234–244.

---

## Mapa interactivo

**[Acessibilidade a Verde Público — Porto]({{ site.baseurl }}/acessibilidade/acessibilidade_verde.html)** — mapa com camadas de acessibilidade 2SFCA, parques e jardins (47 espaços com popups), verde pago/não usufruível e verde privado
