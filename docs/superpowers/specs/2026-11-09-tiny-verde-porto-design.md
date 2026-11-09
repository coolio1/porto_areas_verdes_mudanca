# Tiny Verde Porto — mapa isométrico em pixel-art do verde do Porto

*Estado: rascunho para revisão do utilizador (2026-11-09). Nada foi construído.*

## Resultado dos testes (2026-11-09) — parado

Quatro testes descartáveis (v2 a v5) com ortofoto 25 cm, infravermelho para a vegetação, máscaras das 3 categorias, edifícios OSM e árvores desenhadas, mais um teste com IA (`google/gemini-3.1-flash-image`, 0,068 US$, imagem para imagem). **Nenhum chega ao aspecto do tiny.london.** O procedural dá uma maquete cartográfica (foto estilizada, bolas por copas, contornos grosseiros: as máscaras têm ~7 m/px). A IA genérica quase não repinta e **inventa** (legendas com erros, figuras), o que o projecto proíbe. O tiny.london depende de um modelo treinado com pares «vista 3D ↔ pixel-art» (dados da Google, não utilizáveis aqui) e de GPU. Utilizador: «muito fraco». Sem aprovação da especificação; gerador por construir. Dados obtidos ficam em `%LOCALAPPDATA%\PortoVerdeTiny\` (ortofoto RGB e infravermelho) e `tiny/dados/`. Erro encontrado: `verde_pago.png` tem a forma no alfa (RGB preto), ler pelo alfa.

## Intenção

Um mapa isométrico em pixel-art do município do Porto, no espírito de [tiny.london](https://tiny.london/) (Boris Starkov, Outubro 2026, assente no isometric.nyc de Andy Coenen), em que **o verde é a estrela** e a cidade construída é contexto discreto. O utilizador quer o verde «bonito, como uma foto aérea em pixel-art». O mapa mostra as três categorias de verde do projecto, bem distintas à vista.

## Objectivos

- Vista isométrica (câmara a 45° de inclinação e 15° de rotação, como o isometric.nyc, para ficar parecido) do município do Porto inteiro.
- Os pisos de verde têm **textura real** da ortofoto, reduzida a pixel-art por um processo determinístico (poucas cores, contornos, sombra suave).
- A categoria do verde vem sempre das camadas do projecto, nunca da imagem: **parques e jardins públicos** (`parques_porto.geojson`), **verde pago ou não usufruível** (`verde_pago.png`) e **verde privado, versão limpa** (`interior_subsistente_corrigido.png`). Hierarquia: parques > verde pago > verde privado.
- Edifícios do OSM extrudidos, em cinzento-papel discreto, para o verde se destacar.
- Navegação por zoom e arrasto, em mosaicos (formato Deep Zoom, visualizador OpenSeadragon), a abrir em `file://` e no GitHub Pages.

## Não-objectivos

- Versão com IA para o aspecto «pintado» (ficou para depois, só com a licença das imagens resolvida).
- Nuvens, pesquisa de moradas, camadas de freguesias ou bairros.
- Dados novos de altura de edifícios além do que o OSM tiver.

## Anti-objectivos (seria falha mesmo que funcione)

- **Inventar** objectos ou geometrias. O tiny.london mostra que um modelo de IA desenhou monumentos que não existiam; aqui nada é desenhado por IA.
- Usar imagens do Google (Maps, Earth, Photorealistic 3D Tiles): as políticas da Map Tiles API proíbem guardar, pré-carregar e derivar o conteúdo. **Não se extraem nem por scraping nem pelo browser.**
- Derivar polígonos de parques de imagem (regra do projecto: só PDM ou OSM).
- Perder a fidelidade da categoria: cor da categoria nunca depende do que a imagem «parece».

## Restrições

