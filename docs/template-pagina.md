# Template de página «folha» (Mobilidade, Artigos, Horrores e sucessos)

Todas as páginas de leitura e dados partilham o mesmo topo; mudar em `assets/css/folha.css` = mudar em todas.

## Anatomia
1. **Mesa** `#E6EDEB` + **barra** do site emoldurada (`moldura.js`, `data-menu="barra"`, `data-rodape="leitura"`).
2. **Folha** de filete (1,5 px + filete interior) com quadrícula A–H em cima e em baixo.
3. **Título** (fila 1, `.tit`): `h1` Plex Sans 700 34 px; **2.ª parte em `<em>`** = Plex Serif itálico 400, a verde (`--marca`); por baixo 1–2 frases 13,5 px; à direita (opcional) abas ou contagem.
4. **Conteúdo** em filas (`.fila` > `.p`), filetes de tinta, etiquetas mono, sem sombras nem cantos redondos.
5. **Rodapé** «leitura» (uma linha sob a folha).

## Como usar
- **Páginas Jekyll:** `folha: true` no front matter (o `default.html` põe `body.folha-pg` e liga `folha.css`) e
  `{% include folha-abre.html titulo="…" em="…" texto="…" lado=lado_ %}` … `{% include folha-fecha.html %}`
  (`lado_` = `{% capture lado_ %}…{% endcapture %}`, HTML opcional à direita). Exemplos: `artigos/index.html`, `casos/lista/index.html`.
- **Páginas geradas (Mobilidade):** marcação própria em `gerar_*.py`, mesmas classes (`.pg .folha .int .fila .p.tit`).
- **Mapa de Horrores e sucessos (`/casos/`):** não usa `folha.css` (colide com `estilo.css`); replica a folha em `.dos-*` de `mapa_unico/src/estilo.css`. Mudar o topo → mudar nos dois sítios.
- Cores de capítulo/dados nunca no cromo. Título sempre sem hífen em fim de linha (`hyphens:none`).
