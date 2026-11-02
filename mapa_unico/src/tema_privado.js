/* Tema «Verde privado» (antes interiores/interiores_quarteiroes.html). */
MU.registarTema({
  id: 'privado',
  rotulo: 'Verde privado',
  fundo: 'positron',
  dados: 'privado',
  ctx: { limites: { on: true, cor: '#444444' }, densidade: { on: false } },
  fonte: 'Sentinel-2 10m (ESA) &bull; 2016-17 vs 2024-25<br>Parques exclu&iacute;dos via OpenStreetMap',

  async montar(painel) {
    painel.innerHTML =
      '<b style="font-size:14px;">Verde Privado</b><br>' +
      '<span class="tema-sub">Espa&ccedil;os verdes privados encravados no tecido urbano</span>' +
      '<div class="section">Camadas</div><div class="camadas"></div>';
    await MU.addCamadas(this, painel.querySelector('.camadas'), [
      { id: 'interior_subsistente', label: 'Subsistente (áreas principais)', color: '#2E7D32' },
      { id: 'interior_perdido', label: 'Perdido (2016-2025)', color: '#D7263D' },
      { id: 'centro_alargado', label: 'Interior VCI', color: '#FFD700' }
    ], false);
  },

  activar() { MU.activarCamadas(this); },
  desactivar() { MU.desactivarCamadas(this); }
});