- **Imagem base:** ortofoto da DGT, 25 cm, 2025, RGB+NIR, licença **CC BY 4.0** ([dados.gov.pt](https://dados.gov.pt/en/datasets/6a445f94aa49a7655e288cb7/)). Obriga a atribuição à DGT no mapa. Recursos oficiais: serviço WMS `geo.dgterritorio.gov.pt/wms/ortos2025` e catálogo `cdd.dgterritorio.gov.pt`.
- **Ortofoto obtida (2026-11-09):** `tiny/obter_ortofoto.py` descarregou por WMS (camada `Ortos2025-RGB`, JPEG, EPSG:3763, máx. 4000 × 4000 px por pedido) 72 células de 1 km × 1 km a **0,25 m/px**, 269 MB, para `%LOCALAPPDATA%\PortoVerdeTiny\ortofoto\` (fora do OneDrive), caixa -47000,163000 .. -35000,169000. Existe também a camada `Ortos2025-IRG` (falsa cor com infravermelho), útil para separar vegetação. O Python não consegue ligar ao servidor (SSL EOF); o `curl.exe` do Windows sim.
- **Edifícios:** OSM (ODbL, atribuição). **Obtidos em 2026-11-09** por `tiny/obter_edificios.py` para `tiny/dados/edificios_osm.json` (gitignored, 27 MB): 43 588 edifícios do município (43 420 ways e 168 relações com pátio, todas com geometria). Só 293 têm `height` e 8 516 têm `building:levels`, por isso a maioria precisa de altura por omissão.
- **Autoridade dos dados (decisão do utilizador, 2026-11-09):** quando o OSM e a ortofoto discordarem (edifício que existe numa e não na outra, contorno diferente), **o OSM ganha**. A ortofoto só dá textura aos pisos; nunca decide geometria nem categoria. Discrepâncias ficam registadas para correcção no OSM, não "emendadas" no mapa.
- **Regras do projecto:** cada script gera o seu HTML; dados embutidos, nunca `fetch()` (abre em `file://`); `aplicar_chave(html)` antes de gravar qualquer HTML com mosaicos CARTO (se houver); entrada no menu só por `nav.py`; pasta própria `tiny/`; ficheiros grandes (ortofoto, mosaicos intermédios) fora do OneDrive ou no `.gitignore`.
- **Resolução (decisão do utilizador, 2026-11-09):** qualidade à tiny.london, que usa 0,293 m/px (casa de 5 m = 17 px). Usa-se a resolução nativa da ortofoto, **0,25 m/px** (casa de 5 m = 20 px); a caixa do município tem 46 221 × 20 442 px (cerca de 945 Mpx, 1/30 do mapa de Londres). Substitui o palpite inicial de 1 m/px. Sem IA, não precisa de GPU: processa-se em blocos no CPU.
- **Alturas (decisão do utilizador, 2026-11-09):** LiDAR da DGT (MDS menos MDT, 50 cm, aquisição de Abril 2024 a Março 2025, dados abertos sem restrições, atribuição à DGT), que dá também a altura das copas das árvores. **Cobertura do Porto por confirmar:** o índice de folhas da DGT (`LiDAR2024_2025_Seccionamento`, ficheiro de Julho de 2025, folhas de 1 km) marca as 107 folhas que tocam o Porto como lote 1 e `DISPONIVEL = nao` (no lote 1, 8 803 de 22 807 folhas ainda não estavam disponíveis; os lotes 2 a 4 estavam todos disponíveis). Pode estar desactualizado: a DGT anunciou depois cobertura total. Por verificar na versão actual do catálogo (`cdd.dgterritorio.gov.pt`, produtos MDT 50 cm, MDT 2 m e MDS 50 cm). Plano B: GlobalBuildingAtlas (estimado, erro ~3,5 m, CC BY-NC). Ordem de prioridade por edifício: `height` do OSM, depois LiDAR dentro do contorno OSM, depois `building:levels` × 3 m, depois valor por omissão.

## Decisões do utilizador (como as tomou)

1. Abordagem: isométrico **procedural**, sem IA.
2. Contexto: **edifícios discretos** (não só manchas de verde).
3. Imagem base: **ortofoto pública** (a pedido inicial: Google; recusado por licença).
4. Pendentes que deixou como «deixar como está»: alterações de outras sessões em `~/.claude` e `AI Habitacao`.

## Palpites do desenhador (a rever)

- Python projecta tudo na vista isométrica e pinta; depois corta em mosaicos Deep Zoom.
- Redução a pixel-art: quantização de cores com paleta fixa, contorno fino nas fronteiras de categoria, sombra por direcção de luz.
- Árvores minúsculas desenhadas só se a textura real não chegar.
- Altura dos edifícios: `height` ou `building:levels` do OSM, com valor por omissão por tipo quando faltar.

## Fica para quem constrói

- Escolher a técnica de rasterização (numpy/PIL, ou outra) e o esquema de mosaicos.
- Escolher a paleta e o equilíbrio entre textura da foto e cor da categoria.
- Decidir a resolução final pelo resultado visual.
- Organização do código em `tiny/`, testes mínimos e HTML autónomo.

## Verificação (critérios de «feito»)

- Em `file://`, o mapa abre, faz zoom e mostra as 3 categorias distinguíveis.
- Contagem de pixéis por categoria na imagem final bate com as máscaras de origem (paridade por alfa, como no mapa único).
- Nenhum pixel de verde público fora de `parques_porto.geojson`.
- Atribuições visíveis: DGT (CC BY 4.0) e OpenStreetMap.
