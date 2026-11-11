# Histórico: linha do tempo, cortina e números — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o painel de ~30 caixas do separador Histórico por uma linha do tempo (2023-24 → 1947), uma cortina de comparação e um minigráfico de percentagens, sem NDVI.

**Architecture:** O gerador Python (`mapa_unico.py`) deixa de embutir NDVI e passa a embutir `numeros` (percentagens por época, calculadas das máscaras). `tema_historico.js` é reescrito: estado = época escolhida (um par vegetação/edificado), modo cortina (duas épocas, recorte por `pane`), interruptor perda/ganho, grupo «Contexto» recolhido.

**Tech Stack:** Python 3.13 (PIL, numpy, geopandas, pytest), Leaflet 1.x (imageOverlay, panes), JS sem build, Playwright (Edge, `file://`).

**Spec:** `docs/superpowers/specs/2026-11-11-historico-linha-do-tempo-design.md` (secção «Decisões minhas» incluída; o utilizador aprovou: sem selectores de cor, perda/ganho substitui o mapa da época, barra com nota de cobertura).

## Global Constraints

- PT-PT pré-acordo («acção», «actual»), épocas e listas do mais recente para o mais antigo: 2023-24, 2016-17, 2001-05, 1995-00, 1985-90, 1979, 1972-76, 1947.
- Dados inline em `mapa_unico/dados/*.js`; nunca `fetch()` (abre-se em `file://`).
- HTML e dados só por `python mapa_unico/mapa_unico.py` (`--html` só refaz o HTML); nunca editar `mapa_unico.html` nem `dados/*.js` à mão.
- Cores já gravadas nas máscaras: vegetação `#00FF00`, edificado `#C4A882`; 1947 tingida por filtro SVG (cores 1947: `#228B22`, `#888888`), sem canvas.
- `dados/historico.js` hoje 7 114 438 bytes: depois da alteração tem de ser **menor**.
- Não mexer em `ndvi_historico/`, `layers_historico/ndvi_*.png`, nem nos outros temas.
- `nav.py` é a fonte do menu; `patch_nav.py` não se corre. `?tema=historico` / `#tema=historico` e `vista=1947` continuam a funcionar.
- Escrita directa em `mapa_unico/` pode falhar no OneDrive: se falhar, gerar para a scratchpad e `cp`.
- Commits sem push (o push é do utilizador; repo público). Sem `sed -i` (o hook bloqueia): usar Edit.

## Review Focus

- Época sem cobertura total do concelho (1947 tem grelha própria `BOUNDS_1947`): a barra mostra-se com nota de cobertura; abaixo de 95 % o construtor pára e pergunta (Task 1, teste de cobertura).
- Percentagens têm de conferir com contagem independente de pixels no mesmo concelho (Task 1).
- Cortina com épocas de grelhas diferentes (1947 vs Landsat) e com 1979 (que também tem de comparar com 2 classes).
- Escolher época desliga perda/ganho; perda/ganho não existe em modo cortina.
- `vista=1947` selecciona a época 1947 e liga a ortofoto; `#tema=historico` abre em 2023-24.
- Telemóvel (375 px): linha do tempo com scroll horizontal ou quebra, cortina arrastável com o dedo.

## File Structure

- Create `mapa_unico/historico_numeros.py` — calcula `{época: {veg, edif, cobertura}}` a partir dos PNG (responsabilidade única).
- Create `mapa_unico/tests/test_historico_numeros.py` — testes pytest do cálculo.
- Create `mapa_unico/tests/test_dados_historico.py` — sem NDVI nos dados, `numeros` presente.
- Modify `mapa_unico/mapa_unico.py:116-143` — `dados_historico()`.
- Rewrite `mapa_unico/src/tema_historico.js`.
- Modify `mapa_unico/src/estilo.css` — classes `.h-*` do novo painel, só se faltarem estilos.
- Create `mapa_unico/tests/pw_historico.py` — verificação Playwright em `file://` (Edge).
- Modify `docs/estrutura.md` (secção do mapa único) e `CLAUDE.md` (linha do mapa único), só para o que ficou diferente.

---

### Task 1: Percentagens por época

**Files:**
- Create: `mapa_unico/historico_numeros.py`
- Test: `mapa_unico/tests/test_historico_numeros.py`

**Interfaces:**
- Produces: `percentagens(raiz: Path) -> dict[str, dict]` com chaves exactamente `"2023-24","2016-17","2001-05","1995-00","1985-90","1979","1972-76","1947"`; cada valor `{"veg": float, "edif": float, "cobertura": float}` (percentagens 0-100, 1 casa decimal; `cobertura` = % do concelho abrangida pela grelha da época).
- Produces: `contar(mascara_alfa: np.ndarray, concelho: np.ndarray) -> float` — % de píxeis com alfa > 0 dentro de `concelho` (bool).

