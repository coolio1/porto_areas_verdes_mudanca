/* Tema «Verde privado» (antes interiores/interiores_quarteiroes.html). */
MU.registarTema({
  id: 'privado',
  rotulo: 'Verde privado',
  fundo: 'carta',
  dados: 'privado',
  ctx: { limites: { on: true }, densidade: { on: false } },
  fonte: 'Sentinel-2 10 m (ESA) &middot; 2016-17 e 2024-25 &middot; parques exclu&iacute;dos via OpenStreetMap. ' +
         'Hectares por contagem de p&iacute;xeis (&asymp; 57 m&sup2; cada) dentro do concelho.',

  async montar(painel) {
    var S = MU.DADOS.contexto.stats, map = MU.map, self = this;
    var esc = MU.escala([S.subsistente, S.perdido, S.parques_ha]);
    painel.innerHTML =
      '<p class="desc">O verde que sobra quando se retiram os parques, o verde pago e as estradas: logradouros, interiores de ' +
      'quarteir&atilde;o, quintas privadas. E o que deles se perdeu desde 2016.</p>' +
      '<div class="nums">' + MU.htmlNums([
        { v: MU.n(S.subsistente), u: 'ha', r: 'de verde privado subsistente nas &aacute;reas principais' },
        { v: MU.n(S.perdido), u: 'ha', r: 'de verde privado perdido entre 2016 e 2025' },
        { v: MU.n(S.privado), u: 'ha', r: 'de verde privado em todo o concelho, contando as &aacute;reas pequenas' }
      ]) + '</div>' +
      MU.cab2('Camadas', 'barras: 0&ndash;' + MU.n(esc) + ' ha') + '<div class="camadas"></div>';
    var box = painel.querySelector('.camadas');
    await MU.addCamadas(this, box, [
      { id: 'interior_subsistente', label: 'Subsistente (áreas principais)', color: '#D6C496', ha: S.subsistente },
      { id: 'interior_perdido', label: 'Perdido 2016–2025', color: '#7E3FA0', ha: S.perdido },
      { id: 'centro_alargado', label: 'Interior da VCI', color: '#E0B000', show: false, ha: S.centro_alargado }
    ], esc);
    // verde pago (contexto, pré-colorido), desligado à partida
    map.createPane('privPagoPane'); map.getPane('privPagoPane').style.zIndex = 405;
    this._pago = L.imageOverlay(MU.DADOS.contexto.pago, MU.BOUNDS, { pane: 'privPagoPane' });
    this._lPago = MU.linha(box, {
      label: 'Verde pago ou não usufruível', checked: false, color: '#D9642B', ha: S.pago, esc: esc,
      onToggle: function (on) { if (MU.tema === 'privado') on ? self._pago.addTo(map) : map.removeLayer(self._pago); },
      opacidade: { v: 1, onInput: function (v) { self._pago.setOpacity(v); } }
    });
    MU.linhaParques(this, box, { on: true, esc: esc });
  },

  activar() {
    MU.activarCamadas(this); MU.activarParques(this);
    if (this._lPago.cb.checked) this._pago.addTo(MU.map);
  },
  desactivar() { MU.desactivarCamadas(this); MU.desactivarParques(this); MU.map.removeLayer(this._pago); }
});
