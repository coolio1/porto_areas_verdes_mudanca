# Estrutura do projecto (detalhe)

```
(raiz do projecto)
├── _config.yml, _layouts/, _posts/, index.html, sobre.md   # Jekyll site (GitHub Pages)
├── assets/js/moldura.js    # Fonte única do menu, abas e rodapé (desenhados no browser)
├── nav.py                  # Atalho: get_nav() devolve a etiqueta <script> da moldura
├── check_leaflet_init.py   # Validação Leaflet (pre-commit hook)
├── test_area.py            # Calibração (área teste Serralves)
├── mapa_unico/             # PÁGINA ÚNICA dos mapas (5 temas em separadores) — ver «Mapa único» abaixo
├── regra_303030/           # Regra 3-30-300: pipeline LiDAR/OSM/GHS-POP → máscaras (`layers/`) do tema `regra`; números em `docs/regra_303030_numeros.md`; ver CLAUDE.md
├── mapa/                   # Mapa actual (Sentinel-2 2016-2025); o .html é agora um redirect

│   ├── porto_publish.py    # Pipeline → mapa.html
│   ├── porto_stats.py      # Estatísticas de uso do solo
│   └── mapa.html
├── ndvi_historico/         # Mapa histórico (1947-2024, Landsat)
│   ├── ndvi_historico.py       # Pipeline → ndvi_historico.html
│   ├── ndvi_historico_html.py  # Módulo HTML (build_html)
│   └── ndvi_historico.html
├── interiores/             # Verde Privado
│   ├── interiores_quarteiroes.py  # Pipeline → interiores_quarteiroes.html
│   ├── interiores_html.py         # Módulo HTML (build_html)
│   └── interiores_quarteiroes.html
├── 1947/                   # Classificação ortofoto 1947
│   ├── orto_1947.py        # Pipeline de classificação (tiles WMS + RF)
│   ├── clean_1947.py       # Limpeza/pós-processamento do mosaico
│   └── layers/             # Layers gerados (uso_1947_*.png)
├── animacao/               # Animação crescimento urbano
│   ├── animacao_cairo.py   # Script principal → animacao_cairo.mp4
│   ├── animacao_edificado.py  # Versão anterior da animação
│   ├── export_porto_mask.py   # Exportação da máscara do município
│   ├── frame_1947.py       # Frame estático de 1947
│   └── anim/               # Módulo Python (config, renderer, sdf_engine, data_prep)
├── atropelamentos/         # Dashboard sinistralidade rodoviária
│   ├── mapa_dashboard.py   # Script principal → dashboard_atropelamentos.html
│   ├── compilar_dados.py   # Compilação de CSVs/fontes → DB (atropelamentos_grande_porto.db)
│   ├── schema.sql          # Schema da base de dados
│   ├── *.csv, *.json       # Dados (ANSR, INE, notícias)
│   └── *.xlsx, *.pdf       # Anexos originais ANSR
├── acessibilidade/         # Acessibilidade a verde público
│   ├── acessibilidade_verde.py   # Pipeline principal → acessibilidade_verde.html
│   ├── acessibilidade_html.py    # Módulo HTML (build_html)
│   ├── acessibilidade_gee.py     # Funções GEE partilhadas (Sentinel-2, download)
│   ├── analise_conversao_verde.py  # Candidatos a conversão → conversao_verde.html
│   ├── conversao_html.py         # Módulo HTML da conversão (build_html)
│   └── layers/                   # Layers em cache (PNGs, .npy, .npz)
├── Mobilidade/             # Velocidade dos autocarros STCP (só gerador, testes e página no git)
│   ├── gerar_autocarros.py # Gerador → autocarros.html (`--dados`, `--saida`)
│   ├── velocidade/         # Módulos: dados, esperas, osm, linhas, trocos, pagina, template.html
│   └── tests/              # pytest (sintético; `uv run --with-requirements Mobilidade/requirements.txt`)
├── layers/                 # Layers do mapa actual (Sentinel-2)
├── layers_historico/       # Layers do mapa histórico (Landsat)
└── docs/                   # Planos e specs (excluído do Jekyll)
```

- **OBIA abandonada para 1947** — classificação pixel com Random Forest e texturas locais funciona melhor que OBIA para o ortofoto P&B (resolução insuficiente para segmentação).

- **Overpass API instável** — dividir queries grandes em lotes e usar servidores alternativos; para adições individuais, preferir OSM API v0.6.


## Mapa único (`mapa_unico/`)

Uma só página, `mapa_unico/mapa_unico.html`, com 5 temas (o 2.º, `#tema=regra`, é a Regra 3-30-300: máscaras de `regra_303030/layers/` embutidas por `dados_regra()`): `#tema=hoje` (Mapa 2016-2025), `#tema=acessibilidade`
(+ `&vista=propostas`), `#tema=historico` (+ `&vista=1947` abre com a ortofoto), `#tema=privado`.

- `mapa_unico.py` gera o HTML (nunca editar à mão) e `dados/<tema>.js` (imagens base64 e GeoJSON, carregados só ao
  abrir o separador). `--html` regenera só o HTML. Os dados do Histórico demoram ~1 min (máscaras de 1947 a 1 bit).
- `src/`: `core.js` (núcleo: fundos, contexto comum, hash, temas), `tema_<id>.js` (um por tema, regista-se com
  `MU.registarTema`), `estilo.css`, `template.html`. Novo tema = novo `tema_<id>.js` + entrada em `TEMAS` e dados em `mapa_unico.py`.
- `cobertura_1979.py`: converte o shapefile Land cover 1979 (Filipa Guilherme; pasta no `.gitignore`, só o GeoJSON
  convertido entra no repositório) para GeoJSON simplificado (8 m) e máscaras raster.
