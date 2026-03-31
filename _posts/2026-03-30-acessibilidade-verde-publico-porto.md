---
layout: post
title: "Acessibilidade a Espaços Verdes Públicos no Porto: Uma Análise Espacial pelo Método 2SFCA"
description: "Mapa de acessibilidade da população do Porto a espaços verdes públicos (m²/hab, raio 500m), usando o método Two-Step Floating Catchment Area com dados GHS-POP e PDM."
date: 2026-03-30
tags: [porto, acessibilidade, verde público, 2sfca, gee, ghs-pop, pdm, sentinel-2]
---

**Acessibilidade a Espaços Verdes Públicos no Porto: Uma Análise Espacial pelo Método Two-Step Floating Catchment Area**

---

## 1. Introdução

O Porto dispõe de 19,3 m² de espaço verde público por habitante — um valor que excede confortavelmente o limiar de 9 m²/hab recomendado pela Organização Mundial de Saúde (OMS). Porém, esta métrica agregada esconde uma realidade espacialmente desigual: quem vive junto ao Parque da Cidade beneficia de uma dotação generosa, enquanto quem habita na Sé, em Campanhã ou no interior de Paranhos pode não ter nenhum espaço verde público acessível a pé.

A questão da acessibilidade — distinta da mera existência — tornou-se central na literatura de planeamento urbano. Não basta que uma cidade tenha parques; importa que a população consiga alcançá-los em poucos minutos a pé, e que esses espaços não estejam saturados por uma procura excessiva. Este trabalho aplica o método *Two-Step Floating Catchment Area* (2SFCA) ao município do Porto, cruzando dados de classificação de uso do solo por satélite, a qualificação funcional do Plano Director Municipal (PDM 2021) e a grelha de população GHS-POP do *Joint Research Centre*.

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
| Classificação verde | Sentinel-2 (ESA) | 10 m | 2024–2025 |
| Qualificação funcional | PDM Porto 2021 (CMP) | vectorial | 2021 |
| População | GHS-POP (JRC/EC) | 100 m | 2020 |
| Limites municipais | CAOP 2025 (DGT) | vectorial | 2025 |

### 3.2. Identificação do verde público

A classificação da cobertura verde seguiu a metodologia multi-sazonal descrita em Quental (2026), utilizando compósitos Sentinel-2 de 2024–2025 com regras de decisão baseadas em NDVI de verão, NDVI de primavera, NDVI mínimo anual, rácio NIR/Green e banda B3 — um esquema que demonstrou 90,4% de concordância com o ESA WorldCover 2021 para a classe arbórea. A classe "verde" inclui tanto a cobertura arbórea como o solo permeável/relva (classe *isSolo*), capturando assim toda a superfície vegetada ou permeável.

Para isolar o **verde público**, cruzou-se esta classificação com a qualificação funcional do PDM 2021 (camada `PO_QSFUNCIONAL_PL`), retendo exclusivamente os pixels verdes dentro de polígonos classificados nas seguintes subcategorias (`sc_espaco`):

- **Área verde de fruição colectiva** (90 polígonos) — parques e jardins públicos
- **Área verde lúdico-produtiva** (5 polígonos) — hortas urbanas comunitárias
- **Área verde associada a equipamento** (21 polígonos) — jardins de escolas, hospitais e equipamentos públicos
- **Área de frente atlântica e ribeirinha** (16 polígonos) — espaços verdes costeiros e ripícolas

Excluíram-se deliberadamente as categorias "Área verde de protecção e enquadramento" (taludes, separadores rodoviários — verdes não usufruíveis) e "Área de equipamentos" genérica (edifícios sem jardim).

### 3.3. Dados de população

A grelha GHS-POP 2020 (Schiavina *et al.*, 2023) fornece estimativas de contagem populacional a uma resolução de ~100 m, produzidas pelo *Joint Research Centre* da Comissão Europeia a partir de recenseamentos desagregados e classificação de povoamento (*built-up*). Para o Porto, os valores por célula variam entre 0 (espaços não habitados) e ~708 habitantes (blocos residenciais de alta densidade).

