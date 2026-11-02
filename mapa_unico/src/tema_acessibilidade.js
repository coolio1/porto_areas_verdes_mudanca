/* Tema «Acessibilidade e propostas» (antes acessibilidade/acessibilidade_verde.html e
   acessibilidade/conversao_verde.html). Duas vistas do mesmo mapa:
   «actual» = situação actual; «propostas» = simulação com os 46 candidatos a conversão. */
MU.registarTema({
  id: 'acessibilidade',
  rotulo: 'Acessibilidade e propostas',
  fundo: 'positron',
  dados: 'acessibilidade',
  ctx: { limites: { on: true, cor: '#444444' }, densidade: { on: false } },
  fonte: 'Sentinel-2 10m (ESA) &bull; GHS-POP 100m (JRC)<br>78 parques e jardins (CMP + OSM)<br>' +
         'M&eacute;todo: Two-Step Floating Catchment Area',

  vista: 'actual',       // 'actual' | 'propostas'
  ind: 'acc',            // 'acc' | 'prox' | null
  _ov: {},               // cache de overlays: _ov[chave]
  _nomesCand: true,

  async montar(painel) {
    var self = this, D = MU.DADOS.acessibilidade, map = MU.map;
    map.createPane('accPane'); map.getPane('accPane').style.zIndex = 450;
    map.createPane('lowPopPane'); map.getPane('lowPopPane').style.zIndex = 475;
    map.createPane('parquesPane'); map.getPane('parquesPane').style.zIndex = 540;
    map.createPane('candGeoPane'); map.getPane('candGeoPane').style.zIndex = 550;

    var P = D.meta;
    var pct0 = function (x) { return Math.round(x) + '%'; };
    var pct1 = function (x) { return x.toFixed(1).replace('.', ',') + '%'; };
    this._pct = {
      actual: { prox: pct0(P.pct_actual), acc: pct1(P.sfca_actual_pct) },
      propostas: { prox: pct0(P.pct_simulado), acc: pct1(P.sfca_sim_pct) }
    };

    painel.innerHTML =
      '<b style="font-size:14px;">Acessibilidade a Verde P&uacute;blico</b>' +
      '<div class="ab-group" id="ac-vista" style="margin-top:6px;">' +
        '<button class="ab-btn" data-v="actual">Situa&ccedil;&atilde;o actual</button>' +
        '<button class="ab-btn" data-v="propostas">Com propostas</button></div>' +
      '<div id="ac-intro" class="tema-sub" style="display:none;margin:-2px 0 6px;">Simula&ccedil;&atilde;o sequencial para atingir 80% de cobertura a &le;300m (Konijnendijk)</div>' +
      '<div class="section">Indicador</div>' +
      '<div class="ab-group" id="ac-ind">' +
        '<button class="ab-btn" data-i="acc">Acessibilidade 500m<small></small></button>' +
        '<button class="ab-btn" data-i="prox">Proximidade 300m<small></small></button></div>' +

      '<div id="acc-legend" style="display:none;">' +
        '<div class="section">Acessibilidade 500m (m&sup2;/hab)</div>' +
        '<div class="leg">' +
          '<div><i style="background:#B71C1C"></i><span>0 &ndash; 3 (d&eacute;fice cr&iacute;tico)</span></div>' +
          '<div><i style="background:#E8A838"></i><span>3 &ndash; 9 (insuficiente)</span></div>' +
          '<div><i style="background:#2E7D32"></i><span>&gt;9 (adequado)</span></div>' +
          '<div><i style="background:#C8C8C8"></i><span>Baixa densidade</span></div></div>' +
        '<div class="nota">OMS recomenda &ge;9 m&sup2;/hab</div></div>' +
      '<div id="prox-legend" style="display:none;">' +
        '<div class="section">Proximidade 300m (Konijnendijk 3-30-300)</div>' +
        '<div class="leg">' +
          '<div><i style="background:#2E7D32"></i><span>&le;300m de parque &ge;0,4 ha (cumpre)</span></div>' +
          '<div><i style="background:#B71C1C"></i><span>&gt;300m de parque &ge;0,4 ha (n&atilde;o cumpre)</span></div></div>' +
        '<div class="nota">OMS: &ge;0,4 ha de verde a &lt;300m de casa</div></div>' +
      '<div id="cand-legend" style="display:none;">' +
        '<div class="section">Candidatos (por prioridade)</div>' +
        '<div class="leg">' +
          '<div><i style="background:#00897B"></i><span>Estrat&eacute;gia de expans&atilde;o (CMP)</span></div>' +
          '<div><i style="background:#8D6E63"></i><span>Verde em PDM / fechado ao p&uacute;blico</span></div>' +
          '<div><i style="background:#1565C0"></i><span>Verde privado</span></div></div></div>' +

      '<div class="section">Camadas</div><div id="ac-camadas"></div>';

    var box = painel.querySelector('#ac-camadas');

    // --- Parques e Jardins (GeoJSON, popups, rótulos a partir do zoom 14) ---
    this._parques = L.geoJson(D.parques, {
      pane: 'parquesPane',
      style: function () { return { color: '#1B5E20', weight: 2.5, opacity: 0.9, fillColor: '#2E7D32', fillOpacity: 0.45 }; },
      onEachFeature: function (f, layer) {
        var p = f.properties, area = p.area_calc_ha ? p.area_calc_ha + ' ha' : '';
        layer.bindPopup('<b style="font-size:13px;">' + p.nome + '</b><br><span style="color:#666;">' +
          (p.tipo || '') + (area ? ' &mdash; ' + area : '') + '</span>');
        layer.bindTooltip(p.nome, { permanent: true, direction: 'center', className: 'park-label', offset: [0, 0] });
      }
    });
    this._lParques = MU.linha(box, {
      label: 'Parques e Jardins', checked: true, color: '#2E7D32', editavel: false,
      onToggle: function (on) { self._toggle(self._parques, on); }
    });

    // --- Candidatos a conversão (GeoJSON, popups, rótulos a partir do zoom 13) ---
    var TIPO = {
      'Estrategia de expansao (CMP)': { cor: '#00897B', rot: 'Estratégia de expansão (CMP)' },
      'Verde em PDM / fechado ao publico': { cor: '#8D6E63', rot: 'Verde em PDM / fechado ao público' },
      'Verde privado': { cor: '#1565C0', rot: 'Verde privado' }
    };
    this._cand = L.geoJson(D.candidatos, {
      pane: 'candGeoPane',
      filter: function (f) { return !/^Parques e Jardins j/.test(f.properties.tipo); },
      style: function (f) {
        var c = (TIPO[f.properties.tipo] || {}).cor || '#888';
        return { color: c, weight: 2, opacity: 1, fillColor: c, fillOpacity: 0.45 };
      },
      onEachFeature: function (f, layer) {
        var p = f.properties, t = TIPO[p.tipo] || { rot: p.tipo };
        var h = '<b style="font-size:13px;">#' + p.rank + '</b>' + (p.nome ? ' &mdash; ' + p.nome : '');
        h += '<br><span style="color:#666;">' + t.rot + '</span><br><span style="color:#666;">&Aacute;rea: ' + p.area_ha + ' ha</span>';
        if (p.pop_delta != null) {
          h += '<br><span style="color:#2E7D32;">+' + p.pop_delta.toLocaleString() + ' hab cobertos</span>';
          h += '<br><span style="color:#444;">Cobertura: ' + p.pct_antes + '% &rarr; ' + p.pct_depois + '%</span>';
        }
        layer.bindPopup(h);
        layer.bindTooltip('#' + p.rank + (p.nome ? ' — ' + p.nome : ''),
          { permanent: true, direction: 'center', className: 'cand-label', offset: [0, 0] });
        if (p.label_lat && p.label_lon) {
          layer.on('tooltipopen', function () { layer.getTooltip().setLatLng([p.label_lat, p.label_lon]); });
        }
      }
    });
    this._lCand = MU.linha(box, {
      label: 'Candidatos a conversão (46)', checked: false, color: '#00897B', editavel: false,
      onToggle: function (on) { self._toggle(self._cand, on); self._legendas(); }
    });
    this._lNomes = MU.linha(box, {
      label: 'Nomes dos candidatos', checked: true,
      onToggle: function (on) { self._nomesCand = on; self._rotulos(); }
    });
    this._lNomes.row.style.marginLeft = '20px';

    // --- Verde privado (todas as áreas) e verde em PDM: só visualização, pré-coloridas em Python ---
    this._mono = [];
    [['privado', 'Verde privado (todas as áreas)', '#1565C0'],
     ['pago', 'Verde em PDM / fechado ao público', '#8D6E63']].forEach(function (d) {
      var ov = L.imageOverlay(D.imgs[d[0]], MU.BOUNDS);
      var l = MU.linha(box, {
        label: d[1], checked: false, color: d[2], editavel: false,
        onToggle: function (on) { self._toggle(ov, on); }
      });
      self._mono.push({ ov: ov, linha: l });
    });

    // --- botões: vista e indicador ---
    painel.querySelector('#ac-vista').addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (b) self.setVista(b.dataset.v, true);
    });
    painel.querySelector('#ac-ind').addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      self.ind = (self.ind === b.dataset.i) ? null : b.dataset.i;   // clicar no activo desliga
      self._render();
    });
    map.on('zoomend', function () { if (MU.tema === 'acessibilidade') self._rotulos(); });
  },

  /* ---------- estado ---------- */
  _toggle: function (layer, on) {
    if (MU.tema !== 'acessibilidade') return;
    on ? layer.addTo(MU.map) : MU.map.removeLayer(layer);
    this._rotulos();
  },

  _rotulos: function () {
    var z = MU.map.getZoom(), nomes = this._nomesCand;
    document.querySelectorAll('.park-label').forEach(function (l) { l.style.display = z >= 14 ? '' : 'none'; });
    document.querySelectorAll('.cand-label').forEach(function (l) { l.style.display = (nomes && z >= 13) ? '' : 'none'; });
  },

  _overlay: function () {
    if (!this.ind) return null;
    var D = MU.DADOS.acessibilidade.imgs, k = this.vista + '_' + this.ind;
    var src = { actual_acc: D.acc, propostas_acc: D.acc_sim, actual_prox: D.prox, propostas_prox: D.prox_sim }[k];
    if (!this._ov[k]) this._ov[k] = L.imageOverlay(src, MU.BOUNDS, { opacity: 0.7, pane: 'accPane' });
    return this._ov[k];
  },

  _lowPop: function () {
    if (!this._ovLow) this._ovLow = L.imageOverlay(MU.DADOS.acessibilidade.imgs.baixa, MU.BOUNDS, { pane: 'lowPopPane' });
    return this._ovLow;
  },

  _legendas: function () {
    var $ = function (id) { return document.getElementById(id); };
    $('acc-legend').style.display = this.ind === 'acc' ? 'block' : 'none';
    $('prox-legend').style.display = this.ind === 'prox' ? 'block' : 'none';
    $('cand-legend').style.display = (this._lCand.cb.checked && this.vista === 'propostas') ? 'block' : 'none';
  },

  _render: function () {
    var map = MU.map, self = this;
    Object.keys(this._ov).forEach(function (k) { map.removeLayer(self._ov[k]); });
    map.removeLayer(this._lowPop());
    var ov = this._overlay();
    if (ov) { ov.addTo(map); this._lowPop().addTo(map); }
    document.querySelectorAll('#ac-vista .ab-btn').forEach(function (b) { b.classList.toggle('active', b.dataset.v === self.vista); });
    document.querySelectorAll('#ac-ind .ab-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.i === self.ind);
      b.querySelector('small').textContent = (self.vista === 'actual' ? 'Actual ' : 'Simulado ') + self._pct[self.vista][b.dataset.i];
    });
    document.getElementById('ac-intro').style.display = this.vista === 'propostas' ? 'block' : 'none';
    this._legendas();
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
    this.ind = v === 'propostas' ? 'prox' : 'acc';
    var p = this._lParques.cb, c = this._lCand.cb;
    p.checked = (v === 'actual'); c.checked = (v === 'propostas');
  },

  aoHash: function () {   // #tema=acessibilidade&vista=… alterado à mão com o separador já aberto
    var v = MU.param('vista') === 'propostas' ? 'propostas' : 'actual';
    if (v !== this.vista) this.setVista(v, false);
  },

  activar: function () {
    var map = MU.map, self = this;
    if (!this._iniciado) { this._iniciado = true; this._inicial(); }
    this._render();
    var pares = [[this._lParques, this._parques], [this._lCand, this._cand]];
    pares.forEach(function (p) { if (p[0].cb.checked) p[1].addTo(map); });
    this._mono.forEach(function (m) { if (m.linha.cb.checked) m.ov.addTo(map); });
    MU.setHash({ tema: 'acessibilidade', vista: this.vista });
    this._rotulos();
  },

  desactivar: function () {
    var map = MU.map, self = this;
    Object.keys(this._ov).forEach(function (k) { map.removeLayer(self._ov[k]); });
    map.removeLayer(this._lowPop());
    map.removeLayer(this._parques); map.removeLayer(this._cand);
    this._mono.forEach(function (m) { map.removeLayer(m.ov); });
  }
});
