## Navegação entre páginas

- **Todas as páginas HTML** (mapas, dashboards) devem ter a barra de navegação fixa no topo direito (`#nav`) com links para todas as outras páginas do site — **excepto o index**, que usa a nav do layout Jekyll.
- Os links devem ser relativos e ajustados à profundidade da pasta (`../` para subpastas).
- O link da página activa tem a classe `active`.
- Os scripts Python que geram HTML devem incluir esta nav no template.