Uma nota técnica importante: ao renderizar a grelha GHS-POP na resolução de cálculo (~6,5 m/pixel), o método de reamostragem por vizinho mais próximo (*nearest neighbour*) do Google Earth Engine replica o valor de cada célula nativa em ~175 sub-pixels. Para evitar inflacionar a soma focal de população, aplicou-se um factor de correcção proporcional ao rácio entre a área do pixel de cálculo e a área da célula nativa (57 m² / 10 000 m² ≈ 1/175).

### 3.4. Cálculo do 2SFCA

O cálculo foi implementado em versão raster contínua, dispensando a discretização em pontos de oferta e procura:

1. **Área verde por pixel**: fracção de verde público × área do pixel (57 m²)
2. **Soma focal do verde** (*green_500m*): convolução com kernel circular elíptico de raio 500 m (76×58 pixels), contabilizando ~13 800 pixels por vizinhança
3. **Soma focal da população** (*pop_500m*): mesma operação sobre a grelha de população corrigida
4. **Acessibilidade**: *green_500m* / *pop_500m* (m²/hab), onde *pop_500m* > 0,5

Este procedimento equivale ao 2SFCA clássico na sua versão de campo contínuo, onde cada pixel é simultaneamente potencial consumidor e potencial vizinho de espaços verdes. A escolha de 500 m como raio de captação reflecte um compromisso entre o limiar europeu frequente de 300 m (norma EN 16798) e a realidade topográfica do Porto — cidade de colinas onde 300 m em linha recta podem corresponder a um percurso pedonal significativamente mais longo.

### 3.5. Défice ponderado pela população

Para identificar as áreas onde a insuficiência de verde público afecta o maior número de pessoas, calculou-se um índice de **défice ponderado**:

$$
D_i = P_{500m,i} \times \max(9 - A_i,\; 0)
$$

onde *A_i* é a acessibilidade 2SFCA no pixel *i* e *P_500m,i* é a população total a 500 m. Este índice penaliza duplamente: o défice é tanto maior quanto maior for o *gap* relativamente ao limiar OMS (9 m²/hab) **e** quanto maior for a população afectada. Uma zona despovoada com zero verde pontua zero; uma zona de alta densidade com zero verde pontua no máximo.

---

## 4. Resultados

### 4.1. Verde público: inventário e distribuição

A análise identifica **448 hectares de verde público** no concelho do Porto (132 polígonos PDM com cobertura verde detectada por satélite). Este valor corresponde a **19,3 m² por habitante** — acima do limiar da OMS em termos agregados.

Contudo, o verde público representa apenas **12,5%** da cobertura verde total do município (3 587 ha). A maioria do verde portuense é de natureza privada: jardins de moradias, logradouros, quintais e interiores de quarteirão totalizam uma área estimada de **1 678 hectares** — quase quatro vezes a área verde pública. Esta constatação reforça a relevância dos espaços verdes privados como componente estrutural do ecossistema urbano, embora não contribuam directamente para a acessibilidade pública.

### 4.2. Acessibilidade 2SFCA: a desigualdade revelada

A distribuição espacial da acessibilidade a verde público no raio de 500 m é fortemente heterogénea:

| Classe de acessibilidade | Área (% do concelho) | Interpretação |
|---|---|---|
| 0–3 m²/hab | **20,0%** | Défice severo |
| 3–6 m²/hab | **13,7%** | Insuficiente |
| 6–9 m²/hab | **11,5%** | Limiar OMS |
| 9–15 m²/hab | **15,0%** | Adequado |
| > 15 m²/hab | **39,8%** | Bom |

**45,2% do território habitado do Porto apresenta uma acessibilidade a verde público inferior ao limiar da OMS de 9 m²/hab** — uma realidade radicalmente diferente da narrativa optimista sugerida pela métrica agregada (19,3 m²/hab).

