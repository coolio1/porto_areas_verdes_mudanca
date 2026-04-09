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

O Porto dispõe de 19,3 m² de espaço verde público por habitante — acima do limiar de 9 m²/hab frequentemente atribuído à OMS. Porém, esta métrica agregada esconde uma realidade desigual: quem vive junto ao Parque da Cidade tem uma dotação generosa; quem habita na Sé, em Campanhã ou no interior de Paranhos pode não ter nenhum espaço verde acessível a pé.

Este trabalho aplica o método *Two-Step Floating Catchment Area* (2SFCA) ao município do Porto, cruzando um inventário de 47 parques e jardins de acesso público gratuito, a classificação de uso do solo por Sentinel-2, e a grelha de população GHS-POP. O resultado é um mapa da acessibilidade efectiva a verde público em m² por habitante num raio pedonal de 500 m.

---

## 2. Enquadramento

### 2.1. Verde público no Porto: a ilusão do agregado

A tensão entre indicadores agregados favoráveis e realidades locais deficitárias é um tema recorrente na literatura sobre o Porto. Quental (2010), na sua tese sobre modelação de estrutura urbana sustentável na Área Metropolitana do Porto, já identificava a distribuição espacial assimétrica da infraestrutura verde como um dos principais desafios da sustentabilidade urbana na região. A análise GIS de Quental para as 130 freguesias da AMP revelou que a distância média ponderada pela população ao espaço verde mais próximo era de 1 110 m em 2006 (contra 1 403 m em 1991) — uma melhoria ao longo do tempo, mas ainda muito acima do limiar de 300 m recomendado pela OMS — e que "algumas áreas densas de Vila Nova de Gaia, Gondomar e Matosinhos estão bastante mal equipadas" em termos de verde acessível (Quental, 2010, p. 262). Quental & Macedo (2006), no diagnóstico de indicadores de desenvolvimento sustentável para o Grande Porto, quantificaram esta assimetria e alertaram para a insuficiência das métricas per capita como instrumento de planeamento.

Graça *et al.* (2018) mapearam 95 espaços verdes no Porto (~424 ha). A presente análise identifica **448 ha de verde público classificado** pelo PDM 2021 — valor coerente. Contudo, desta área, apenas ~202 ha correspondem a parques e jardins de acesso efectivamente livre. Hoffimann *et al.* (2017), usando análise de rede viária e o *Public Open Space Tool*, demonstraram que o acesso a verde no Porto varia com o estatuto socioeconómico: 90% da população nos bairros menos desfavorecidos vive a ≤800 m de um espaço verde, contra 75,8% nos mais desfavorecidos. Saraiva *et al.* (2025) confirmaram estas desigualdades com análise de correspondência múltipla aplicada a 89 espaços verdes públicos.

### 2.2. Equidade e vulnerabilidade térmica

Wolch *et al.* (2014) sintetizaram a evidência de que populações de menor rendimento tendem a residir em bairros com menor acesso a verde — o *green gentrification paradox*. No Porto, Lopes *et al.* (2025) demonstraram que 32,6% do território se encontra em zonas de elevado risco térmico, precisamente nas áreas de maior densidade e menor cobertura vegetal. Os modelos de Quental (2010) para a AMP — que classificaram a estrutura territorial de 130 freguesias em domínios de sustentabilidade usando redes neuronais, equações estruturais e regressão múltipla — já mostravam que a forma urbana compacta favorece padrões de mobilidade e consumo mais sustentáveis, mas que o rendimento e a dimensão das famílias são os factores que mais influenciam os padrões ambientais à escala da freguesia. Este resultado reforça a necessidade de intervir directamente na infraestrutura verde das zonas densas, onde a forma urbana por si só não compensa o défice.

### 2.3. O método 2SFCA

As métricas tradicionais — área per capita por freguesia, buffers de proximidade, NDVI médio — apresentam limitações conhecidas: diluem a informação em médias administrativas, não distinguem dimensão dos espaços, ou confundem verde público com privado.

O método *Two-Step Floating Catchment Area* (Luo & Wang, 2003) supera estas limitações ao considerar simultaneamente a oferta (área verde) e a procura (população) num raio definido. Para cada espaço verde, calcula-se o rácio área/população servida; para cada ponto de população, somam-se os rácios dos espaços acessíveis. O resultado captura o efeito de saturação: um parque pequeno rodeado por muita gente vale menos, por pessoa, do que um parque grande com pouca população. Dai (2011) aplicou-o a Atlanta, Rigolon (2016) evidenciou o papel da qualidade dos parques, e Luo & Qi (2009) propuseram a variante com decaimento gaussiano — embora para raios pedonais curtos (≤500 m) a diferença prática seja marginal (Langford *et al.*, 2008).

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

