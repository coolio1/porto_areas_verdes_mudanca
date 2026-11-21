# Casos (Horrores e Sucessos) — regras do subprojecto

Mapa e galeria de casos conhecidos no Porto: destruição ou perda urbanística, patrimonial e de verde com contestação pública (galeria `horrores`); contraponto `sucessos` com o mesmo modelo. Desenho: `docs/superpowers/specs/2026-11-21-horrores-design.md`.

## Peças
- `_casos/<slug>.md` = **fonte única** (front matter = esquema; corpo = descrição). Só casos revistos; tudo o que está aqui é publicado.
- `casos_pipeline/` = modelo + validador (`python -m casos_pipeline.validar`); `mapa_unico.py` lê os mesmos ficheiros → `mapa_unico/dados/casos.js` (`--casos` regenera só isto).
- `_layouts/caso.html` + `casos/lista/index.html` + `assets/css/casos.css` = lista `/casos/lista/` e fichas `/casos/<slug>/` (URL neutra: serve as duas galerias).
- **`/casos/` = mapa autónomo «Horrores e sucessos»** (Positron por defeito), abas Mapa | Lista. `casos/index.html` é **gerado** por `mapa_unico.py` (mesmo `core.js`/template, só o tema `casos`, dados partilhados `mapa_unico/dados/casos.js` via `MU.URL_DADOS`); nunca editar à mão. O mapa único já não tem o tema; `mapa_unico.html#tema=casos` redirige para `/casos/`.
- **Design «Dossiê» (proposta B, escolhida 2026-11-21):** IBM Plex Serif nos títulos e texto, Plex Mono nas etiquetas, filetes duplos; ficha = díptico antes/depois, lead da contestação, ficha + linha do tempo (de `referencias[].data`) à direita, fontes em grelha (`_layouts/caso.html`, `assets/css/casos.css`); mapa `/casos/` = página que rola como a maquete B (cabeçalho de jornal, barra de números, mapa + índice/filtros, cartões «Para ler já»): modelo `mapa_unico/src/template_casos.html`, regras `.mu-dossie`/`.dos-*` em `estilo.css`, números e cartões em `tema_casos.js` (`_dossie`). Maquetes: artefacto «Horrores e sucessos — 3 propostas de design».
- Tema `casos`: `mapa_unico/src/tema_casos.js`; forma do marcador = tipo, cor = galeria, contorno tracejado = `aproximada`.
- Rascunhos: `docs/horrores/rascunhos/` (**gitignored**, repo público); promover = mover para `_casos/`.
- Texto lido de cada fonte: `Fontes\Horrores\<slug>\<n>.txt` (fora do repo); fotos: `Horrores/media/<slug>/` (JPEG ≤ 900 px).

## Regras
- Entrada: fonte documental de contestação (notícia, petição, acta, queixa, parecer) **ou** lista de património em risco / classificação alterada. Juízo editorial só se preciso, `criterio: editorial` (mostra «Avaliação do Porto Verde»).
- Cada `referencias[]` com `excerto` **literal** do texto guardado (validador); nunca citar de memória; Haiku nunca cita.
- Sem nomes de pessoas singulares; voz neutra; juízo atribuído à fonte («segundo …»); instituições só se constarem da fonte.
- Só dentro do Porto (CAOP, `dtmn` 1312); `freguesia` derivada, não escrita.
- **Fotos (decisão do utilizador, 2026-11-21, revoga o «nunca copiar»):** copiar a foto da página da fonte (imprensa, arquivo, Commons, Flickr CC) para `Horrores/media/<slug>/` (JPEG ≤ 900 px) e creditar sempre: `fotos: [{papel, ficheiro, ano, fonte (meio ou autor), url (página de origem), sha256}]`; revisão humana foto a foto. `fotos_ligadas` fica só para fotos que não se conseguem obter. Nunca fotos de utilizadores do Google Maps; Street View/Earth só com termos confirmados.
- Antes/depois em par não é obrigatório; página mostra lado a lado (maquete A, aprovada 2026-11-21).
- Cobertura nunca «completa»: «casos conhecidos e documentados».
- Não fundir com os 50 Espaços (layout congelado).

## Fluxo
1. Candidatos (pesquisa online, agentes Sonnet) → rascunho + texto lido em `Fontes\Horrores\`; o utilizador escolhe.
2. Ficha + fotos → revisão do utilizador → mover para `_casos/`.
3. `python -m casos_pipeline.validar` → `python mapa_unico/mapa_unico.py` → testes (`casos_pipeline/tests`, `mapa_unico/tests`, `test_casos_site.py`) → commit.
4. Depois do deploy: abrir `/casos/#tema=casos&caso=<slug>`, `/casos/lista/` e `/casos/<slug>/`.
