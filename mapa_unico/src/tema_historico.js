/* Tema «Histórico»: escada das épocas 2023-24 → 1947 (uma de cada vez, cada uma com a sua cor), números-chave,
   edificado opcional, perda e ganho de vegetação, cortina para comparar duas épocas e, para 1979, o detalhe
   das 5 classes de Filipa Guilherme. (sem NDVI — a página ndvi_historico/ continua à parte). */
(function () {
  /* id, rótulo, fonte/resolução, fonte diferente das restantes (ressalva), cor da época (maquete V2b) */
  var L30 = 'Landsat 5 TM, 30 m; NDVI &ge; 0,25';
  var L8 = 'Landsat 8/9 OLI (harmonizado para TM, Roy et al. 2016), 30 m; NDVI &ge; 0,25';
  var EPOCAS = [
    { id: '2023-24', nome: '2023-2024', curto: '2023–24', cor: '#2E8B4E', fonte: L8 },
    { id: '2016-17', nome: '2016-2017', curto: '2016–17', cor: '#7A55B8', fonte: L8 },
    { id: '2001-05', nome: '2001-2005', curto: '2001–05', cor: '#C08A12', fonte: L30 },
    { id: '1995-00', nome: '1995-2000', curto: '1995–2000', cor: '#10A38A', fonte: L30 },
    { id: '1985-90', nome: '1985-1990', curto: '1985–90', cor: '#3E6AB3', fonte: L30 },
    { id: '1979', nome: '1979', curto: '1979', cor: '#B03A7A', dif: true,
      fonte: 'Ocupa&ccedil;&atilde;o do solo 1979 (Filipa Guilherme), vectorial; vegeta&ccedil;&atilde;o = &aacute;rvores, arbustos e herb&aacute;ceas, edificado = elementos artificiais' },
    { id: '1947', nome: '1947', curto: '1947', cor: '#8C5A2B', dif: true,
      fonte: 'Ortofotomapa 1947 (CIIMAR/FCUP); Pixel RF (textura local), limpo com Sentinel-2 e Landsat 1985' }
  ];
  var RESSALVA = 'Fonte diferente das outras &eacute;pocas: n&atilde;o compar&aacute;vel em rigor.';
  var BOUNDS_1947 = [[41.12912995365261, -8.700884213830351], [41.189999037480554, -8.539187462666328]];
  var COR = { edif: '#C4A882', perda: '#6A3FB5', ganho: '#E0B000' };  /* todas as máscaras são tingidas por filtro SVG */
  var CLASSES_1979 = [
    ['ABE', 'Elementos artificiais (constru&iacute;do)', '#C4A882'],
    ['TRS', '&Aacute;rvores e arbustos', '#357A47'],
    ['HER', 'Herb&aacute;ceas', '#8DBF7E'],
    ['SPV', 'Vegeta&ccedil;&atilde;o esparsa (terrestre)', '#D9CBA0'],
    ['AQU', 'Vegeta&ccedil;&atilde;o esparsa (aqu&aacute;tica)', '#86BCD6']
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

  var pc = function (x) { return MU.n(x, 1) + ' %'; };
  var ha = function (x) { return MU.n(x) + ' ha'; };
  var por = function (id) { return EPOCAS.filter(function (e) { return e.id === id; })[0]; };

  MU.registarTema({
    id: 'historico',
    rotulo: 'Histórico 1947–2024',
  artigo: { url: 'https://portoverde.pt/posts/mudanca-verde-porto-1947-2025/' },
    fundo: 'carta',
    dados: 'historico',
    ctx: { limites: { on: true }, densidade: { on: false } },
    fonte: 'Ortofotomapa 1947 (CIIMAR/FCUP) &middot; Landsat MSS/TM/OLI (USGS/NASA), NDVI &ge; 0,25 (Roy et al. 2016) &middot; ' +
           '1947: Pixel RF (textura local), limpo com Sentinel-2 e Landsat 1985 &middot; ' +
           'ocupa&ccedil;&atilde;o do solo 1979: <a href="https://www.cibio.up.pt/en/people/details/filipa-isabel-jesus-guilherme/" target="_blank" rel="noopener">Filipa Guilherme</a> &middot; ' +
           'limites: CAOP 2025 (DGT). Hectares por contagem de p&iacute;xeis (&asymp; 57 m&sup2; cada) dentro do concelho.',

    async montar(painel) {
      var D = MU.DADOS.historico, S = MU.DADOS.contexto.stats, map = MU.map, self = this;
      var est = { epoca: null, edif: false, perdaGanho: false, det79: false, comparar: false, esq: '2023-24', dir: '1947' };
      var activo = false, visiveis = [], cache = {}, opac = 0.9, mud = null, det = null, pos = 0.5;
      var PANES = { masc: 'hMascPane', o47: 'h1947Pane' };
      var PANES_ESQ = { masc: 'hEsqPane', o47: 'hEsqPane' }, PANES_DIR = { masc: 'hDirPane', o47: 'hDirPane' };
      [['h1947Pane', 405], ['hCobPane', 408], ['hMascPane', 415], ['hEsqPane', 416], ['hDirPane', 417], ['hMudPane', 420]]
        .forEach(function (p) { map.createPane(p[0]); map.getPane(p[0]).style.zIndex = p[1]; });

      /* ---- painel ---- */
      var num = D.numeros;
      var escada = EPOCAS.map(function (e) {
        var n = num[e.id];
        var tip = e.nome + ': vegetação ' + pc(n.veg) + ', edificado ' + pc(n.edif) +
                  (n.cobertura < 100 ? ' (cobertura ' + pc(n.cobertura) + ' do concelho)' : '');
        return '<button type="button" role="radio" data-epoca="' + e.id + '" style="--ep:' + e.cor + '" title="' + tip + '">' +
          '<span>' + e.curto + (e.dif ? '<small>outra fonte</small>' : '') + '</span>' +
          '<span class="b"><i style="width:' + n.veg.toFixed(1) + '%"></i></span><span>' + pc(n.veg) + '</span></button>';
      }).join('');
      var opcoes = EPOCAS.map(function (e) { return '<option value="' + e.id + '">' + e.nome + '</option>'; }).join('');
      var cobBaixa = EPOCAS.filter(function (e) { return num[e.id].cobertura < 100; }).map(function (e) {
        return e.nome + ': cobertura ' + pc(num[e.id].cobertura) + ' do concelho';
      });
      painel.innerHTML =
        '<p class="desc">Vegeta&ccedil;&atilde;o do concelho em sete &eacute;pocas. 1947 e 1979 v&ecirc;m de outras fontes: compara&ccedil;&atilde;o indicativa.</p>' +
        '<div class="nums" id="h-nums"></div>' +
        '<div id="h-escada">' + MU.cab2('&Eacute;poca &middot; vegeta&ccedil;&atilde;o no concelho', '0&ndash;100 %') +
        '<div class="escada" id="h-tempo" role="radiogroup" aria-label="&Eacute;poca">' + escada + '</div></div>' +
        '<div class="h-comp" id="h-comp" style="display:none">' + MU.cab2('Comparar duas &eacute;pocas', 'arrasta a barra no mapa') +
          '<label>Esquerda <select id="h-esq">' + opcoes + '</select></label>' +
          '<label>Direita <select id="h-dir">' + opcoes + '</select></label></div>' +
        '<p class="h-fonte" id="h-fonte"></p>' +
        MU.cab2('Camadas', '') + '<div id="h-parq"></div><div id="h-mud"></div><div id="h-cams"></div>' +
        '<div class="leg" id="h-leg"></div>' +
        '<button type="button" id="h-cmp" class="btn">Comparar duas &eacute;pocas</button>' +
        '<button type="button" id="h-79" class="btn" style="display:none">Ver as 5 classes de 1979</button>' +
        '<p class="fonte" style="margin-top:12px">* outra fonte: n&atilde;o compar&aacute;vel em rigor. O resto (solo nu, &aacute;gua, sombras) n&atilde;o est&aacute; contado.' +
          (cobBaixa.length ? '<br>' + cobBaixa.join('<br>') : '') + '</p>';

      /* filtro SVG que tinge as máscaras (alfa) com a cor de cada época; sem canvas de 170 Mpx */
      var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', '0'); svg.setAttribute('height', '0'); svg.style.position = 'absolute';
      var matriz = function (hex) {
        var c = MU.hexToRgb(hex).map(function (v) { return (v / 255).toFixed(4); });
        return '0 0 0 0 ' + c[0] + '  0 0 0 0 ' + c[1] + '  0 0 0 0 ' + c[2] + '  0 0 0 1 0';
      };
      var tons = [['edif', COR.edif], ['perda', COR.perda], ['ganho', COR.ganho]]
        .concat(EPOCAS.map(function (e) { return ['ep' + e.id, e.cor]; }));
      svg.innerHTML = tons.map(function (k) {
        return '<filter id="h-tint-' + k[0] + '" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="' +
               matriz(k[1]) + '"/></filter>';
      }).join('');
      painel.appendChild(svg);

      /* ---- camadas de cada época (criadas à primeira utilização) ---- */
      var imagem = function (url, bounds, pane, tom) {
        var ov = L.imageOverlay(url, bounds, { pane: pane, opacity: opac });
        ov.on('add', function () { ov.getElement().style.filter = 'url(#h-tint-' + tom + ')'; });
        return ov;
      };
      function camadas(id, panes) {   // [vegetação, edificado]
        var k = id + '|' + panes.masc;
        if (cache[k]) return cache[k];
        var ls;
        if (id === '1947') {
          ls = [['uso_1947_vegetacao', 'ep1947'], ['uso_1947_edificado', 'edif']].map(function (d) {
            return imagem(D[d[0]], BOUNDS_1947, panes.o47, d[1]);
          });
        } else {
          ls = [['veg', 'ep' + id], ['edif', 'edif']].map(function (p) { return imagem(D[p[0] + '_' + id], MU.BOUNDS, panes.masc, p[1]); });
        }
        return (cache[k] = ls);
      }
      var daEpoca = function (id, panes) { var c = camadas(id, panes); return est.edif ? c : [c[0]]; };
      function perdaGanho() {
        return mud || (mud = [['veg_perda', 'perda'], ['veg_ganho', 'ganho']].map(function (d) {
          return imagem(D[d[0]], MU.BOUNDS, 'hMudPane', d[1]);
        }));
      }
      function detalhe79() {
        return det || (det = CLASSES_1979.map(function (c) {
          return L.geoJson(D.cobertura_1979, {
            pane: 'hCobPane',
            filter: function (f) { return f.properties.c === c[0]; },
            style: function () { return { stroke: false, fillColor: c[2], fillOpacity: 0.75 }; },
            onEachFeature: function (f, layer) {
              layer.bindPopup('<b style="font-size:13px;">' + c[1] + '</b><br><span style="color:#4B6270;">1979 &mdash; ' +
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

      /* ---- linhas de camadas ---- */
      var q = function (s) { return painel.querySelector(s) || document.querySelector(s); };   // #h-nums vive no cartão do mapa
      var boxEdif = MU.linha(q('#h-cams'), {
        label: 'Edificado na &eacute;poca escolhida', checked: false, color: COR.edif,
        onToggle: function (on) { est.edif = on; mostrar(); }
      });
      var boxVeg = MU.linha(q('#h-cams'), {
        label: 'Vegeta&ccedil;&atilde;o na &eacute;poca escolhida', checked: true, color: EPOCAS[0].cor,
        onToggle: function (on) { est.veg = on; mostrar(); },
        opacidade: { v: 90, min: 10, max: 100, step: 5, id: 'h-op', onInput: function (v) {
          opac = v / 100;
          Object.keys(cache).forEach(function (k) { cache[k].forEach(function (o) { o.setOpacity(opac); }); });
          if (mud) mud.forEach(function (o) { o.setOpacity(opac); });
        } }
      });
      est.veg = true;
      var boxMud = MU.linha(q('#h-mud'), {
        label: 'Perda e ganho 1985-90 &rarr; 2023-24', checked: false,
        color: 'linear-gradient(90deg,' + COR.perda + ' 0 50%,' + COR.ganho + ' 50%)',
        leg: [[COR.perda, 'Perda de vegeta&ccedil;&atilde;o &middot; <span class="n">' + ha(S.perda) + '</span>'],
              [COR.ganho, 'Ganho de vegeta&ccedil;&atilde;o &middot; <span class="n">' + ha(S.ganho) + '</span>']],
        onToggle: function (on) { est.perdaGanho = on; mostrar(); }
      });
      MU.linhaParques(this, q('#h-parq'), { on: false, contorno: true, label: 'Parques e jardins actuais (contorno)', ha: false });

      /* ---- estado → mapa e painel ---- */
      var leg = function (cor, txt) { return '<div><i style="background:' + cor + '"></i><span>' + txt + '</span></div>'; };
      var difPP = function (a, b) { var d = num[a].veg - num[b].veg; return MU.n(Math.abs(d), 1); };
      function mostrar() {
        visiveis.forEach(function (l) { map.removeLayer(l); });
        visiveis = [];
        sep.style.display = (activo && est.comparar) ? 'block' : 'none';
        if (!activo) return;
        var ls = est.comparar ? daEpoca(est.esq, PANES_ESQ).concat(daEpoca(est.dir, PANES_DIR))
               : est.perdaGanho ? perdaGanho()
               : (est.epoca === '1979' && est.det79) ? detalhe79() : daEpoca(est.epoca, PANES);
        if (!est.comparar && !est.perdaGanho && !est.det79 && !est.veg) ls = ls.slice(1);
        ls.forEach(function (l) { l.addTo(map); visiveis.push(l); });
        q('#h-escada').style.display = est.comparar ? 'none' : 'block';
        q('#h-comp').style.display = est.comparar ? 'block' : 'none';
        var bc = q('#h-cmp'); bc.textContent = est.comparar ? 'Sair da comparação' : 'Comparar duas épocas'; bc.classList.toggle('active', est.comparar);
        boxMud.cb.disabled = est.comparar;
        painel.querySelectorAll('#h-tempo [data-epoca]').forEach(function (b) {
          var on = !est.comparar && !est.perdaGanho && b.dataset.epoca === est.epoca;
          b.classList.toggle('active', on); b.setAttribute('aria-checked', on);
        });
        var b79 = q('#h-79');
        if (est.comparar) {
          var a = por(est.esq), d = por(est.dir), na = num[est.esq], nd = num[est.dir];
          q('#h-esq').value = est.esq; q('#h-dir').value = est.dir;
          boxVeg.row.style.setProperty('--sw', 'linear-gradient(90deg,' + a.cor + ' 0 50%,' + d.cor + ' 50%)');
          q('#h-fonte').innerHTML = '<b>Esq. ' + a.nome + '</b>: ' + a.fonte + '<br><b>Dir. ' + d.nome + '</b>: ' + d.fonte +
            ((a.dif || d.dif) ? '<br><i>' + RESSALVA + '</i>' : '');
          q('#h-nums').innerHTML = MU.htmlNums([
            { v: MU.n(na.veg, 1), u: '%', r: 'de vegeta&ccedil;&atilde;o em ' + a.nome + ' (esq.)' },
            { v: MU.n(nd.veg, 1), u: '%', r: 'em ' + d.nome + ' (dir.)' },
            { v: difPP(est.esq, est.dir), u: 'p.p.', r: 'de diferen&ccedil;a' }
          ]);
          b79.style.display = 'none';
          q('#h-leg').innerHTML = leg(a.cor, 'Vegeta&ccedil;&atilde;o, esquerda: ' + a.nome) + leg(d.cor, 'Vegeta&ccedil;&atilde;o, direita: ' + d.nome) +
            (est.edif ? leg(COR.edif, 'Edificado') : '');
          sep.querySelector('.h-etq-e').textContent = a.nome;
          sep.querySelector('.h-etq-d').textContent = d.nome;
          recorte();
          return;
        }
        var e = por(est.epoca), n = num[est.epoca];
        boxVeg.row.style.setProperty('--sw', e.cor);
        if (est.perdaGanho) {
          q('#h-fonte').innerHTML = '<b>Perda e ganho</b>: diferen&ccedil;a entre 1985-90 e 2023-24. ' + por('1985-90').fonte + ' / ' + por('2023-24').fonte;
          q('#h-nums').innerHTML = MU.htmlNums([
            { v: MU.n(S.perda), u: 'ha', r: 'de vegeta&ccedil;&atilde;o perdida, 1985-90 a 2023-24' },
            { v: MU.n(S.ganho), u: 'ha', r: 'ganhos' },
            { v: difPP('1985-90', '2023-24'), u: 'p.p.', r: 'de vegeta&ccedil;&atilde;o a menos' }
          ]);
        } else {
          q('#h-fonte').innerHTML = '<b>' + e.nome + '</b>: ' + e.fonte + (e.dif ? '<br><i>' + RESSALVA + '</i>' : '');
          q('#h-nums').innerHTML = MU.htmlNums([
            { v: MU.n(n.veg, 1), u: '%', r: 'de vegeta&ccedil;&atilde;o em ' + e.nome + (e.dif ? ' (outra fonte)' : '') },
            { v: MU.n(n.edif, 1), u: '%', r: 'de edificado' },
            { v: difPP('1947', '2023-24'), u: 'p.p.', r: 'de vegeta&ccedil;&atilde;o a menos desde 1947' }
          ]);
        }
        b79.style.display = (est.epoca === '1979' && !est.perdaGanho) ? 'block' : 'none';
        b79.textContent = est.det79 ? 'Voltar às 2 classes' : 'Ver as 5 classes de 1979';
        b79.classList.toggle('active', est.det79);
        q('#h-leg').innerHTML = (est.epoca === '1979' && est.det79 && !est.perdaGanho)
          ? CLASSES_1979.map(function (c) { return leg(c[2], c[1] + ' (' + ha(D.cobertura_1979_ha[c[0]]) + ')'); }).join('')
          : '';
      }
      function seleccionar(id) {
        if (!por(id)) return;
        if (id !== '1979') est.det79 = false;
        est.epoca = id; est.perdaGanho = false; est.comparar = false;
        if (boxMud) { boxMud.cb.checked = false; boxMud.row.classList.add('off'); }
        mostrar();
      }
      function comparar(on, esq, dir) {
        if (on) {
          if (esq && por(esq)) est.esq = esq;
          if (dir && por(dir)) est.dir = dir;
          est.perdaGanho = false; est.det79 = false; boxMud.cb.checked = false; boxMud.row.classList.add('off');
        } else if (est.comparar) est.epoca = est.esq;
        est.comparar = !!on;
        mostrar();
      }

      q('#h-79').addEventListener('click', function () { est.det79 = !est.det79; mostrar(); });
      q('#h-cmp').addEventListener('click', function () { comparar(!est.comparar); });
      q('#h-esq').addEventListener('change', function () { est.esq = this.value; mostrar(); });
      q('#h-dir').addEventListener('change', function () { est.dir = this.value; mostrar(); });
      q('#h-tempo').addEventListener('click', function (ev) {
        var b = ev.target.closest && ev.target.closest('[data-epoca]');
        if (b) seleccionar(b.dataset.epoca);
      });
      q('#h-tempo').addEventListener('keydown', function (ev) {   // setas percorrem as épocas (radiogroup)
        var d = (ev.key === 'ArrowDown' || ev.key === 'ArrowRight') ? 1 : (ev.key === 'ArrowUp' || ev.key === 'ArrowLeft') ? -1 : 0;
        if (!d) return;
        var i = EPOCAS.indexOf(por(est.epoca)) + d;
        if (i < 0 || i >= EPOCAS.length) return;
        seleccionar(EPOCAS[i].id); q('#h-tempo [data-epoca="' + EPOCAS[i].id + '"]').focus(); ev.preventDefault();
      });

      MU.historico = {
        epocas: EPOCAS.map(function (e) { return e.id; }),
        seleccionar: seleccionar,
        comparar: comparar,
        cortina: cortina,
        estado: function () { return { epoca: est.epoca, perdaGanho: est.perdaGanho, comparar: est.comparar, edif: est.edif }; },
        ligar1979Detalhe: function (on) { est.det79 = !!on; mostrar(); },
        _ligar: function (on) { activo = on; if (on && !est.epoca) est.epoca = '2023-24'; mostrar(); }
      };
    },

    activar() {
      var h = MU.historico;
      h._ligar(true);   // mantém o estado (época, cortina, perda/ganho) ao voltar ao tema
      MU.activarParques(this);
      if (MU.param('vista') === '1947') {
        h.seleccionar('1947');
        if (!MU.fundoManual) MU.setFundo('orto1947');
      }
    },
    aoHash() {   // só mudou um parâmetro do hash com o tema aberto
      if (MU.param('vista') === '1947') {
        MU.historico.seleccionar('1947');
        if (!MU.fundoManual) MU.setFundo('orto1947');
      }
    },
    desactivar() { MU.historico._ligar(false); MU.desactivarParques(this); }
  });
})();
