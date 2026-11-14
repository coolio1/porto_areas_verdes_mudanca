# GEE Porto — Espaços Verdes e Uso do Solo

## Credenciais
- **API keys** do `.env` global (`C:\Users\quent\OneDrive\Claude\.env`), carregado no topo de `GEE/server.py`; um `.env` local pode sobrepor.
- `GEE_PROJECT` no `.env` (local ou global), nunca hardcoded; asset paths em f-strings: `f'projects/{GEE_PROJECT}/assets/...'`
- **`CARTO_BASEMAPS_KEY`** (`.env` local, gitignored): o CARTO exige chave nos mosaicos (sem ela, marca de água «API KEY REQUIRED»). `carto.py` (`aplicar_chave`/`com_chave`) acrescenta `?key=` aos URLs `basemaps.cartocdn.com`; **todo gerador de mapa chama `aplicar_chave(html)` antes de gravar** (também os novos).

## Estrutura do projecto

Detalhe completo em `docs/estrutura.md`. Resumo (raiz = site Jekyll/GitHub Pages):

- **`mapa_unico/` = página única dos mapas (4 temas em separadores; detalhe em `docs/estrutura.md`); as páginas antigas abaixo são redirects (`mapa_unico/gerar_stubs.py`)**; `mapa/` (Sentinel-2 2016-2025), `ndvi_historico/` (Landsat 1947-2024), `interiores/` (verde privado), `1947/` (classificação ortofoto), `animacao/`, `atropelamentos/` (dashboard + DB), `acessibilidade/` (pipeline 2SFCA + conversão)
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

- **Estudos e fichas (2026-11-01):** o permalink das fichas é `/50espacos/espacos/<concelho>/<slug>/`; documentos que já têm ficha vão para `50espacos/media/<slug>/`, não para Estudos (comparar md5 antes de alojar). Em descargas em lote, validar `%%EOF` no fim do PDF: cópias do Wayback truncam em múltiplos de 1 MiB e um limite de leitura próprio também trunca. O hook proíbe escrever em «Para arquivar»: preparar a pasta na scratchpad e o utilizador copia com `! cp -rn`. Pendentes de descarga: `docs/50espacos/estudos_por_descarregar.md`. Verificar o ciclo dos PGRH (as versões de 2011 são do 1.º ciclo; os agentes contaram-nas como 2.º).
- **Fotos das fichas (2026-11-01):** `50espacos/media/<slug>/creditos.json` (`{"01.jpg": {"fonte", "url"}}`) mostra o crédito sob a foto; fontes com outros direitos são aceites desde que creditadas. Fotos de utilizadores do Google Maps não se usam. O Street View não serve para os espaços sem foto (Vessada, Taím, Monte Penedo, Frejufe): as coordenadas têm 2 casas decimais e o Google só tem o topónimo. Sem foto: o utilizador fornece-a.
- **Mapa único (2026-11-02):** ao fundir páginas, medir a paridade contra o HTML **publicado**, não contra o gerador (divergem: o `interiores` publicado tem o «Subsistente» corrigido, 295 mil px, e `layers/interior_subsistente.png` tem 450 mil), e comparar os PNG por alfa. Duas páginas com o «mesmo» dado podem ter versões diferentes (1947: a página 1947 mostrava a classificação bruta, o Histórico a limpa por `clean_1947.py`); verificar a origem antes de escolher. Testar em `file://` com Playwright (a extensão Chrome não abre `file://`); o hook bloqueia `sed -i` no OneDrive: usar Edit. Dados embutidos em `mapa_unico/dados/*.js`: ver `docs/estrutura.md`.
- **Menu:** `patch_nav.py` é bloqueado pelo hook; editar só `nav.py` e deixar o pre-commit propagar.
- **Artigos com textos enviados a entidades (caso Aurifícia):** nunca publicar o original nem dados pessoais/referências de notificações; ver `docs/artigos-textos-entidades.md`.

## Modelo dos subagentes (2026-11-06, pedido do utilizador: poupar custo)

Medido em 7 dias: 2 555 turnos de subagentes `general-purpose` neste projecto, todos em Sonnet por herança. Ao despachar, **especificar `model` em cada chamada**:
- `haiku`: inventariar ficheiros ou estudos, verificar online se um documento existe ou está acessível, triar pastas («online ou não»), explorar páginas, localizar fotos candidatas, contar ou comparar listas.
- `sonnet`: pesquisa com raciocínio (ordenamento, PDM, biodiversidade, fichas GAMP), síntese e redacção, qualquer decisão de classificação com critério (ex.: ciclo dos PGRH).
- Nunca Haiku para citar autores, anos ou referências (ver «Nunca inventar referências»). Se um lote de Haiku sair com erros, repetir esse lote em `sonnet` e anotar aqui o tipo de tarefa.

