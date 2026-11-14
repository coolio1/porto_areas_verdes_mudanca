# GEE Porto — Espaços Verdes e Uso do Solo

## Credenciais
- **API keys** do `.env` global (`C:\Users\quent\OneDrive\Claude\.env`), carregado no topo de `GEE/server.py`; um `.env` local pode sobrepor.
- `GEE_PROJECT` no `.env` (local ou global), nunca hardcoded; asset paths em f-strings: `f'projects/{GEE_PROJECT}/assets/...'`.
- **`CARTO_BASEMAPS_KEY`** (`.env` local, gitignored): sem chave, os mosaicos CARTO saem com marca de água «API KEY REQUIRED». `carto.py` (`aplicar_chave`/`com_chave`) junta `?key=` aos URLs `basemaps.cartocdn.com`; **todo gerador de mapa (também os novos) chama `aplicar_chave(html)` antes de gravar**.

## Estrutura do projecto
Raiz = site Jekyll/GitHub Pages; detalhe em `docs/estrutura.md`.
- **`mapa_unico/` = página única dos mapas (4 temas em separadores); as páginas antigas abaixo são redirects (`mapa_unico/gerar_stubs.py`)**: `mapa/` (Sentinel-2 2016-2025), `ndvi_historico/` (Landsat 1947-2024), `interiores/` (verde privado), `1947/` (classificação ortofoto), `animacao/`, `atropelamentos/` (dashboard + DB), `acessibilidade/` (pipeline 2SFCA + conversão).
- `layers/`, `layers_historico/` — layers partilhados na raiz; `docs/` — planos e specs (fora do Jekyll).
- `assets/js/moldura.js` (menu, abas da Mobilidade e rodapé: única fonte), `nav.py` (atalho que devolve a etiqueta `<script>`), `assets/css/porto-verde.css`, `capture_cards.py`, `check_leaflet_init.py`.

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

## Validação
- Script alterado → no mínimo `python -m py_compile <script>.py`.
- Scripts GEE dependem de autenticação: `ee.Initialize()` a falhar não é bug do código.
- Mapas HTML gerados têm de abrir no browser e mostrar as layers.

## Cards do index e artigos (`_posts/`)
Thumbnails e criação de artigos: skill `porto-verde-posts`. Nunca editar `index.html` para juntar artigos (lista `site.posts` sozinho).

## Regras de código
- Grayscale: `np.mean(array[:,:,:3], axis=2)`, **nunca** `PIL .convert('L')`.
- Pontos de treino: SÓ coordenadas dadas pelo utilizador; nunca gerar.
- Mapas: cores fortes, basemaps visíveis; vídeo MP4 (não GIF); texto via PIL (não cv2) por causa dos acentos; proporções corrigidas com cos(latitude).
- `.db` é gerado por `compilar_dados.py` e gitignored — não commitar.

## Operações em dados geoespaciais
- **GeoJSON >50 linhas ou substituição de blocos:** NUNCA editar inline com Edit/Write → script Python descartável que lê a fonte, transforma e escreve; apagá-lo depois.
- **GEE:** só classificação raster (NDVI, uso do solo pixel-a-pixel). **Proibido gerar ou derivar polígonos de parques com GEE.**
- **Antes de juntar um polígono:** existe no PDM? Senão, OSM. Nunca inventar nem aproximar geometrias.

