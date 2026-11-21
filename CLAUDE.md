# GEE Porto — Espaços Verdes e Uso do Solo

## Credenciais
- **Todas as chaves** no `.env` global (`C:\Users\quent\OneDrive\Claude\.env`; desde 2026-11-17 inclui `GEE_PROJECT`, `CARTO_BASEMAPS_KEY`, `DGT_USER`, `DGT_PASS`), carregado no topo de `GEE/server.py` e de cada gerador (`load_dotenv(.../'..'/'.env')`); um `.env` local, se existir, sobrepõe. Já não há `.env` no projecto.
- `GEE_PROJECT` no `.env`, nunca hardcoded; asset paths em f-strings: `f'projects/{GEE_PROJECT}/assets/...'`.
- **`CARTO_BASEMAPS_KEY`** (`.env` global): sem chave, os mosaicos CARTO saem com marca de água «API KEY REQUIRED». `carto.py` (`aplicar_chave`/`com_chave`) junta `?key=` aos URLs `basemaps.cartocdn.com`; **todo gerador de mapa (também os novos) chama `aplicar_chave(html)` antes de gravar**.

## Estrutura do projecto
Raiz = site Jekyll/GitHub Pages; detalhe em `docs/estrutura.md`.
- **`mapa_unico/` = página única dos mapas (5 temas em separadores); as páginas antigas abaixo são redirects (`mapa_unico/gerar_stubs.py`)**: `mapa/` (Sentinel-2 2016-2025), `ndvi_historico/` (Landsat 1947-2024), `interiores/` (verde privado), `1947/` (classificação ortofoto), `animacao/`, `atropelamentos/` (dashboard + DB), `acessibilidade/` (pipeline 2SFCA + conversão).
- `layers/`, `layers_historico/` — layers partilhados na raiz; `docs/` — planos e specs (fora do Jekyll).
- `assets/js/moldura.js` (menu, abas da Mobilidade e rodapé: única fonte), `nav.py` (atalho que devolve a etiqueta `<script>`), `assets/css/porto-verde.css`, `check_leaflet_init.py`.

## Navegação entre páginas
Menu, abas e rodapé: `assets/js/moldura.js` em todas as páginas (`docs/navegacao.md`); os geradores só escrevem a etiqueta `<script>` (`nav.get_nav`). Rodapé: «Porto Verde» (nunca o nome pessoal do utilizador) e fontes curtas por página (`FONTES` no JS).

## Regras de organização
- **Cada script gera o seu HTML** — nunca editar HTMLs à mão.
- **Layers na raiz, não na pasta do script:** `layers/` (partilhada por `mapa/` e `interiores/`: o verde privado subtrai-se da mesma classificação Sentinel-2), `layers_historico/` (de `ndvi_historico/`); excepção `1947/layers/` (só de `1947/`, dentro da própria pasta).
- **Ficheiros de teste/debug** nunca nas pastas de layers; scripts obsoletos apagam-se (git e disco sincronizados).
- **`_config.yml` exclude** inclui: `*.py`, docs, .claude, .superpowers, `__pycache__/`, `*.bak`, `*.npy`, `*.npz`.
- **Cada sub-projecto tem a sua pasta** — nunca dados espalhados na raiz.
- **Links no `index.html`** apontam para o caminho dentro da pasta (ex: `atropelamentos/dashboard_atropelamentos.html`).

## Camadas de verde — definições e dependências
**Três camadas mutuamente exclusivas**; hierarquia parques > verde pago > verde privado; alterar parques → regenerar as outras.
1. **Parques e jardins** (`parques_porto.geojson`): verde de acesso público gratuito; fonte autoritativa. Polígonos **só** do PDM (fruição colectiva) ou OSM; **nunca do GEE** (buffers Sentinel/Landsat proibidos como geometria; §«Operações em dados geoespaciais»).
2. **Verde pago ou não usufruível** (`verde_pago.png`): pixels (a) em polígonos PDM das categorias verde de fruição colectiva, lúdico-produtiva, protecção e enquadramento, ou associada a equipamento — **excluindo** frente atlântica e ribeirinha; (b) verdes no Sentinel-2; (c) **fora** de qualquer parque/jardim.
3. **Verde privado** (`interior_subsistente.png`): pixels verdes no Sentinel-2 que **não** são parques/jardins, **nem** verde pago, **nem** estradas (logradouros, quarteirões, quintas privadas).

## Acessibilidade — pipeline de regeneração
`acessibilidade/` usa PNGs em cache em `acessibilidade/layers/`. **Ao alterar parques** (adicionar, remover, editar geometria):
1. Editar `parques_porto.geojson` directamente (preferir polígonos PDM ou OSM).
2. **Apagar os PNGs em cache** dependentes: `layers/verde_publico.png`, `layers/verde_pago.png`, `layers/acessibilidade_2sfca.png`, `layers/proximidade_300m.png`, `layers/kernel_300.npy`, `layers/reach_300.npy`.
3. `python acessibilidade_verde.py` — só regenera PNGs que não existam.
4. **Depois**: regenerar o verde privado (abaixo).

