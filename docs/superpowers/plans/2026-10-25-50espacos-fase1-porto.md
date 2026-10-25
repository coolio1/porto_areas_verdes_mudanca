# 50 Espaços — Fase 1 (infraestrutura + piloto Porto) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar `/50espacos/` com a narrativa da campanha, a imprensa, a lista/mapa e as 23 páginas de espaço do Porto, geradas por scripts a partir das quatro fontes.

**Architecture:** Pipeline em `espacos_pipeline/` (Python, excluído do Jekyll por `*.py`): extractores por fonte → JSON intermédio em `docs/fonte_campanha/extraido/` (gitignored) → reconciliação (tabela de divergências) → texto fundido revisto pelo utilizador (`docs/fonte_campanha/fusao/<slug>.md`, versionado em `docs/50espacos/fusao/`) → gerador que escreve `_espacos/<concelho>/<slug>.md`, `_data/espacos_mapa.json` e copia fotos/PDFs para `50espacos/`. Colecção Jekyll `espacos` separada de `_posts/`.

**Tech Stack:** Python 3 (python-docx, openpyxl, Pillow, pytest, pdftotext/PyMuPDF se instalado), Jekyll/GitHub Pages, Leaflet (mapa de pontos).

**Spec:** `docs/superpowers/specs/2026-10-25-50espacos-design.md`

## Global Constraints

