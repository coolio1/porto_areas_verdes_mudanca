/* Tema «Mudanças 2016–2025» (antes mapa/mapa.html): transições 2016-17 → 2024-25 e uso do solo 2024-25
   (Sentinel-2, 10 m). Cores da maquete «Carta» V2b; as máscaras são tingidas no browser. */
MU.registarTema({
  id: 'hoje',
  rotulo: 'Mudanças 2016–2025',
  fundo: 'carta',
  dados: 'hoje',
  ctx: { limites: { on: true }, densidade: { on: false } },
  fonte: 'Sentinel-2 10 m (ESA, Copernicus) &middot; 2016-17 e 2024-25. Hectares por contagem de p&iacute;xeis (&asymp; 57 m&sup2; cada) dentro do concelho.',

  async montar(painel) {
    var S = MU.DADOS.contexto.stats;
    var trans = [
      { id: 'arvores_edificado', label: 'Árvores para edificado', color: '#D93A3A', ha: S.arvores_edificado },
      { id: 'arvores_solo', label: 'Árvores para solo', color: '#C98A1A', ha: S.arvores_solo },
      { id: 'solo_edificado', label: 'Solo para edificado', color: '#7A55B8', ha: S.solo_edificado },
      { id: 'solo_arvores', label: 'Solo para árvores', color: '#1FA6A0', ha: S.solo_arvores }
    ];
    var uso = [
      { id: 'uso_arvores', label: 'Árvores 2024-25', color: '#4F9A62', show: false, op: 0.55, ha: S.uso_arvores },
      { id: 'uso_solo', label: 'Solo 2024-25', color: '#D9B77A', show: false, op: 0.6, ha: S.uso_solo },
      { id: 'uso_edificado', label: 'Edificado 2024-25', color: '#8A8496', show: false, op: 0.45, ha: S.uso_edificado }
    ];
    var esc = MU.escala(trans.map(function (c) { return c.ha; }));
    painel.innerHTML =
      '<p class="desc">O que mudou entre 2016-17 e 2024-25, p&iacute;xel a p&iacute;xel, na classifica&ccedil;&atilde;o Sentinel-2 de 10 m: ' +
      '&aacute;rvores que deram lugar a edificado ou solo, e solo que ganhou &aacute;rvores.</p>' +
      '<div class="nums">' + MU.htmlNums([
        { v: MU.n(S.arvores_edificado + S.arvores_solo), u: 'ha', r: 'de &aacute;rvores perdidas para edificado ou solo, 2016-17 a 2024-25' },
        { v: MU.n(S.solo_arvores), u: 'ha', r: 'de solo que ganhou &aacute;rvores no mesmo per&iacute;odo' },
        { v: MU.n(S.solo_edificado), u: 'ha', r: 'de solo que passou a edificado' }
      ]) + '</div>' +
      MU.cab2('Camadas', 'barras: 0&ndash;' + MU.n(esc) + ' ha') + '<div class="camadas"></div>';
    var box = painel.querySelector('.camadas');
    await MU.addCamadas(this, box, trans, esc);
    await MU.addCamadas(this, box, uso, esc);
    MU.linhaParques(this, box, { on: true, contorno: true, label: 'Parques e jardins (contorno)', ha: false });
  },

  activar() { MU.activarCamadas(this); MU.activarParques(this); },
  desactivar() { MU.desactivarCamadas(this); MU.desactivarParques(this); }
});
