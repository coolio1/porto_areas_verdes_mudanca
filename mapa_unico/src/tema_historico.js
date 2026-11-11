/* Tema «Histórico»: linha do tempo 2023-24 → 1947 (uma época de cada vez), minigráfico de
   percentagens, perda e ganho de vegetação e, para 1979, o detalhe das 5 classes de Filipa Guilherme.
   (antes: ~30 caixas por camada; sem NDVI — a página ndvi_historico/ continua à parte). */
(function () {
  /* id, rótulo, fonte/resolução, fonte diferente das restantes (ressalva) */
  var L30 = 'Landsat 5 TM, 30 m; NDVI &ge; 0,25';
  var L8 = 'Landsat 8/9 OLI (harmonizado para TM, Roy et al. 2016), 30 m; NDVI &ge; 0,25';
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
      var est = { epoca: null, perdaGanho: false, det79: false, comparar: false, esq: '2023-24', dir: '1947' };
      var activo = false, visiveis = [], cache = {}, opac = 1, mud = null, det = null, pos = 0.5;
      var PANES = { masc: 'hMascPane', o47: 'h1947Pane' };
      var PANES_ESQ = { masc: 'hEsqPane', o47: 'hEsqPane' }, PANES_DIR = { masc: 'hDirPane', o47: 'hDirPane' };
      [['h1947Pane', 405], ['hCobPane', 408], ['hMascPane', 415], ['hEsqPane', 416], ['hDirPane', 417], ['hMudPane', 420]]
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
      var opcoes = EPOCAS.map(function (e) { return '<option value="' + e.id + '">' + e.nome + '</option>'; }).join('');
      var cobBaixa = EPOCAS.filter(function (e) { return num[e.id].cobertura < 100; }).map(function (e) {
        return e.nome + ': cobertura ' + pc(num[e.id].cobertura) + ' do concelho';
      });
      painel.innerHTML =
        '<b style="font-size:14px;">Vegeta&ccedil;&atilde;o e edificado do Porto</b><br>' +
        '<span class="tema-sub">1947-2024 &bull; escolhe uma &eacute;poca</span>' +
        '<div class="h-tempo" id="h-tempo">' + EPOCAS.map(function (e) {
          return '<button type="button" class="ab-btn" data-epoca="' + e.id + '">' + e.id + '</button>';
        }).join('') + '</div>' +
        '<div class="h-comp" id="h-comp" style="display:none">' +
          '<label>Esquerda <select id="h-esq">' + opcoes + '</select></label>' +
          '<label>Direita <select id="h-dir">' + opcoes + '</select></label>' +
          '<span class="tema-sub">Arrasta a barra no mapa.</span></div>' +
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
        '<button type="button" id="h-cmp" class="ab-btn" style="margin:4px 0;width:100%">Comparar duas &eacute;pocas</button>' +
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

      /* ---- cortina: dois conjuntos de overlays, cada um num pane recortado ---- */
      var sep = document.createElement('div');
      sep.id = 'h-cortina'; sep.style.display = 'none';
      sep.innerHTML = '<span class="h-etq h-etq-e"></span><span class="h-linha"></span>' +
                      '<span class="h-asa" tabindex="0" role="slider" aria-label="Posição da comparação" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50" title="Arrasta ou usa as setas">&#8596;</span><span class="h-etq h-etq-d"></span>';
      map.getContainer().appendChild(sep);
      L.DomEvent.disableClickPropagation(sep);
      function recorte() {
        if (!activo || !est.comparar) return;
        var tam = map.getSize(), x = pos * tam.x;
        var nw = map.containerPointToLayerPoint([0, 0]), se = map.containerPointToLayerPoint(tam), cx = nw.x + x;
        map.getPane('hEsqPane').style.clip = 'rect(' + nw.y + 'px,' + cx + 'px,' + se.y + 'px,' + nw.x + 'px)';
        map.getPane('hDirPane').style.clip = 'rect(' + nw.y + 'px,' + se.x + 'px,' + se.y + 'px,' + cx + 'px)';
        sep.style.left = x + 'px';
      }
      map.on('move zoom resize', recorte);
      function cortina(p) {
        pos = Math.max(0.02, Math.min(0.98, p)); recorte();
        sep.querySelector('.h-asa').setAttribute('aria-valuenow', Math.round(pos * 100));
      }
      sep.addEventListener('keydown', function (ev) {
        var d = ev.key === 'ArrowLeft' ? -0.05 : ev.key === 'ArrowRight' ? 0.05 : 0;
        if (d) { cortina(pos + d); ev.preventDefault(); ev.stopPropagation(); }
      });
      var arrasto = false;
      sep.addEventListener('pointerdown', function (ev) {
        if (!ev.target.closest('.h-asa, .h-linha')) return;
        arrasto = true;
        try { ev.target.setPointerCapture(ev.pointerId); } catch (x) { /* sem captura */ }
        ev.preventDefault(); ev.stopPropagation();
      });
      sep.addEventListener('pointermove', function (ev) {
        if (!arrasto) return;
        var r = map.getContainer().getBoundingClientRect();
        cortina((ev.clientX - r.left) / r.width);
      });
      var fimArrasto = function () { arrasto = false; };
      sep.addEventListener('pointerup', fimArrasto);
      sep.addEventListener('pointercancel', fimArrasto);

      /* ---- estado → mapa e painel ---- */
      var leg = function (cor, txt) { return '<div><i style="background:' + cor + '"></i><span>' + txt + '</span></div>'; };
      var legVegEdif = function (id) {
        return id === '1947' ? leg(COR.veg47, 'Vegeta&ccedil;&atilde;o 1947') + leg(COR.edif47, 'Edificado 1947')
                             : leg(COR.veg, 'Vegeta&ccedil;&atilde;o') + leg(COR.edif, 'Edificado');
      };
      var q = function (s) { return painel.querySelector(s); };
      function mostrar() {
        visiveis.forEach(function (l) { map.removeLayer(l); });
        visiveis = [];
        sep.style.display = (activo && est.comparar) ? 'block' : 'none';
        if (!activo) return;
        var ls = est.comparar ? camadas(est.esq, PANES_ESQ).concat(camadas(est.dir, PANES_DIR))
               : est.perdaGanho ? perdaGanho()
               : (est.epoca === '1979' && est.det79) ? detalhe79() : camadas(est.epoca, PANES);
        ls.forEach(function (l) { l.addTo(map); visiveis.push(l); });
        q('#h-tempo').style.display = est.comparar ? 'none' : 'grid';
        q('#h-comp').style.display = est.comparar ? 'block' : 'none';
        q('#h-cmp').textContent = est.comparar ? 'Sair da comparação' : 'Comparar duas épocas';
        boxMud.cb.disabled = est.comparar;
        painel.querySelectorAll('[data-epoca]').forEach(function (b) {
          b.classList.toggle('active', !est.comparar && !est.perdaGanho && b.dataset.epoca === est.epoca);
        });
        var b79 = q('#h-79');
        if (est.comparar) {
          var a = por(est.esq), d = por(est.dir), na = num[est.esq], nd = num[est.dir];
          q('#h-esq').value = est.esq; q('#h-dir').value = est.dir;
          q('#h-fonte').innerHTML = '<b>Esq. ' + a.nome + '</b>: ' + a.fonte + '<br><b>Dir. ' + d.nome + '</b>: ' + d.fonte +
            ((a.dif || d.dif) ? '<br><i>' + RESSALVA + '</i>' : '');
          q('#h-nums').innerHTML = a.nome + ': veg. <b>' + pc(na.veg) + '</b>, edif. <b>' + pc(na.edif) + '</b><br>' +
            d.nome + ': veg. <b>' + pc(nd.veg) + '</b>, edif. <b>' + pc(nd.edif) + '</b>';
          b79.style.display = 'none';
          q('#h-leg').innerHTML = (est.esq === '1947' || est.dir === '1947')
            ? leg(COR.veg, 'Vegeta&ccedil;&atilde;o') + leg(COR.edif, 'Edificado') + leg(COR.veg47, 'Vegeta&ccedil;&atilde;o 1947') + leg(COR.edif47, 'Edificado 1947')
            : legVegEdif(est.esq);
          sep.querySelector('.h-etq-e').textContent = a.nome;
          sep.querySelector('.h-etq-d').textContent = d.nome;
          recorte();
          return;
        }
        var e = por(est.epoca), n = num[est.epoca];
        if (est.perdaGanho) {
          q('#h-fonte').innerHTML = '<b>Perda e ganho</b>: diferen&ccedil;a entre 1985-90 e 2023-24. ' + por('1985-90').fonte + ' / ' + por('2023-24').fonte;
          q('#h-nums').innerHTML = '';
        } else {
          q('#h-fonte').innerHTML = '<b>' + e.nome + '</b>: ' + e.fonte + (e.dif ? '<br><i>' + RESSALVA + '</i>' : '');
          q('#h-nums').innerHTML = e.nome + ': vegeta&ccedil;&atilde;o <b>' + pc(n.veg) + '</b> &bull; edificado <b>' + pc(n.edif) + '</b>';
        }
        b79.style.display = (est.epoca === '1979' && !est.perdaGanho) ? 'block' : 'none';
        b79.textContent = est.det79 ? 'Voltar às 2 classes' : 'Ver as 5 classes de 1979';
        q('#h-leg').innerHTML = est.perdaGanho
          ? leg(COR.perda, 'Perda de vegeta&ccedil;&atilde;o (1985-90 &rarr; 2023-24)') + leg(COR.ganho, 'Ganho de vegeta&ccedil;&atilde;o')
          : (est.epoca === '1979' && est.det79)
            ? CLASSES_1979.map(function (c) { return leg(c[2], c[1] + ' (' + ha(D.cobertura_1979_ha[c[0]]) + ')'); }).join('')
            : legVegEdif(est.epoca);
      }
      function seleccionar(id) {
        if (!por(id)) return;
        if (id !== '1979') est.det79 = false;
        est.epoca = id; est.perdaGanho = false; est.comparar = false;
        if (boxMud) boxMud.cb.checked = false;
        mostrar();
      }
      function comparar(on, esq, dir) {
        if (on) {
          if (esq && por(esq)) est.esq = esq;
          if (dir && por(dir)) est.dir = dir;
          est.perdaGanho = false; est.det79 = false; boxMud.cb.checked = false;
        } else if (est.comparar) est.epoca = est.esq;
        est.comparar = !!on;
        mostrar();
      }

      var boxMud = MU.linha(q('#h-mud'), {
        label: 'Perda e ganho de vegetação (1985-90 → 2023-24)', checked: false,
        onToggle: function (on) { est.perdaGanho = on; mostrar(); }
      });
      q('#h-79').addEventListener('click', function () { est.det79 = !est.det79; mostrar(); });
      q('#h-cmp').addEventListener('click', function () { comparar(!est.comparar); });
      q('#h-esq').addEventListener('change', function () { est.esq = this.value; mostrar(); });
      q('#h-dir').addEventListener('change', function () { est.dir = this.value; mostrar(); });
      painel.addEventListener('click', function (ev) {
        var b = ev.target.closest && ev.target.closest('#h-tempo [data-epoca], #h-graf [data-epoca]');
        if (b) seleccionar(b.dataset.epoca);
      });
      q('#h-op').addEventListener('input', function () {
        opac = +this.value / 100;
        q('#h-op-v').textContent = this.value + '%';
        Object.keys(cache).forEach(function (k) { cache[k].forEach(function (o) { o.setOpacity(opac); }); });
        if (mud) mud.forEach(function (o) { o.setOpacity(opac); });
      });

      MU.historico = {
        epocas: EPOCAS.map(function (e) { return e.id; }),
        seleccionar: seleccionar,
        comparar: comparar,
        cortina: cortina,
        estado: function () { return { epoca: est.epoca, perdaGanho: est.perdaGanho, comparar: est.comparar }; },
        ligar1979Detalhe: function (on) { est.det79 = !!on; mostrar(); },
        _ligar: function (on) { activo = on; if (on && !est.epoca) est.epoca = '2023-24'; mostrar(); }
      };
    },

    activar() {
      var h = MU.historico;
      h._ligar(true);   // mantém o estado (época, cortina, perda/ganho) ao voltar ao separador
      if (MU.param('vista') === '1947') {
        h.seleccionar('1947');
        if (!MU.fundoManual) MU.setFundo('orto1947');
      }
    },
    aoHash() {   // só mudou um parâmetro do hash com o separador aberto
      if (MU.param('vista') === '1947') {
        MU.historico.seleccionar('1947');
        if (!MU.fundoManual) MU.setFundo('orto1947');
      }
    },
    desactivar() { MU.historico._ligar(false); }
  });
})();