A distribuição geográfica das classes de acessibilidade revela um padrão espacial claro e expectável:

- **Zona ocidental (Foz, Nevogilde, Aldoar)**: acessibilidade consistentemente elevada (>15 m²/hab), beneficiando da proximidade ao Parque da Cidade, a Serralves e ao corredor da frente atlântica. É a única zona do concelho onde a acessibilidade excede largamente o limiar.

- **Eixo Boavista–Palácio de Cristal**: acessibilidade adequada (9–15 m²/hab), sustentada pelos Jardins do Palácio de Cristal e pela arborização de praças e alamedas.

- **Centro histórico e Baixa (Sé, Miragaia, Vitória, Cedofeita)**: défice severo a insuficiente (0–6 m²/hab). O tecido urbano densíssimo e a quase inexistência de espaços verdes públicos de dimensão significativa produzem valores de acessibilidade próximos de zero — agravados pela elevada densidade populacional.

- **Interior de Paranhos e Ramalde**: valores heterogéneos, com bolsas de défice severo intercaladas com zonas de acessibilidade razoável junto a equipamentos escolares com jardim.

- **Campanhã oriental**: défice persistente, apesar da presença pontual de verde associado a equipamentos. A estrutura verde pública é residual e fragmentada.

### 4.3. Défice ponderado: onde o problema é mais grave

O mapa de défice ponderado pela população revela as zonas críticas onde a combinação de alta densidade habitacional e baixa acessibilidade a verde público produz o maior impacto:

As áreas de maior défice ponderado concentram-se no **eixo central e oriental** — Cedofeita, Bonfim, Paranhos interior e Campanhã ocidental. Estas são zonas de elevada densidade residencial (100–300 hab/pixel na grelha GHS-POP) onde o verde público mais próximo se encontra a mais de 500 m, ou onde os espaços existentes são demasiado pequenos para a população envolvente.

Em contrapartida, a periferia norte e oriental — apesar de valores de acessibilidade igualmente baixos — pontua menos no défice ponderado por ter densidades populacionais menores. O método permite assim distinguir entre "pouco verde num campo" (problema menor) e "pouco verde num bairro denso" (problema urgente).

### 4.4. O papel do verde privado

Um resultado notável desta análise é a magnitude do verde privado: os 1 678 hectares de espaços verdes encravados em quarteirões, logradouros e jardins de moradias representam uma "infraestrutura verde oculta" que — embora não acessível ao público — presta serviços ecossistémicos locais críticos: infiltração pluvial, regulação microclimática, habitat para fauna urbana e valor estético.

Se se incluísse o verde privado no cálculo de acessibilidade (o que não é conceptualmente correcto para uma análise de equidade no acesso público, mas é relevante para uma análise de serviços ecossistémicos), os valores de acessibilidade subiriam substancialmente em zonas residenciais de baixa densidade — precisamente as áreas que já beneficiam de maior dotação pública. Este resultado sublinha um paradoxo de equidade: as zonas com mais verde privado tendem a ter também mais verde público, enquanto as zonas densas carecem de ambos.

---

## 5. Discussão

### 5.1. Concordância com a literatura

O rácio agregado de 19,3 m²/hab de verde público é coerente com os 18,3 m²/hab reportados por Madureira *et al.* (2018) — a pequena diferença pode dever-se ao crescimento da arborização em espaços existentes e a diferenças de delimitação e de classificação.

A forte heterogeneidade espacial revelada pelo 2SFCA confirma as preocupações de Monteiro *et al.* (2025) sobre a desigualdade térmica no Porto: as zonas identificadas como de maior risco térmico (centro e leste) coincidem com as de menor acessibilidade a verde público. Esta sobreposição sugere um mecanismo de reforço mútuo: a ausência de verde agrava o calor urbano, que por sua vez torna mais urgente a necessidade de espaços verdes para refúgio.

### 5.2. Limitações

