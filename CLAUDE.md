# GEE Porto — Espaços Verdes e Uso do Solo

## Credenciais
- GEE project ID vive em `.env` (gitignored), carregado via `load_dotenv()` + `os.environ["GEE_PROJECT"]`
- Asset paths usam f-strings: `f'projects/{GEE_PROJECT}/assets/...'`

## Estrutura do projecto

```
GEE/
├── _config.yml, _layouts/, _posts/, index.html, sobre.md   # Jekyll site (GitHub Pages)
├── porto_publish.py        # Mapa actual (Sentinel-2 2016-2025) → mapa.html
├── ndvi_historico.py       # Mapa histórico (1947-2024, Landsat) → ndvi_historico.html
├── interiores_quarteiroes.py  # Verde Privado → interiores_quarteiroes.html
├── porto_stats.py          # Estatísticas de uso do solo
├── test_area.py            # Calibração (área teste Serralves)
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
├── layers/                 # Layers do mapa actual (Sentinel-2)
├── layers_historico/       # Layers do mapa histórico (Landsat)
└── docs/                   # Planos e specs (excluído do Jekyll)
```

## Navegação entre páginas

- **Todas as páginas HTML** (mapas, dashboards) devem ter a barra de navegação fixa no topo direito (`#nav`) com links para todas as outras páginas do site — **excepto o index**, que usa a nav do layout Jekyll.
- Os links devem ser relativos e ajustados à profundidade da pasta (`../` para subpastas).
- O link da página activa tem a classe `active`.
- Os scripts Python que geram HTML devem incluir esta nav no template.

## Regras de organização

- **Cada script gera o seu HTML** — nunca editar HTMLs à mão
- **Layers ficam na pasta do seu pipeline**: `layers/` (actual), `layers_historico/` (histórico), `1947/layers/` (1947)
- **Ficheiros de teste/debug** nunca ficam nas pastas de layers — apagar depois de usar
- **Scripts obsoletos** apagam-se directamente (git e disco sincronizados)
- **`_config.yml` exclude** deve incluir: `*.py`, docs, .claude, .superpowers, `__pycache__/`, `*.bak`, `*.npy`, `*.npz`
- **Cada sub-projecto tem a sua pasta** — nunca espalhar ficheiros de dados pela raiz
- **Links no `index.html`** devem apontar para o caminho correcto dentro da pasta (ex: `atropelamentos/dashboard_atropelamentos.html`)

## Camadas de verde — definições e dependências

O projecto usa **três camadas de verde mutuamente exclusivas**:

1. **Parques e jardins** (`parques_porto.geojson`): espaços verdes de acesso público gratuito. Polígonos obtidos preferencialmente do PDM (fruição colectiva) ou OSM. Fonte autoritativa.
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

O verde privado (`layers/interior_subsistente.png`) é calculado por `interiores_quarteiroes.py`:

1. **Classificação Sentinel-2** — base: `acessibilidade/layers/verde_total.png` (todos os pixels verdes)
2. **Subtrair parques e jardins** — camada `acessibilidade/parques_porto.geojson`
3. **Subtrair verde pago** — camada `acessibilidade/layers/verde_pago.png`
4. **Máscara de estradas** — OSM (buffer por tipo de via)
5. **Vectorização e filtragem** — área mínima e forma

**Para regenerar sem GEE**: apagar `layers/interior_subsistente.png` e `layers/interior_perdido.png`, depois correr `python interiores_quarteiroes.py`. A fase 1 re-descarrega do GEE (~30s); as fases 2-5 são locais.

**Alternativa rápida (sem GEE)**: usar `acessibilidade/layers/verde_total.png` como base, aplicar as máscaras de parques + verde pago + estradas localmente.

**Overpass API:**
- Pode dar timeout com muitos elementos — o script divide em lotes e tenta servidores alternativos
- Se falhar persistentemente, usar `adicionar_jardins.py` (OSM API v0.6, mais estável) para adicionar parques individualmente ao GeoJSON existente

## Validação
- Após alterar um script, verificar pelo menos que executa sem erros de sintaxe: `python -m py_compile <script>.py`
- Scripts GEE dependem de autenticação — se `ee.Initialize()` falhar, não é bug do código
- Mapas HTML gerados devem abrir no browser e mostrar layers correctamente

## Artigos (`_posts/`)

- **Espaçamento antes de títulos**: gerido pelo CSS em `_layouts/default.html` (`article h2 { margin-top: 2.5rem }`, `article h3 { margin-top: 2rem }`). **Não usar `&nbsp;`** — o espaçamento é automático.
- Formato: Markdown com acentuação PT-PT correcta
- Referências bibliográficas no final, ordenadas alfabeticamente

## Regras de código

- Python com `ee` (Earth Engine API) e `geemap` quando aplicável
- Grayscale: usar `np.mean(array[:,:,:3], axis=2)`, **nunca** `PIL .convert('L')`
- Pontos de treino: usar APENAS coordenadas fornecidas pelo utilizador, nunca gerar automaticamente
- Mapas e visualizações: cores fortes, basemaps visíveis, sem esbatidos
- Vídeo em MP4 (não GIF); texto renderizado via PIL (não cv2) para suportar acentos
- Proporções geográficas correctas são essenciais (cos(latitude) correction)
- `.db` é gerado por `compilar_dados.py` e gitignored — não commitar

## Higiene do repositório

- **`.gitignore` obrigatório** — deve conter: `__pycache__/`, `*.pyc`, `.claude/`, `.superpowers/`, `*.bak`, `.env`, `*.db`, `*.npy`, `*.npz`, `*.mp4`
- **`requirements.txt`** — manter actualizado ao adicionar dependências Python
- **Ficheiros binários grandes** (MP4, NPY, DB) são gitignored — nunca rastrear no Git
- **Scripts de uso único** — apagar após execução, não acumular no repo
- **Ficheiros `.bak`** — apagar do disco após confirmar que o original está no Git