## Lições aprendidas
- **Verificar consumidores antes de alterar dados** — ao editar `parques_porto.geojson` ou outra fonte partilhada, grep por todos os que a referenciam e actualizar em cadeia.
- Lições técnicas antigas (OBIA 1947, Overpass): fim de `docs/estrutura.md`.
- **Nunca inventar referências** — verificar sempre online autores, anos e títulos antes de citar.
- **Estudos e fichas:** permalink das fichas `/50espacos/espacos/<concelho>/<slug>/`; documentos com ficha vão para `50espacos/media/<slug>/`, não para Estudos (comparar md5 antes de alojar). Descargas em lote: validar `%%EOF` no fim do PDF (cópias do Wayback truncam em múltiplos de 1 MiB; um limite de leitura próprio também trunca). O hook proíbe escrever em «Para arquivar»: preparar a pasta na scratchpad; o utilizador copia com `! cp -rn`. Pendentes: `docs/50espacos/estudos_por_descarregar.md`. Verificar o ciclo dos PGRH (as versões de 2011 são do 1.º ciclo, não do 2.º).
- **Fotos das fichas:** `50espacos/media/<slug>/creditos.json` (`{"01.jpg": {"fonte", "url"}}`) mostra o crédito sob a foto; fontes com outros direitos aceites se creditadas. Nunca fotos de utilizadores do Google Maps. Street View não serve para os espaços sem foto (Vessada, Taím, Monte Penedo, Frejufe: coordenadas com 2 casas decimais, o Google só tem o topónimo). Sem foto: o utilizador fornece-a.
- **Mapa único:** ao fundir páginas, medir a paridade contra o HTML **publicado**, não o gerador (divergem: o `interiores` publicado tem o «Subsistente» corrigido, 295 mil px; `layers/interior_subsistente.png` tem 450 mil); comparar PNG por alfa. O «mesmo» dado pode ter versões diferentes (1947: a página 1947 mostrava a classificação bruta, o Histórico a limpa por `clean_1947.py`) → verificar a origem antes de escolher. Testar em `file://` com Playwright (a extensão Chrome não abre `file://`). O hook bloqueia `sed -i` no OneDrive → Edit. Dados embutidos em `mapa_unico/dados/*.js`: `docs/estrutura.md`.
- **Moldura (menu, abas, rodapé):** só `assets/js/moldura.js` (lista de páginas, abas, `FONTES` por página); mudar lá muda todas as páginas, sem regenerar. Página nova: adicionar a etiqueta `<script src="<raiz>/assets/js/moldura.js" data-pagina="<caminho>">` (gerador: `nav.get_nav(caminho, depth)`); `test_moldura.py` guarda isto. Cores e tipografia: `porto-verde.css`.
- **Identidade visual (2026-11-14):** tokens e tipografia em `assets/css/porto-verde.css` (Literata nos títulos de texto, Schibsted nos rótulos; verde do logo, ouro só no logo; sem laranja nem azul de interface). Páginas de texto: escala única da secção «Leitura» do CSS, nada de h1/h2/h3 próprios por página. **Os 50 Espaços (`50espacos.css`) ficam como estão, a pedido do utilizador.** Camadas dos mapas (paleta C): parques `#0B5232`, verde pago `#D9642B`, verde privado `#D6C496` (geradores `acessibilidade_html.py`/`conversao_html.py` e `tema_acessibilidade.js`; mudar = regenerar PNG coloridos e `mapa_unico.py`).
- **Artigos com textos enviados a entidades (caso Aurifícia):** nunca publicar o original nem dados pessoais/referências de notificações; `docs/artigos-textos-entidades.md`.

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

## Fluxo rápido de regeneração
`acessibilidade/regenerar_html.py` e `regenerar_conversao_html.py` regeneram os HTML em ~2 s a partir dos PNGs em cache; detalhe em `docs/fluxo-rapido-regeneracao.md`.

**Dados inline, nunca `fetch()`:** GeoJSON embutidos nos HTML gerados (`fetch()` falha em `file://`, onde os mapas se abrem). Fonte partilhada alterada → regenerar todos os HTML que a consomem.

## Chat «Perguntar» (apagado)
Página `chat/`, código do Worker e infra-estrutura na Cloudflare (Worker, AI Search, Turnstile) apagados; já não há `chat/` neste repo. Registo e motivo: `Fontes\Habitacao\CLAUDE.md`. Não voltar a propor um chat sem decisão do utilizador.

## Mobilidade — velocidade dos autocarros (`Mobilidade/`)
Menu só com «Mobilidade»; separadores Autocarros | Análise | Atropelamentos (`nav.get_abas_mobilidade()`, barra sob o menu; a página dos atropelamentos e a Análise acendem «Mobilidade» por alias em `nav.py`); pastas e URLs não mudaram. **O `dashboard_atropelamentos.html` publicado diverge do gerador `mapa_dashboard.py`** (CSS de telemóvel e gráficos editados à mão; separadores só no HTML): não o regenerar sem comparar. Spec e plano: `docs/superpowers/specs|plans/2026-11-11-mapa-velocidades-autocarros*`.