### 3.2. Inventário de parques

Compilou-se uma lista de **47 parques e jardins de acesso público e gratuito**, partindo do directório oficial da CMP (20 espaços) e complementando com espaços omitidos mas de acesso comprovadamente livre: gestão municipal (21), gestão institucional com acesso gratuito (8), espaços adicionais identificados (9) e micro-jardins (9). Contornos obtidos via OpenStreetMap (Overpass API / API v0.6), com polígonos PDM e buffers georreferenciados como recurso. Área total: **~202 hectares**.

A classificação Sentinel-2 seguiu a metodologia multi-sazonal descrita em Quental (2026), com 90,4% de concordância com o ESA WorldCover 2021 para a classe arbórea. Esta classificação é utilizada para a **camada visual** do mapa, mas o cálculo de acessibilidade usa a área total dos polígonos.

Os 132 polígonos do PDM que **não correspondem** a nenhum dos 47 parques (jardins de escolas, hortas com acesso restrito, separadores viários) são apresentados como "Verde pago ou não usufruível".

### 3.3. Cálculo do 2SFCA

Implementação em versão raster contínua no Google Earth Engine:

1. Máscara binária dos 47 parques × área do pixel (57 m²)
2. Soma focal do verde num kernel circular de raio 500 m (76×58 pixels)
3. Soma focal da população (GHS-POP, corrigida para reamostragem: factor ~1/175)
4. Filtro: exclui pixels com <50 hab no raio de 500 m
5. Acessibilidade = verde_500m / pop_500m (m²/hab)

O raio de 500 m é um compromisso entre o limiar europeu de 300 m (OMS, 2016) e a topografia acidentada do Porto.

---

## 4. Resultados

### 4.1. Verde público: inventário

O inventário totaliza **47 parques e jardins** (~202 ha), inferior aos 448 ha do PDM por excluir espaços sem usufruto livre. Os 202 ha correspondem a **~8,7 m²/hab** — ligeiramente abaixo do limiar de 9 m²/hab.

<details>
<summary><strong>Tabela: 47 parques e jardins inventariados (clicar para expandir)</strong></summary>

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
| Parque de Requesende | 31 600 |
| Rotunda da Boavista | 30 800 |
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
| Alameda das Fontainhas | 11 300 |
| Jardim de Sarah Afonso | 10 400 |
| Parque Urbano Dr. Mário Soares | 8 200 |
| Jardim de Teodoro de Sousa | 7 800 |
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
| **Total** | **2 018 300** |

</details>

### 4.2. Acessibilidade 2SFCA: a desigualdade revelada

| Classe de acessibilidade | População | % |
|---|---:|---:|
| Défice crítico (0–3 m²/hab) | 154 033 | 63,5% |
| Insuficiente (3–9 m²/hab) | 49 330 | 20,3% |
| Adequado (>9 m²/hab) | 39 062 | 16,1% |

**83,9% da população do Porto** — ~203 mil pessoas — vive com acessibilidade inferior a 9 m²/hab num raio de 500 m. Quase dois terços (63,5%) estão em défice crítico (<3 m²/hab). Apenas 16,1% tem acesso adequado.

### 4.3. Padrão geográfico

- **Centro histórico e Baixa** (Sé, Miragaia, Santo Ildefonso): défice crítico. Tecido urbano denso, espaços verdes diminutos (Cordoaria, S. Lázaro) insuficientes para a população. Zona com o défice mais severo do concelho.
- **Cedofeita interior e Bonfim**: 0–6 m²/hab. Malha consolidada com poucos interstícios verdes.
- **Paranhos e Ramalde interiores**: heterogéneos. O Parque da Asprela e o de Requesende servem a zona universitária, mas os bairros entre a VCI e a Circunvalação apresentam défice.
- **Campanhã**: Parque Oriental e Quinta de Bonjóia melhoram pontualmente, mas a zona industrial e os bairros a norte ficam próximos de zero.
- **Eixo Boavista–Palácio de Cristal**: adequado (>9 m²/hab).
- **Foz–Nevogilde–Aldoar**: consistentemente >15 m²/hab — Parque da Cidade, Frente Atlântica, jardins marítimos. Única zona que excede largamente o limiar.

