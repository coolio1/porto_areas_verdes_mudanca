# Tiny Verde Porto — mapa isométrico em pixel-art do verde do Porto

*Estado: rascunho para revisão do utilizador (2026-11-09). Nada foi construído.*

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
- **Estado do acesso (2026-11-09):** o WMS cortou a ligação (SSL EOF) em duas tentativas a partir de scripts neste PC; ficheiros, tamanhos, nomes de camadas e limite por pedido por confirmar. Se só houver descarga manual, os ficheiros têm 8 × 5 km.
- **Edifícios:** OSM (ODbL, atribuição). **Obtidos em 2026-11-09** por `tiny/obter_edificios.py` para `tiny/dados/edificios_osm.json` (gitignored, 27 MB): 43 588 edifícios do município (43 420 ways e 168 relações com pátio, todas com geometria). Só 293 têm `height` e 8 516 têm `building:levels`, por isso a maioria precisa de altura por omissão.
- **Autoridade dos dados (decisão do utilizador, 2026-11-09):** quando o OSM e a ortofoto discordarem (edifício que existe numa e não na outra, contorno diferente), **o OSM ganha**. A ortofoto só dá textura aos pisos; nunca decide geometria nem categoria. Discrepâncias ficam registadas para correcção no OSM, não "emendadas" no mapa.
- **Regras do projecto:** cada script gera o seu HTML; dados embutidos, nunca `fetch()` (abre em `file://`); `aplicar_chave(html)` antes de gravar qualquer HTML com mosaicos CARTO (se houver); entrada no menu só por `nav.py`; pasta própria `tiny/`; ficheiros grandes (ortofoto, mosaicos intermédios) fora do OneDrive ou no `.gitignore`.
- **Resolução-alvo (palpite do desenhador, não decisão do utilizador):** cerca de 1 m/px, imagem final de ordem 7 000 × 6 000 px, a confirmar com a extensão do município.

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
