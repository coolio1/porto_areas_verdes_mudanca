# GEE Porto — Espaços Verdes e Uso do Solo

## Credenciais
- **API keys** do `.env` global (`C:\Users\quent\OneDrive\Claude\.env`), carregado no topo de `GEE/server.py`; um `.env` local pode sobrepor.
- `GEE_PROJECT` no `.env` (local ou global), nunca hardcoded; asset paths em f-strings: `f'projects/{GEE_PROJECT}/assets/...'`
- **`CARTO_BASEMAPS_KEY`** (`.env` local, gitignored): o CARTO exige chave nos mosaicos (sem ela, marca de água «API KEY REQUIRED»). `carto.py` (`aplicar_chave`/`com_chave`) acrescenta `?key=` aos URLs `basemaps.cartocdn.com`; **todo gerador de mapa chama `aplicar_chave(html)` antes de gravar** (também os novos).

## Estrutura do projecto

Detalhe completo em `docs/estrutura.md`. Resumo (raiz = site Jekyll/GitHub Pages):

- `mapa/` (Sentinel-2 2016-2025), `ndvi_historico/` (Landsat 1947-2024), `interiores/` (verde privado), `1947/` (classificação ortofoto), `animacao/`, `atropelamentos/` (dashboard + DB), `acessibilidade/` (pipeline 2SFCA + conversão)
- `layers/`, `layers_historico/` — layers partilhados na raiz; `docs/` — planos e specs (excluído do Jekyll)
- `nav.py` + `patch_nav.py` (nav única, pre-commit), `capture_cards.py`, `check_leaflet_init.py`

## Navegação entre páginas

Todas as páginas HTML, excepto o index, têm a barra fixa `#nav` com links relativos a todas as outras (detalhe: `docs/navegacao.md`); os scripts que geram HTML incluem-na no template.

## Regras de organização

- **Cada script gera o seu HTML** — nunca editar HTMLs à mão
- **Layers ficam na raiz do projecto, não na pasta do script**: `layers/` (partilhada entre `mapa/` e `interiores/` — o verde privado subtrai-se da mesma classificação Sentinel-2), `layers_historico/` (usada por `ndvi_historico/`), `1947/layers/` (usada só por `1947/`, essa sim dentro da própria pasta)
- **Ficheiros de teste/debug** nunca ficam nas pastas de layers; scripts obsoletos apagam-se (git e disco sincronizados)
- **`_config.yml` exclude** deve incluir: `*.py`, docs, .claude, .superpowers, `__pycache__/`, `*.bak`, `*.npy`, `*.npz`
- **Cada sub-projecto tem a sua pasta** — nunca espalhar ficheiros de dados pela raiz
- **Links no `index.html`** devem apontar para o caminho correcto dentro da pasta (ex: `atropelamentos/dashboard_atropelamentos.html`)

## Camadas de verde — definições e dependências

O projecto usa **três camadas de verde mutuamente exclusivas**:

1. **Parques e jardins** (`parques_porto.geojson`): espaços verdes de acesso público gratuito. Polígonos obtidos **exclusivamente** do PDM (fruição colectiva) ou OSM. **Nunca derivar polígonos do GEE** (buffers Sentinel/Landsat são proibidos como fonte de geometria). Fonte autoritativa.
2. **Verde pago ou não usufruível** (`verde_pago.png`): pixels que são (a) dentro de polígonos PDM das categorias verde de fruição colectiva, lúdico-produtiva, protecção e enquadramento, ou associada a equipamento — **excluindo** frente atlântica e ribeirinha; (b) verdes no Sentinel-2; (c) **fora** de qualquer parque/jardim.
3. **Verde privado** (`interior_subsistente.png`): pixels verdes no Sentinel-2 que **não** são parques/jardins **nem** verde pago, **nem** estradas. Corresponde a logradouros, quarteirões e quintas privadas.

**Hierarquia**: parques > verde pago > verde privado. Ao alterar parques, as outras camadas devem ser regeneradas.

## Acessibilidade — pipeline de regeneração

O mapa de acessibilidade (`acessibilidade/`) usa PNGs em cache na pasta `acessibilidade/layers/`.

**Ao alterar parques (adicionar, remover, editar geometria):**
1. Editar `parques_porto.geojson` directamente (preferir polígonos PDM ou OSM)
2. **Apagar os PNGs em cache** que dependem dos parques:
   - `layers/verde_publico.png`, `layers/verde_pago.png`, `layers/acessibilidade_2sfca.png`
   - `layers/proximidade_300m.png`, `layers/kernel_300.npy`, `layers/reach_300.npy`
