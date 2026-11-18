/* Tema «Acessibilidade e propostas» (antes acessibilidade/acessibilidade_verde.html e
   acessibilidade/conversao_verde.html). Duas vistas do mesmo mapa:
   «actual» = situação actual; «propostas» = simulação com os 46 candidatos a conversão. */
(function () {
  /* paleta das categorias (maquete V2b); as imagens chegam já recoloridas de mapa_unico.py (RECOLOR_ACC) */
  var CAT = { crit: '#A23B86', insuf: '#E6A6CC', adeq: '#3E6AB3', baixa: '#C8C8C8' };
  var TIPO = {
    'Estrategia de expansao (CMP)': { cor: '#00A884', rot: 'Estratégia de expansão (CMP)' },
    'Verde em PDM / fechado ao publico': { cor: '#D9642B', rot: 'Verde em PDM fechado ao público' },
    'Verde privado': { cor: '#D6C496', rot: 'Verde privado' }
  };
  var orla = function (hex) {   // contorno tracejado: a própria cor escurecida para a tinta
    var a = MU.hexToRgb(hex), b = MU.hexToRgb('#10212C');
    return '#' + a.map(function (v, i) { return ('0' + Math.round(v + (b[i] - v) * 0.4).toString(16)).slice(-2); }).join('');
  };

  MU.registarTema({
    id: 'acessibilidade',
    rotulo: 'Acessibilidade e propostas',
  artigo: { url: 'https://portoverde.pt/posts/acessibilidade-verde-publico-porto/' },
    fundo: 'carta',
    dados: 'acessibilidade',
    ctx: { limites: { on: true }, densidade: { on: false } },
    fonte: 'Sentinel-2 10 m (ESA) &middot; GHS-POP 100 m (JRC) &middot; 78 parques e jardins (CMP, OSM) &middot; ' +
           'm&eacute;todo Two-Step Floating Catchment Area (2SFCA). Hectares por contagem de p&iacute;xeis (&asymp; 57 m&sup2; cada) dentro do concelho.',

    vista: 'actual',       // 'actual' | 'propostas'
    ind: null,             // 'acc' | 'prox' | null
    _ov: {},               // cache de overlays: _ov[chave]
    _nomesCand: true,

    async montar(painel) {
      var self = this, D = MU.DADOS.acessibilidade, C = MU.DADOS.contexto, S = C.stats, map = MU.map;
      map.createPane('accPane'); map.getPane('accPane').style.zIndex = 450;
      map.createPane('lowPopPane'); map.getPane('lowPopPane').style.zIndex = 475;
      map.createPane('accMonoPane'); map.getPane('accMonoPane').style.zIndex = 480;
      map.createPane('candGeoPane'); map.getPane('candGeoPane').style.zIndex = 550;

      var P = D.meta;
      this._num = {
        actual: { prox: P.pct_actual, acc: P.sfca_actual_pct },
        propostas: { prox: P.pct_simulado, acc: P.sfca_sim_pct }
      };
      var esc = MU.escala([S.parques_ha, S.pago, S.privado]);

      painel.innerHTML =
        '<p class="desc">Popula&ccedil;&atilde;o a &le; 300&nbsp;m de um parque e verde p&uacute;blico por habitante. As propostas juntam 46 espa&ccedil;os candidatos.</p>' +
        '<div class="nums" id="ac-nums"></div>' +
        '<div class="seg" id="ac-vista" role="group" aria-label="Vista">' +
          '<button type="button" data-v="actual">Situa&ccedil;&atilde;o actual</button>' +
          '<button type="button" data-v="propostas">Com 46 propostas</button></div>' +
        '<div id="ac-intro" class="tema-sub" style="display:none;margin:6px 0 0;">Simula&ccedil;&atilde;o sequencial para atingir 80% de cobertura a &le; 300 m (Konijnendijk 3-30-300).</div>' +
        MU.cab2('Camadas', 'barras: 0&ndash;' + MU.n(esc) + ' ha') + '<div id="ac-camadas"></div>';

      var box = painel.querySelector('#ac-camadas');

      // topo da lista = topo do mapa: Candidatos (550) > Parques (540) > verdes (480) > indicadores (450-475)
      // --- Candidatos a conversão (GeoJSON tracejado; clicar abre a ficha; nomes a partir do zoom 14) ---
      this._cand = L.geoJson(D.candidatos, {
        pane: 'candGeoPane',
        filter: function (f) { return !/^Parques e Jardins j/.test(f.properties.tipo); },
        style: function (f) {
          var c = (TIPO[f.properties.tipo] || {}).cor || '#888888';
          return { color: orla(c), weight: 1.6, opacity: 1, dashArray: '5 3', fillColor: c, fillOpacity: 0.6 };
        },
        onEachFeature: function (f, layer) {
          var p = f.properties, t = TIPO[p.tipo] || { rot: p.tipo, cor: '#888888' };
          layer.on('click', function (e) {
            L.DomEvent.stopPropagation(e);
            MU.ficha({
              titulo: p.nome || 'Candidato sem nome', sub: 'Candidato n.&ordm; ' + p.rank + ' &middot; ' + t.rot, cor: t.cor,
              layer: layer, grupo: self._cand,
              linhas: [['&Aacute;rea', MU.n(p.area_ha, 2) + ' ha']].concat(p.pop_delta != null ? [
                ['Habitantes que passam a ter parque a &le; 300 m', '+' + MU.n(p.pop_delta)],
                ['Cobertura do concelho', MU.n(p.pct_antes, 1) + ' % &rarr; ' + MU.n(p.pct_depois, 1) + ' %']] : [])
            });
          });
          layer.bindTooltip('#' + p.rank + (p.nome ? ' — ' + p.nome : ''),
            { permanent: true, direction: 'center', className: 'cand-label', offset: [0, 0] });
          if (p.label_lat && p.label_lon) {
            layer.on('tooltipopen', function () { layer.getTooltip().setLatLng([p.label_lat, p.label_lon]); });
          }
        }
      });
      this._lCand = MU.linha(box, {
        label: 'Candidatos a convers&atilde;o (46)', checked: false,
        color: 'linear-gradient(90deg,' + TIPO['Estrategia de expansao (CMP)'].cor + ' 0 33%,#D9642B 33% 66%,#D6C496 66%)',
        leg: Object.keys(TIPO).map(function (k) { return [TIPO[k].cor, TIPO[k].rot, true]; }),
        onToggle: function (on) { self._toggle(self._cand, on); },
        opacidade: { v: 0.6, onInput: function (v) { self._cand.setStyle({ fillOpacity: v }); } }
      });
      this._lNomes = MU.linha(box, {
        label: 'Nomes dos candidatos', checked: true, sub: true,
        onToggle: function (on) { self._nomesCand = on; self._rotulos(); }
      });

      // --- Parques e jardins (camada comum; clicar abre a ficha) ---
      this._lParques = MU.linhaParques(this, box, { on: true, esc: esc });

      // --- verde pago e verde privado (todas as áreas): pré-coloridos em Python, cores fixas das camadas ---
      this._mono = [];
      [[C.pago, 'Verde pago ou n&atilde;o usufru&iacute;vel', '#D9642B', S.pago],
       [D.imgs.privado, 'Verde privado', '#D6C496', S.privado]].forEach(function (d) {
        var ov = L.imageOverlay(d[0], MU.BOUNDS, { pane: 'accMonoPane' });
        var l = MU.linha(box, {
          label: d[1], checked: true, color: d[2], ha: d[3], esc: esc,
          onToggle: function (on) { self._toggle(ov, on); },
          opacidade: { v: 1, onInput: function (v) { ov.setOpacity(v); } }
        });
        self._mono.push({ ov: ov, linha: l });
      });

      // --- indicadores (um de cada vez): verde público a 500 m por habitante, parque a 300 m ---
      this._opInd = 0.75;
      var opInd = { v: 0.75, onInput: function (v) { self._opInd = v; Object.keys(self._ov).forEach(function (k) { self._ov[k].setOpacity(v); }); } };
      this._lInd = {
        acc: MU.linha(box, {
          label: 'Verde p&uacute;blico a 500 m, por habitante', checked: false,
          color: 'linear-gradient(90deg,' + CAT.crit + ' 0 33%,' + CAT.insuf + ' 33% 66%,' + CAT.adeq + ' 66%)',
          leg: [[CAT.crit, '0 a 3 m&sup2;, d&eacute;fice cr&iacute;tico'], [CAT.insuf, '3 a 9 m&sup2;, insuficiente'],
                [CAT.adeq, 'mais de 9 m&sup2;, adequado (OMS: &ge; 9 m&sup2;/hab)'], [CAT.baixa, 'baixa densidade']],
          onToggle: function (on) { self._setInd(on ? 'acc' : null); }, opacidade: opInd
        }),
        prox: MU.linha(box, {
          label: 'Parque a 300 m ou menos', checked: false,
          color: 'linear-gradient(90deg,' + CAT.adeq + ' 0 50%,' + CAT.crit + ' 50%)',
          leg: [[CAT.adeq, 'a 300 m ou menos de um parque &ge; 0,4 ha'], [CAT.crit, 'a mais de 300 m'], [CAT.baixa, 'baixa densidade']],
          onToggle: function (on) { self._setInd(on ? 'prox' : null); }, opacidade: opInd
        })
      };

      painel.querySelector('#ac-vista').addEventListener('click', function (e) {
        var b = e.target.closest('button'); if (b) self.setVista(b.dataset.v, true);
      });
      map.on('zoomend', function () { if (MU.tema === 'acessibilidade') self._rotulos(); });
    },

    /* ---------- estado ---------- */
    _toggle: function (layer, on) {
      if (MU.tema !== 'acessibilidade') return;
      on ? layer.addTo(MU.map) : MU.map.removeLayer(layer);
      this._rotulos();
    },

    _setInd: function (ind) {
      this.ind = ind;
      var self = this;
      ['acc', 'prox'].forEach(function (k) {
        var l = self._lInd[k], on = k === ind;
        if (l.cb.checked !== on) { l.cb.checked = on; l.row.classList.toggle('off', !on); }
      });
      this._render();
    },

    _rotulos: function () {
      var z = MU.map.getZoom(), nomes = this._nomesCand;
      document.querySelectorAll('.cand-label').forEach(function (l) { l.style.display = (nomes && z >= 14) ? '' : 'none'; });
    },

    _overlay: function () {
      if (!this.ind) return null;
      var D = MU.DADOS.acessibilidade.imgs, k = this.vista + '_' + this.ind;
      var src = { actual_acc: D.acc, propostas_acc: D.acc_sim, actual_prox: D.prox, propostas_prox: D.prox_sim }[k];
      if (!this._ov[k]) this._ov[k] = L.imageOverlay(src, MU.BOUNDS, { opacity: this._opInd, pane: 'accPane' });
      this._ov[k].setOpacity(this._opInd);
      return this._ov[k];
    },

    _lowPop: function () {
      if (!this._ovLow) this._ovLow = L.imageOverlay(MU.DADOS.acessibilidade.imgs.baixa, MU.BOUNDS, { pane: 'lowPopPane' });
      return this._ovLow;
    },

    _render: function () {
      var map = MU.map, self = this, S = MU.DADOS.contexto.stats, pr = this.vista === 'propostas', N = this._num[this.vista];
      Object.keys(this._ov).forEach(function (k) { map.removeLayer(self._ov[k]); });
      map.removeLayer(this._lowPop());
      if (MU.tema === 'acessibilidade') {
        var ov = this._overlay();
        if (ov) { ov.addTo(map); this._lowPop().addTo(map); }
      }
      document.querySelectorAll('#ac-vista button').forEach(function (b) {
        var on = b.dataset.v === self.vista;
        b.classList.toggle('active', on); b.setAttribute('aria-pressed', on);
      });
      document.getElementById('ac-nums').innerHTML = MU.htmlNums([
        { v: MU.n(S.m2hab, 1), u: 'm&sup2;', r: 'de parque por habitante' },
        { v: MU.n(N.prox), u: '%', r: 'a &le; 300 m de um parque (&ge; 0,4 ha)' + (pr ? ', com propostas' : '') },
        { v: MU.n(N.acc, 1), u: '%', r: 'com &ge; 9 m&sup2; de verde a 500 m' + (pr ? ', com propostas' : '') }
      ]);
      document.getElementById('ac-intro').style.display = pr ? 'block' : 'none';
      this._lCand.row.style.display = pr ? '' : 'none';
      this._lNomes.row.style.display = pr ? '' : 'none';
    },

    /* alterna entre situação actual e propostas; o indicador mantém-se */
    setVista: function (v, deUtilizador) {
      if (v === this.vista && !deUtilizador) return;
      this.vista = v;
      var c = this._lCand.cb;
      if (c.checked !== (v === 'propostas')) { c.checked = (v === 'propostas'); c.dispatchEvent(new Event('change')); }
      MU.setHash({ tema: 'acessibilidade', vista: v });
      this._render();
    },

    /* primeira entrada: vista pedida no URL; «propostas» abre como a página original (proximidade, parques desligados) */
    _inicial: function () {
      var v = MU.param('vista') === 'propostas' ? 'propostas' : 'actual';
      this.vista = v;
      var p = this._lParques.cb, c = this._lCand.cb;
      p.checked = (v === 'actual'); p.closest('.cam').classList.toggle('off', !p.checked);
      c.checked = (v === 'propostas'); c.closest('.cam').classList.toggle('off', !c.checked);
      if (v === 'propostas') this._setInd('prox');
    },

    aoHash: function () {   // #tema=acessibilidade&vista=… alterado à mão com o tema já aberto
      var v = MU.param('vista') === 'propostas' ? 'propostas' : 'actual';
      if (v !== this.vista) this.setVista(v, false);
    },

    activar: function () {
      var map = MU.map;
      if (!this._iniciado) { this._iniciado = true; this._inicial(); }
      this._render();
      MU.activarParques(this);
      if (this._lCand.cb.checked) this._cand.addTo(map);
      this._mono.forEach(function (m) { if (m.linha.cb.checked) m.ov.addTo(map); });
      MU.setHash({ tema: 'acessibilidade', vista: this.vista });
      this._rotulos();
    },

    desactivar: function () {
      var map = MU.map, self = this;
      Object.keys(this._ov).forEach(function (k) { map.removeLayer(self._ov[k]); });
      map.removeLayer(this._lowPop());
      MU.desactivarParques(this);
      map.removeLayer(this._cand);
      this._mono.forEach(function (m) { map.removeLayer(m.ov); });
    }
  });
})();
