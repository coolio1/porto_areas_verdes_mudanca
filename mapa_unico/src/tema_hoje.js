/* Tema «Mapa 2016-2025» (antes mapa/mapa.html): uso do solo 2024-25 e transições 2016 → 2025. */
MU.registarTema({
  id: 'hoje',
  rotulo: 'Mapa 2016-2025',
  fundo: 'dark',
  dados: 'hoje',
  ctx: { limites: { on: true, cor: '#FFFFFF' }, densidade: { on: false } },
  fonte: 'Fonte: Sentinel-2 (ESA) &bull; Copernicus',

  async montar(painel) {
    painel.innerHTML =
      '<b style="font-size:14px;">Espa&ccedil;o verde do Porto</b><br>' +
      '<span class="tema-sub">2016-17 &rarr; 2024-25 &bull; Sentinel-2 10m</span>' +
      '<div class="section">Uso do solo (2024-25)</div><div class="uso"></div>' +
      '<div class="section">Transi&ccedil;&otilde;es (2016 &rarr; 2025)</div><div class="trans"></div>';
    await MU.addCamadas(this, painel.querySelector('.uso'), [
      { id: 'uso_arvores', label: 'Árvores (2024-25)', color: '#228B22', show: false },
      { id: 'uso_solo', label: 'Solo (2024-25)', color: '#C2B280', show: false },
      { id: 'uso_edificado', label: 'Edificado (2024-25)', color: '#888888', show: false }
    ], true);
    await MU.addCamadas(this, painel.querySelector('.trans'), [
      { id: 'arvores_edificado', label: 'Árvores → Edificado', color: '#D7263D' },
      { id: 'arvores_solo', label: 'Árvores → Solo', color: '#E8A838' },
      { id: 'solo_edificado', label: 'Solo → Edificado', color: '#6A1B9A' },
      { id: 'solo_arvores', label: 'Solo → Árvores', color: '#2E7D32' }
    ], true);
  },

  activar() { MU.activarCamadas(this); },
  desactivar() { MU.desactivarCamadas(this); }
});
