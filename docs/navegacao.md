## Navegação entre páginas

- **Todas as páginas** têm o menu e o rodapé, desenhados por `assets/js/moldura.js` (única fonte; a raiz deduz-se do `src` do script). Mudar o menu = editar esse ficheiro.
- Cada página liga-o com `<script src="<raiz>/assets/js/moldura.js" data-pagina="<caminho>">` (geradores: `nav.get_nav(caminho, depth)`; Jekyll: `_layouts/default.html`). Opções `data-menu`, `data-rodape`, `data-fontes`: cabeçalho do JS.
- A página activa acende sozinha; abas e fontes por página: `ABAS`, `ALIAS`, `FONTES` no JS.

- **Mapas:** a nav tem uma só entrada «Mapas» (`mapa_unico/mapa_unico.html`); os 4 temas são separadores dentro da página.
  Ligações directas: `mapa_unico/mapa_unico.html#tema=<hoje|acessibilidade|historico|privado>`. As páginas antigas são redirects (`mapa_unico/gerar_stubs.py`).
