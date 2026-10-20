## Verde privado — pipeline de regeneração

O verde privado (`layers/interior_subsistente.png`) é calculado por `interiores/interiores_quarteiroes.py`:

1. **Classificação Sentinel-2** — base: `acessibilidade/layers/verde_total.png` (todos os pixels verdes)
2. **Subtrair parques e jardins** — camada `acessibilidade/parques_porto.geojson`
3. **Subtrair verde pago** — camada `acessibilidade/layers/verde_pago.png`
4. **Máscara de estradas** — OSM (buffer por tipo de via)
5. **Vectorização e filtragem** — área mínima e forma

**Para regenerar sem GEE**: apagar `layers/interior_subsistente.png` e `layers/interior_perdido.png`, depois correr `python interiores/interiores_quarteiroes.py` a partir da raiz do projecto. A fase 1 re-descarrega do GEE (~30s); as fases 2-5 são locais.

**Alternativa rápida (sem GEE)**: usar `acessibilidade/layers/verde_total.png` como base, aplicar as máscaras de parques + verde pago + estradas localmente.

**Overpass API:**
- Pode dar timeout com muitos elementos — o script divide em lotes e tenta servidores alternativos
- Se falhar persistentemente, usar `adicionar_jardins.py` (OSM API v0.6, mais estável) para adicionar parques individualmente ao GeoJSON existente