3. Correr `python acessibilidade_verde.py` — só regenera PNGs que não existam
4. **Depois**: regenerar o verde privado (ver abaixo)

## Verde privado — pipeline de regeneração

Calculado por `interiores/interiores_quarteiroes.py` (Sentinel-2 → subtrai parques e verde pago → máscara de estradas OSM → vectorização). Para regenerar sem GEE: apagar `layers/interior_subsistente.png` e `layers/interior_perdido.png` e correr o script a partir da raiz. Passos completos e alternativa rápida: `docs/pipeline-verde-privado.md`.

## Validação
- Após alterar um script, verificar pelo menos que executa sem erros de sintaxe: `python -m py_compile <script>.py`
- Scripts GEE dependem de autenticação — se `ee.Initialize()` falhar, não é bug do código
- Mapas HTML gerados devem abrir no browser e mostrar layers correctamente

## Cards do index e artigos (`_posts/`)

Protocolos de thumbnails e de criação de artigos: skill `porto-verde-posts`. Nunca editar `index.html` para adicionar artigos (lista `site.posts` automaticamente).


## Regras de código

- Grayscale: usar `np.mean(array[:,:,:3], axis=2)`, **nunca** `PIL .convert('L')`
- Pontos de treino: usar APENAS coordenadas fornecidas pelo utilizador, nunca gerar automaticamente
- Mapas: cores fortes, basemaps visíveis; vídeo em MP4 (não GIF), texto via PIL (não cv2) para acentos; corrigir proporções com cos(latitude)
- `.db` é gerado por `compilar_dados.py` e gitignored — não commitar

## Operações em dados geoespaciais

- **GeoJSON com >50 linhas ou substituição de blocos**: NUNCA editar inline com Edit/Write. Criar um script Python descartável que lê o ficheiro fonte, transforma os dados e escreve o output. Apagar o script após execução.
- **GEE**: serve exclusivamente para classificação raster (NDVI, uso do solo pixel-a-pixel). **Proibido usar GEE para gerar ou derivar polígonos de parques.**
- **Antes de adicionar qualquer polígono**: verificar se existe no PDM. Se não existir no PDM, usar OSM. Nunca inventar ou aproximar geometrias.

## Lições aprendidas

- **Verificar consumidores antes de alterar dados** — ao editar `parques_porto.geojson` ou qualquer fonte partilhada, grep por todos os ficheiros que a referenciam e actualizar em cadeia.
- Lições técnicas antigas (OBIA 1947, Overpass): fim de `docs/estrutura.md`.
- **Nunca inventar referências** — verificar sempre autores, anos e títulos online antes de citar.

- **Menu:** `patch_nav.py` é bloqueado pelo hook; editar só `nav.py` e deixar o pre-commit propagar.
- **Artigos com textos enviados a entidades (caso Aurifícia):** nunca publicar o original nem dados pessoais/referências de notificações; ver `docs/artigos-textos-entidades.md`.

## Higiene do repositório

- Regras base (`.gitignore`, scripts one-off, binários, `.bak`): ver global.
- **Adicional específico deste projecto no `.gitignore`:** `*.db`, `*.npy`, `*.npz`, `*.mp4` (dados GEE + animações).
- **`requirements.txt`** — manter actualizado.

## Jekyll — comandos essenciais

Ver skill `/jekyll`. Config específica: `baseurl: /porto_areas_verdes_mudanca`; imagens via `{{ site.baseurl }}/assets/...`.

## Fluxo rápido de regeneração

`acessibilidade/regenerar_html.py` e `regenerar_conversao_html.py` regeneram os HTML em ~2 s a partir dos PNGs em cache. Detalhe em `docs/fluxo-rapido-regeneracao.md`.

**Dados inline, nunca `fetch()`:** os GeoJSON são embutidos nos HTML gerados (`fetch()` falha em `file://`, onde os mapas são abertos). Ao alterar uma fonte partilhada, regenerar todos os HTML que a consomem.

## 50 Espaços (`/50espacos/`)

Secção da campanha da Campo Aberto (111 espaços, 50 seleccionados). Regras completas, pipeline e fases: `docs/regras-50espacos.md`. Essenciais:

- Nunca editar `_espacos/**` à mão (gerado por `espacos_pipeline/gerar.py`).
- Só se publica texto com `revisto: true`; o utilizador revê antes.
- Sem dados pessoais: nada de nomes de pessoas singulares nem contactos; instituições sim. `docs/50espacos/dossiers/` é gitignored.
- Não existe ranking dos 50.

