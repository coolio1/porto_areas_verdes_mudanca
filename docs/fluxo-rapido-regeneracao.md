# Fluxo rápido: regenerar HTML

**Novo fluxo para desenvolvimento rápido — editar parques/candidatos e ver mudanças em ~2s:**

```bash
# Editar parques e jardins
nano acessibilidade/parques_porto.geojson

# Regenerar acessibilidade_verde.html (reutiliza PNGs em cache)
cd acessibilidade
python regenerar_html.py
# F5 no browser para recarregar

# Editar candidatos a conversão
nano acessibilidade/candidatos_conversao.geojson

# Regenerar conversao_verde.html (reutiliza PNGs + metadados)
python regenerar_conversao_html.py
# F5 no browser para recarregar
```

**Scripts novos:**
- `acessibilidade/regenerar_html.py` — regenera acessibilidade_verde.html (~2s)
- `acessibilidade/regenerar_conversao_html.py` — regenera conversao_verde.html (~2s)

**Fluxo completo (quando pronto com cálculos):**
```bash
python acessibilidade/acessibilidade_verde.py        # ~1-2 min (GEE + 2SFCA + HTML)
python acessibilidade/analise_conversao_verde.py     # ~1-2 min (proximidade + HTML)
```

**Arquitectura:** GeoJSONs são lidos do disco e embutidos inline nos templates HTML (nunca `fetch()` — bloqueia em `file://`). Scripts rápidos regeneram HTML sem recalcular PNGs. Se faltarem PNGs em cache, o utilizador avisa-se e deve correr acessibilidade_verde.py ou analise_conversao_verde.py.