1. **Verde público vs. verde acessível**: o PDM define zonas de qualificação funcional, não parcelas individuais de acesso público. Alguns espaços classificados como "verde de fruição colectiva" podem ter restrições de acesso, enquanto certos jardins privados abertos ao público (como espaços de universidades) podem não estar contemplados.

2. **Distância euclidiana vs. distância de rede**: o raio de 500 m é medido em linha recta, não pela rede viária. Em áreas com barreiras topográficas (encostas íngremes, viadutos, linhas de comboio), a distância real percorrida é significativamente superior. Uma análise futura com distância de rede (baseada em dados OpenStreetMap) aumentaria a precisão do modelo.

3. **Resolução temporal**: os dados populacionais (GHS-POP 2020) podem não reflectir alterações demográficas recentes — nomeadamente o crescimento do alojamento local turístico, que reduz a população residente efectiva em certas zonas (Baixa, Cedofeita) sem alterar a contagem censitária.

4. **Qualidade do verde**: o método trata todos os metros quadrados de verde como equivalentes. Na realidade, um relvado degradado junto a uma via rápida não presta os mesmos serviços que um parque arborizado com equipamento de lazer. A incorporação de indicadores de qualidade (dimensão das manchas, presença de arvoredo, equipamento) enriqueceria a análise.

### 5.3. Implicações para o planeamento

Os resultados sugerem que a estratégia municipal de verde público deveria priorizar investimentos no **eixo central e oriental** — as zonas onde o défice ponderado pela população é mais elevado. Intervenções como a abertura de logradouros e interiores de quarteirão ao uso público, a conversão de terrenos expectantes em jardins de bolso (*pocket parks*), e a arborização intensiva de praças e arruamentos poderiam melhorar significativamente a acessibilidade nas zonas mais carenciadas.

O contraste entre a abundância de verde privado (1 678 ha) e a escassez de verde público acessível (448 ha) levanta uma questão de política urbanística: até que ponto podem ser criados mecanismos de permeabilização do verde privado — por exemplo, incentivos à abertura parcial de logradouros, servidões de passagem em interiores de quarteirão, ou a obrigação de cedências verdes em operações urbanísticas — para complementar a rede de espaços verdes formalmente públicos?

---

## 6. Conclusões

A aplicação do método 2SFCA ao Porto revela que, apesar de uma dotação agregada de 19,3 m² de verde público por habitante — acima do limiar OMS —, **45,2% do território habitado da cidade apresenta uma acessibilidade efectiva inferior a 9 m²/hab** num raio pedonal de 500 m. O défice concentra-se no eixo central e oriental (Cedofeita, Bonfim, Paranhos interior, Campanhã ocidental), precisamente as zonas de maior densidade habitacional e, segundo a literatura, de maior vulnerabilidade térmica.

Esta análise demonstra que a métrica agregada per capita é insuficiente para avaliar a equidade no acesso a verde urbano. A acessibilidade espacial — que pondera simultaneamente a oferta, a procura e a distância — oferece um diagnóstico mais fiel da experiência real dos residentes e constitui um instrumento de planeamento mais rigoroso para a priorização de investimentos.

O mapa de défice ponderado pela população, em particular, identifica as áreas onde a intervenção teria o maior impacto social — fornecendo aos decisores uma ferramenta objectiva para a alocação de recursos na criação e melhoria de espaços verdes urbanos.

---

## 7. Nota Metodológica

Todo o processamento foi realizado em Python com *Google Earth Engine*, *scipy*, *NumPy* e *Shapely*. O código é aberto e reproduzível:

- [`acessibilidade/acessibilidade_verde.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/acessibilidade/acessibilidade_verde.py) — *pipeline* completo (classificação + 2SFCA + HTML)

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

**[Acessibilidade a Verde Público — Porto]({{ site.baseurl }}/acessibilidade/acessibilidade_verde.html)** — mapa com camadas de acessibilidade 2SFCA, défice ponderado, verde público e verde privado