### 4.4. Proximidade 300m: o critério de Konijnendijk

A regra 3-30-300 (Konijnendijk, 2023) propõe que todos os residentes devem ter acesso a um espaço verde de ≥1 ha a ≤300 m de casa. Aplicando este critério aos 28 parques do inventário com área ≥1 ha:

| Critério 300m (parques ≥1 ha) | População | % |
|---|---:|---:|
| Cumpre (≤300 m) | 78 938 | 32,6% |
| Não cumpre (>300 m) | 163 487 | 67,4% |

**Dois terços da população do Porto** não tem acesso a um parque de dimensão significativa a uma distância pedonal curta. Este resultado complementa o 2SFCA: mesmo os 20,3% da população na faixa "insuficiente" (3–9 m²/hab) podem estar a mais de 300 m do parque mais próximo — a acessibilidade 2SFCA reflecte parques distantes que "chegam" ao raio de 500 m mas não ao de 300 m.

### 4.5. Verde privado: o paradoxo de equidade

Os 1 678 ha de verde privado (quarteirões, logradouros, moradias) prestam serviços ecossistémicos locais — mas não são acessíveis ao público. As zonas com mais verde privado são as mesmas que já dispõem de mais verde público, enquanto as zonas densas carecem de ambos.

---

## 5. O Porto no Contexto Europeu e Internacional

O défice de acessibilidade a verde no Porto não é um caso isolado — mas a comparação com outras cidades exige cautela, porque os valores de m²/hab variam enormemente conforme a definição adoptada: verde público acessível, verde público total (incluindo parques periféricos), ou verde total (incluindo florestas urbanas). A tabela seguinte compara o Porto com Lisboa e oito cidades internacionais, distinguindo os valores "com tudo" dos valores "efectivos".

### 5.1. Lisboa: o mesmo problema com números diferentes

Lisboa é o caso comparativo mais directo. A cidade reporta ~37 m²/hab de verde público — mas este valor inclui o Parque Florestal de Monsanto (~900 ha), que sozinho representa cerca de metade do verde total. Sem Monsanto, a dotação cai para ~7–10 m²/hab, comparável ao Porto sem o Parque da Cidade. Catarino *et al.* (2025), num estudo de 26 capitais europeias, calcularam para Lisboa um *Urban Green Equity Index* de 0,387 — abaixo da média europeia — com desigualdades intra-urbanas marcadas: bairros como o Parque das Nações dispõem de verde abundante, enquanto Marvila e Beato apresentam défices severos. O projecto GREEN SURGE (2015) já documentara esta fragmentação. O diagnóstico é estruturalmente o mesmo que no Porto: um ou dois grandes parques periféricos mascaram a escassez no tecido urbano denso.

### 5.2. Panorama internacional

| Cidade | Verde/hab | Valor efectivo | Desigualdade intra-urbana |
|---|---|---|---|
| **Porto** | 19,3 m² (PDM total) | **8,7 m²** (usufruível) | 83,9% da pop. abaixo de 9 m²/hab; centro histórico ≈0 |
| **Lisboa** | ~37 m² (c/ Monsanto) | **~7–10 m²** (s/ Monsanto) | UGEI 0,387; Marvila/Beato vs. Parque das Nações |
| **Barcelona** | ~17 m² (c/ Collserola) | **~7 m²** (s/ Collserola) | Apenas 33% da pop. a <300 m de parque urbano |
| **Paris** | ~10,6 m² (c/ Bois) | **~8,6 m²** (intra-muros) | 42–55% abaixo de 10 m²/hab; plano bioclimático 2035 |
| **Copenhaga** | ~32 m² | **~32 m²** | ≥80% a <300 m de verde; meta: todos a <15 min a pé |
| **Amesterdão** | ~24 m² | **~24 m²** | Standard NL: 60 m²/hab acessível num raio de 500 m |
| **Berlim** | ~88 m² (c/ florestas) | **variável** | Standard: ≥0,5 ha a <500 m; 74% da pop. a <300 m |
| **Viena** | 55–95 m² (c/ Wienerwald) | **<2 m²** nos distritos centrais | Josefstadt 0,8 m²; Neubau 1,2 m²; Margareten 1,5 m² |
| **Londres** | ~32 m² (16 m² parques) | **<0,44 m²** para 750 mil pessoas | 47% da área é verde, mas distribuição muito desigual |
| **Singapura** | ~66 m² | **variável** | 46% do território é verde; heterogeneidade por área de planeamento |