## Higiene do repositório

- Regras base (`.gitignore`, scripts one-off, binários, `.bak`): ver global.
- **Adicional específico deste projecto no `.gitignore`:** `*.db`, `*.npy`, `*.npz`, `*.mp4` (dados GEE + animações).
- **`requirements.txt`** — manter actualizado.

## Jekyll — comandos essenciais

Ver skill `/jekyll`. Config específica: `baseurl: /porto_areas_verdes_mudanca`; imagens via `{{ site.baseurl }}/assets/...`.

## Fluxo rápido de regeneração

`acessibilidade/regenerar_html.py` e `regenerar_conversao_html.py` regeneram os HTML em ~2 s a partir dos PNGs em cache. Detalhe em `docs/fluxo-rapido-regeneracao.md`.

**Dados inline, nunca `fetch()`:** os GeoJSON são embutidos nos HTML gerados (`fetch()` falha em `file://`, onde os mapas são abertos). Ao alterar uma fonte partilhada, regenerar todos os HTML que a consomem.

## Chat «Perguntar» (apagado 2026-11-14)

Página `chat/`, código do Worker e a infra-estrutura na Cloudflare (Worker, AI Search, Turnstile) foram apagados; já não há `chat/` neste repo. Registo e motivo: `Fontes\Habitacao\CLAUDE.md`. Não voltar a propor um chat sem decisão do utilizador.

## Mobilidade — velocidade dos autocarros (`Mobilidade/`, 2026-11-11)

Página `Mobilidade/autocarros.html` (menu «Mobilidade»). Os atropelamentos estão dentro da Mobilidade como **separador** (2026-11-11): o menu só tem «Mobilidade» (a página dos atropelamentos acende-o por alias em `nav.py`) e `nav.get_abas_mobilidade()` põe a barra Autocarros | Atropelamentos por baixo do menu nas duas páginas; pastas e URLs não mudaram. **O `dashboard_atropelamentos.html` publicado diverge do gerador `mapa_dashboard.py`** (CSS de telemóvel e gráficos editados à mão): não o regenerar sem comparar; os separadores foram acrescentados só ao HTML. Spec e plano: `docs/superpowers/specs|plans/2026-11-11-mapa-velocidades-autocarros*`.

