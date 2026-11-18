# Histórico: ponte Landsat 7, fracção de vegetação e incerteza (2026-11-18)

Substitui a normalização PIF (regressão em 3 tipos de alvo), que criava uma queda artificial de ~14 p.p. (52,4 → 38,0 %) entre 1985-90 e 2023-24, e o limiar fixo NDVI ≥ 0,25. Revisto com o advisor (Opus) no mesmo dia.

## Diagnóstico (`ndvi_historico/diagnostico_anos.py`)
- Landsat 5 ≈ Landsat 7 (49,8 vs 49,5 % em 1999–2011, limiar 0,25). Landsat 8/9 dá +7 a +9 p.p. sobre o 7 na sobreposição 2013–2021: salto de sensor, não de paisagem.
- O limiar 0,25 a 30 m sobrestimava a vegetação urbana: 27 % do construído de 1979 contava como vegetação em 1985-90 (36 % em 2023-24).

## Método (`ndvi_historico/ndvi_historico.py`)
0. **Controlo por cena** (`controlo_cenas.py` → `layers_historico/controlo_cenas.csv`; `cenas_aprovadas.py`). NDVI de cada cena (609, Jun–Set, 1985–2024) em dois alvos que não mudaram: construído 1979 ∩ construído Sentinel-2 2024 e árvores 1979 ∩ árvores 2024 (erodidos ~1 píxel Landsat). Cena rejeitada se o NDVI no construído está a > 3 desvios robustos (MAD) da mediana do sensor, ou nas árvores a > 3,5: 78 de 609 rejeitadas (névoa/nuvem não mascarada: ex. L8 2014-09-11 dá 0,37 onde o normal é 0,14). 2002 fica sem cenas válidas e sai do cálculo ano a ano.
1. **Ponte de sensor.** L5 em bruto. L8/9 passa à escala L7 por uma **recta** NDVI₇ = −0,0198 + 0,9586·NDVI₈, ajustada às medianas dos dois alvos (construído, árvores) na sobreposição L7/L8 2013–2021 (o desvio cresce com o NDVI: 0,026 no construído, 0,051 nas árvores). Substitui o desvio aditivo fixo +0,034. Nos construídos estáveis o NDVI fica plano entre épocas (0,127 / 0,121 / 0,115 / 0,112 / 0,118).
2. **Fracção de vegetação por píxel.** Curva empírica **monótona** NDVI → fracção (médias por classe de NDVI, regressão isotónica), calibrada em 2023-24 contra «Árvores + Solo» do tema Hoje (Sentinel-2, 10 m; `layers/uso_arvores.png` + `uso_solo.png`). Guardada em `layers_historico/fvc_calibracao.json`. Fracção 50 % ≈ NDVI 0,36; o limiar antigo 0,25 correspondia a só ~16 %. A mesma curva aplica-se a todas as épocas.
3. **Camadas.** `veg_<época>.png`: alfa = fracção (16 níveis); `edif_<época>.png`: alfa = 1 − fracção, só dentro do concelho e sem água permanente (JRC > 50 %). Números = média do alfa no concelho (`mapa_unico/historico_numeros.py`; 1947 e 1979 contam píxeis, são binárias).
4. **Perda/ganho 1985-90 → 2023-24.** Variação da fracção ≥ 0,30 entre o início (média 1985-90 e 1995-00) e o fim (média 2016-17 e 2023-24), em manchas ≥ 0,5 ha dentro do concelho: ~228 ha de perda e ~290 ha de ganho.
5. **Incerteza** (`layers_historico/incerteza.json`): erro-padrão da % por ano dentro de cada época; épocas L8/9 somam em quadratura o erro da ponte L8−L7 (resíduo após a recta: +0,6 ± 0,5 p.p.).

## Série (% do concelho com vegetação; 1σ)
2023-24 35,3 (±0,5) · 2016-17 34,7 (±1,4) · 2001-05 30,2 (±0,7) · 1995-00 33,0 (±0,6) · 1985-90 32,6 (±1,3) · 1979 50,0 (outra fonte) · 1947 74,5 (outra fonte).
Consistente com o tema Hoje (35,6 % por construção) e com Guilherme et al. 2022 (~35 % em 2019, em segunda mão). 1985-90 → 2023-24 = +2,7 p.p. (σ combinado 1,4): ligeira subida; a quebra está em 2001-05 (mínimo, 30,2 %). **A série é robusta ao controlo por cena e à recta de ponte**: antes (cenas todas, desvio +0,034) 32,5 / 32,8 / 30,0 / 34,6 / 35,2; depois 32,6 / 33,0 / 30,2 / 34,7 / 35,3 (≤ 0,2 p.p.). Calibrar para impor «sem aumento» não se faz: era assumir a resposta.

## Limites
- A referência é uma classificação de satélite (Sentinel-2, regras sazonais), não verdade de terreno. A ortofoto DGT 2025 foi tentada e não serve: só RGB, as copas escuras ficam cinzentas (ExGR, ExG e HSV falharam).
- Ponte L8→L7: recta de dois alvos (resíduo +0,6 ± 0,5 p.p.). As árvores estáveis sobem de NDVI com o tempo (0,56 em 1985–90 → 0,71 em 2023–24, na escala L7): maturação das copas e/ou sensor, não separável.
- 1947 (74,5 %, `1947/clean_1947.py` só converte edificado em vegetação) e 1979 (50,0 %, vegetação = árvores, arbustos e herbáceas) usam outra definição: **não comparáveis** com a série Landsat (os 1979 e 1947 ficam acima porque contam herbáceas/campos como vegetação). Série longa de uma só fonte: camadas de Guilherme et al. 1947/1979/2019 (pedir à autora).
- O artigo `_posts/2026-03-21-mudanca-verde-porto-1947-2025.md` foi corrigido em 2026-11-18 (série, método, Sentinel-2 só do concelho; revisão por leitor leigo). A animação (`animacao/`) usa a série antiga: por refazer.
