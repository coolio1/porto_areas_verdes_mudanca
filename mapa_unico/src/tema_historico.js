/* Tema «Histórico»: linha do tempo 2023-24 → 1947 (uma época de cada vez), minigráfico de
   percentagens, perda e ganho de vegetação e, para 1979, o detalhe das 5 classes de Filipa Guilherme.
   (antes: ~30 caixas por camada; sem NDVI — a página ndvi_historico/ continua à parte). */
(function () {
  /* id, rótulo, fonte/resolução, fonte diferente das restantes (ressalva) */
  var L30 = 'Landsat 5 TM, 30 m; NDVI &ge; 0,25 (Roy et al. 2016)';
  var L8 = 'Landsat 8 OLI, 30 m; NDVI &ge; 0,25 (Roy et al. 2016)';
  var EPOCAS = [
    { id: '2023-24', nome: '2023-2024', fonte: L8 },
    { id: '2016-17', nome: '2016-2017', fonte: L8 },
    { id: '2001-05', nome: '2001-2005', fonte: L30 },
    { id: '1995-00', nome: '1995-2000', fonte: L30 },
    { id: '1985-90', nome: '1985-1990', fonte: L30 },
    { id: '1979', nome: '1979', dif: true,
      fonte: 'Ocupa&ccedil;&atilde;o do solo 1979 (Filipa Guilherme), vectorial; vegeta&ccedil;&atilde;o = &aacute;rvores, arbustos e herb&aacute;ceas, edificado = elementos artificiais' },
    { id: '1972-76', nome: '1972-1976', dif: true,
      fonte: 'Landsat MSS, 60 m (resolu&ccedil;&atilde;o mais grosseira); NDVI &ge; 0,25' },
    { id: '1947', nome: '1947', dif: true,
      fonte: 'Ortofotomapa 1947 (CIIMAR/FCUP); Pixel RF (textura local), limpo com Sentinel-2 e Landsat 1985' }
  ];
  var RESSALVA = 'Fonte diferente das outras &eacute;pocas: n&atilde;o compar&aacute;vel em rigor.';
  var BOUNDS_1947 = [[41.12912995365261, -8.700884213830351], [41.189999037480554, -8.539187462666328]];
  var COR = { veg: '#00FF00', edif: '#C4A882', veg47: '#228B22', edif47: '#888888', perda: '#FF4444', ganho: '#44FF44' };
  var CLASSES_1979 = [
    ['ABE', 'Elementos artificiais (constru&iacute;do)', '#888888'],
    ['TRS', '&Aacute;rvores e arbustos', '#1B5E20'],
    ['HER', 'Herb&aacute;ceas', '#9CCC65'],
    ['SPV', 'Vegeta&ccedil;&atilde;o esparsa (terrestre)', '#E0C080'],
    ['AQU', 'Vegeta&ccedil;&atilde;o esparsa (aqu&aacute;tica)', '#4FC3F7']
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

  var pc = function (x) { return x.toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' %'; };
  var ha = function (x) { return x.toLocaleString('pt-PT', { maximumFractionDigits: 0 }) + ' ha'; };
  var por = function (id) { return EPOCAS.filter(function (e) { return e.id === id; })[0]; };

  MU.registarTema({
    id: 'historico',
    rotulo: 'Histórico 1947-2024',
    fundo: 'positron',
    dados: 'historico',
    ctx: { limites: { on: true, cor: '#444444' }, densidade: { on: false } },
    fonte: 'Ortofotomapa 1947 (CIIMAR/FCUP) &bull; Landsat MSS/TM/OLI (USGS/NASA)<br>' +
           '1947: Pixel RF (textura local), limpo com Sentinel-2 e Landsat 1985<br>' +
           'Hist&oacute;rico: NDVI &ge; 0,25 &bull; Roy et al. 2016<br>' +
           'Ocupa&ccedil;&atilde;o do solo 1979: <a href="https://www.cibio.up.pt/en/people/details/filipa-isabel-jesus-guilherme/" target="_blank" rel="noopener">Filipa Guilherme</a><br>' +
           'Limites: CAOP 2025 (DGT)',

    async montar(painel) {
      var D = MU.DADOS.historico, map = MU.map;
      var est = { epoca: null, perdaGanho: false, det79: false };
      var activo = false, visiveis = [], cache = {}, opac = 1, mud = null, det = null;
      var PANES = { masc: 'hMascPane', o47: 'h1947Pane' };
      [['h1947Pane', 405], ['hCobPane', 408], ['hMascPane', 415], ['hMudPane', 420]]
        .forEach(function (p) { map.createPane(p[0]); map.getPane(p[0]).style.zIndex = p[1]; });

      /* ---- painel ---- */
      var num = D.numeros;
      var grafico = EPOCAS.map(function (e) {
        var n = num[e.id];
        var tip = e.nome + ': vegetação ' + pc(n.veg) + ', edificado ' + pc(n.edif) +
                  (n.cobertura < 100 ? ' (cobertura ' + pc(n.cobertura) + ' do concelho)' : '');
        return '<button type="button" class="h-col" data-epoca="' + e.id + '" title="' + tip + '">' +
          '<span class="h-barras"><i class="h-b h-bv" style="height:' + (n.veg * 0.6).toFixed(1) + 'px"></i>' +
          '<i class="h-b h-be" style="height:' + (n.edif * 0.6).toFixed(1) + 'px"></i></span>' +
          '<span class="h-ano">' + e.id.slice(0, 4) + (e.dif ? '*' : '') + '</span></button>';
      }).join('');
      var cobBaixa = EPOCAS.filter(function (e) { return num[e.id].cobertura < 100; }).map(function (e) {
        return e.nome + ': cobertura ' + pc(num[e.id].cobertura) + ' do concelho';
      });
      painel.innerHTML =
        '<b style="font-size:14px;">Vegeta&ccedil;&atilde;o e edificado do Porto</b><br>' +
        '<span class="tema-sub">1947-2024 &bull; escolhe uma &eacute;poca</span>' +
        '<div class="h-tempo" id="h-tempo">' + EPOCAS.map(function (e) {
          return '<button type="button" class="ab-btn" data-epoca="' + e.id + '">' + e.id + '</button>';
        }).join('') + '</div>' +
        '<div class="h-fonte" id="h-fonte"></div>' +
        '<div class="section">% do concelho em cada &eacute;poca</div>' +
        '<div class="h-graf" id="h-graf">' + grafico + '</div>' +
        '<div class="leg h-leg2"><div><i style="background:' + COR.veg + '"></i><span>vegeta&ccedil;&atilde;o</span>' +
          '<i style="background:' + COR.edif + ';margin-left:8px"></i><span>edificado</span></div></div>' +
        '<div class="h-nums" id="h-nums"></div>' +
        '<div class="nota">* fonte diferente (n&atilde;o compar&aacute;vel em rigor). O resto (solo nu, &aacute;gua, sombras) n&atilde;o est&aacute; contado.' +
          (cobBaixa.length ? '<br>' + cobBaixa.join('<br>') : '') + '</div>' +
        '<div class="section">Vista</div>' +
        '<div id="h-mud"></div>' +
        '<button type="button" id="h-79" class="ab-btn" style="display:none;margin:4px 0;width:100%">Ver as 5 classes de 1979</button>' +
        '<div class="leg" id="h-leg"></div>' +
        '<div class="row" style="margin-top:4px;"><label style="font-size:11px;color:#666;" for="h-op">Opacidade</label>' +
          '<input type="range" id="h-op" min="10" max="100" step="5" value="100" style="flex:1;">' +
          '<span id="h-op-v" class="tema-sub" style="width:30px;">100%</span></div>';

      /* filtro SVG para tingir a 1947 (imagens a 1 bit; sem canvas de 170 Mpx) */
      var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', '0'); svg.setAttribute('height', '0'); svg.style.position = 'absolute';
      var matriz = function (hex) {
        var c = MU.hexToRgb(hex).map(function (v) { return (v / 255).toFixed(4); });
        return '0 0 0 0 ' + c[0] + '  0 0 0 0 ' + c[1] + '  0 0 0 0 ' + c[2] + '  0 0 0 1 0';
      };
      svg.innerHTML = [['veg', COR.veg47], ['edif', COR.edif47]].map(function (k) {
        return '<filter id="h-tint-' + k[0] + '" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="' +
               matriz(k[1]) + '"/></filter>';
      }).join('');
      painel.appendChild(svg);

      /* ---- camadas de cada época (criadas à primeira utilização) ---- */
      var imagem = function (url, bounds, pane) {
        return L.imageOverlay(url, bounds, { pane: pane, opacity: opac });
      };
      function camadas(id, panes) {
        var k = id + '|' + panes.masc;
        if (cache[k]) return cache[k];
        var ls;
        if (id === '1947') {
          ls = [['uso_1947_vegetacao', 'veg'], ['uso_1947_edificado', 'edif']].map(function (d) {
            var ov = imagem(D[d[0]], BOUNDS_1947, panes.o47);
            ov.on('add', function () { ov.getElement().style.filter = 'url(#h-tint-' + d[1] + ')'; });
            return ov;
          });
        } else {
          ls = ['veg', 'edif'].map(function (p) { return imagem(D[p + '_' + id], MU.BOUNDS, panes.masc); });
        }
        return (cache[k] = ls);
      }
      function perdaGanho() {
        return mud || (mud = [['veg_perda'], ['veg_ganho']].map(function (d) {
          return imagem(D[d[0]], MU.BOUNDS, 'hMudPane');
        }));
      }
      function detalhe79() {
        return det || (det = CLASSES_1979.map(function (c) {
          return L.geoJson(D.cobertura_1979, {
            pane: 'hCobPane',
            filter: function (f) { return f.properties.c === c[0]; },
            style: function () { return { stroke: false, fillColor: c[2], fillOpacity: 0.75 }; },
            onEachFeature: function (f, layer) {
              layer.bindPopup('<b style="font-size:13px;">' + c[1] + '</b><br><span style="color:#666;">1979 &mdash; ' +
                f.properties.ha.toLocaleString('pt-PT') + ' ha</span>');
            }
          });
        }));
      }

      /* ---- estado → mapa e painel ---- */
      var leg = function (cor, txt) { return '<div><i style="background:' + cor + '"></i><span>' + txt + '</span></div>'; };
      function mostrar() {
        visiveis.forEach(function (l) { map.removeLayer(l); });
        visiveis = [];
        if (!activo) return;
        var ls = est.perdaGanho ? perdaGanho()
               : (est.epoca === '1979' && est.det79) ? detalhe79() : camadas(est.epoca, PANES);
        ls.forEach(function (l) { l.addTo(map); visiveis.push(l); });
        var e = por(est.epoca), n = num[est.epoca];
        painel.querySelectorAll('[data-epoca]').forEach(function (b) {
          b.classList.toggle('active', !est.perdaGanho && b.dataset.epoca === est.epoca);
        });
        painel.querySelector('#h-fonte').innerHTML = '<b>' + e.nome + '</b>: ' + e.fonte + (e.dif ? '<br><i>' + RESSALVA + '</i>' : '');
        painel.querySelector('#h-nums').innerHTML = e.nome + ': vegeta&ccedil;&atilde;o <b>' + pc(n.veg) + '</b> &bull; edificado <b>' + pc(n.edif) + '</b>';
        var b79 = painel.querySelector('#h-79');
        b79.style.display = (est.epoca === '1979' && !est.perdaGanho) ? 'block' : 'none';
        b79.textContent = est.det79 ? 'Voltar às 2 classes' : 'Ver as 5 classes de 1979';
        painel.querySelector('#h-leg').innerHTML = est.perdaGanho
          ? leg(COR.perda, 'Perda de vegeta&ccedil;&atilde;o (1985-90 &rarr; 2023-24)') + leg(COR.ganho, 'Ganho de vegeta&ccedil;&atilde;o')
          : (est.epoca === '1979' && est.det79)
            ? CLASSES_1979.map(function (c) { return leg(c[2], c[1] + ' (' + ha(D.cobertura_1979_ha[c[0]]) + ')'); }).join('')
            : est.epoca === '1947' ? leg(COR.veg47, 'Vegeta&ccedil;&atilde;o 1947') + leg(COR.edif47, 'Edificado 1947')
            : leg(COR.veg, 'Vegeta&ccedil;&atilde;o') + leg(COR.edif, 'Edificado');
      }
      function seleccionar(id) {
        if (!por(id)) return;
        if (id !== '1979') est.det79 = false;
        est.epoca = id; est.perdaGanho = false;
        if (boxMud) boxMud.cb.checked = false;
        mostrar();
      }

      var boxMud = MU.linha(painel.querySelector('#h-mud'), {
        label: 'Perda e ganho de vegetação (1985-90 → 2023-24)', checked: false,
        onToggle: function (on) { est.perdaGanho = on; mostrar(); }
      });
      painel.querySelector('#h-79').addEventListener('click', function () { est.det79 = !est.det79; mostrar(); });
      painel.addEventListener('click', function (ev) {
        var b = ev.target.closest && ev.target.closest('#h-tempo [data-epoca], #h-graf [data-epoca]');
        if (b) seleccionar(b.dataset.epoca);
      });
      painel.querySelector('#h-op').addEventListener('input', function () {
        opac = +this.value / 100;
        painel.querySelector('#h-op-v').textContent = this.value + '%';
        Object.keys(cache).forEach(function (k) { cache[k].forEach(function (o) { o.setOpacity(opac); }); });
        if (mud) mud.forEach(function (o) { o.setOpacity(opac); });
      });

      MU.historico = {
        epocas: EPOCAS.map(function (e) { return e.id; }),
        seleccionar: seleccionar,
        estado: function () { return { epoca: est.epoca, perdaGanho: est.perdaGanho, comparar: false }; },
        ligar1979Detalhe: function (on) { est.det79 = !!on; mostrar(); },
        _ligar: function (on) { activo = on; if (on) { if (!est.epoca) est.epoca = '2023-24'; } mostrar(); }
      };
    },

    activar() {
      var h = MU.historico;
      h._ligar(true);
      if (MU.param('vista') === '1947') {
        h.seleccionar('1947');
        if (!MU.fundoManual) MU.setFundo('orto1947');
      } else h.seleccionar(h.estado().epoca || '2023-24');
    },
    desactivar() { MU.historico._ligar(false); }
  });
})();