- PT-PT anterior ao Acordo Ortográfico em todo o texto publicado e nas mensagens.
- Fontes só em `docs/fonte_campanha/` (cópia local, gitignored; `Arquivo\` é inacessível para escrita/Bash).
- Nunca editar à mão `_espacos/**`, `_data/espacos_mapa.json`, `50espacos/**` gerado: só o gerador os escreve.
- Nunca polígonos nesta fase; pontos só com coordenadas, com `origem_coord`.
- Nada com dados pessoais: sem contactos de proponentes, inscrições, lista do grupo de trabalho, pontuações individuais.
- Hierarquia por camada: 2006–2008 → 2014–2015 (PDF) → Webnode (mais recente). Divergências registadas, nunca resolvidas em silêncio.
- Cada afirmação datada na frase; nunca misturar 2006 com 2019 sem data.
- Antes de afirmar o que um PDF diz: `python ~/.claude/scripts/pdf_audit.py <pdf> --ocr --out <scratchpad>`; cor de fundo só confirmada no PNG da página.
- `_config.yml`: `baseurl` actual é `""` (o CLAUDE.md fala de `/porto_areas_verdes_mudanca`: confirmar antes da Task 1; usar sempre `{{ site.baseurl }}`).
- URLs: `/50espacos/`, `/50espacos/imprensa/`, `/50espacos/espacos/`, `/50espacos/espacos/<concelho>/<slug>/`.
- Estado actual ∈ {por verificar, preservado, parcialmente construído, destruído, ameaçado}, com `data_verificacao`.
- Commit só quando o utilizador pedir; os passos "Commit" abaixo são propostas a executar nessa altura.
- Fora desta fase: os 8 concelhos que aderiram à AMP depois de 2006 (Arouca, Oliveira de Azeméis, Paredes, Santa Maria da Feira, Santo Tirso, São João da Madeira, Trofa, Vale de Cambra) e os restantes concelhos originais (Fase 2, decidida pelo utilizador depois do piloto).

## Review Focus

1. Ficha só numa fonte (zip sem projecto ou vice-versa): deve aparecer na tabela de reconciliação, não desaparecer.
2. Nome com gralha/variante entre fontes (`Quinta dos Ananases` vs `quinta dos ananases`): mesmo slug, sem página duplicada.
3. Espaço sem coordenadas: página existe, fica fora do mapa, sem `lat`/`lon` a zero.
4. Espaço seleccionado sem `selecao` válida (`2009-04` ou `posterior`): o gerador falha em vez de publicar.
5. Texto fundido com número de telefone, e-mail ou nome de proponente com contacto: o validador falha.

---

## Estrutura de ficheiros

- Create `espacos_pipeline/__init__.py`, `modelo.py` (dataclass `Espaco`, slugify, validação), `extrair_docx.py`, `extrair_pdf.py`, `extrair_webnode.py`, `extrair_selecao.py`, `reconciliar.py`, `gerar.py`, `copiar_media.py`
- Create `espacos_pipeline/tests/` (um ficheiro por módulo, fixtures pequenas em `tests/fixtures/`)
- Create `_layouts/espaco.html`, `_layouts/campanha.html`, `50espacos/index.md`, `50espacos/imprensa.md`, `50espacos/espacos/index.md`
- Modify `_config.yml` (colecção, defaults), `nav.py` (`_JEKYLL_EXTRA`), `.gitignore`, `index.html`/card via skill `porto-verde-posts`, `CLAUDE.md` do projecto
- Generated: `_espacos/porto/*.md`, `_data/espacos_mapa.json`, `50espacos/media/**`

---

### Task 1: Esqueleto Jekyll da secção

**Files:**
- Modify: `_config.yml`
- Create: `_layouts/espaco.html`, `50espacos/index.md`, `50espacos/espacos/index.md`, `_espacos/porto/_exemplo-teste.md` (apagar no fim da task)
- Test: `espacos_pipeline/tests/test_site_build.py`

**Interfaces:**
- Produces: colecção `espacos` (`output: true`, permalink `/50espacos/espacos/:path/`), layout `espaco` que lê `page.titulo`, `page.concelho`, `page.freguesia`, `page.seleccionado`, `page.posicao_2009`, `page.area_ha`, `page.estado_actual`, `page.data_verificacao`, `page.fontes`, `page.fotos`, `page.anexos`.

- [ ] **Step 1: Confirmar `baseurl` e disponibilidade do Jekyll** — `grep baseurl _config.yml; bundle exec jekyll -v` (ou skill `/jekyll`). Registar no relatório; se o Jekyll não correr localmente, o teste passa a verificar só o front matter e o build fica para o GitHub Pages.
- [ ] **Step 2: Test `test_exemplo_gera_pagina_em_permalink_esperado`**: faz build para pasta temporária e assere que existe `_site/50espacos/espacos/porto/exemplo-teste/index.html` contendo o `titulo`.
- [ ] **Step 3: Run** `pytest espacos_pipeline/tests/test_site_build.py -v` → FAIL (colecção inexistente).
- [ ] **Step 4: Implementar** em `_config.yml`: `collections: espacos: {output: true, permalink: /50espacos/espacos/:path/}`, `defaults` com `scope: {path: "_espacos", type: "espacos"}`, `layout: espaco`; `exclude` acrescenta `espacos_pipeline`. Layout `espaco.html` estende `default` e segue a secção «Design das páginas» da spec: migalhas, título, etiquetas (seleccionado + posição, estado), linha de dados, `{{ content }}`, galeria, mini-mapa (só se houver `lat`/`lon`), anexos e fontes. Estilo igual ao de `post.html` (variáveis `--text`, `--muted`, `--green`), legível a 375 px.
- [ ] **Step 5: Run** o teste → PASS; apagar `_espacos/porto/_exemplo-teste.md`.
- [ ] **Step 6: Commit** `feat: colecção espacos e layout`

---

### Task 1b: Sistema visual «Dossiê de campo»

**Files:**
- Create: `assets/css/50espacos.css`, `assets/fonts/` (woff2 das duas famílias, licença OFL), `_includes/marcas_111.html`
- Modify: `_layouts/espaco.html`, `_layouts/campanha.html` (ligam a folha de estilo)
- Test: `espacos_pipeline/tests/test_visual.py`

**Interfaces:**
- Produces: tokens CSS `--papel --floresta --verde --sinal --grafite --rio` (+ variante escura), classes `.ficha-dados` (tabela de caixas), `.marcas` / `.marca[data-seleccionado]`; `_includes/marcas_111.html` lê `site.data.espacos_mapa` (ou lista completa) e escreve uma marca por espaço, as seleccionadas com `data-seleccionado="true"`, cada uma um `<a>` com `aria-label` = nome.

- [ ] **Step 1: Test** `test_css_define_tokens_e_variante_escura` (os 6 tokens e `prefers-color-scheme: dark`), `test_marcas_tem_uma_ligacao_por_espaco_com_aria_label`, `test_animacao_desligada_com_reduced_motion`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implementar** o CSS e o include segundo a secção «Direcção visual» da spec (um único movimento: preenchimento sequencial das marcas ao carregar). Fontes alojadas localmente; descarregar de fontes oficiais e verificar a licença.
- [ ] **Step 4: Run** → PASS. **Step 5:** Verificar no browser a 375 px e 1280 px, tema claro e escuro; capturas ao utilizador para aprovar **antes** das Tarefas 9 e 11.
- [ ] **Step 6: Commit** `feat: sistema visual dossiê de campo`

---

### Task 2: Modelo de dados e validação

**Files:**
- Create: `espacos_pipeline/modelo.py`
- Test: `espacos_pipeline/tests/test_modelo.py`

**Interfaces:**
- Produces: `slugify(nome: str) -> str` (minúsculas, sem acentos, hífens; `"Quinta dos Ananases"` e `"quinta dos ananases "` → `quinta-dos-ananases`); `@dataclass Espaco` com os campos do front matter da spec; `validar(e: Espaco) -> list[str]` (lista de erros); `CONCELHOS_FASE1 = {"porto"}`; `ESTADOS: tuple[str, ...]`.

- [ ] **Step 1: Tests**: `test_slug_ignora_caixa_acentos_espacos`; `test_seleccionado_sem_selecao_falha` (Review Focus 4); `validar_lote(list[Espaco]) -> list[str]` só verifica slugs repetidos; `test_lat_lon_sem_origem_falha`; `test_lat_lon_zero_falha` (Review Focus 3); `test_estado_fora_da_lista_falha`; `test_texto_com_telefone_ou_email_falha` (regex `\b\d{9}\b`, `\+351`, `@`; Review Focus 5).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implementar** `modelo.py` com as assinaturas acima.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: modelo de dados dos espaços`

---

### Task 3: Extracção das fichas 2006–2008 (.docx) — zip e projecto

**Files:**
- Create: `espacos_pipeline/extrair_docx.py`
- Test: `espacos_pipeline/tests/test_extrair_docx.py`, fixture `tests/fixtures/ficha_exemplo.docx` (cópia de uma ficha real do Porto, sem contactos)

**Interfaces:**
- Consumes: `slugify`.
- Produces: `extrair_ficha(path: Path) -> dict` com `titulo, n_ficha, texto, tabelas, origem_ficheiro`; CLI `python -m espacos_pipeline.extrair_docx` que lê `docs/fonte_campanha/site_zip/espacos/lista*/` e `docs/fonte_campanha/projecto/Espacos/Fichas/` e escreve `docs/fonte_campanha/extraido/docx_zip.json` e `docx_projecto.json` (chave = slug). Contactos/e-mails/telefones são removidos na extracção e contados em `contactos_removidos`.

- [ ] **Step 1: Inspeccionar** a estrutura real (Glob em `docs/fonte_campanha/projecto/Espacos/Fichas/` e `site_zip/espacos/lista/`); anotar convenção de nomes e onde está o N.º de ficha. Se a ficha for `.doc` binário, usar a conversão disponível (LibreOffice) e registar.
- [ ] **Step 2: Test** `test_extrair_ficha_devolve_titulo_e_texto` e `test_contactos_sao_removidos` (assert que nenhum `@` nem sequência de 9 dígitos fica em `texto`).
- [ ] **Step 3: Run** → FAIL. **Step 4: Implementar** com `python-docx`. **Step 5: Run** → PASS.
- [ ] **Step 6: Correr a CLI** e verificar: `python -c "import json;print(len(json.load(open('docs/fonte_campanha/extraido/docx_zip.json'))))"` — a contagem é apenas relatada (esperado ≈110 zip, 112 projecto, a confirmar na reconciliação).
- [ ] **Step 7: Commit** `feat: extractor das fichas 2006-2008`

---

### Task 4: Extracção do PDF de 2016 (camadas por cor)

**Files:**
- Create: `espacos_pipeline/extrair_pdf.py`
- Test: `espacos_pipeline/tests/test_extrair_pdf.py` (fixture: PDF de 2–3 páginas recortado do original)

**Interfaces:**
- Produces: `extrair_pdf(path: Path, paginas: range | None) -> dict[str, list[Bloco]]` com `Bloco(texto: str, camada: Literal["2006-2008","oficial","campo_aberto","cidadaos","ultima_hora","desconhecida"], pagina: int)`; mapeamento camada ← cor de fundo dominante do bloco (verde, azul, amarelo, salmão, branco). CLI escreve `extraido/pdf2016.json`.

- [ ] **Step 1: Auditar** o PDF (`docs/fonte_campanha/` não o contém — está em `scratchpad/web111/111espacos-TOTAL.pdf`; copiar para `docs/fonte_campanha/pdf2016/`): `pdf_audit.py` **sem `--ocr`** primeiro (o OCR expirou na pág. 146), depois `--ocr` com `--pages` por troços de 20 até cobrir tudo. Registar páginas-imagem.
- [ ] **Step 2: Decidir método de cor** com 3 páginas de amostra: renderizar PNG (PyMuPDF/pdftoppm), amostrar a cor de fundo por faixa de texto. Mostrar ao utilizador os PNGs das 3 amostras e a legenda inferida, e só prosseguir com a confirmação dele (a legenda vem do texto do PDF, não da minha inferência).
- [ ] **Step 3: Test** `test_bloco_verde_classifica_oficial` e `test_pagina_branca_e_2006_2008` na fixture. **Step 4: Run** FAIL. **Step 5: Implementar.** **Step 6: Run** PASS.
- [ ] **Step 7: Correr no PDF inteiro** e relatar nº de espaços encontrados (esperado 111) e blocos `desconhecida`.
- [ ] **Step 8: Commit** `feat: extractor do PDF de 2016 por camada`

---

### Task 5: Extracção do Webnode (Porto)

**Files:**
- Create: `espacos_pipeline/extrair_webnode.py`
- Test: `espacos_pipeline/tests/test_extrair_webnode.py` (fixture HTML guardado de 1 espaço)

**Interfaces:**
- Produces: `extrair_webnode(html: str) -> list[dict]` com `nome, freguesia, proponente, area_ha, lat, lon, estado_texto, texto, seleccionado`; CLI com `requests` lê `https://espacosvivos-grporto-amp.webnode.pt/` (páginas Porto e "Últimos espaços livres no Porto": 7 seleccionados + 16 não seleccionados) e escreve `extraido/webnode_porto.json`, com `data_recolha`.

- [ ] **Step 1: Guardar** o HTML bruto em `docs/fonte_campanha/webnode/` (reprodutível; evita depender do site vivo).
- [ ] **Step 2: Test** `test_extrai_coordenadas_wgs84_duas_casas` e `test_espaco_sem_coordenadas_devolve_none` (Review Focus 3). **Step 3–5:** FAIL → implementar → PASS.
- [ ] **Step 6: Verificar** contagem = 23 (7+16); divergência → relatar, não ajustar.
- [ ] **Step 7: Commit** `feat: extractor Webnode Porto`

---

### Task 6: Selecção de 2009 (50 e ordem)

**Files:**
- Create: `espacos_pipeline/extrair_selecao.py`
- Test: `espacos_pipeline/tests/test_extrair_selecao.py`

**Interfaces:**
- Produces: `ler_selecao(xlsx: Path) -> list[tuple[int, str]]` (nome, concelho, `selecao`), **sem** pontuações nem ordem; CLI escreve `extraido/selecao2009.json`.

- [ ] **Step 1:** Ler `projecto/Espacos/50espacos.xlsx` e `Avaliacao/` (openpyxl, só leitura); localizar `SeleccaoEV.xlsx` (Glob). Se `50espacos.xlsx` e `SeleccaoEV.xlsx` divergirem, parar e perguntar ao utilizador qual vale (decisão dele).
- [ ] **Step 2: Test** `test_selecao_junta_lista_de_abril_e_lista_do_livro` e `test_resultado_nao_contem_colunas_de_grupos_nem_ordem` (feito: 48 + 2 = 50). **Step 3–5:** FAIL → implementar → PASS.
- [ ] **Step 6: Commit** `feat: extractor da selecção de 2009`

---

### Task 7: Reconciliação e tabela de divergências

**Files:**
- Create: `espacos_pipeline/reconciliar.py`
- Test: `espacos_pipeline/tests/test_reconciliar.py`
- Output: `docs/superpowers/specs/2026-10-25-50espacos-reconciliacao.md` (tabela gerada)

**Interfaces:**
- Consumes: JSON das Tasks 3–6.
- Produces: `reconciliar(fontes: dict[str, dict]) -> Relatorio` com, por slug, presença em cada fonte (`zip`, `projecto`, `pdf`, `webnode`, `selecao`), nomes variantes, e `divergencias: list[Divergencia(slug, campo, fonte_a, valor_a, fonte_b, valor_b)]` para `area_ha`, `freguesia`, `proponente`; `escrever_md(r: Relatorio, path: Path)`.

- [ ] **Step 1: Tests**: `test_ficha_so_no_zip_aparece_no_relatorio` (Review Focus 1); `test_variantes_de_nome_juntam_no_mesmo_slug` (Review Focus 2); `test_divergencia_de_area_e_registada_e_nao_resolvida`.
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Correr** e **apresentar ao utilizador** o ponto único de decisão: lista final de 111, extras (`arboreto escola EB2 Canelas`, `quinta dos ananases`, `espacos compilados`), e as 23 do Porto (zip 23 / projecto 25 / Webnode 23). Decisões 1 a 1 com AskUserQuestion.
- [ ] **Step 6: Commit** `feat: reconciliação das fontes`

---

### Task 8: Fusão editorial dos 23 do Porto (rascunhos para revisão)

**Files:**
- Create: `docs/50espacos/fusao/porto/<slug>.md` (23 ficheiros) com front matter `slug`, `fontes_usadas` e corpo; `espacos_pipeline/preparar_fusao.py`
- Test: `espacos_pipeline/tests/test_preparar_fusao.py`

**Interfaces:**
- Produces: `montar_dossier(slug: str, fontes: dict) -> str` — Markdown com as camadas lado a lado (2006–2008, 2014–2015 por cor, Webnode + data) para escrever o texto único; o texto final tem as datas inline (ex.: «Em 2007 …; em 2015 a CMP …; em 2019 …»).

- [ ] **Step 1: Test** `test_dossier_contem_todas_as_camadas_presentes_e_datas`. **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Piloto** — escrever o texto fundido de **1 espaço** (Parque Oriental, tem texto até 2019) e mostrá-lo ao utilizador para aprovar tom e extensão **antes** dos restantes 22.
- [ ] **Step 6:** Escrever os restantes 22 em PT-PT pré-AO, sem inventar factos (só o que as fontes dizem, cada camada datada). Validador de Task 2 sobre todos.
- [ ] **Step 7:** Utilizador revê os 23 (um lote, ficheiros em `docs/50espacos/fusao/porto/`); marcar `revisto: true` no front matter só após o OK dele.
- [ ] **Step 8: Commit** `docs: texto fundido dos espaços do Porto`

---

### Task 9: Gerador de páginas, lista e mapa

**Files:**
- Create: `espacos_pipeline/gerar.py`, `50espacos/espacos/index.md` (lista + Leaflet), `_includes/espacos_mapa.html`
- Test: `espacos_pipeline/tests/test_gerar.py`

**Interfaces:**
- Consumes: `Espaco`, `validar_lote`, JSON de extracção, `fusao/**/*.md` com `revisto: true`.
- Produces: `gerar(espacos: list[Espaco], raiz: Path) -> list[Path]` escreve `_espacos/<concelho>/<slug>.md` e `_data/espacos_mapa.json` (só com `lat`/`lon`, campos `slug, titulo, lat, lon, origem_coord, seleccionado`); falha (excepção, nada escrito) se `validar_lote` devolver erros; idempotente (2 execuções = mesmo output).

- [ ] **Step 1: Tests**: `test_gerar_escreve_front_matter_e_corpo`; `test_gerar_e_idempotente`; `test_espaco_sem_coordenadas_nao_entra_no_mapa`; `test_erro_de_validacao_nao_escreve_nada`; `test_nao_publica_fusao_sem_revisto`.
- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5:** Página de lista (spec, «Design das páginas»): mapa no topo, lista com filtros concelho / «só os 50» / estado em JavaScript simples sobre `_data/espacos_mapa.json` e a lista; clique no ponto ou na linha abre a ficha; mapa com aviso «Localizações aproximadas (WGS84, 2 casas decimais ≈ 1 km); fonte: Webnode».
- [ ] **Step 6: Gerar o Porto**, build Jekyll, abrir `/50espacos/espacos/` no browser e confirmar visualmente mapa e 23 páginas (Chrome MCP ou `jekyll serve`).
- [ ] **Step 7: Commit** `feat: gerador de páginas e mapa dos espaços`

---

### Task 10: Fotos e PDFs de apoio

**Files:**
- Create: `espacos_pipeline/copiar_media.py`
- Test: `espacos_pipeline/tests/test_copiar_media.py`

**Interfaces:**
- Produces: `copiar_media(slug: str, origens: list[Path], destino: Path, max_lado: int = 1400) -> list[str]` — copia fotos com redimensionamento (Pillow, JPEG q=82), PDFs/mapas tal como estão; ignora `.doc/.docx`, `Thumbs.db`, `.mno`, `.html`; devolve caminhos relativos para `fotos`/`anexos`.

- [ ] **Step 1: Medir** o peso das mídias dos 23 do Porto e das imprensa (35 PDFs) antes de copiar: `du`/Python; se o total exceder 100 MB, parar e perguntar ao utilizador (GitHub Pages aceita até 1 GB, mas o clone fica pesado; decisão dele).
- [ ] **Step 2: Tests**: `test_foto_grande_e_reduzida`; `test_extensoes_excluidas_ignoradas`; `test_pdf_copiado_sem_alteracao` (hash igual).
- [ ] **Step 3–5:** FAIL → implementar → PASS. **Step 6:** Correr para o Porto; `gerar` inclui `fotos`/`anexos`.
- [ ] **Step 7: Commit** `feat: cópia de fotos e anexos`

---

### Task 11: Narrativa da campanha e imprensa

**Files:**
- Create: `50espacos/index.md`, `50espacos/imprensa.md`, `_data/imprensa.yml`, `espacos_pipeline/gerar_imprensa.py`
- Test: `espacos_pipeline/tests/test_gerar_imprensa.py`

**Interfaces:**
- Produces: `gerar_imprensa(pasta_pdf: Path, destino: Path) -> list[dict]` (`ficheiro, jornal, data, titulo`) escrito em `_data/imprensa.yml`; cópia dos 35 PDFs para `50espacos/imprensa/`.

- [ ] **Step 1:** Ler `site_zip/comunicacao/revista_imprensa/`; auditar os 35 PDFs com `pdf_audit.py` e identificar jornal/data/título de cada um **a partir do PDF** (conferir no PNG); o que não for legível fica «a identificar», nunca adivinhado.
- [ ] **Step 2: Test** `test_cada_pdf_tem_entrada_com_ficheiro_existente`. **Step 3–5:** FAIL → implementar → PASS.
- [ ] **Step 3b:** Ler também `descricao`, `actividades`, `downloads`, «Apelo à CMP» (Webnode). Layout `campanha.html` (números-chave, atalhos, linha do tempo 2006→hoje) e `imprensa.md` agrupada por ano, mais recente primeiro, sem miniaturas (spec, «Design das páginas»). Escrever `50espacos/index.md`: história, critérios, metodologia, fases (2006–2009 → hoje), número 111 com os números datados (115/113/«mais de 70»), ligação ao livro, ligação ao formulário (decisão: manter o Google Forms do Webnode ou omitir — AskUserQuestion). Sem pontuações nem contactos. Utilizador revê.
- [ ] **Step 4: Commit** `feat: narrativa e imprensa da campanha`

---

### Task 12: Navegação, card e documentação

**Files:**
- Modify: `nav.py` (`_JEKYLL_EXTRA` ← `("50espacos/", "50 Espaços")`), `_includes/nav.html` (regenerado), `.gitignore`, `CLAUDE.md`
- Create: card no index via skill `porto-verde-posts`

- [ ] **Step 1:** Invocar a skill `porto-verde-posts` para o protocolo do card/thumbnail (`capture_cards.py`); seguir o protocolo.
- [ ] **Step 2:** Editar `nav.py` e correr `python patch_nav.py`; `python patch_nav.py --check` → sem divergência.
- [ ] **Step 3:** `CLAUDE.md`: secção «50 Espaços» (pipeline, comandos, regra de não editar `_espacos/`, fonte em `docs/fonte_campanha/`).
- [ ] **Step 4:** `.gitignore`: `docs/fonte_campanha/extraido/`.
- [ ] **Step 5: Verificação final** (`superpowers:verification-before-completion`): `pytest espacos_pipeline -v` todo verde; build Jekyll sem erros; links internos 200 (rastreio local); 23 páginas do Porto; grep em `_espacos/` e `50espacos/` por `@`, `\b\d{9}\b`, «Pontuação» → 0 ocorrências.
- [ ] **Step 6: Commit** `feat: secção 50 Espaços — fase 1 (Porto)`

---

## Fase 2 (fora deste plano)

Fusão e geração dos restantes 88 espaços, verificação do estado actual por fases e polígonos PDM/OSM: planear depois do piloto, decidida pelo utilizador.

## Self-review

- Cobertura da spec: objectivos (Tasks 9, 11, 12), modelo de dados (2), pipeline 1–5 (3–10), mapa (9), hierarquia/divergências (7), anexos (10), nav+card (12), dados pessoais (2, 3, 12). Estado actual: campo e `data_verificacao` existem; preenchido «por verificar» no piloto (verificação é Fase 2, conforme decisão 4).
- Pendentes da spec resolvidos em tarefas: cor do PDF (4), reconciliação 111/110/112 (7), `SeleccaoEV.xlsx` (6), Webnode vs PDF (7, divergências), subpáginas (11), Google Forms (11), peso (10).
- Tipos consistentes: `Espaco`, `slugify`, `validar`, `validar_lote` definidos na Task 2 e usados nas Tasks 7–9.
