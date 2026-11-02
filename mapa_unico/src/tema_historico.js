/* Tema «Histórico» (antes ndvi_historico/ndvi_historico.html e 1947/orto_1947.html):
   classificação 1947 (ortofoto), ocupação do solo 1979, épocas Landsat 1972-2024, NDVI,
   perda e ganho de vegetação. */
(function () {
  var EPOCAS = [
    ['1972-76', '1972-1976'], ['1979', '1979'], ['1985-90', '1985-1990'], ['1995-00', '1995-2000'],
    ['2001-05', '2001-2005'], ['2016-17', '2016-2017'], ['2023-24', '2023-2024']
  ];
  var NDVI = [
    ['1972-76', 'NDVI 1972-1976 (MSS)'], ['1985-90', 'NDVI 1985-1990 (Landsat 5)'],
    ['1995-00', 'NDVI 1995-2000 (Landsat 5)'], ['2001-05', 'NDVI 2001-2005 (Landsat 5)'],
    ['2016-17', 'NDVI 2016-2017 (Landsat 8)'], ['2023-24', 'NDVI 2023-2024 (Landsat 8)']
  ];
  var BOUNDS_1947 = [[41.12912995365261, -8.700884213830351], [41.189999037480554, -8.539187462666328]];
  var COR_VEG = '#00FF00', COR_EDIF = '#C4A882';   // cores já gravadas nas máscaras por época
  var CLASSES_1979 = [
    ['ABE', 'Elementos artificiais (construído)', '#888888'],
    ['TRS', 'Árvores e arbustos', '#1B5E20'],
    ['HER', 'Herbáceas', '#9CCC65'],
    ['SPV', 'Vegetação esparsa (terrestre)', '#E0C080'],
    ['AQU', 'Vegetação esparsa (aquática)', '#4FC3F7']
  ];

  /* fundo «Ortofoto 1947» (WMS do CIIMAR/FCUP); só faz sentido neste tema */
  MU.FUNDOS.push({
    id: 'orto1947', nome: 'Ortofoto 1947', so: 'historico',
    criar: function () {
      return L.tileLayer.wms('https://gis.ciimar.up.pt/porto/wms', {
        layers: 'Orto_Porto_1947', format: 'image/png', transparent: false,
        version: '1.1.1', maxZoom: 20, attribution: 'CIIMAR/FCUP'
      });
    }
  });

  var ha = function (x) { return x.toLocaleString('pt-PT', { maximumFractionDigits: 0 }) + ' ha'; };

  MU.registarTema({
    id: 'historico',
    rotulo: 'Histórico 1947-2024',
    fundo: 'positron',
    dados: 'historico',
    ctx: { limites: { on: true, cor: '#444444' }, densidade: { on: false } },
    fonte: 'Ortofotomapa 1947 (CIIMAR/FCUP) &bull; Landsat MSS/TM/OLI (USGS/NASA)<br>' +
           '1947: Pixel RF (textura local), limpo com Sentinel-2 e Landsat 1985<br>' +
           'Hist&oacute;rico: NDVI &ge; 0,25 &bull; Roy et al. 2016<br>' +
           'Ocupa&ccedil;&atilde;o do solo 1979: Filipa Guilherme<br>' +
           'Limites: CAOP 2025 (DGT)',

    _regs: [],

    /* regista uma camada com a sua linha no painel; activar/desactivar tratam do conjunto */
    _reg: function (box, layer, o) {
      var self = this, r = { layer: layer, linha: null };
      r.linha = MU.linha(box, {
        label: o.label, checked: !!o.checked, color: o.color, editavel: !!o.editavel,
        onToggle: function (on) {
          if (MU.tema !== 'historico') return;
          on ? layer.addTo(MU.map) : MU.map.removeLayer(layer);
          if (o.aoLigar) o.aoLigar(on, r);
        },
        onColor: o.onColor
      });
      self._regs.push(r);
      return r;
    },

    async montar(painel) {
      var self = this, D = MU.DADOS.historico, map = MU.map;
      [['h1947Pane', 405], ['hCobPane', 408], ['hNdviPane', 410], ['hMascPane', 415], ['hMudPane', 420]]
        .forEach(function (p) { map.createPane(p[0]); map.getPane(p[0]).style.zIndex = p[1]; });

      painel.innerHTML =
        '<b style="font-size:14px;">Vegeta&ccedil;&atilde;o do Porto</b><br>' +
        '<span class="tema-sub">1947-2024 &bull; Ortofoto 1947 + Landsat MSS 60m / TM-OLI 30m</span>' +
        '<div class="section">Uso do solo 1947 (ortofoto)</div><div id="h-1947"></div>' +
        '<div class="row" style="margin-top:4px;"><label style="font-size:11px;color:#666;" for="h-op">Opacidade</label>' +
          '<input type="range" id="h-op" min="10" max="100" step="5" value="100" style="flex:1;">' +
          '<span id="h-op-v" class="tema-sub" style="width:30px;">100%</span></div>' +
        '<div class="section">Ocupa&ccedil;&atilde;o do solo 1979</div><div id="h-1979"></div>' +
        '<div class="nota" style="margin:2px 0 0;">Dados de Filipa Guilherme</div>' +
        '<div class="section">Vegeta&ccedil;&atilde;o por &eacute;poca</div><div id="h-veg"></div>' +
        '<div class="section">Edificado por &eacute;poca</div><div id="h-edif"></div>' +
        '<div class="nota">1979: vegeta&ccedil;&atilde;o = &aacute;rvores, arbustos e herb&aacute;ceas; edificado = elementos artificiais</div>' +
        '<div class="section">Perda e ganho (1985-90 vs 2023-24)</div><div id="h-mud"></div>' +
        '<div class="section">NDVI por &eacute;poca (uma de cada vez)</div><div id="h-ndvi"></div>';

      /* ---- 1947: imagens a 1 bit; opacidade por setOpacity, cor por filtro SVG (sem canvas de 170 Mpx) ---- */
      var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', '0'); svg.setAttribute('height', '0'); svg.style.position = 'absolute';
      svg.innerHTML =
        ['veg', 'edif'].map(function (k) {
          return '<filter id="h-tint-' + k + '" color-interpolation-filters="sRGB">' +
                 '<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter>';
        }).join('');
      painel.appendChild(svg);
      this._o1947 = [];
      var box47 = painel.querySelector('#h-1947');
      [['uso_1947_vegetacao', 'Vegetação 1947', '#228B22', 'veg'],
       ['uso_1947_edificado', 'Edificado 1947', '#888888', 'edif']].forEach(function (d) {
        var ov = L.imageOverlay(D[d[0]], BOUNDS_1947, { pane: 'h1947Pane' });
        var tint = function (hex) {
          var rgb = MU.hexToRgb(hex).map(function (v) { return (v / 255).toFixed(4); });
          svg.querySelector('#h-tint-' + d[3] + ' feColorMatrix').setAttribute('values',
            '0 0 0 0 ' + rgb[0] + '  0 0 0 0 ' + rgb[1] + '  0 0 0 0 ' + rgb[2] + '  0 0 0 1 0');
          ov._tinta = true;
          if (ov.getElement()) ov.getElement().style.filter = 'url(#h-tint-' + d[3] + ')';
        };
        ov.on('add', function () { if (ov._tinta) ov.getElement().style.filter = 'url(#h-tint-' + d[3] + ')'; });
        self._reg(box47, ov, { label: d[1], checked: true, color: d[2], editavel: true, onColor: tint });
        self._o1947.push(ov);
      });
      painel.querySelector('#h-op').addEventListener('input', function () {
        var v = +this.value;
        painel.querySelector('#h-op-v').textContent = v + '%';
        self._o1947.forEach(function (o) { o.setOpacity(v / 100); });
      });

      /* ---- ocupação do solo 1979 (polígonos por classe) ---- */
      var box79 = painel.querySelector('#h-1979');
      CLASSES_1979.forEach(function (c) {
        var gj = L.geoJson(D.cobertura_1979, {
          pane: 'hCobPane',
          filter: function (f) { return f.properties.c === c[0]; },
          style: function () { return { stroke: false, fillColor: c[2], fillOpacity: 0.75 }; },
          onEachFeature: function (f, layer) {
            layer.bindPopup('<b style="font-size:13px;">' + c[1] + '</b><br><span style="color:#666;">1979 &mdash; ' +
              f.properties.ha.toLocaleString('pt-PT') + ' ha</span>');
          }
        });
        self._reg(box79, gj, {
          label: c[1] + ' (' + ha(D.cobertura_1979_ha[c[0]]) + ')', checked: false, color: c[2], editavel: true,
          onColor: function (hex) { gj.setStyle({ fillColor: hex }); }
        });
      });

      /* ---- épocas Landsat (máscaras pré-coloridas) ---- */
      var mascara = function (prefixo, box, rotulo, cor) {
        EPOCAS.forEach(function (e) {
          var ov = L.imageOverlay(D[prefixo + '_' + e[0]], MU.BOUNDS, { pane: 'hMascPane' });
          self._reg(box, ov, { label: rotulo + ' ' + e[1], checked: false, color: cor });
        });
      };
      mascara('veg', painel.querySelector('#h-veg'), 'Vegetação', COR_VEG);
      mascara('edif', painel.querySelector('#h-edif'), 'Edificado', COR_EDIF);

      /* ---- perda e ganho ---- */
      var boxM = painel.querySelector('#h-mud');
      [['veg_perda', 'Perda de vegetação (85-90 → 23-24)', '#FF4444'],
       ['veg_ganho', 'Ganho de vegetação (85-90 → 23-24)', '#44FF44']].forEach(function (d) {
        self._reg(boxM, L.imageOverlay(D[d[0]], MU.BOUNDS, { pane: 'hMudPane' }),
          { label: d[1], checked: false, color: d[2] });
      });

      /* ---- NDVI: exclusivo (ligar uma desliga as outras) ---- */
      var boxN = painel.querySelector('#h-ndvi'), ndvi = [];
      NDVI.forEach(function (n) {
        var ov = L.imageOverlay(D['ndvi_' + n[0]], MU.BOUNDS, { pane: 'hNdviPane' });
        var r = self._reg(boxN, ov, {
          label: n[1], checked: false,
          aoLigar: function (on, r) {
            if (!on) return;
            ndvi.forEach(function (o) {
              if (o !== r && o.linha.cb.checked) { o.linha.cb.checked = false; map.removeLayer(o.layer); }
            });
          }
        });
        ndvi.push(r);
      });
    },

    activar() {
      this._regs.forEach(function (r) { if (r.linha.cb.checked) r.layer.addTo(MU.map); });
      if (MU.param('vista') === '1947' && !MU.fundoManual) MU.setFundo('orto1947');
    },
    desactivar() {
      this._regs.forEach(function (r) { MU.map.removeLayer(r.layer); });
    }
  });
})();