- `gerar_stubs.py` escreve nas páginas antigas (`mapa/mapa.html`, `acessibilidade/*.html`, `ndvi_historico/*.html`,
  `1947/orto_1947.html`, `interiores/*.html`) redirecções para o tema certo. Os geradores antigos escrevem nesses
  ficheiros: se algum for corrido, correr `gerar_stubs.py` a seguir.
- A página 1947 mostrava a classificação em bruto; o Histórico usa a **limpa** (`1947/clean_1947.py`).
- **Histórico (2026-11-11):** linha do tempo 2023-24 → 1947 (uma época de cada vez, vegetação + edificado), cortina
  para comparar duas épocas, minigráfico de percentagens por época, perda/ganho como vista, 1979 com 2 classes
  (e botão para as 5). **Sem NDVI no mapa único** (`ndvi_historico/` e `layers_historico/ndvi_*.png` ficam).
  `historico_numeros.py` calcula as percentagens (denominador = concelho, `porto_mask.png`; 1947 reamostrada para
  a sua grelha) e `dados_historico()` grava-as em `numeros`. Testes: `mapa_unico/tests/` (pytest + `pw_historico.py`,
  Playwright com Edge em `file://`). Desenho e plano: `docs/superpowers/specs|plans/2026-11-11-historico-linha-do-tempo*`.
- **Água (2026-11-15):** o oceano vem de `layers_historico/rio.png`; o Douro e outras massas de água, de `layers/agua_osm.png`, gerada por `mapa_unico/agua_osm.py` (OSM via Overpass; se a gravação directa falhar, `AGUA_SAIDA=<scratchpad>` e `cp`). `dados_contexto()` junta as duas. A «placa» do fundo Carta vive em `placaPane` (z 205): o SVG do Leaflet tem z-index 200 e tapava a imagem da água na `cartaPane`.
- Os PNG do tema Privado vêm de `layers/` (`interior_subsistente_corrigido.png` = versão corrigida; a da
  Acessibilidade, «todas as áreas», é `layers/interior_subsistente_colored.png`).
- Ficheiros `layers/` e `acessibilidade/layers/` continuam a ser a fonte dos PNG; o mapa único não os lê em
  tempo de execução (tudo embutido em `dados/`), por isso `file://` funciona.
- **Desenho «Carta» (maquete V2b, 2026-11-15):** ordem dos temas Acessibilidade (abre por omissão) → Mudanças →
  Histórico → Privado, em separadores fixos no topo do painel (só o corpo do tema faz scroll; 2026-11-17: o acordeão
  escondia os outros temas abaixo da dobra no Surface Pro); opacidade atrás de um botão por linha; o fundo do mapa
  é um seletor sobre o mapa (`#fundo-select`, ao lado de «Ir para um parque»); barra do site (`nav.get_nav(..., menu="barra")`) e rodapé da
  `moldura.js`. Fundo por omissão «Carta» (sem mosaicos): placa de papel, água (`layers_historico/rio.png`, só o
  oceano; o Douro não tem máscara no repositório) e véu sobre os concelhos vizinhos; tracejado fora da área de
  estudo, quadrícula, esquadria, norte, escala e rótulos (parques + 14 lugares com coordenadas fixas) num canvas
  (`core.js`, `MU.desenharCarta`).
- **Ordem das camadas (2026-11-17):** topo da lista do painel = topo do mapa, com nível fixo por camada (`z` nas
  defs de `MU.addCamadas`, `MU.pane`), nunca pela ordem em que se ligam (Leaflet empilha por ordem de adição no
  mesmo pane). Limites: Parques 540, candidatos 550; camadas dos temas entre 410 e 480. Camada nova → pôr o `z` e a
  linha na posição certa da lista.
- **Números-chave (2026-11-18):** o bloco `.nums` de cada tema sai do painel (que fica para a legenda) para o cartão `#nums-card`
  sobre o mapa (em baixo à esquerda, por cima da escala), com X; fechado = botão «Números» (`#nums-chip`); a escolha fica em
  `localStorage` (`pv-nums-fechado`) e em ecrã ≤760 px abre fechado. `core.js`: `MU.moverNums/mostrarNums/fecharNums`; o bloco é
  movido, não copiado (os temas continuam a actualizá-lo por id). Tema novo com números = `<div class="nums">` no painel e nada mais.
  **Artigo do site:** campo opcional `artigo: {url}` na definição do tema (`tema_<id>.js`) acrescenta «Ler o artigo →» no fundo do
  cartão; sem o campo, sem ligação. **Texto curto (2026-11-18):** `.desc` = 1 frase; legenda de cada número ≤ 6 palavras, sem repetir
  a unidade nem o período; detalhe de método vai para a nota «Como se mediu», não para o topo do painel. Hoje: Acessibilidade → 2SFCA; Mudanças e Histórico → dinâmicas 1947–2025; 3-30-300 e Privado
  ainda sem artigo (quando o artigo for publicado, pôr o campo e o `/posts/<slug>/`).
- `dados/contexto.js` tem o comum a todos os temas: limites, GHS-POP, parques (GeoJSON), verde pago, água, véu e
  `stats` (hectares por contagem de píxeis × 56,87 m² dentro de `acessibilidade/layers/porto_mask.npy`; barras
  das camadas; o bloco fixo «Os três verdes» foi removido em 2026-11-17).
- **`RECOLOR_ACC`** (`mapa_unico.py`): as categorias da acessibilidade (vermelho/âmbar/verde) são recoloridas para
  a paleta V2b (`#A23B86`/`#E6A6CC`/`#3E6AB3`) só ao embutir; os PNG de `acessibilidade/layers/` ficam iguais. Cor
  desconhecida = erro (assert). As cores fixas dos três verdes não mudam.
