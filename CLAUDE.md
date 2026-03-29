# GEE Porto Green Space Project

## Idioma
- Toda a escrita é em **Português de Portugal** (PT-PT), com acentuação correcta e ortografia europeia.
- Nunca omitir acentos: é, á, ã, õ, ç, ê, ô, í, ú, etc.
- Usar vocabulário PT-PT (peão, autocarro, passadeira, etc.), não brasileiro.

## Credentials

- GEE project ID lives in `.env` (gitignored), loaded via `python-dotenv`
- **Never hardcode** the project ID or any credential as a string literal in code
- Always use `os.environ["GEE_PROJECT"]` after calling `load_dotenv()`
- Asset paths use f-strings: `f'projects/{GEE_PROJECT}/assets/...'`
- If you spot hardcoded secrets in existing code, flag it immediately

## Project structure

```
GEE/
├── _config.yml, _layouts/, _posts/, index.html   # Jekyll site
├── porto_publish.py        # Mapa actual (Sentinel-2 2016-2025) → mapa.html
├── ndvi_historico.py       # Mapa historico (1947-2024, Landsat) → ndvi_historico.html
├── interiores_quarteiroes.py  # Interiores de quarteirão → interiores_quarteiroes.html
├── porto_stats.py          # Estatisticas de uso do solo
├── test_area.py            # Calibracao (area teste Serralves)
├── 1947/                   # Classificacao ortofoto 1947
│   ├── orto_1947.py        # Pipeline de classificacao (tiles WMS + RF)
│   └── layers/             # Layers gerados (uso_1947_*.png)
├── animacao/               # Animacao crescimento urbano
│   ├── animacao_cairo.py   # Script principal → animacao_cairo.mp4
│   └── anim/               # Modulo Python (config, renderer, sdf_engine)
├── layers/                 # Layers do mapa actual (Sentinel-2)
├── layers_historico/       # Layers do mapa historico (Landsat)
├── atropelamentos/         # Dashboard sinistralidade rodoviária
│   ├── mapa_dashboard.py   # Script principal → dashboard_atropelamentos.html
│   ├── compilar_dados.py   # Compilação de CSVs/fontes → DB
│   ├── *.csv, *.json       # Dados (ANSR, INE, notícias)
│   └── *.xlsx, *.pdf       # Anexos originais ANSR
├── CLC/                    # Scripts Corine Land Cover (experimental)
├── docs/                   # Planos e specs (excluido do Jekyll)
└── archive/                # Scripts e HTMLs obsoletos
```

### Rules for keeping it clean

- **Each script generates o seu HTML** — nunca editar HTMLs à mão
- **Layers ficam na pasta do seu pipeline**: `layers/` (actual), `layers_historico/` (historico), `1947/layers/` (1947)
- **Ficheiros de teste/debug** nunca ficam nas pastas de layers — apagar depois de usar
- **Scripts obsoletos** vão para `archive/`, nunca apagar do git
- **`_config.yml` exclude** deve incluir: `*.py`, docs, archive, .claude, .superpowers
- **1947/** é uma pasta dedicada — todo o código e layers de 1947 ficam lá
- **atropelamentos/** é uma pasta dedicada — todo o código, dados e HTMLs de atropelamentos ficam lá, nunca na raiz
- **Cada sub-projecto tem a sua pasta** — nunca espalhar ficheiros de dados (csv, json, xlsx, pdf, db) pela raiz do repositório
- **Links no `index.html`** devem apontar para o caminho correcto dentro da pasta (ex: `atropelamentos/dashboard_atropelamentos.html`)