- [ ] **Step 1: Write the failing tests** em `test_historico_numeros.py`:
  - `test_contar_conta_so_dentro_do_concelho`: `concelho` 4×4 com 8 `True`, máscara com 2 píxeis ligados dentro e 3 fora → `contar(...) == 25.0`.
  - `test_percentagens_tem_as_oito_epocas_do_mais_recente_ao_mais_antigo`: `list(percentagens(RAIZ))` == a lista da Global Constraints.
  - `test_percentagens_conferem_com_contagem_independente`: para `2023-24` recalcular no teste com PIL+numpy (`veg_2023-24.png` e `porto_mask.png`, grelha 2048×769) e comparar com tolerância 0,1.
  - `test_valores_plausiveis`: `0 <= veg+edif <= 100` e `0 < cobertura <= 100` em todas; `veg` de 2023-24 > 0.
  - `test_1947_cobertura_declarada`: `percentagens(RAIZ)["1947"]["cobertura"]` existe (é a % do concelho dentro de `BOUNDS_1947`, via reamostragem do `porto_mask` para a grelha 18432×9216).
- [ ] **Step 2: Run** `python -B -m pytest -q -p no:cacheprovider mapa_unico/tests/test_historico_numeros.py` — Expected: FAIL (`ModuleNotFoundError: historico_numeros`).
- [ ] **Step 3: Implement** `contar` e `percentagens` em `historico_numeros.py`: ler `layers_historico/veg_<época>.png`/`edif_<época>.png` e `porto_mask.png` com `Image.MAX_IMAGE_PIXELS = None`; 1979 via `cobertura_1979.mascara_png(g, ["TRS","HER"], ...)` e `["ABE"]` (mesma grelha 2048×769); 1947 via `1947/layers/uso_1947_*.png`, reamostrando `porto_mask` por vizinho mais próximo para a grelha 1947 usando os limites de `BOUNDS_1947` e `GRELHA_BOUNDS` (`cobertura_1979.GRELHA_BOUNDS`). Primeiro **verificar** que o alfa de `porto_mask.png` é de facto o concelho (contar píxeis e comparar com a área do Porto, ≈ 41,4 km²); se não for, ajustar e anotar no CLAUDE.md. Se alguma `cobertura` < 95, o teste `test_cobertura_minima_95` (acrescentar) falha: **parar e perguntar ao utilizador** em vez de baixar o limiar.
- [ ] **Step 4: Run** o mesmo comando — Expected: PASS (todos).
- [ ] **Step 5: Commit** `git add mapa_unico/historico_numeros.py mapa_unico/tests/test_historico_numeros.py && git commit -m "Histórico: cálculo das percentagens por época"`.

---

### Task 2: Dados do Histórico sem NDVI e com `numeros`

**Files:**
- Modify: `mapa_unico/mapa_unico.py:116-143` (`dados_historico`)
- Test: `mapa_unico/tests/test_dados_historico.py`

**Interfaces:**
- Consumes: `percentagens(raiz)` da Task 1.
- Produces: `dados_historico()` devolve as chaves actuais **sem** `ndvi_*` e com `numeros` (o dict da Task 1). `ndvi_*` não existe em nenhuma chave.

- [ ] **Step 1: Write the failing tests**: `test_sem_ndvi` (nenhuma chave começa por `ndvi_`), `test_numeros_presente` (`d["numeros"]` tem as 8 épocas), `test_chaves_mantidas` (continuam `uso_1947_vegetacao`, `uso_1947_edificado`, `veg_<época>`, `edif_<época>` das 6 épocas Landsat, `veg_1979`, `edif_1979`, `veg_perda`, `veg_ganho`, `cobertura_1979`, `cobertura_1979_ha`). Chamar `dados_historico()` pode demorar ~2 min por causa das máscaras 1947: marcar com `@pytest.fixture(scope="module")` e fazer uma só chamada.
- [ ] **Step 2: Run** `python -B -m pytest -q -p no:cacheprovider mapa_unico/tests/test_dados_historico.py` — Expected: FAIL (`ndvi_` presente, `numeros` ausente).
- [ ] **Step 3: Implement**: em `dados_historico()` trocar `("ndvi","veg","edif")` por `("veg","edif")` e acrescentar `d["numeros"] = percentagens(RAIZ)`; actualizar a docstring. O `fonte:` do tema (JS, Task 3) perde a linha NDVI.
- [ ] **Step 4: Run** o teste — Expected: PASS.
- [ ] **Step 5: Regenerar e medir:** `python mapa_unico/mapa_unico.py` e `python -c "import os;print(os.path.getsize('mapa_unico/dados/historico.js'))"` — Expected: < 7 114 438. Commit `mapa_unico/mapa_unico.py`, testes, `dados/historico.js`, `mapa_unico.html`.