Fontes: Russo & Cirella (2018); Kabisch & Haase (2014); Nghiem *et al.* (2021); Catarino *et al.* (2025); EEA (2022); dados municipais.

### 5.3. Três lições da comparação

**1. O "efeito Monsanto" é universal.** Porto, Lisboa, Barcelona, Paris e Viena partilham o mesmo padrão: um ou dois grandes parques periféricos (Parque da Cidade, Monsanto, Collserola, Bois de Boulogne/Vincennes, Wienerwald) que inflacionam os indicadores agregados enquanto os bairros densos do centro ficam com valores próximos de zero. As cidades do Sul da Europa são particularmente afectadas pela combinação de centros históricos compactos com malha verde residual. O Porto encaixa-se neste padrão mediterrânico de défice estrutural.

**2. Ter muito verde não garante equidade.** Viena ilustra isto de forma extrema: com 55–95 m²/hab no agregado, é uma das cidades mais verdes da Europa — mas os distritos centrais de Josefstadt e Neubau ficam abaixo de 1,5 m²/hab, valores comparáveis aos piores do centro do Porto. Londres, com 47% da sua área classificada como verde, ainda tem 750 mil pessoas com menos de 0,44 m²/hab (CPRE London). A lição é clara: a quantidade total de verde não substitui a acessibilidade local.

**3. O standard de 9 m²/hab precisa de ser repensado.** O limiar de 9 m²/hab, frequentemente atribuído à OMS, tem na realidade origem provável no Decreto Ministerial italiano de 1968 (Przewoźna *et al.*, 2024). A OMS recomenda oficialmente que todos os residentes tenham acesso a **≥0,5 ha de verde a <300 m de casa** (OMS, 2016) — um critério de proximidade, não de área per capita. A regra 3-30-300 de Konijnendijk (2023) vai mais longe: 3 árvores visíveis de cada casa, 30% de cobertura de copa por bairro, 300 m até ao verde mais próximo. Na AMP, Quental (2010) mediu uma distância média ponderada de 1 110 m ao espaço verde mais próximo — quase quatro vezes o limiar da OMS. Copenhaga e Amesterdão adoptaram standards ainda mais exigentes (15 min a pé e 60 m²/hab a 500 m, respectivamente), demonstrando que é possível estabelecer metas ambiciosas.

---

## 6. Discussão

### Concordância com a literatura

A forte heterogeneidade revelada pelo 2SFCA confirma três décadas de alertas sobre a desigualdade verde no Porto: desde o diagnóstico de indicadores de sustentabilidade do Grande Porto (Quental & Macedo, 2006), passando pelas desigualdades socioeconómicas documentadas por Hoffimann *et al.* (2017), até à vulnerabilidade térmica de Lopes *et al.* (2025). As zonas de maior risco térmico coincidem com as de menor acessibilidade a verde — um reforço mútuo entre ausência de verde e calor urbano. Quental (2010) demonstrou que a distância ao espaço verde mais próximo na AMP diminuiu de 1 403 m (1991) para 1 110 m (2006), reflectindo investimentos em parques, mas que a variável `green space distance` não se revelou estatisticamente significativa na modelação da mobilidade — sugerindo que a mera proximidade a verde, sem massa crítica de área, pode não ser suficiente para alterar comportamentos. Esta observação sublinha a importância de avaliar a acessibilidade efectiva (área por habitante, como no 2SFCA) e não apenas a distância ao parque mais próximo.

### Limitações

O raio de 500 m é euclidiano; a distância real pela rede viária é superior, especialmente nas encostas do Porto. Os dados de população (GHS-POP 2020) podem não reflectir alterações recentes do alojamento local. O método trata todos os m² de verde como equivalentes — a incorporação de qualidade (arvoredo, equipamento, como proposto por Rigolon, 2016) enriqueceria a análise. Podem existir pequenos espaços verdes de acesso livre não contemplados no inventário.

### Implicações

A estratégia municipal deveria priorizar o **eixo central e oriental** — onde o défice ponderado pela população é mais severo. Intervenções possíveis: abertura de logradouros ao uso público, conversão de terrenos expectantes em jardins de bolso (*pocket parks*), arborização intensiva de praças. O contraste entre 1 678 ha de verde privado e 202 ha de verde usufruível levanta a questão da permeabilização: incentivos à abertura parcial de logradouros, servidões de passagem, cedências verdes em operações urbanísticas — mecanismos que Quental (2010) já propunha como instrumento de reequilíbrio territorial no Porto.

