# Estrutura do projecto (detalhe)

```
(raiz do projecto)
├── _config.yml, _layouts/, _posts/, index.html, sobre.md   # Jekyll site (GitHub Pages)
├── nav.py, patch_nav.py    # Fonte única da nav + patcher (git pre-commit hook)
├── capture_cards.py        # Thumbnails dos cards do index (Playwright)
├── check_leaflet_init.py   # Validação Leaflet (pre-commit hook)
├── test_area.py            # Calibração (área teste Serralves)
├── mapa/                   # Mapa actual (Sentinel-2 2016-2025)
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
├── layers/                 # Layers do mapa actual (Sentinel-2)
├── layers_historico/       # Layers do mapa histórico (Landsat)
└── docs/                   # Planos e specs (excluído do Jekyll)
```