## Verde privado — pipeline de regeneração
`interiores/interiores_quarteiroes.py` (Sentinel-2 → subtrai parques e verde pago → máscara de estradas OSM → vectorização). Sem GEE: apagar `layers/interior_subsistente.png` e `layers/interior_perdido.png` e correr o script a partir da raiz. Passos completos e alternativa rápida: `docs/pipeline-verde-privado.md`.

## Regra 3-30-300 (`regra_303030/`; tema `regra` do mapa único)
- Unidade = edifício OSM (42 104). Dados pesados em `S:\3 30 300\dados` (`PV_REGRA_DADOS`); venv `%LOCALAPPDATA%\PortoVerde\venv` (`requirements.txt`); `pip` fora do venv ≠.
- Ordem: `obter_pbf.py` (Geofabrik→edifícios+rede) → `obter_lidar.py` (DGT, `DGT_USER/DGT_PASS` no `.env` global) → `rede300.py` («300») → `copa.py` (nDSM, folhas más) → `arvores.py` → `vista3.py` («3») → `copa500.py` («30») → `numeros.py` (tabela em `docs/regra_303030_numeros.md`) → `populacao.py` (GHS-POP calibrado ao Censos 2021) → `mapa_png.py` (máscaras em `regra_303030/layers/`) → `mapa_unico.py` (`dados/regra.js`).
- Folha LiDAR má = datas MDS/MDT >30 d **e** >2 % nDSM<−1 m disperso; mancha negativa contínua ≥10 000 px = água, não erro.
- Serralves e espaços vedados contam como parque (decisão do utilizador, 2026-11-17). Validação (2026-11-18): 150 edifícios lidos na ortofoto DGT por IA, sem o utilizador; ver `docs/regra_303030_validacao.md`.
- Atribuição ODbL (OSM) obrigatória na fonte do tema. Testes: `pytest regra_303030/tests` (venv) + `python mapa_unico/tests/pw_regra.py`.

## Validação
- Script alterado → no mínimo `python -m py_compile <script>.py`.
- Scripts GEE dependem de autenticação: `ee.Initialize()` a falhar não é bug do código.
- Mapas HTML gerados têm de abrir no browser e mostrar as layers.

## Entrada e artigos (`_posts/`)
Criação de artigos: skill `porto-verde-posts`. **Lista `/artigos/` (maquete A «Índice»):** `artigos/index.html` + `assets/css/artigos.css` + `assets/js/artigos.js`; o filtro usa o campo `tema:` de cada artigo (chave `temas:` no front matter da página; artigo sem tema aparece na lista mas sem filtro). Nunca editar `index.html` para juntar artigos (lista `site.posts` sozinho).
- **Entrada (`index.html`, maquete P2b «Palco e régua»):** estilo `assets/css/inicio.css` (tudo sob `.inicio`), comportamento `assets/js/inicio.js`, imagens `assets/images/inicio/`; temas e fontes no front matter; contagens só de Liquid/dados. Rede dos autocarros: `python gerar_inicio.py` → `_data/inicio_autocarros.json` (lê `Mobilidade/autocarros.html` e `analise.html`; `gerar_autocarros.py` e `gerar_analise.py` chamam-no sozinhos no fim quando gravam a página publicada; `test_inicio.py` acusa dados velhos). Mapas de fundo: `gerar_inicio_mapas.py` (só do repo, água do OSM; difere ~2 % dos PNG publicados, gerar para outra pasta e comparar antes de substituir).

## Regras de código
- Grayscale: `np.mean(array[:,:,:3], axis=2)`, **nunca** `PIL .convert('L')`.
- Pontos de treino: SÓ coordenadas dadas pelo utilizador; nunca gerar.
- Mapas: cores fortes, basemaps visíveis; vídeo MP4 (não GIF); texto via PIL (não cv2) por causa dos acentos; proporções corrigidas com cos(latitude).
- `.db` é gerado por `compilar_dados.py` e gitignored — não commitar.

## Operações em dados geoespaciais
- **GeoJSON >50 linhas ou substituição de blocos:** NUNCA editar inline com Edit/Write → script Python descartável que lê a fonte, transforma e escreve; apagá-lo depois.
- **GEE:** só classificação raster (NDVI, uso do solo pixel-a-pixel). **Proibido gerar ou derivar polígonos de parques com GEE.**
- **Cálculos só dentro do concelho (2026-11-18, pedido do utilizador):** totais, percentagens, hectares e população contam só o que está dentro do Porto (CAOP 2025, `dtmn` 1312); as imagens podem passar o limite, esbatidas. Fonte que passa o limite (OSM, Land cover 1979) → recortar ao CAOP antes de somar (`edificios.dentro_do_porto`, `cobertura_1979.recortar_ao_porto`). O contexto de vizinhança (copa a 500 m em volta de um edifício de fronteira) pode ir além do limite, é medição e não contagem.
- **Antes de juntar um polígono:** existe no PDM? Senão, OSM. Nunca inventar nem aproximar geometrias.

