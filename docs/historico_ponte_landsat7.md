# Histórico: ponte Landsat 7, fracção de vegetação e incerteza (2026-11-18)

Substitui a normalização PIF (regressão em 3 tipos de alvo), que criava uma queda artificial de ~14 p.p. (52,4 → 38,0 %) entre 1985-90 e 2023-24, e o limiar fixo NDVI ≥ 0,25. Revisto com o advisor (Opus) no mesmo dia.

## Diagnóstico (`ndvi_historico/diagnostico_anos.py`)
- Landsat 5 ≈ Landsat 7 (49,8 vs 49,5 % em 1999–2011, limiar 0,25). Landsat 8/9 dá +7 a +9 p.p. sobre o 7 na sobreposição 2013–2021: salto de sensor, não de paisagem.
- O limiar 0,25 a 30 m sobrestimava a vegetação urbana: 27 % do construído de 1979 contava como vegetação em 1985-90 (36 % em 2023-24).

## Método (`ndvi_historico/ndvi_historico.py`)
1. **Ponte de sensor.** L5 em bruto. L8/9 em reflectância de superfície C2, sem harmonização de Roy (os coeficientes usados não eram os de Roy para NDVI e a Google não a recomenda na C2). Desvio aditivo de NDVI = média(L8 − L7) no concelho, 2013–2021: **+0,0341**, subtraído a 2016-17 e 2023-24.
2. **Fracção de vegetação por píxel.** Curva empírica **monótona** NDVI → fracção (médias por classe de NDVI, regressão isotónica), calibrada em 2023-24 contra «Árvores + Solo» do tema Hoje (Sentinel-2, 10 m; `layers/uso_arvores.png` + `uso_solo.png`). Guardada em `layers_historico/fvc_calibracao.json`. Fracção 50 % ≈ NDVI 0,34; o limiar antigo 0,25 correspondia a só ~23 %. A mesma curva aplica-se a todas as épocas.
3. **Camadas.** `veg_<época>.png`: alfa = fracção (16 níveis); `edif_<época>.png`: alfa = 1 − fracção, só dentro do concelho e sem água permanente (JRC > 50 %). Números = média do alfa no concelho (`mapa_unico/historico_numeros.py`; 1947 e 1979 contam píxeis, são binárias).
4. **Perda/ganho 1985-90 → 2023-24.** Variação da fracção ≥ 0,30 entre o início (média 1985-90 e 1995-00) e o fim (média 2016-17 e 2023-24), em manchas ≥ 0,5 ha dentro do concelho: ~223 ha de perda e ~294 ha de ganho.
5. **Incerteza** (`layers_historico/incerteza.json`): erro-padrão da % por ano dentro de cada época; épocas L8/9 somam em quadratura o erro da ponte L8−L7 (resíduo após o desvio: +0,8 ± 0,4 p.p.).

## Série (% do concelho com vegetação; 1σ)
2023-24 35,2 (±0,5) · 2016-17 34,6 (±1,4) · 2001-05 30,0 (±0,9) · 1995-00 32,8 (±0,6) · 1985-90 32,5 (±1,3) · 1979 50,0 (outra fonte) · 1947 74,5 (outra fonte).
Consistente com o tema Hoje (35,6 % por construção) e com Guilherme et al. 2022 (~35 % em 2019, em segunda mão). 1985-90 → 2023-24 = +2,7 p.p. (σ combinado 1,4): ligeira subida; a quebra está em 2001-05 (mínimo, 30,0 %).

## Limites
- A referência é uma classificação de satélite (Sentinel-2, regras sazonais), não verdade de terreno. A ortofoto DGT 2025 foi tentada e não serve: só RGB, as copas escuras ficam cinzentas (ExGR, ExG e HSV falharam).
- O desvio de sensor é único (média do concelho); sobra +0,8 p.p. de resíduo entre L8 e L7.
- 1947 (74,5 %, `1947/clean_1947.py` só converte edificado em vegetação) e 1979 (50,0 %, vegetação = árvores, arbustos e herbáceas) usam outra definição: **não comparáveis** com a série Landsat (os 1979 e 1947 ficam acima porque contam herbáceas/campos como vegetação). Série longa de uma só fonte: camadas de Guilherme et al. 1947/1979/2019 (pedir à autora).
- O artigo `_posts/2026-03-21-mudanca-verde-porto-1947-2025.md` foi corrigido em 2026-11-18 (série, método, Sentinel-2 só do concelho; revisão por leitor leigo). A animação (`animacao/`) usa a série antiga: por refazer.
