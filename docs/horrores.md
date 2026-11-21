# Casos (Horrores e Sucessos) — regras do subprojecto

Mapa e galeria de casos conhecidos no Porto: destruição ou perda urbanística, patrimonial e de verde com contestação pública (galeria `horrores`); contraponto `sucessos` com o mesmo modelo. Desenho: `docs/superpowers/specs/2026-11-21-horrores-design.md`.

## Peças
- `_casos/<slug>.md` = **fonte única** (front matter = esquema; corpo = descrição). Só casos revistos; tudo o que está aqui é publicado.
- `casos_pipeline/` = modelo + validador (`python -m casos_pipeline.validar`); `mapa_unico.py` lê os mesmos ficheiros → `mapa_unico/dados/casos.js` (`--casos` regenera só isto).
- `_layouts/caso.html` + `casos/index.html` + `assets/css/casos.css` = páginas `/casos/` e `/casos/<slug>/` (URL neutra: serve as duas galerias).
- Tema `casos` do mapa único: `mapa_unico/src/tema_casos.js`; forma do marcador = tipo, cor = galeria, contorno tracejado = `aproximada`.
- Rascunhos: `docs/horrores/rascunhos/` (**gitignored**, repo público); promover = mover para `_casos/`.
- Texto lido de cada fonte: `Fontes\Horrores\<slug>\<n>.txt` (fora do repo); fotos: `Horrores/media/<slug>/` (JPEG ≤ 900 px).

## Regras
- Entrada: fonte documental de contestação (notícia, petição, acta, queixa, parecer) **ou** lista de património em risco / classificação alterada. Juízo editorial só se preciso, `criterio: editorial` (mostra «Avaliação do Porto Verde»).
- Cada `referencias[]` com `excerto` **literal** do texto guardado (validador); nunca citar de memória; Haiku nunca cita.
- Sem nomes de pessoas singulares; voz neutra; juízo atribuído à fonte («segundo …»); instituições só se constarem da fonte.
- Só dentro do Porto (CAOP, `dtmn` 1312); `freguesia` derivada, não escrita.
- Fotos «depois»/actuais com direitos reservados: **nunca copiar**; `fotos_ligadas: [{papel, ano, fonte, url}]` mostra só a ligação à página da fonte (decisão do utilizador, 2026-11-21). Fotos copiadas (`fotos:`) só com licença livre: crédito + `url` de origem + `sha256` por foto; revisão humana foto a foto; nunca fotos de utilizadores do Google Maps; Street View/Earth só como último recurso e com termos confirmados antes de guardar/republicar (senão, ligação externa).
- Antes/depois em par não é obrigatório; página mostra lado a lado (maquete A, aprovada 2026-11-21).
- Cobertura nunca «completa»: «casos conhecidos e documentados».
- Não fundir com os 50 Espaços (layout congelado).

## Fluxo
1. Candidatos (pesquisa online, agentes Sonnet) → rascunho + texto lido em `Fontes\Horrores\`; o utilizador escolhe.
2. Ficha + fotos → revisão do utilizador → mover para `_casos/`.
3. `python -m casos_pipeline.validar` → `python mapa_unico/mapa_unico.py` → testes (`casos_pipeline/tests`, `mapa_unico/tests`, `test_casos_site.py`) → commit.
4. Depois do deploy: abrir `/casos/`, `/casos/<slug>/` e `mapa_unico.html#tema=casos&caso=<slug>`.