---

### Task 3: Linha do tempo, minigráfico, fonte por época (sem cortina)

**Files:**
- Rewrite: `mapa_unico/src/tema_historico.js`
- Modify (se necessário): `mapa_unico/src/estilo.css`
- Test: `mapa_unico/tests/pw_historico.py`

**Interfaces:**
- Consumes: `MU.registarTema`, `MU.linha`, `MU.map`, `MU.BOUNDS`, `MU.DADOS.historico`, `MU.FUNDOS`, `MU.setFundo`, `MU.param`, `MU.hexToRgb`, `MU.tema`, `MU.fundoManual`; `D.numeros` (Task 2).
- Produces (em `window.MU.historico`, para os testes e para a Task 4): `epocas: string[]` (ordem da Global Constraints), `seleccionar(id: string): void`, `estado(): {epoca: string, perdaGanho: boolean, comparar: boolean}`, `ligar1979Detalhe(on: boolean): void`.
- Texto das fontes por época (só o que o `fonte:` já cita): 1947 «Ortofotomapa 1947 (CIIMAR/FCUP); classificação Pixel RF, limpa com Sentinel-2 e Landsat 1985»; 1972-76 «Landsat MSS, 60 m; NDVI ≥ 0,25»; 1979 «Ocupação do solo 1979, Filipa Guilherme (vectorial)»; restantes «Landsat 5/8, 30 m; NDVI ≥ 0,25 (Roy et al. 2016)». 1947, 1972-76 e 1979 levam ressalva «fonte diferente: não comparável em rigor».

- [ ] **Step 1: Write the failing Playwright script** `pw_historico.py` (Edge, `channel="msedge"`, `file://…/mapa_unico/mapa_unico.html#tema=historico`) com asserções: (a) botões da linha do tempo existem pela ordem pedida (`MU.historico.epocas`); (b) `estado().epoca == "2023-24"` ao abrir; (c) nenhuma linha do painel contém «NDVI»; (d) exactamente um par de overlays de época no mapa (`.leaflet-pane` das máscaras tem 2 imagens); (e) o minigráfico tem 8 barras e clicar na de 1947 faz `estado().epoca == "1947"`; (f) a linha de fonte muda com a época e inclui a ressalva em 1947/1972-76/1979; (g) `?vista=1947` selecciona 1947 e o fundo `orto1947`; (h) `perdaGanho`: ligar mostra `veg_perda`/`veg_ganho` e esconde o par da época; escolher época desliga-o; (i) opacidade global muda o `opacity` dos overlays de época, incluindo 1947; (j) sem erros na consola.
- [ ] **Step 2: Run** `python mapa_unico/tests/pw_historico.py` — Expected: FAIL (painel antigo: ordem e NDVI).
- [ ] **Step 3: Rewrite `tema_historico.js`** mantendo o que existe: fundo `orto1947` (`so: 'historico'`), panes (`h1947Pane`, `hCobPane`, `hMascPane`, `hMudPane`; `hNdviPane` sai), filtro SVG de 1947 com cores fixas, `ctx` (limites on, densidade off), `fonte:` sem a linha NDVI, popup e totais em ha das 5 classes de 1979. Estrutura do painel: título; linha do tempo (botões em fila, activo destacado); linha de fonte/ressalva; minigráfico (barras separadas por época, nunca linha; barras de 1947, 1972-76 e 1979 com símbolo de «fonte diferente»; nota «cobertura X %» quando < 100 %; clicar selecciona); botão «ver as 5 classes» (só com 1979; mostra os GeoJSON por classe em vez do par vegetação/edificado de 1979); interruptor «Perda e ganho (1985-90 → 2023-24)»; botão «Comparar» (inactivo até à Task 4, apenas desenhado); opacidade global (aplica-se a todas as imagens de época); grupo «Contexto» recolhido (`<details>`) com limites, densidade e o fundo orto1947 (já tratado por `MU.FUNDOS`). `seleccionar(id)` remove o par anterior, adiciona o novo (época Landsat/1979: `veg_`+`edif_` em `hMascPane`; 1947: dois overlays em `h1947Pane` com filtro), desliga perda/ganho e actualiza fonte e destaque. `activar()` selecciona 2023-24 (ou 1947 se `MU.param('vista')==='1947'`, e então `MU.setFundo('orto1947')` se `!MU.fundoManual`); `desactivar()` remove tudo. Sem selectores de cor (`editavel` sai). Legenda fixa: verde = vegetação, bege = edificado (1947: verde-escuro e cinzento, na legenda da época).
- [ ] **Step 4: Run** `python mapa_unico/mapa_unico.py --html` e depois `python mapa_unico/tests/pw_historico.py` — Expected: PASS (a)-(j). Tirar captura 1280 px e 375 px e conferir à vista (frontend-design: protótipo visível; tamanhos e disposição que sejam gosto vão ao utilizador numa caixa, uma de cada vez).
- [ ] **Step 5: Commit** `tema_historico.js`, `estilo.css`, `pw_historico.py`, `mapa_unico.html`.

