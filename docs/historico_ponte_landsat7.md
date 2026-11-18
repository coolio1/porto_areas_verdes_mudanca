# Histórico: ponte Landsat 7 (2026-11-18)

Substitui a normalização PIF (regressão em 3 tipos de alvo, REF 1985-90), que criava uma queda artificial de ~14 p.p. (52,4 → 38,0 %) entre 1985-90 e 2023-24.

## Diagnóstico (`ndvi_historico/diagnostico_anos.py`, % do concelho com NDVI ≥ 0,25, bruto)
- Landsat 5 (1985–2011): 45–56 %. Landsat 7 (1999–2021): 46–57 %; L5 ≈ L7 (49,8 vs 49,5 % em 1999–2011).
- Landsat 8/9 (2013–2024): 60–64 %; L8 62,6 % vs L7 53,6 % na sobreposição 2013–2021 → salto de sensor, não de paisagem.

## Método
- L5 em bruto (sem ajuste).
- L8/9: harmonização OLI→TM (Roy 2016) + desvio aditivo de NDVI = média(L8 − L7) sobre o concelho, 2013–2021: **+0,0413**, subtraído às épocas 2016-17 e 2023-24.
- Resultado na sobreposição: L8 corrigido 53,1 % vs L7 53,6 %.

## Série resultante (% do concelho)
2023-24 53,8 · 2016-17 52,5 · 2001-05 47,3 · 1995-00 50,9 · 1985-90 52,4 · 1979 50,0 (outra fonte) · 1947 74,5 (outra fonte).

## Limites
- O desvio é único (média do concelho); não corrige diferenças locais.
- Variação ano a ano (seca) de ±3–5 p.p. > diferença 1985-90 vs 2023-24 (+1,4 p.p.): sem tendência afirmável nesse intervalo.
- O artigo `_posts/2026-03-21-mudanca-verde-porto-1947-2025.md` usa números e método PIF anteriores (ex.: 30,0 % em 2024): por rever.