**Autocarros (`Mobilidade/autocarros.html`)**
- **Gera:** `uv run --no-project --with-requirements Mobilidade/requirements.txt python Mobilidade/gerar_autocarros.py` (≈ 2,5 min). Lê os CSV da recolha em `C:\Users\quent\Dados\autocarros\` (fora do OneDrive; descarregar do VPS com `descarregar_recolha.py <IP>`, memória `reference_vps_recolha_autocarros`) e rotas/paragens STCP do OSM (cache em `Dados\autocarros\osm\`). Mais dados → basta voltar a gerar; push é do utilizador (repo público). Escrita directa em `Mobilidade/` falha → `--saida` para a scratchpad e `cp`.
- `autocarros.html` usa só a recolha própria.
- **Método:** leituras coladas aos troços (~200 m) da própria linha (OSM, ≤ 30 m, direcção); média por (troço, sentido, período, dia útil/fim-de-semana) com mínimo 20 leituras, 3 veículos, 2 dias; crítico = < 14 km/h; tamanho = minutos perdidos por hora face a 25 km/h.
- **Esperas descontadas:** ≤ 2 km/h a < 40 m de paragem (salvo se os outros autocarros ali também andam < 8 km/h); paradas ≥ 15 leituras seguidas; **paragens ≥ 5 min (25 m) a < 100 m do início ou fim de uma viagem** (`marcar_paradas_em_terminal`; as 15 leituras ≈ 15 min deixavam escapar 26 %). **Os zeros do trânsito contam sempre.** No modo «Agora» e no habitual: ≤ 2 km/h a < 100 m de um terminal (`habitual.terminais`: células de 80 m com ≥ 10 pontas de viagem, embutidas no HTML); raio 60–250 m dá o mesmo.
- **No git:** só `gerar_autocarros.py`, `velocidade/`, `tests/`, `requirements.txt`, `autocarros.html` (`.gitignore` `Mobilidade/*` + excepções). **Fora:** `recolher_autocarros.py`, `verificar_recolha.py`, `descarregar_recolha.py`, `deploy/` e dados brutos (IP do VPS e posições nunca no repo). Só se publicam agregados por troço, sem identificadores de veículo.
- Fim-de-semana desactivado até haver 2 dias (a partir de 16 de Novembro).
- **Modo «Agora»:** 4.º botão do seletor «Mostrar» (não é página nem separador). Esconde dia/período, mapa escuro, feed da Porto Digital (CORS aberto, `speed` em m/s) a cada 20 s. Cada autocarro cola-se (≤ 30 m, sentido) a um troço de `D.trocos`; as partículas correm por essas ruas, passando ao troço ligado no fim (sem inversão de marcha), só com autocarros do mesmo sentido (a média de vectores anulava os dois sentidos); um ponto por autocarro, da cor do rasto (pane `pontosAgora`, sobre o canvas). Sem rua → fora do desenho, não das estatísticas. Mostrador: média da rede, % parados, 5 linhas mais lentas, contra o habitual por hora (`velocidade/habitual.py`: dias úteis anteriores a hoje, esperas descontadas pela mesma regra simples nas duas séries; vai no HTML com as paragens, ~110 KB). Gera-se com o resto (`gerar_autocarros.py`). Nada ao vivo é gravado; o único `fetch()` da página é o do feed. Limite: fila parada num terminal a > 40 m de uma paragem OSM pode aparecer como «linha lenta». O pacote `STCP-dados-e-codebook` (GPS sem velocidade, só pontas) não entra no habitual.
- Lição: «adicionar um» sem mais contexto, numa página com selectores = mais um item do selector; ler a página antes de propor a forma.

**Página «Análise» (`Mobilidade/analise.html`)**: 12 gráficos D3 em 5 capítulos (Quando, Onde, Linhas, Horário, Excepção) + secção VI. Gera: `uv run --no-project --with-requirements Mobilidade/requirements.txt python -X utf8 Mobilidade/gerar_analise.py` (≈ 5 min; `--guardar-json` / `--json` guardam e reutilizam os agregados para afinar só a página).
- **Velocidades só da recolha própria:** a do pacote STCP subestima 3–5 km/h e infla os troços críticos (532 vs 293 de manhã); a calibração não resolve. O pacote só entra em atrasos, pelotões, horários e oferta (`analise/agregar_stcp.py`, lê `C:\Users\quent\Dados\autocarros\stcp\`: posições `AAAA-MM-DD.csv` + `passagens_estimadas.csv`, `horarios_aplicados.csv`, `horarios_referencia.csv`).
- **Dia atípico:** `agregar.DIAS_ATIPICOS` (quarta 11 Nov: viagens −18 %, atraso −1,5 min, causa desconhecida) sai dos «dias úteis típicos» e tem o capítulo V; nunca afirmar a causa.
- Títulos e números do texto vêm dos dados (JS), nunca à mão.
- **Corredores BUS:** gráfico G13 em «Onde», troços com vs sem corredor (anel de distância aos Aliados e mesma rua); dados CMP (CC0, dadosabertos.cm-porto.pt/dataset/corredores-bus) em `C:\Users\quent\Dados\autocarros\corredores_bus.geojson` (fora do repo; sem ele a figura esconde-se). «Com» = ≥ 60 % do troço a ≤ 15 m de corredor activo; «sem» = nada a ≤ 30 m; não distingue sentido nem horário; não prova causa.
- **Propostas (secção VI):** `analise/propostas.py` — zonas críticas robustas (< 14 km/h em ≥ 75 % dos dias, ≥ 2 linhas, ≥ 50 leituras, ≥ 300 m contínuos), tipo provável (trânsito de ponta / paragem / rotunda / semáforo / atraso fixo) e medida; **corredor BUS só se trânsito de ponta e OSM ≥ 2 faixas por sentido**; ganho com intervalo (alvo = velocidade dos troços com corredor no mesmo anel, limitada à velocidade entre pontas; leave-one-day-out); confiança «alta» só com ≥ 10 dias úteis. Semáforos CMP (CC0) em `Dados\autocarros\semaforos_cmp.geojson` (fora do repo). Texto sempre «hipóteses a validar»; nunca «o corredor X resolve»; não é proposta da CMP/STCP.

## 50 Espaços (`/50espacos/`)
Campanha da Campo Aberto (111 espaços, 50 seleccionados). Regras completas, pipeline e fases: `docs/regras-50espacos.md`. Essenciais:
- Nunca editar `_espacos/**` à mão (gerado por `espacos_pipeline/gerar.py`).
- Só se publica texto com `revisto: true`; o utilizador revê antes.
- Sem dados pessoais: nenhum nome de pessoa singular nem contacto; instituições sim. `docs/50espacos/dossiers/` é gitignored.
- Não existe ranking dos 50.