- **Gera:** `uv run --no-project --with-requirements Mobilidade/requirements.txt python Mobilidade/gerar_autocarros.py` (≈ 2,5 min). Lê os CSV da recolha em `C:\Users\quent\Dados\autocarros\` (fora do OneDrive; descarregar do VPS com `descarregar_recolha.py <IP>`, ver memória `reference_vps_recolha_autocarros`) e as rotas/paragens STCP do OSM (cache em `Dados\autocarros\osm\`). Melhora sozinho com mais dados: basta voltar a gerar; o push é do utilizador (repo público). Se a escrita directa em `Mobilidade/` falhar, gerar com `--saida` para a scratchpad e `cp`.
- **Método:** leituras coladas aos troços (~200 m) da própria linha (OSM, ≤ 30 m, direcção); média por (troço, sentido, período, dia útil/fim-de-semana) com mínimo 20 leituras, 3 veículos, 2 dias; crítico = < 14 km/h; tamanho = minutos perdidos por hora face a 25 km/h.
- **Esperas descontadas** (≤ 2 km/h a < 40 m de paragem, salvo se os outros autocarros ali também andam < 8 km/h; paradas ≥ 15 leituras seguidas; **paragens ≥ 5 min (25 m) a < 100 m do início ou fim de uma viagem**, `marcar_paradas_em_terminal`, 2026-11-13: havia 1 562 em 5 dias, 92 % em terminais, e a regra das 15 leituras (≈ 15 min) deixava escapar 26 % das leituras); **os zeros do trânsito contam sempre**. No modo «Agora» e no habitual o equivalente é ≤ 2 km/h a < 100 m de um terminal (`habitual.terminais`: células de 80 m com ≥ 10 pontas de viagem, embutidas no HTML); raio de 60 a 250 m dá o mesmo resultado.
- **No git:** só `gerar_autocarros.py`, `velocidade/`, `tests/`, `requirements.txt` e `autocarros.html` (`.gitignore` `Mobilidade/*` + excepções). **Fora:** `recolher_autocarros.py`, `verificar_recolha.py`, `descarregar_recolha.py`, `deploy/` e dados brutos (IP do VPS e posições nunca no repo). Só se publicam agregados por troço, sem identificadores de veículo.
- Fim-de-semana fica desactivado até haver 2 dias (a partir de 16 de Novembro).
- **Modo «Agora» (2026-11-13):** quarto botão do seletor «Mostrar» de `autocarros.html` (não é página nem separador: o pedido «adicionar um com a velocidade agora» era mais um modo). Esconde dia/período, troca para mapa escuro e liga o feed da Porto Digital (CORS aberto, `speed` em m/s) a cada 20 s: rastos de partículas que seguem só os autocarros do mesmo sentido (a média de vectores anulava os dois sentidos), mostrador com média da rede, % parados e 5 linhas mais lentas, contra o habitual por hora (`velocidade/habitual.py`: dias úteis anteriores a hoje, esperas descontadas pela mesma regra simples nas duas séries; entra no HTML com as paragens, ~110 KB). **Rastos pelas ruas (2026-11-13):** cada autocarro cola-se (≤ 30 m, sentido) a um troço de `D.trocos` e as partículas correm ao longo dessas ruas, passando ao troço ligado no fim (sem inversão de marcha); um ponto por autocarro, da cor do rasto (pane `pontosAgora`, por cima do canvas). Autocarros que não se colam a nenhuma rua ficam de fora do desenho (não das estatísticas). Gera-se com o resto (`gerar_autocarros.py`). Nada ao vivo é gravado; o único `fetch()` da página é o do feed. Limite conhecido: uma fila de autocarros parados num terminal a > 40 m de uma paragem OSM pode aparecer como «linha lenta». O pacote `STCP-dados-e-codebook` (GPS sem velocidade, só pontas) não entra no habitual. Lição: «adicionar um» sem mais contexto, numa página que já tem selectores, é um item do selector; ler a página antes de propor a forma.

**Página «Análise» (`Mobilidade/analise.html`, 2026-11-13):** terceiro separador (Autocarros | Análise | Atropelamentos; alias em `nav.py`), 12 gráficos D3 em 5 capítulos (Quando, Onde, Linhas, Horário, Excepção). Gera: `uv run --no-project --with-requirements Mobilidade/requirements.txt python -X utf8 Mobilidade/gerar_analise.py` (≈ 5 min; `--guardar-json` / `--json` guardam e reutilizam os agregados para afinar só a página). **Velocidades só da recolha própria** (a velocidade calculada do pacote STCP subestima 3–5 km/h e infla os troços críticos: 532 contra 293 de manhã; calibração 2026-11-13 não resolve); o pacote entra só em atrasos, pelotões, horários e oferta (`analise/agregar_stcp.py`, lê `C:\Users\quent\Dados\autocarros\stcp\`: posições `AAAA-MM-DD.csv` + `passagens_estimadas.csv`, `horarios_aplicados.csv`, `horarios_referencia.csv`). **Dia atípico:** `agregar.DIAS_ATIPICOS` (quarta 11 Nov: viagens −18 %, atraso −1,5 min, causa desconhecida) sai dos «dias úteis típicos» e tem o capítulo V; nunca afirmar a causa. Títulos e números do texto vêm dos dados (JS), não à mão. `autocarros.html` usa só a recolha própria (decisão 2026-11-14). **Corredores BUS (2026-11-14):** gráfico G13 em «Onde», troços com vs sem corredor (anel de distância aos Aliados e mesma rua); dados da CMP (CC0, dadosabertos.cm-porto.pt/dataset/corredores-bus) em `C:\Users\quent\Dados\autocarros\corredores_bus.geojson` (fora do repo; sem o ficheiro, a figura esconde-se). «Com» = ≥ 60 % do troço a ≤ 15 m de corredor activo; «sem» = nada a ≤ 30 m; não distingue sentido nem horário; não prova causa. **Propostas (2026-11-14, secção VI da Análise):** `analise/propostas.py` — zonas críticas robustas (< 14 km/h em ≥ 75 % dos dias, ≥ 2 linhas, ≥ 50 leituras, ≥ 300 m contínuos), tipo provável (trânsito de ponta / paragem / rotunda / semáforo / atraso fixo) e medida; **corredor BUS só se trânsito de ponta e OSM ≥ 2 faixas por sentido**; ganho com intervalo (alvo = velocidade dos troços com corredor no mesmo anel, limitada à velocidade entre pontas; leave-one-day-out); confiança «alta» só com ≥ 10 dias úteis. Semáforos CMP (CC0) em `Dados\autocarros\semaforos_cmp.geojson` (fora do repo). Texto sempre «hipóteses a validar»; nunca «o corredor X resolve»; não é proposta da CMP/STCP.

## 50 Espaços (`/50espacos/`)

Secção da campanha da Campo Aberto (111 espaços, 50 seleccionados). Regras completas, pipeline e fases: `docs/regras-50espacos.md`. Essenciais:

- Nunca editar `_espacos/**` à mão (gerado por `espacos_pipeline/gerar.py`).
- Só se publica texto com `revisto: true`; o utilizador revê antes.
- Sem dados pessoais: nada de nomes de pessoas singulares nem contactos; instituições sim. `docs/50espacos/dossiers/` é gitignored.
- Não existe ranking dos 50.