---

## 7. Conclusões

**83,9% da população do Porto** vive com acessibilidade a verde público inferior a 9 m²/hab num raio de 500 m. **63,5%** encontra-se em défice crítico (<3 m²/hab), concentrado no centro e leste — as zonas mais densas e termicamente vulneráveis. Apenas 16,1% tem acesso adequado. Aplicando o critério de proximidade de Konijnendijk (2023), **67,4% da população** não tem um parque de ≥1 ha a ≤300 m de casa.

Dos 448 ha classificados como verde público pelo PDM, apenas ~202 ha são efectivamente usufruíveis. A métrica agregada per capita é insuficiente para avaliar a equidade — e o Porto não é caso único: Lisboa, Barcelona e Paris partilham o mesmo padrão de défice estrutural em núcleos densos.

---

## 8. Nota Metodológica

Processamento em Python com *Google Earth Engine*, *scipy*, *NumPy* e *Shapely*. Código aberto:

- [`acessibilidade_verde.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/acessibilidade/acessibilidade_verde.py) — pipeline completo (classificação + 2SFCA + HTML)
- [`criar_parques.py`](https://github.com/coolio1/porto_areas_verdes_mudanca/blob/main/acessibilidade/criar_parques.py) — inventário de 47 parques (Overpass API + PDM)

---

## 9. Referências

- Catarino, L. *et al.* (2025). Mapping Green Space Inequalities in 26 European Cities. *Land*, 14(12), 2362. [doi:10.3390/land14122362](https://doi.org/10.3390/land14122362)
- Dai, D. (2011). Racial/ethnic and socioeconomic disparities in urban green space accessibility: Where to intervene? *Landscape and Urban Planning*, 102(4), 234–244. [doi:10.1016/j.landurbplan.2011.05.002](https://doi.org/10.1016/j.landurbplan.2011.05.002)
- EEA (2022). *Who benefits from nature in cities? Social inequalities in access to urban green and blue spaces across Europe*. European Environment Agency. [https://www.eea.europa.eu/publications/who-benefits-from-nature-in](https://www.eea.europa.eu/publications/who-benefits-from-nature-in)
- Graça, M., Alves, P., Gonçalves, J., Nowak, D.J., Hoehn, R., Farinha-Marques, P. & Cunha, M. (2018). Assessing how green space types affect ecosystem services delivery in Porto, Portugal. *Landscape and Urban Planning*, 170, 195–208. [doi:10.1016/j.landurbplan.2017.11.007](https://doi.org/10.1016/j.landurbplan.2017.11.007)
- GREEN SURGE (2015). *Lisbon, Portugal — Case study portrait*. GREEN SURGE Project, EU FP7.
- Hoffimann, E., Barros, H. & Ribeiro, A.I. (2017). Socioeconomic inequalities in green space quality and accessibility — Evidence from a Southern European city. *International Journal of Environmental Research and Public Health*, 14(8), 916. [doi:10.3390/ijerph14080916](https://doi.org/10.3390/ijerph14080916)
- Kabisch, N. & Haase, D. (2014). Green justice or just green? Provision of urban green spaces in Berlin, Germany. *Landscape and Urban Planning*, 122, 129–139. [doi:10.1016/j.landurbplan.2013.11.016](https://doi.org/10.1016/j.landurbplan.2013.11.016)
- Konijnendijk, C.C. (2023). Evidence-based guidelines for greener, healthier, more resilient neighbourhoods: Introducing the 3-30-300 rule. *Journal of Forestry Research*, 34, 821–830. [doi:10.1007/s11676-022-01523-z](https://doi.org/10.1007/s11676-022-01523-z)
- Langford, M., Higgs, G., Radcliffe, J. & White, S. (2008). Urban population distribution models and service accessibility estimation. *Computers, Environment and Urban Systems*, 32(1), 66–80. [doi:10.1016/j.compenvurbsys.2007.06.001](https://doi.org/10.1016/j.compenvurbsys.2007.06.001)
- Lopes, H.S., Vidal, D.G., Cherif, N., Silva, L. & Remoaldo, P.C. (2025). Green infrastructure and its influence on urban heat island, heat risk, and air pollution: A case study of Porto (Portugal). *Journal of Environmental Management*, 376, 124446. [doi:10.1016/j.jenvman.2025.124446](https://doi.org/10.1016/j.jenvman.2025.124446)
- Luo, W. & Qi, Y. (2009). An enhanced two-step floating catchment area (E2SFCA) method for measuring spatial accessibility to primary care physicians. *Health & Place*, 15(4), 1100–1107. [doi:10.1016/j.healthplace.2009.06.002](https://doi.org/10.1016/j.healthplace.2009.06.002)
- Luo, W. & Wang, F. (2003). Measures of spatial accessibility to health care in a GIS environment: Synthesis and a case study in the Chicago region. *Environment and Planning B*, 30(6), 865–884. [doi:10.1068/b29120](https://doi.org/10.1068/b29120)
- Nghiem, L.T., Zhang, Y., Oh, R.R.Y., Chang, C.C., Tan, C.L., Shanahan, D.F. & Carrasco, L.R. (2021). Equity in green and blue spaces availability in Singapore. *Landscape and Urban Planning*, 210, 104083. [doi:10.1016/j.landurbplan.2021.104083](https://doi.org/10.1016/j.landurbplan.2021.104083)
- OMS (2016). *Urban green spaces and health: A review of evidence*. WHO Regional Office for Europe. [https://www.who.int/europe/publications/i/item/WHO-EURO-2016-3352-43111-60341](https://www.who.int/europe/publications/i/item/WHO-EURO-2016-3352-43111-60341)
- Przewoźna, P. *et al.* (2024). Accessibility to urban green spaces: A critical review of the WHO standard. *Ecological Indicators*, 166. [doi:10.1016/j.ecolind.2024.112357](https://doi.org/10.1016/j.ecolind.2024.112357)
- Quental, N. (2010). *Modeling a sustainable urban structure: An application to the Metropolitan Area of Porto*. Tese de doutoramento, Instituto Superior Técnico. [PDF](https://coolio1.github.io/pdfs/2010-08-02%20-%20Tese%20de%20doutoramento.pdf)
- Quental, N. (2026). Dinâmicas de Ocupação do Solo e Cobertura Vegetal na Cidade do Porto (1947–2025). [https://coolio1.github.io/porto_areas_verdes_mudanca/posts/mudanca-verde-porto-1947-2025/](https://coolio1.github.io/porto_areas_verdes_mudanca/posts/mudanca-verde-porto-1947-2025/)
- Quental, N. & Macedo, M. (2006). *Indicadores de desenvolvimento sustentável para o Grande Porto*. Futuro Sustentável / Universidade Católica Portuguesa. [PDF](https://coolio1.github.io/pdfs/2005%20-%20Indicadores%20de%20sustentabilidade%20para%20o%20Grande%20Porto.pdf)
- Rigolon, A. (2016). A complex landscape of inequity in access to urban parks: A literature review. *Landscape and Urban Planning*, 153, 160–169. [doi:10.1016/j.landurbplan.2016.05.017](https://doi.org/10.1016/j.landurbplan.2016.05.017)
- Russo, A. & Cirella, G.T. (2018). Modern compact cities: How much greenery do we need? *International Journal of Environmental Research and Public Health*, 15(10), 2180. [doi:10.3390/ijerph15102180](https://doi.org/10.3390/ijerph15102180)
- Saraiva, M., Cavallaro, F., Sá Marques, T., Teixeira, B. & Ribeiro, G. (2025). Assessing equity in the accessibility to urban greenspaces: A socio-spatial vulnerability perspective in Porto, Portugal. *Environment and Planning B*. [doi:10.1177/23998083251407460](https://doi.org/10.1177/23998083251407460)
- Schiavina, M., Freire, S. & MacManus, K. (2023). GHS-POP R2023A — GHS population grid multitemporal (1975–2030). *European Commission, Joint Research Centre*. [https://data.jrc.ec.europa.eu/dataset/2ff68a52-5b5b-4a22-8f40-c41da8332cfe](https://data.jrc.ec.europa.eu/dataset/2ff68a52-5b5b-4a22-8f40-c41da8332cfe)
- Wolch, J.R., Byrne, J. & Newell, J.P. (2014). Urban green space, public health, and environmental justice: The challenge of making cities 'just green enough'. *Landscape and Urban Planning*, 125, 234–244. [doi:10.1016/j.landurbplan.2014.01.017](https://doi.org/10.1016/j.landurbplan.2014.01.017)

---

## Mapa interactivo

**[Acessibilidade a Verde Público — Porto]({{ site.baseurl }}/acessibilidade/acessibilidade_verde.html)** — mapa com camadas de acessibilidade 2SFCA, parques e jardins (47 espaços com popups), verde pago/não usufruível e verde privado