---

### Task 4: Cortina de comparação

**Files:**
- Modify: `mapa_unico/src/tema_historico.js`, `mapa_unico/src/estilo.css`
- Test: `mapa_unico/tests/pw_historico.py` (acrescentar asserções)

**Interfaces:**
- Consumes: `MU.historico.seleccionar`, `estado` da Task 3.
- Produces: `MU.historico.comparar(on: boolean, esq?: string, dir?: string): void` (por omissão `esq="2023-24"`, `dir="1947"`), `MU.historico.cortina(pos: number): void` (0-1, fracção da largura do mapa onde está o separador).

- [ ] **Step 1: Write the failing assertions** em `pw_historico.py`: (a) `comparar(true)` → `estado().comparar === true`, dois selectores de época visíveis com 2023-24 e 1947; (b) com `cortina(0.5)` o recorte da imagem do lado esquerdo termina a meio do mapa e o do direito começa (verificar `clip`/`clip-path` dos panes, ou `getBoundingClientRect` do separador ≈ metade da largura do mapa); (c) comparar 1979 contra 2023-24 e 1947 contra 1972-76 funciona (grelhas diferentes) sem erro de consola; (d) o interruptor perda/ganho fica inactivo em modo cortina e `comparar(false)` repõe a época da esquerda; (e) arrastar o separador com o rato e com `touchscreen` (375 px) muda a posição.
- [ ] **Step 2: Run** `python mapa_unico/tests/pw_historico.py` — Expected: FAIL (`MU.historico.comparar` não definido).
- [ ] **Step 3: Implement** a cortina: dois conjuntos de overlays (esquerdo e direito) em panes próprios (`hEsqPane`, `hDirPane`, z-index entre 408 e 415); recorte do pane esquerdo `clip-path: inset(0 <(1-pos)*100>% 0 0)` e do direito `inset(0 0 0 <pos*100>%)`, recalculado em `move`/`zoom` (o pane está dentro do `mapPane`, que se desloca: compensar com a posição do mapPane, como no plugin leaflet-side-by-side); separador `div` arrastável (pointer events, funciona com toque) sobre o mapa; selectores das duas épocas; 1947 e 1979 respeitam as suas técnicas (filtro SVG / par de máscaras 1979). 1979 em modo cortina mostra as 2 classes. O desenho exacto do separador e do estilo fica ao construtor.
- [ ] **Step 4: Run** `python mapa_unico/mapa_unico.py --html` e `python mapa_unico/tests/pw_historico.py` — Expected: PASS. Capturas 1280 px e 375 px.
- [ ] **Step 5: Commit** os ficheiros alterados e `mapa_unico.html`.

---

### Task 5: Paridade, regressão, documentação e fecho

**Files:**
- Modify: `docs/estrutura.md`, `CLAUDE.md` (só a linha/secção do Histórico se citar NDVI ou as caixas)

- [ ] **Step 1: Regressão:** `python -B -m pytest -q -p no:cacheprovider mapa_unico/tests Mobilidade/tests` — Expected: tudo verde (os 58 testes anteriores incluídos). Abrir os outros três temas em `file://` com Playwright e confirmar que não há erros de consola e que `?tema=hoje|acessibilidade|privado` continuam a abrir.
- [ ] **Step 2: Paridade com o publicado:** comparar `veg_<época>`/`edif_<época>` (2023-24, 1985-90) e `uso_1947_*` embutidos com os do HTML publicado (git `HEAD~` antes da Task 2) por alfa; esperado: idênticos (só o NDVI saiu).
- [ ] **Step 3: Docs:** actualizar a descrição do tema Histórico em `docs/estrutura.md` (linha do tempo, cortina, minigráfico, sem NDVI) e, se citar o NDVI do mapa único, `CLAUDE.md`. `Grep` de «ndvi» em `mapa_unico/` para limpar órfãos das minhas alterações.
- [ ] **Step 4: Verificação final:** abrir `mapa_unico/mapa_unico.html#tema=historico` no browser (`cmd /c start "" "<caminho>"`) para o utilizador rever; confirmar tamanho de `dados/historico.js` < 7 114 438 bytes.
- [ ] **Step 5: Commit** `git add` dos ficheiros tocados (ler `git status` antes: não incluir `_build/`, spec apagado de tiny-verde nem outros trabalhos); **sem push**.
