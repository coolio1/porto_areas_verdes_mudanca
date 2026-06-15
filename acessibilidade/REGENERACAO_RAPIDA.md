# Guia: Regeneração Rápida de HTMLs

## Problema Resolvido

Antes desta solução:
- Editar parques → aguardar 1-2 minutos → ver mudanças (requer recálculos GEE)

Agora:
- Editar parques → executar script ~2s → ver mudanças imediatamente

## Fluxo Rápido: Editar Parques

```bash
# 1. Abrir e editar parques
nano parques_porto.geojson

# 2. Regenerar acessibilidade_verde.html rapidamente
python regenerar_html.py

# 3. Recarregar browser (F5)
```

## Fluxo Rápido: Editar Candidatos

```bash
# 1. Abrir e editar candidatos
nano candidatos_conversao.geojson

# 2. Regenerar conversao_verde.html rapidamente
python regenerar_conversao_html.py

# 3. Recarregar browser (F5)
```

## Scripts Disponíveis

### `regenerar_html.py`
- Regenera `acessibilidade_verde.html` (~2 segundos)
- Reutiliza PNGs em cache (não recalcula)
- Verifica quais PNGs existem e avisa se faltarem
- Chama `acessibilidade_html.build_html()`

### `regenerar_conversao_html.py`
- Regenera `conversao_verde.html` (~2 segundos)
- Reutiliza PNGs em cache + metadados de cobertura
- Verifica quais PNGs existem e avisa se faltarem
- Chama `conversao_html.build_html()`

## O que Acontece

**Scripts rápidos:**
1. Carregam GeoJSONs do disco
2. Carregam PNGs existentes em cache
3. Chamam função `build_html()` para gerar novo HTML
4. HTML é escrito com dados actualizados

**PNGs não são recalculados:**
- Dados de acessibilidade (2SFCA) mantêm-se stale até correr `acessibilidade_verde.py`
- Dados de proximidade simulada mantêm-se stale até correr `analise_conversao_verde.py`

## Fluxo Completo (com Cálculos Pesados)

Quando pronto para recalcular **tudo** (GEE, 2SFCA, proximidade):

```bash
# Recalcular acessibilidade (GEE + 2SFCA + HTML)
python acessibilidade_verde.py              # ~1-2 minutos

# Recalcular conversão (proximidade simulada + HTML)
python analise_conversao_verde.py           # ~1-2 minutos
```

Estes scripts executam tudo:
- Descarregam dados do GEE (Sentinel-2)
- Recalculam PNGs
- Chamam `build_html()` para regenerar HTML

## Casos Especiais

### Se um PNG está missing

Quando correr um script rápido, verá:
```
✓ Verde público
✗ Verde pago
✓ Acessibilidade 2SFCA
...
```

Se algum PNG está marcado com `✗`, significa:
- PNGs foram apagados ou ainda não foram criados
- Deve correr `acessibilidade_verde.py` (ou `analise_conversao_verde.py`)

### Se HTML não mostra polígonos

1. Verificar que `parques_porto.geojson` existe e é válido JSON
2. Correr `python regenerar_html.py` de novo
3. Limpar cache do browser (Ctrl+Shift+Delete) ou abrir em Incognito

### Se candidatos não aparecem

1. Verificar que `candidatos_conversao.geojson` é válido
2. Correr `python regenerar_conversao_html.py` de novo
3. Verificar que o tipo do polígono está em `['Estrategia de expansao (CMP)', 'Verde em PDM / fechado ao publico', 'Verde privado']`

## Arquitectura

```
GeoJSON (disco) ─┐
                 ├─> build_html() ─> HTML com dados inline
PNGs (cache)   ─┘
```

**Por que inline?**
- `fetch()` é bloqueado pelo navegador em `file://` protocol
- GeoJSONs são pequenos (<10 KB)
- Dados são lidos do disco a cada regeneração
- Simplifica a arquitectura (sem servidor HTTP)

## Dúvidas?

Consultar `CLAUDE.md` na raiz do projecto (secção "Fluxo rápido").
