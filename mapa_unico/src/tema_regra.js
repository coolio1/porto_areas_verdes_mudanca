/* Tema «Regra 3-30-300»: edifícios que cumprem cada indicador. Máscaras de 3 m geradas por regra_303030/mapa_png.py;
   cores da paleta «Carta» (adequado/défice como no tema de acessibilidade). */
MU.registarTema({
  id: 'regra',
  rotulo: 'Regra 3-30-300',
  fundo: 'carta',
  dados: 'regra',
  ctx: { limites: { on: true }, densidade: { on: false } },
  fonte: 'Edif&iacute;cios e rede pedonal: &copy; contribuidores do OpenStreetMap (ODbL) &middot; copa: LiDAR da DGT, MDS/MDT de 50 cm (CC BY 4.0) &middot; ' +
         '&aacute;rvores: invent&aacute;rio da C&acirc;mara do Porto &middot; popula&ccedil;&atilde;o: GHS-POP 2020 (JRC), calibrada ao Censos 2021 (INE).',

  async montar(painel) {
    var N = MU.DADOS.regra.numeros;
    function p(x) { return MU.n(x, 1) + ' %'; }
    var camadas = [
      { id: 'todos', label: 'Cumprem os tr&ecirc;s', color: '#3E6AB3', op: 0.95, ha: N.todos.ha, z: 470 },
      { id: 'nenhum', label: 'N&atilde;o cumprem nenhum', color: '#A23B86', op: 0.95, ha: N.nenhum.ha, z: 460 },
      { id: 'c3', label: 'Cumprem o &laquo;3&raquo; (&aacute;rvores)', color: '#4F9A62', show: false, op: 0.95, ha: N.c3.ha, z: 450 },
      { id: 'c30', label: 'Cumprem o &laquo;30&raquo; (copa)', color: '#1FA6A0', show: false, op: 0.95, ha: N.c30.ha, z: 440 },
      { id: 'c300', label: 'Cumprem o &laquo;300&raquo; (parque)', color: '#E0B000', show: false, op: 0.95, ha: N.c300.ha, z: 430 }
    ];
    var esc = MU.escala(camadas.map(function (c) { return c.ha; }));
    painel.innerHTML =
      '<p class="desc"><b>3</b> &aacute;rvores &agrave; vista, <b>30&nbsp;%</b> de copa a 500&nbsp;m, um parque a <b>300&nbsp;m</b> a p&eacute;: edif&iacute;cio a edif&iacute;cio.</p>' +
      '<div class="nums">' + MU.htmlNums([
        { v: MU.n(N.todos.residentes_pct, 1), u: '%', r: 'dos residentes cumprem os tr&ecirc;s' },
        { v: MU.n(N.c30.residentes_pct, 1), u: '%', r: 'cumprem o &laquo;30&raquo;' },
        { v: MU.n(N.nenhum.residentes_pct, 1), u: '%', r: 'n&atilde;o cumprem nenhum' }
      ]) + '</div>' +
      MU.cab2('Camadas', 'barras: 0&ndash;' + MU.n(esc) + ' ha de edificado') + '<div class="camadas"></div>' +
      '<details class="nota-lim"><summary>Como se mediu e o que n&atilde;o garante</summary>' +
      '<p class="tema-sub">Regra de Cecil Konijnendijk. Residentes que cumprem cada indicador: &laquo;3&raquo; ' + p(N.c3.residentes_pct) + ', &laquo;30&raquo; ' + p(N.c30.residentes_pct) + ', &laquo;300&raquo; ' + p(N.c300.residentes_pct) + '; os tr&ecirc;s: ' + p(N.todos.edificios_pct) + ' dos edif&iacute;cios.</p>' +
      '<p class="tema-sub">&laquo;3&raquo;: &aacute;rvores com copa &ge; 25&nbsp;m&sup2; e &ge; 3&nbsp;m (LiDAR) mais o invent&aacute;rio da C&acirc;mara, vistas a &le; 30&nbsp;m de janelas simuladas a cada 5&nbsp;m, em linha de vista 2D (ignora a altura dos obst&aacute;culos). O &laquo;3&raquo; n&atilde;o tem base cient&iacute;fica pr&oacute;pria.</p>' +
      '<p class="tema-sub">&laquo;30&raquo;: o resultado depende muito do limiar: a 25&nbsp;% passa de ' + MU.n(N.c30.edificios_pct, 1) + '&nbsp;% para ' + MU.n(N.sens.c30_limiar25_pct, 1) + '&nbsp;% dos edif&iacute;cios. O LiDAR &eacute; de inverno (2024&ndash;26): copas de folha caduca podem estar subestimadas. Duas folhas com alturas n&atilde;o fi&aacute;veis ficam de fora.</p>' +
      '<p class="tema-sub">&laquo;300&raquo;: a p&eacute; pela rede do OpenStreetMap, parques &ge; 0,5&nbsp;ha (com &ge; 1&nbsp;ha: ' + MU.n(N.sens.c300_1ha_pct, 1) + '&nbsp;% dos edif&iacute;cios). Serralves e outros espa&ccedil;os vedados contam como parque.</p>' +
      '<p class="tema-sub">Residentes: GHS-POP 2020 repartido pelos edif&iacute;cios por &aacute;rea &times; altura e calibrado ao Censos 2021 (modelo, n&atilde;o contagem).</p>' +
      '<p class="tema-sub">Valida&ccedil;&atilde;o: 150 edif&iacute;cios (amostra estratificada) comparados com a leitura da ortofoto DGT 2025 de 25&nbsp;cm feita por IA, n&atilde;o no terreno. Concord&acirc;ncia: &laquo;30&raquo; 89&nbsp;% (copa do modelo +2,9 pontos percentuais acima da ortofoto), &laquo;300&raquo; 75&nbsp;% (as diferen&ccedil;as v&ecirc;m de parques a 309&ndash;650&nbsp;m a p&eacute;, mas &le; 300&nbsp;m em linha recta), &laquo;3&raquo; 71&nbsp;%: o modelo &eacute; conservador, metade das diferen&ccedil;as vem de edif&iacute;cios a tapar a vista, que a ortofoto n&atilde;o v&ecirc;.</p></details>';
    var box = painel.querySelector('.camadas');
    MU.linhaParques(this, box, { on: false, contorno: true, label: 'Parques e jardins (contorno)', ha: false });
    await MU.addCamadas(this, box, camadas, esc);
  },

  activar() { MU.activarCamadas(this); MU.activarParques(this); },
  desactivar() { MU.desactivarCamadas(this); MU.desactivarParques(this); }
});
