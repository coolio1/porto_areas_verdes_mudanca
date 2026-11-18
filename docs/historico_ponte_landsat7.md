# Histórico: ponte Landsat 7 e incerteza (2026-11-18)

Substitui a normalização PIF (regressão em 3 tipos de alvo, REF 1985-90), que criava uma queda artificial de ~14 p.p. (52,4 → 38,0 %) entre 1985-90 e 2023-24. Revisto com o advisor (Opus) no mesmo dia.

## Diagnóstico (`ndvi_historico/diagnostico_anos.py`, % do concelho com NDVI ≥ 0,25, bruto)
- Landsat 5 (1985–2011): 45–56 %. Landsat 7 (1999–2021): 46–57 %; L5 ≈ L7 (49,8 vs 49,5 % em 1999–2011).
- Landsat 8/9 (2013–2024): 60–64 %; salto de sensor, não de paisagem.

## Método (`ndvi_historico/ndvi_historico.py`)
- L5 em bruto. L8/9 em reflectância de superfície C2, **sem** harmonização de Roy (retirada: os coeficientes usados não eram os de Roy para NDVI e a Google não a recomenda na C2).
- Desvio aditivo de NDVI = média(L8 − L7) no concelho, 2013–2021: **+0,0341**, subtraído a 2016-17 e 2023-24. Sobreposição: L7 53,6 %, L8 bruto 60,7 %, L8 corrigido 52,8 %.
- Incerteza (`layers_historico/incerteza.json`): erro-padrão da % por ano dentro de cada época; épocas L8/9 somam em quadratura o erro da ponte (±0,4 p.p.).
- Perda/ganho 1985-90 → 2023-24 com histerese: classe igual nas 2 épocas de cada ponta, salto de NDVI ≥ 0,15 e manchas ≥ 0,5 ha (filtro em Python depois do download). Resultado: ~44 ha de perda, ~46 ha de ganho (a versão simples dava 1336/1043 ha: ruído do limiar).

## Série (% do concelho com vegetação; ±1σ)
2023-24 53,6 (±0,5) · 2016-17 52,2 (±1,4) · 2001-05 47,3 (±1,2) · 1995-00 50,9 (±0,9) · 1985-90 52,4 (±1,5) · 1979 50,0 (outra fonte) · 1947 74,5 (outra fonte).
1985-90 → 2023-24: +1,2 p.p., = 0,8σ (σ combinado 1,6) → sem tendência detectável.

## Limites e por fazer (fase 2, decidida: «tudo, por fases»)
- A métrica «píxel ≥ 0,25» sobrestima a vegetação (27 % do construído de 1979 conta como vegetação em 1985-90; 36 % em 2023-24) e não separa perda real de píxeis mistos. Fase 2: fracção de vegetação por píxel (NDVI→cobertura calibrado com Sentinel-2 2024-25 / ortofoto DGT 2025 / copa LiDAR) e ponte por regressão L8~L7 por píxel.
- O 1947 (74,5 %) usa uma limpeza (`1947/clean_1947.py`) que só converte edificado em vegetação (edificado 40,3 → 21,2 %); o «desde 1947» saiu do painel. Série longa de uma só fonte: camadas de Guilherme et al. 1947/1979/2019 (pedir à autora).
- O desvio é único (média do concelho).
- O artigo `_posts/2026-03-21-mudanca-verde-porto-1947-2025.md` usa números e método PIF anteriores: por rever.
