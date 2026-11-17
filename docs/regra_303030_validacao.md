# 3-30-300 · validação do modelo (2026-11-18)

**Método.** 150 edifícios (30 por estrato: cumprem os três, nenhum, só o «3», só o «30», só o «300»; semente 303030,
`regra_303030/validacao.py`). Para cada um, 2 recortes da ortofoto DGT 2025 de 25 cm (CC BY 4.0) com contorno do
edifício, faixa de 30 m e círculos de 300 m e 500 m (`validacao_imagens.py`). Cinco leitores (subagentes de IA, 30
pontos cada) rotularam as imagens sem ver o veredicto do modelo (`validacao_comparar.py` junta e compara com o modelo).
**Não é verdade de terreno**: é uma segunda leitura de imagem, vista de cima. As percentagens valem para a amostra
(estratificada), não para o Porto.

| Indicador | Concordância | Modelo sim / ortofoto não | Modelo não / ortofoto sim |
|---|---:|---:|---:|
| «3» árvores à vista | 70,7 % | 4 | 40 |
| «30» copa 500 m | 89,3 % | 11 | 5 |
| «300» parque a pé | 75,3 % | 12 | 25 |

- **«30»:** copa do modelo +2,9 pontos percentuais acima da ortofoto, correlação 0,76. Concordância 92 % nos casos de
  confiança média e 57 % nos de confiança baixa.
- **«300»:** dos 25 casos «modelo não / ortofoto sim», o modelo dá 309–650 m a pé (média 420 m): o leitor usou o
  círculo de 300 m em linha recta. Não é erro do modelo; vários são mata de acesso incerto.
- **«3»:** o modelo é conservador (conta 1,1 árvores onde a ortofoto conta 5,1 nos 40 desacordos). Em 21 deles o
  `n30_sem_bloqueio` chega a ≥3: edifícios a tapar a vista, que de cima não se vê (diferença de definição). Os outros 19
  ficam por explicar (copas sob a altura mínima, deteção do LiDAR ou leitura generosa da ortofoto; 17 dos 40 com
  confiança baixa). Concordância 80 % com confiança alta e 54 % com confiança baixa.

**Leitura.** O «30» e o «300» estão alinhados com a ortofoto no que é mensurável. O «3» é o menos fiável: usar o
valor com bloqueio (61,2 % dos edifícios) como limite inferior e o sem bloqueio (77,4 %) como superior.
Dados: `S:\3 30 300\dados\validacao_*.csv` (fora do repo).
