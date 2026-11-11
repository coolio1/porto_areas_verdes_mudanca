# Mapa de velocidades dos autocarros — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar `Mobilidade/autocarros.html`, um mapa Leaflet/Positron com troços de rua coloridos pela velocidade média dos autocarros STCP e marcadores nos pontos críticos, a partir dos CSV da recolha.

**Architecture:** Pacote Python `Mobilidade/velocidade/` com um módulo por responsabilidade (dados → esperas → colagem às linhas → agregação → página) e um CLI `Mobilidade/gerar_autocarros.py`. As leituras são coladas a troços de ~200 m das vias das rotas OSM da STCP (restritas à `linha` de cada leitura e à direcção do movimento), agregadas por troço, período e tipo de dia, e embutidas no HTML (sem `fetch()`).

**Tech Stack:** Python 3.11 via `uv run` (pandas, numpy, scipy, shapely, truststore), pytest, Leaflet 1.9.4 (cdnjs), CARTO Positron via `carto.aplicar_chave`, Overpass API (OSM).

**Spec:** `docs/superpowers/specs/2026-11-11-mapa-velocidades-autocarros-design.md`

## Global Constraints

- Só autocarros **STCP**; o título e o aviso nunca dizem «AMP» (spec, Não-objectivos).
- `velocidade` do CSV está em **m/s**; ×3,6 para km/h (spec, Dados).
- Descartar leituras com atraso `recebido − observado` < 0 ou > 300 s e com velocidade > 90 km/h (spec, Dados).
- Períodos em hora local (Europe/Lisbon): dia todo 6h–21h59, ponta da manhã 7h–9h59, ponta da tarde 17h–19h59.
- Espera = leitura ≤ 2 km/h a < 40 m de uma paragem, salvo se ≥ 2 leituras de outros veículos fora de paragens, a < 300 m e ± 3 min, tiverem mediana < 8 km/h (então é trânsito e mantém-se). Inconclusivo (< 2 vizinhos) = espera. Zeros fora de paragens **nunca** se descartam.
- Tempo perdido (min de autocarro/hora) = passagens/h × max(0, L/(max(v,2)/3,6) − L/(25/3,6)) / 60, com L = comprimento do troço em metros.
- Destaque só abaixo de **14 km/h** (fixo). Amostra mínima por troço+direcção, período e tipo de dia: **≥ 20 leituras, ≥ 3 veículos, ≥ 2 dias**.
- Marcadores: ≤ ~15 por período e tipo de dia, troços críticos contíguos fundidos; nome = rua + cruzamento mais próximo (OSM).
- Página: Leaflet com dados inline, tiles Positron com `aplicar_chave(html)` antes de gravar, menu via `nav.get_nav`, alvo ≤ 3 MB, PT-PT pré-acordo («acção», «actualização»).
- Repo público: nenhum CSV bruto, IP da VPS, chave SSH ou chave CARTO fixa no código. CSV bruto em `C:\Users\quent\Dados\autocarros\` (fora do OneDrive); cache OSM em `C:\Users\quent\Dados\autocarros\osm\`.
- Fim-de-semana desactivado até haver sábado e domingo completos (primeiro: 2026-11-16).
- Nunca editar o HTML à mão; correr `python -m py_compile` em cada `.py`; sem caches de dependências no OneDrive.

## Review Focus

Entradas que o spec não menciona e que mais provavelmente morderão, por ordem:

1. **Leituras sem rota** (linhas 107 e 605, ~1,3 %) ou longe de qualquer troço (> 30 m): ignoradas sem erro; o aviso do mapa diz a percentagem de leituras coladas.
2. **Dia a meio** (o ficheiro do dia corrente): o denominador das passagens/h conta só os dias que têm leituras nesse período; uma quarta-feira só de manhã não pode diminuir as passagens da ponta da tarde.
3. **Veículos parados muito tempo** (garagem, terminal fora do raio de 40 m): ≥ 15 leituras consecutivas do mesmo veículo a < 15 m são espera, mesmo longe de paragens, para não aparecerem como críticos.
4. **Reinício do recolhedor / ficheiros sobrepostos:** leituras repetidas (mesmo `veiculo` e `observado_utc`) contam uma vez.
5. **Direcção ruidosa ou nula a ~0 km/h:** a leitura cola-se ao troço mais próximo (sem teste de direcção) e `dir = 0`; não pode ser descartada nem duplicada nas duas direcções.
6. **Feriados** contam como dias úteis (limitação conhecida, declarada no aviso se existirem no intervalo; fora do âmbito corrigir).

---

## File Structure

| Ficheiro | Responsabilidade |
|---|---|
| `Mobilidade/velocidade/geo.py` | projecção local lon/lat → metros |
| `Mobilidade/velocidade/dados.py` | ler CSV(.gz), limpar, períodos, tipo de dia |
| `Mobilidade/velocidade/esperas.py` | marcar esperas (paragens) e paragens longas |
| `Mobilidade/velocidade/osm.py` | descarregar/ler paragens e rotas OSM (cache) |
| `Mobilidade/velocidade/linhas.py` | dividir vias em troços; colar leituras |
| `Mobilidade/velocidade/trocos.py` | agregar, tempo perdido, críticos, marcadores |
| `Mobilidade/velocidade/pagina.py` + `template.html` | dados JSON → HTML Leaflet |
| `Mobilidade/gerar_autocarros.py` | CLI que encadeia tudo |
| `Mobilidade/descarregar_recolha.py` | `scp` da VPS para `C:\Users\quent\Dados\autocarros\` |
| `Mobilidade/tests/` | `conftest.py` + `test_<módulo>.py` |
| `.gitignore`, `_config.yml`, `nav.py`, `CLAUDE.md` | exclusões, menu e regras (Tarefa 8) |

Comando de testes (da raiz `Porto Verde`):
`uv run --no-project --with-requirements Mobilidade/requirements.txt --with pytest python -m pytest Mobilidade/tests -q`

---

### Task 0: Preparação (git, dependências, dados, esqueleto de testes)

**Files:**
- Modify: `.gitignore:52-53`, `Mobilidade/requirements.txt`
- Create: `Mobilidade/tests/conftest.py`, `Mobilidade/velocidade/__init__.py`, `Mobilidade/descarregar_recolha.py`

**Interfaces:**
- Produces: `descarregar_recolha.main(argv: list[str]) -> int` (argumentos `ip`, `--destino`, `--chave`; sem IP fixo); fixtures de `conftest.py`: `pasta_csv(tmp_path)` que escreve CSV sintéticos com o cabeçalho de `recolher_autocarros.CAMPOS`.

- [ ] **Step 1:** Substituir a regra `Mobilidade/` do `.gitignore` por `Mobilidade/*` seguida das excepções `!Mobilidade/gerar_autocarros.py`, `!Mobilidade/autocarros.html`, `!Mobilidade/requirements.txt`, `!Mobilidade/velocidade/`, `!Mobilidade/tests/`, e acrescentar `Mobilidade/velocidade/__pycache__/`. Manter o comentário a explicar a decisão de 2026-11-09 e a excepção de 2026-11-11.
- [ ] **Step 2: Verificar a regra.** Run: `git check-ignore -v Mobilidade/recolher_autocarros.py Mobilidade/verificar_recolha.py Mobilidade/deploy/LEIAME.md Mobilidade/gerar_autocarros.py Mobilidade/velocidade/dados.py`. Expected: as três primeiras **ignoradas**; as duas últimas **não** (sem saída para elas).
- [ ] **Step 3:** Escrever `Mobilidade/requirements.txt` com `pandas`, `numpy`, `scipy`, `shapely`, `truststore` (versões fixadas ao instalar) e manter a nota de que `recolher_autocarros.py` só usa a biblioteca padrão.
- [ ] **Step 4: Escrever `descarregar_recolha.py`** (`main(argv) -> int`): chama `scp -i <chave> -o BatchMode=yes -r root@<ip>:/var/lib/recolha/. <destino>`, só leitura na VPS; destino por omissão `C:\Users\quent\Dados\autocarros`; cria a pasta; devolve o código do `scp`. O IP vem sempre de argumento (ver memória `reference_vps_recolha_autocarros`, nunca no repo).
- [ ] **Step 5:** Correr uma vez com o IP da memória. Expected: ficheiros `posicoes_2026-11-0*.csv(.gz)` em `C:\Users\quent\Dados\autocarros\`; `ls` mostra o dia 2026-11-11 actualizado.
- [ ] **Step 6:** `conftest.py` põe `Mobilidade/` no `sys.path` e define `pasta_csv`. Run: `... pytest Mobilidade/tests -q`. Expected: `no tests ran` sem erros de importação.
- [ ] **Step 7: Commit** só dos ficheiros acrescentados: `git add .gitignore Mobilidade/requirements.txt Mobilidade/velocidade/__init__.py Mobilidade/descarregar_recolha.py Mobilidade/tests/conftest.py` e `git status` limpo para o resto. Mensagem: `Mobilidade: versionar gerador do mapa de autocarros (excepções no .gitignore)`.

---

### Task 1: Dados — leitura, limpeza, períodos

**Files:** Create `Mobilidade/velocidade/geo.py`, `Mobilidade/velocidade/dados.py`; Test `Mobilidade/tests/test_dados.py`

**Interfaces:**
- Produces: `geo.xy(lon: np.ndarray, lat: np.ndarray) -> np.ndarray` (n×2, metros, `KX = 111320·cos(41,15°)`, `KY = 111320`); `dados.PERIODOS: dict[str, tuple[int, int]] = {"dia": (6, 21), "am": (7, 9), "pm": (17, 19)}`; `dados.carregar(pasta: Path) -> pd.DataFrame` com colunas `obs` (UTC), `veiculo`, `lon`, `lat`, `kmh`, `direccao`, `linha`, `viagem`, `dia` (data local), `hora` (int local), `tipo_dia` (`"util"`/`"fds"`); `dados.dias_com_dados(df, periodo: str, tipo_dia: str) -> int`.

- [ ] **Step 1: Testes** (`pasta_csv` com linhas sintéticas) — `test_limpa_atraso_e_velocidade_absurda` (linhas com atraso −5 s, 400 s e 120 km/h desaparecem; atraso 30 s a 10 m/s fica com `kmh == 36.0`); `test_ignora_duplicados_entre_ficheiros` (mesmo `veiculo`+`observado_utc` em dois CSV → 1 linha); `test_hora_local_e_tipo_dia` (UTC `2026-11-14T08:00Z` → `hora == 8`, `tipo_dia == "fds"`; `2026-11-09T17:30Z` → `"util"`); `test_dias_com_dados_conta_so_dias_com_leituras_no_periodo` (dia só com leituras às 8h → 0 para `"pm"`, 1 para `"am"`).
- [ ] **Step 2:** Correr; Expected: FAIL (módulo inexistente).
- [ ] **Step 3: Implementar** `geo.py` e `dados.py` com as assinaturas acima (lê `.csv` e `.csv.gz`, `pd.read_csv` com `linha`, `viagem` como `str`).
- [ ] **Step 4:** Correr; Expected: PASS.
- [ ] **Step 5: Commit** `Mobilidade: leitura e limpeza dos dados dos autocarros`.

---

### Task 2: Esperas e veículos parados

**Files:** Create `Mobilidade/velocidade/esperas.py`; Test `Mobilidade/tests/test_esperas.py`

**Interfaces:**
- Consumes: `geo.xy`, DataFrame de `dados.carregar` (+ `obs`, `kmh`, `veiculo`).
- Produces: `esperas.marcar_esperas(df: pd.DataFrame, paragens: pd.DataFrame, raio_m: float = 40.0) -> pd.Series` (bool, alinhado com `df.index`; `paragens` com colunas `lat`, `lon`); `esperas.marcar_paradas_longas(df: pd.DataFrame, min_leituras: int = 15, raio_m: float = 15.0) -> pd.Series`.

- [ ] **Step 1: Testes** — `test_zero_no_meio_da_rua_nunca_e_espera` (zero a 200 m de qualquer paragem → `False`); `test_zero_em_paragem_sem_vizinhos_e_espera` (inconclusivo → `True`); `test_zero_em_paragem_com_fila_a_volta_e_transito` (≥ 2 outros veículos a < 300 m, ± 3 min, fora de paragens, a 3 e 5 km/h → `False`); `test_zero_em_paragem_com_transito_fluido_e_espera` (vizinhos a 25 km/h → `True`); `test_leitura_em_movimento_junto_a_paragem_nunca_e_espera` (30 km/h a 10 m da paragem → `False`); `test_paradas_longas` (15 leituras consecutivas do mesmo veículo a < 15 m → `True` nas 15; 14 → `False`).
- [ ] **Step 2:** Correr; Expected: FAIL.
- [ ] **Step 3: Implementar** com `cKDTree` 3D (x, y, `t·1,67`) para os vizinhos (300 m ≈ 180 s) e um segundo para as paragens; os vizinhos têm de ser de **outro** veículo e estar fora do raio das paragens.
- [ ] **Step 4:** Correr; Expected: PASS.
- [ ] **Step 5: Commit** `Mobilidade: regra das esperas e paradas longas`.

---

### Task 3: OSM — paragens e rotas

**Files:** Create `Mobilidade/velocidade/osm.py`; Test `Mobilidade/tests/test_osm.py`

**Interfaces:**
- Produces: dataclasses `Via(way_id: int, nome: str, coords: np.ndarray, nodes: list[int])` (coords n×2 lon/lat) e `Rota(rel_id: int, ref: str, vias: list[Via])`; `osm.descarregar(destino: Path) -> None` (grava `paragens.json` e `rotas.json`, tenta `overpass-api.de` e depois `overpass.kumi.systems`, `truststore.inject_into_ssl()`, falhas nunca gravam ficheiros vazios); `osm.carregar_paragens(pasta: Path) -> pd.DataFrame` (`lat`, `lon`, `nome`); `osm.carregar_rotas(pasta: Path) -> list[Rota]` (só relações com `operator` contendo STCP).

- [ ] **Step 1: Testes** com respostas Overpass sintéticas em JSON — `test_carregar_rotas_filtra_stcp_e_junta_vias` (1 relação STCP, 1 UNIR → 1 `Rota` com `ref` certa e as vias pela ordem dos membros); `test_carregar_paragens_ignora_nao_paragens` (`waste_basket` fora); `test_descarregar_nao_grava_em_falha` (servidores a falhar → nenhum ficheiro, levanta `RuntimeError`).
- [ ] **Step 2:** Correr; Expected: FAIL.
- [ ] **Step 3: Implementar.** Consultas Overpass: paragens (`node["highway"="bus_stop"]`, `amenity=bus_station`) na caixa `41.05,-8.80,41.30,-8.40`; rotas `rel["type"="route"]["route"="bus"]["operator"~"STCP"]` seguida de `way(r)` com `out tags geom` (precisam de `nodes` e geometria). Verificar a sintaxe numa chamada real antes de escalar.
- [ ] **Step 4:** Correr; Expected: PASS.
- [ ] **Step 5:** Correr `osm.descarregar` uma vez sobre `C:\Users\quent\Dados\autocarros\osm`. Expected: ≥ 6 000 paragens e ≥ 130 rotas STCP (esperado: 140 relações, 72 `ref`; 6 972 paragens em 2026-11-11). Se menos, parar e reportar.
- [ ] **Step 6: Commit** `Mobilidade: obtenção das paragens e rotas STCP do OSM`.

---

### Task 4: Troços e colagem às linhas

**Files:** Create `Mobilidade/velocidade/linhas.py`; Test `Mobilidade/tests/test_linhas.py`

**Interfaces:**
- Consumes: `osm.Rota`/`Via`, `geo.xy`, DataFrame de `dados.carregar` com `direccao`.
- Produces: `linhas.dividir(rotas: list[Rota], alvo_m: float = 200.0) -> pd.DataFrame` (índice `troco_id: str = "<way_id>:<n>"`; colunas `way_id`, `nome`, `comprimento_m`, `geom` (shapely LineString em metros), `latlon` (lista de `[lat, lon]`), `refs: frozenset[str]`, `nos: frozenset[int]`); `linhas.colar(df: pd.DataFrame, trocos: pd.DataFrame, max_dist_m: float = 30.0) -> pd.DataFrame` (devolve `df` com as colunas `troco_id` (NaN se não colou) e `dir` ∈ {+1, −1, 0}).

- [ ] **Step 1: Testes** (via recta E-O sintética de 650 m, relações das linhas «A» e «B») — `test_divide_em_trocos_de_cerca_de_200m` (650 m → 3 troços de ~217 m, nenhum fora de 150–300 m); `test_cola_so_a_vias_da_propria_linha` (leitura da linha «A» a 5 m de uma via que só a «B» usa → `troco_id` NaN); `test_direccao_distingue_sentidos` (heading 90° → `dir = +1`, 270° → `dir = −1`); `test_parado_sem_direccao_cola_com_dir_zero` (`kmh = 0` e `direccao` NaN → cola ao mais próximo, `dir = 0`); `test_longe_de_tudo_nao_cola` (50 m → NaN); `test_linha_sem_rota_nao_rebenta` (linha «107» → NaN, sem excepção).
- [ ] **Step 2:** Correr; Expected: FAIL.
- [ ] **Step 3: Implementar.** Projecção de cada leitura no traçado dos troços das vias da sua `linha` (índice espacial `shapely.STRtree`), distância máxima 30 m; `dir` pelo sinal de cos(heading − tangente do troço) quando `kmh > 2`; a leitura parada (≤ 2 km/h) tem `dir = 0` e conta para as duas direcções do troço na agregação (Tarefa 5).
- [ ] **Step 4:** Correr; Expected: PASS.
- [ ] **Step 5: Commit** `Mobilidade: troços das linhas e colagem das leituras`.

---

### Task 5: Agregação, tempo perdido, críticos e marcadores

**Files:** Create `Mobilidade/velocidade/trocos.py`; Test `Mobilidade/tests/test_trocos.py`

**Interfaces:**
- Consumes: `df` com `troco_id`, `dir`, `espera`, `kmh`, `veiculo`, `viagem`, `dia`, `hora`, `tipo_dia`; `trocos` de `linhas.dividir`; `dados.PERIODOS`, `dados.dias_com_dados`.
- Produces: `trocos.agregar(df, trocos, periodo: str, tipo_dia: str) -> pd.DataFrame` (colunas `troco_id`, `dir`, `n`, `veic`, `dias`, `v`, `ph`, `perdido`; só linhas que cumprem o mínimo 20/3/2); `trocos.criticos(agg: pd.DataFrame, limiar: float = 14.0) -> pd.DataFrame`; `trocos.marcadores(crit: pd.DataFrame, trocos: pd.DataFrame, maximo: int = 15) -> list[dict]` (cada um com `lat`, `lon`, `rua`, `cruzamento`, `perdido`, `v`, `troco_ids`).

- [ ] **Step 1: Testes** — `test_velocidade_ignora_esperas_mas_mantem_zeros_de_transito` (leituras 0, 0, 30 km/h com a primeira marcada `espera` → `v == 15.0`); `test_passagens_contam_todas_as_leituras_e_so_dias_com_periodo` (2 dias, 1 sem leituras no período → denominador 1 dia); `test_minimo_de_amostra` (19 leituras, ou 2 veículos, ou 1 dia → o troço não sai); `test_tempo_perdido_valor_exacto` (L = 200 m, v = 10 km/h, 30 passagens/h → `perdido == 30 * (72.0 - 28.8) / 60 = 21.6`); `test_leitura_parada_dir_zero_conta_nas_duas_direccoes`; `test_criticos_limiar` (13,9 entra, 14,0 não); `test_marcadores_fundem_troços_contiguos_e_nomeiam` (3 críticos seguidos na «Rua X» com a via «Rua Y» a partilhar um nó → 1 marcador, `rua == "Rua X"`, `cruzamento == "Rua Y"`); `test_marcadores_maximo` (30 pontos separados → 15, os de maior `perdido`).
- [ ] **Step 2:** Correr; Expected: FAIL.
- [ ] **Step 3: Implementar.** Passagem = `(veiculo, viagem, dia)` distinta; `ph = passagens / (dias_com_dados(df, periodo, tipo_dia) × horas_do_periodo)`; fusão de críticos por vizinhança (troços da mesma via com índices seguidos, ou a < 100 m); cruzamento = nome da outra via mais próxima que partilha um nó (`nos`) com o marcador; sem cruzamento → `""`.
- [ ] **Step 4:** Correr; Expected: PASS.
- [ ] **Step 5: Commit** `Mobilidade: agregação por troço, tempo perdido e marcadores`.

---

### Task 6: Validação com dados reais (portão antes da página)

**Files:** Create `Mobilidade/gerar_autocarros.py` (só a parte de cálculo: `calcular(pasta_dados: Path, pasta_osm: Path) -> dict`); sem testes novos.

**Interfaces:**
- Consumes: Tarefas 1–5.
- Produces: `gerar_autocarros.calcular(pasta_dados: Path, pasta_osm: Path) -> dict` com `{"trocos": DataFrame, "agg": {(tipo_dia, periodo): DataFrame}, "marcadores": {(tipo_dia, periodo): list[dict]}, "dias": {tipo_dia: int}, "coladas_pct": float, "intervalo": (data_ini, data_fim)}`.

- [ ] **Step 1:** Implementar `calcular` encadeando carregar → esperas (+ paradas longas) → colar → `agregar` para cada (tipo_dia, período) com ≥ 1 dia.
- [ ] **Step 2: Correr sobre os dados reais** e imprimir: % de leituras coladas (esperado ~98 %), nº de troços que cumprem o mínimo por variante, top 5 marcadores da ponta da tarde (dias úteis) com rua, cruzamento e v.
- [ ] **Step 3: Conferir.** Os pontos mais pesados da maquete (centro do Porto: 41,166/−8,624; 41,157/−8,630; 41,148/−8,612) têm de aparecer entre os marcadores, com nomes de rua coerentes; nenhum terminal conhecido (Campanhã) como crítico. Se não, **parar** e reportar ao utilizador antes de avançar (REPLAN).
- [ ] **Step 4: Sensibilidade das esperas.** Repetir com `raio_m` = 25, 40 e 60 e comparar o top 10: reportar quantos mudam. Fixar o raio só se o top 10 for estável (≥ 8 em 10 iguais); caso contrário, reportar e decidir com o utilizador.
- [ ] **Step 5:** Comparar a velocidade média por troço com a calculada pelo deslocamento entre leituras consecutivas (dt 40–90 s) nos 20 troços mais pesados: reportar a diferença mediana (valida a nota do spec sobre a média).
- [ ] **Step 6: Commit** `Mobilidade: cálculo completo e validação`.

---

### Task 7: Página HTML

**Files:** Create `Mobilidade/velocidade/pagina.py`, `Mobilidade/velocidade/template.html`; extend `Mobilidade/gerar_autocarros.py` com `main(argv) -> int`; Test `Mobilidade/tests/test_pagina.py`

**Interfaces:**
- Consumes: `gerar_autocarros.calcular`, `carto.aplicar_chave`, `nav.get_nav("Mobilidade/autocarros.html", depth=1)`.
- Produces: `pagina.dados_json(resultado: dict) -> dict` (geometria dos troços **uma vez**, depois, por variante, `[idx_troco, dir, v, ph, perdido, n]`; marcadores; `dias`, `intervalo`, `coladas_pct`); `pagina.renderizar(resultado: dict, template: Path) -> str`; `main(argv)` com `--dados` (omissão `C:\Users\quent\Dados\autocarros`), `--saida` (omissão `Mobilidade/autocarros.html`).

- [ ] **Step 1: Testes** — `test_html_sem_fetch_e_com_chave_carto` (sem `fetch(`; todos os URLs `basemaps.cartocdn.com` com `?key=`); `test_html_nao_diz_AMP_e_diz_STCP` (título e aviso); `test_so_dados_publicaveis` (sem `recebido_utc`, sem `veiculo`, sem `@`, sem IP no formato `\d+\.\d+\.\d+\.\d+`); `test_tamanho_maximo_3MB` (resultado sintético grande ≤ 3 MB); `test_fim_de_semana_desactivado_sem_dados` (`dias["fds"] == 0` → botão com `disabled` e «16 de Novembro»); `test_variante_sem_amostra_diz_sem_dados`.
- [ ] **Step 2:** Correr; Expected: FAIL.
- [ ] **Step 3: Implementar** `template.html` a partir da maquete aprovada (cabeçalho, botões de dia e período, legenda 3→14 km/h do vermelho escuro ao creme, círculo/linha por troço com tamanho ∝ `perdido`, popups com velocidade, autocarros/hora e minutos perdidos, aviso «Só autocarros STCP… esperas descontadas», «N dias de dados» por tipo de dia, marcadores com rua e cruzamento) e o resto das assinaturas. Linhas desenhadas a partir de `latlon`; a direcção mais lenta por cima.
- [ ] **Step 4:** Correr; Expected: PASS.
- [ ] **Step 5:** `python Mobilidade/gerar_autocarros.py` (via `uv run`); `python -m py_compile` em todos os `.py` novos. Expected: `Mobilidade/autocarros.html` criado, tamanho impresso ≤ 3 MB.
- [ ] **Step 6: Commit** `Mobilidade: página do mapa de velocidades dos autocarros`.

---

### Task 8: Verificação, menu, regras e fecho

**Files:** Modify `nav.py`, `_config.yml`, `CLAUDE.md`, `docs/estrutura.md`; Create nada de novo.

- [ ] **Step 1:** `nav.py`: acrescentar a `PAGES` a entrada `("Mobilidade/autocarros.html", "Mobilidade")` depois de Atropelamentos. Não editar `patch_nav.py` (bloqueado pelo hook): dizer ao utilizador que a linha de `TARGETS` para a página nova é opcional, porque o gerador já grava o menu.
- [ ] **Step 2:** `_config.yml` `exclude`: acrescentar `Mobilidade/velocidade`, `Mobilidade/tests`.
- [ ] **Step 3: Verificar no browser em `file://` com Playwright** (a extensão Chrome não abre `file://`): sem erros na consola; sem a marca de água «API KEY REQUIRED»; botões de período trocam as camadas; «Fim-de-semana» desactivado com o texto; popup de um marcador mostra rua e cruzamento; captura de ecrã dos 3 períodos e olhar para elas. Expected: todos OK.
- [ ] **Step 4:** Documentar em `CLAUDE.md` do projecto (secção curta «Mobilidade — velocidade dos autocarros»: o que gera, dados fora do OneDrive, regra das esperas, páginas, o que fica ignorado) e em `docs/estrutura.md`.
- [ ] **Step 5:** `git status` em `Porto Verde`: nada de `Mobilidade/recolher_autocarros.py`, `verificar_recolha.py`, `deploy/` ou CSV a entrar. Commit `Mobilidade: menu, regras e documentação`. **Não** fazer push (repo público: o utilizador publica).
- [ ] **Step 6:** Abrir `Mobilidade/autocarros.html` no browser do utilizador (`cmd /c start`) e apresentar o fecho (feito/verificado; o que sobra).

---

## Self-review

- **Cobertura do spec:** objectivos 1–7 → Tarefas 4–7 (ruas+marcadores), 5 (crítico), 1+7 (períodos, dias), 6–7 (actualização: o gerador volta a correr sobre `Dados\autocarros` com a descarga da Tarefa 0), 7 (estilo B, Positron, avisos), 8 (menu-mãe). Anti-objectivos → Tarefas 2 (terminais, zeros de trânsito), 4–6 (rua errada, validação), 5 (amostra), 7 (privacidade). Decisões minhas do revisor → Tarefas 2, 5, 7.
- **Consistência de tipos:** `troco_id`, `dir`, `espera`, `tipo_dia`, `PERIODOS` e `calcular(...)` usam os mesmos nomes de ponta a ponta.
- **Proporção:** ~1,5× o spec; código só em testes e assinaturas.
- **Fora do plano por decisão do spec:** outros operadores, mover os atropelamentos, GTFS, previsões.
- **Riscos que o plano não elimina:** colagem na rua errada em cruzamentos complexos (mitigada na Tarefa 6, não garantida); amostra pequena de fim-de-semana (a página diz «sem dados» até haver).