## Lições aprendidas
- **Método do Histórico mudou → grep do artigo (2026-11-18):** o artigo `_posts/2026-03-21-mudanca-verde-porto-1947-2025.md` e a animação repetem números do Histórico e do Sentinel-2; ao mudar `ndvi_historico.py` ou `porto_stats.py`, `Grep` dos valores antigos em `_posts/` e `animacao/` e corrigir (o artigo ficou com a queda artificial 45→30 %). Cálculos só do concelho, nunca do rectângulo do mapa.
- **Verificar consumidores antes de alterar dados** — ao editar `parques_porto.geojson` ou outra fonte partilhada, grep por todos os que a referenciam e actualizar em cadeia.
- Lições técnicas antigas (OBIA 1947, Overpass): fim de `docs/estrutura.md`.
- **Nunca inventar referências** — verificar sempre online autores, anos e títulos antes de citar.
- **Artigos com textos enviados a entidades (caso Aurifícia):** nunca publicar o original nem dados pessoais/referências de notificações; `docs/artigos-textos-entidades.md`.
- **Detalhe (50 Espaços, fichas/fotos, mapa único, moldura, design/identidade visual, artigos, PDF da habitação) → `docs/licoes.md`; ler antes de mexer nesses temas.**

## Modelo dos subagentes (pedido do utilizador: poupar custo)
Ao despachar, **`model` explícito em cada chamada** (por herança, os `general-purpose` saem todos em Sonnet):
- `haiku`: inventariar ficheiros ou estudos, verificar online se um documento existe/está acessível, triar pastas («online ou não»), explorar páginas, localizar fotos candidatas, contar ou comparar listas.
- `sonnet`: pesquisa com raciocínio (ordenamento, PDM, biodiversidade, fichas GAMP), síntese e redacção, decisão de classificação com critério (ex.: ciclo dos PGRH).
- Nunca Haiku para citar autores, anos ou referências (§«Nunca inventar referências»). Lote de Haiku com erros → repetir em `sonnet` e anotar aqui o tipo de tarefa.

## Higiene do repositório
- Regras base (`.gitignore`, scripts one-off, binários, `.bak`): ver global.
- **`.gitignore` deste projecto, adicional:** `*.db`, `*.npy`, `*.npz`, `*.mp4` (dados GEE + animações).
- **`requirements.txt`** — manter actualizado.

## Jekyll — comandos essenciais
Skill `/jekyll`. Config específica: `url: https://portoverde.pt`, `baseurl: ""`; imagens via `{{ site.baseurl }}/assets/...`.
- **`exclude` do `_config.yml` casa por prefixo (2026-11-14):** `Mobilidade/analise` escondeu `Mobilidade/analise.html` (404 com o build «built»). Pasta com o mesmo começo que uma página → escrever `"pasta/*"`. Página nova → abrir o URL real, nunca dar por publicada só com o build verde.

## Fluxo rápido de regeneração
`acessibilidade/regenerar_html.py` e `regenerar_conversao_html.py` regeneram os HTML em ~2 s a partir dos PNGs em cache; detalhe em `docs/fluxo-rapido-regeneracao.md`.

**Dados inline, nunca `fetch()`:** GeoJSON embutidos nos HTML gerados (`fetch()` falha em `file://`, onde os mapas se abrem). Fonte partilhada alterada → regenerar todos os HTML que a consomem.

## Chat «Perguntar» (apagado)
Página `chat/`, código do Worker e infra-estrutura na Cloudflare (Worker, AI Search, Turnstile) apagados; já não há `chat/` neste repo. Registo e motivo: `Fontes\Habitacao\CLAUDE.md`. Não voltar a propor um chat sem decisão do utilizador.

## Mobilidade (`Mobilidade/`)
Autocarros e atropelamentos: método, geração, `.gitignore`, modo «Agora», Análise, Propostas → `docs/mobilidade.md` (ler antes de mexer em `Mobilidade/`). `dashboard_atropelamentos.html` publicado ≠ gerador `mapa_dashboard.py`: não regenerar sem comparar.

## Horrores e sucessos (`/casos/` = mapa autónomo gerado por `mapa_unico.py`; lista `/casos/lista/`)
Regras, esquema e fluxo → `docs/horrores.md` (ler antes de mexer). Nunca editar `mapa_unico/dados/casos.js` à mão; rascunhos só em `docs/horrores/rascunhos/` (gitignored).

## 50 Espaços (`/50espacos/`)
Campanha da Campo Aberto (111 espaços, 50 seleccionados). Regras completas, pipeline e fases: `docs/regras-50espacos.md`. Essenciais:
- Nunca editar `_espacos/**` à mão (gerado por `espacos_pipeline/gerar.py`).
- Só se publica texto com `revisto: true`; o utilizador revê antes.
- Sem dados pessoais: nenhum nome de pessoa singular nem contacto; instituições sim. `docs/50espacos/dossiers/` é gitignored.
- Não existe ranking dos 50.
