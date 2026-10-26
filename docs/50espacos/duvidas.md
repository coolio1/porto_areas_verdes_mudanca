# Dúvidas em aberto — 50 Espaços (fase 1, Porto)

Registadas em 2026-10-25 para pesquisa online no fim. Estado: `[ ]` por resolver.

## Factos nos textos
- [ ] Parque Oriental: área de concepção (85 ha vs 80 ha da descrição inicial) e se o parque está «completo» após a inauguração de 2019 (afirmação do Webnode, «parecem indicar»).
- [ ] Quinta da Bouça: propriedade (pública na descrição inicial, não pública segundo a Câmara em 2014).
- [ ] Hospital Conde de Ferreira, Cemitério Inglês, Pinheiros Mansos: fichas quase vazias; procurar descrição, propriedade e estatuto actual.
- [ ] Santo António, Quinta do Monte, Frades, Ribeira da Granja, Villa Monte Crasto: textos reescritos por engano por dois subagentes; conferir factos com fontes públicas.
- [ ] Estado actual (2026) de cada espaço: construído, ameaçado, classificado? Os textos param em 2014–2019.

## Imprensa
- [ ] 7 notícias com data incerta em `_data/imprensa.yml` (ver campo de nota).

## Layout
- [ ] Manter ou retirar as etiquetas «Seleccionado em Abril de 2009 / Entre os 50 desde depois de Abril de 2009» e a linha «Ficha de 2006: n.º …» em `_layouts/espaco.html`.

## Publicação
- [ ] Build Jekyll e verificação visual (375 px, tema claro) só possíveis no GitHub Pages; o repositório não está na `ALLOWED` do `guard-git-push.py`.
- [ ] `docs/fonte_campanha` (3 GB, gitignored) sincroniza com o OneDrive; excluir do sync fora do Claude Code.

## Resultados da pesquisa online (2026-10-25)
- **Parque Oriental**: documento da Câmara ([ambiente.cm-porto.pt](https://ambiente.cm-porto.pt/files/uploads/cms/parque-da-cidade-oriental.pdf)) dá 16 ha em duas áreas contínuas, 2.ª fase inaugurada em Outubro de 2019; [Nature-Based Solutions Porto](https://naturebasedsolutions.porto.pt/en/?p=3833) dá 16,7 ha (8,7 + 8). Um documento municipal de 2005 refere um corredor de 53 ha. Conclusão: o parque está concluído com ~16 ha, cerca de um quinto dos 85 ha (o texto diz «um quarto»). **Proposta: corrigir o parágrafo final.**
- **Quinta da Bouça**: sem fonte pública sobre propriedade; a pesquisa só devolve outras quintas homónimas (Gondomar, Lousada). Fica «incerta» no texto. Sugestão: pedir à Câmara (DMGA) ou consultar o PDM/cadastro.
- **Hospital Conde de Ferreira**: edifícios propriedade da Santa Casa da Misericórdia do Porto (manteve a propriedade após 1974); abriu em 1883 (Decreto-Lei 232/95 diz 1893, erro provável). Jardins amplos descritos em 1903. Estado actual da gestão não confirmado.
- **Cemitério Inglês (St James)**: único cemitério protestante do Norte, terreno comprado em 1787 pela British Factory, 4 talhões, ~1200 sepulturas, visita por marcação; sem classificação confirmada. Ver [St James Church](https://www.stjamesoporto.org/history.html) e [CWGC](https://www.cwgc.org/visit-us/find-cemeteries-memorials/cemetery-details/2086510/OPORTO%20(ST%20JAMES)%20BRITISH%20CHURCHYARD/).
- **Pinheiros Mansos**: o topónimo actual é Rua do Pinheiro Manso (Boavista); o pinheiro original caiu no ciclone de 1941. Zona hoje residencial/imobiliário de luxo; nada sobre o logradouro como espaço verde.
- Por pesquisar: estado actual dos outros espaços, datas da imprensa, 5 fichas reescritas por engano.

## Fase 2 — 88 espaços dos outros 8 concelhos (2026-10-25)
Todos os textos novos estão em `docs/50espacos/fusao/<concelho>/` com `revisto: false`: só aparecem no site depois de os rever e passar a `true`.
- [ ] **Revisão dos 88 textos** (Gaia 22, Maia 25, Gondomar 18, Matosinhos 7, Vila do Conde 6, Valongo 4, Espinho 4, Póvoa de Varzim 2). Os mais finos, por falta de fontes: Estrada da Circunvalação, Montes Caulinos, Zona rural do Monte Espinho, Margem do Douro (Medas e Melres).
- [ ] **Coordenadas**: Ribeira de Vila Cova (Valongo) vinha como `41,0,6`; assumi 41,06. Confirmar.
- [ ] **Castro de Ovil**: aquisição em 1985 (ficha) ou 1986 (Câmara); usei 1986.
- [ ] **Espaços sem página no Webnode**: um em Gondomar, um em Maia, um em Matosinhos e os dois da Póvoa de Varzim (só têm ficha e PDF).
- [ ] **Robinson / Parque Oriental**: o zip repete o id 1443 para dois espaços do Porto.
- [ ] **Áreas que não batem**: Tabãos 106 ha (ficha 2006) vs 78 ha (PDM); Margens do Leça 57 ha vs cerca de 90 ha propostos pela Câmara; Quinta do Mosteiro de Pedroso 53 ha vs 18 ha da propriedade.
- [ ] **Quinta do Soeime**: a ficha dizia RAN, a Câmara diz que nunca esteve; segui a Câmara.
- [ ] **Gaia**: o Arboreto da EB2 de Canelas já não existe (obras da Parque Escolar); texto no passado. Decidir se mantém ficha.
- [ ] **Media**: 119 MB para os 111 espaços (`50espacos/media/`); o repositório cresce. Avaliar se se reduz a resolução.
- [ ] **Bug corrigido**: `copiar_media` duplicava fotos (`-2`) ao voltar a correr; agora é idempotente (teste novo).
- [ ] **Zona verde circundante ao Rio Leça (Maia)**: sem coordenadas em nenhuma fonte; tem página mas não aparece no mapa. Indicar um ponto.
- [ ] **Publicação sem revisão (2026-10-26)**: os 88 textos foram publicados com `revisto: true` por indicação do utilizador, sem revisão prévia. Rever no ar.
