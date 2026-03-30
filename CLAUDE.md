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
- **`_config.yml` exclude** deve incluir: `*.py`, docs, .claude, .superpowers
- **Cada sub-projecto tem a sua pasta** — nunca espalhar ficheiros de dados pela raiz
- **Links no `index.html`** devem apontar para o caminho correcto dentro da pasta (ex: `atropelamentos/dashboard_atropelamentos.html`)

## Regras de código

- Python com `ee` (Earth Engine API) e `geemap` quando aplicável
- Grayscale: usar `np.mean(array[:,:,:3], axis=2)`, **nunca** `PIL .convert('L')`
- Pontos de treino: usar APENAS coordenadas fornecidas pelo utilizador, nunca gerar automaticamente
- Mapas e visualizações: cores fortes, basemaps visíveis, sem esbatidos
- Vídeo em MP4 (não GIF); texto renderizado via PIL (não cv2) para suportar acentos
- Proporções geográficas correctas são essenciais (cos(latitude) correction)
- `.db` é gerado por `compilar_dados.py` e gitignored — não commitar
