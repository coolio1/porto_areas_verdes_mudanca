/* Tema «Casos»: horrores e sucessos urbanísticos, patrimoniais e de verde do Porto, com fonte e fotos antes/depois.
   Dados de mapa_unico.py (`dados_casos`, texto já escapado). Hover = cartão; clique = ficha fixa (MU.ficha com `corpo`);
   `#tema=casos&caso=<slug>` abre um caso. Marcador = disco com glifo do tipo; cor = galeria (vermelho horrores, azul sucessos). */
(function () {
  var TIPOS = [
    ['arvores', 'Árvores e verde'], ['demolicao', 'Demolições'], ['patrimonio_alterado', 'Património alterado'],
    ['lojas_historicas', 'Lojas históricas']
  ];
  var ROTULO = {}; TIPOS.forEach(function (t) { ROTULO[t[0]] = t[1]; });
  var COR = { horrores: '#B42F2F', sucessos: '#3E6AB3' };
  var GAL = { horrores: 'Horrores', sucessos: 'Sucessos' };
  var ESTADO = { demolido: 'Demolido', alterado: 'Alterado', abatido: 'Abatido', revertido: 'Revertido', outro: 'Outro' };
  var PAPEL = { antes: 'Antes', depois: 'Depois', outra: 'Foto' };
  // Marcador = disco da cor da galeria com o glifo do tipo (30 px); aproximada = contorno tracejado e miolo branco.
  var GLIFO = {   // [corpo do glifo, preenchido?] no viewBox 30
    arvores: ['<circle cx="15" cy="12" r="5"/><rect x="14" y="15" width="2" height="7"/>', true],
    demolicao: ['<path d="M8 21V12l4 3v-3l4 3V9h6v12z"/>', true],
    patrimonio_alterado: ['<path d="M8 21h14M10 21V13M15 21V13M20 21V13M8 12l7-5 7 5z"/>', false],
    lojas_historicas: ['<path d="M8 12l1.5-4h11L22 12v2a3 3 0 0 1-6 0 3 3 0 0 1-6 0V12zM9 16v6h12v-6"/>', false]
  };

  function svg(tipo, cor, aprox, tam) {
    var g = GLIFO[tipo] || ['<circle cx="15" cy="15" r="4"/>', true], gc = aprox ? cor : '#fff';   // tipo desconhecido (dados em cache antigos): ponto
    var disco = aprox ? '<circle cx="15" cy="15" r="13" fill="#fff" stroke="' + cor + '" stroke-width="2.2" stroke-dasharray="3 2.4"/>'
                      : '<circle cx="15" cy="15" r="13" fill="' + cor + '" stroke="#fff" stroke-width="2"/>';
    var corpo = g[1] ? '<g fill="' + gc + '">' + g[0] + '</g>'
                     : '<g fill="none" stroke="' + gc + '" stroke-width="1.8" stroke-linejoin="round">' + g[0] + '</g>';
    return '<svg viewBox="0 0 30 30" width="' + tam + '" height="' + tam + '" aria-hidden="true">' + disco + corpo + '</svg>';
  }
  // só http(s) nas ligações vindas dos dados
  function seguro(u) { return /^https?:\/\//i.test(u) ? u : '#'; }
  function attr(v) { return String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }
  function texto(h) { var t = document.createElement('textarea'); t.innerHTML = h; return t.value; }
  function foto0(c) {
    return c.fotos.filter(function (f) { return f.papel === 'depois'; })[0] || c.fotos[0];
  }
  function cartaoHover(c) {   // cartão pequeno e inteiro clicável: foto à esquerda (se houver), título, ano · tipo
    var f = foto0(c);
    return '<a class="hv ver-caso' + (f ? '' : ' sem-foto') + '" href="' + attr(c.url) + '" aria-label="Abrir a página: ' + attr(texto(c.titulo)) + '">' +
      (f ? '<img src="' + attr(f.src) + '" alt="" loading="lazy">' : '') +
      '<span class="tx"><span class="t">' + c.titulo + '</span><span class="s">' + c.ano + ' · ' + (ROTULO[c.tipo] || '') + '</span></span></a>';
  }
  function corpoFicha(c) {   // ficha compacta: fotos, resumo (1.º parágrafo, 3 linhas); o texto completo e as referências ficam na página
    var h = '';
    if (c.fotos.length) {
      h += '<div class="fotos n' + Math.min(c.fotos.length, 2) + '">' + c.fotos.slice(0, 2).map(function (f) {
        return '<figure><img src="' + attr(f.src) + '" alt="' + PAPEL[f.papel] + ': ' + c.titulo + '" loading="lazy"><figcaption>' +
          PAPEL[f.papel] + (f.ano ? ' · ' + f.ano : '') + ' · <a href="' + seguro(f.url) + '" target="_blank" rel="noopener noreferrer">' +
          (f.fonte || 'fonte') + '</a></figcaption></figure>';
      }).join('') + '</div>';
    }
    var p1 = (c.corpo_html.match(/<p>[\s\S]*?<\/p>/) || [''])[0];
    h += '<div class="resumo">' + p1 + '</div>';
    var n = c.referencias.length;
    h += '<p class="nrefs">' + n + (n === 1 ? ' referência' : ' referências') + ' · na página do caso</p>';
    return h;
  }

  MU.registarTema({
    id: 'casos',
    rotulo: 'Casos',
    fundo: 'carta',
    dados: 'casos',
    ctx: { limites: { on: true }, densidade: { on: false } },
    fonte: 'imprensa, petições, actas e arquivos citados em cada caso; fotos com crédito e ligação à origem.',

    async montar(painel) {
      var self = this, D = MU.DADOS.casos, N = D.numeros;
      self._grupo = L.layerGroup();
      self._entradas = [];
      self._filtro = { galeria: { horrores: true, sucessos: true }, tipo: {} };
      TIPOS.forEach(function (t) { self._filtro.tipo[t[0]] = true; });
      var nums = '<div class="nums">' + MU.htmlNums([
        { v: MU.n(N.total), u: '', r: 'casos documentados' },
        { v: MU.n(N.por_galeria.horrores), u: '', r: 'horrores' },
        { v: MU.n(N.por_galeria.sucessos), u: '', r: 'sucessos' }
      ]) + '</div>';
      var desc = '<p class="desc">Abates, demolições e alterações que geraram contestação, com fonte e fotos de antes e depois.</p>';
      if (!D.casos.length) {
        painel.innerHTML = desc + nums + '<p class="tema-sub casos-vazio">Ainda sem casos publicados.</p>';
        return;
      }
      painel.innerHTML = desc + nums + '<div class="casos-filtros">' +
        MU.cab2('Galeria', '') + Object.keys(GAL).map(function (g) {
          return '<label><input type="checkbox" data-galeria="' + g + '" checked><span class="sw">' + '<svg viewBox="0 0 30 30" width="20" height="20" aria-hidden="true"><circle cx="15" cy="15" r="13" fill="' + COR[g] + '"/></svg>' +
            '</span>' + GAL[g] + ' <em>' + N.por_galeria[g] + '</em></label>';
        }).join('') +
        MU.cab2('Tipo', 'glifo do marcador') + TIPOS.map(function (t) {
          return '<label><input type="checkbox" data-tipo="' + t[0] + '" checked><span class="sw">' + svg(t[0], '#10212C', false, 20) +
            '</span>' + t[1] + ' <em>' + N.por_tipo[t[0]] + '</em></label>';
        }).join('') +
        '<p class="tema-sub">Contorno tracejado: localização aproximada.</p></div>';
      D.casos.forEach(function (c) {
        var m = L.marker([c.lat, c.lon], {
          icon: L.divIcon({ className: 'caso-mk', html: svg(c.tipo, COR[c.galeria], c.aproximada, 30), iconSize: [30, 30], iconAnchor: [15, 15] }),
          pane: MU.pane('mu-casos', 480), keyboard: true, riseOnHover: true
        });
        m.on('add', function () {
          var e = m.getElement(); e.dataset.slug = c.slug;
          e.setAttribute('role', 'button'); e.setAttribute('aria-label', texto(c.titulo) + ', ' + (ROTULO[c.tipo] || ''));
        });
        // cartão ao pairar: abre no marcador e só fecha ~300 ms depois de o rato sair do marcador E do cartão
        m.on('mouseover', function () { self._cartao(c, m); });
        m.on('mouseout', function () { self._agendarFecho(); });
        m.on('click', function (e) { L.DomEvent.stopPropagation(e); self._fecharCartao(); self._abrir(c, false); });
        m.on('keypress', function (e) { if (e.originalEvent.key === 'Enter') { self._fecharCartao(); self._abrir(c, false); } });
        self._entradas.push({ c: c, m: m });
      });
      painel.querySelectorAll('.casos-filtros input').forEach(function (cb) {
        cb.addEventListener('change', function () {
          if (cb.dataset.galeria) self._filtro.galeria[cb.dataset.galeria] = cb.checked;
          else self._filtro.tipo[cb.dataset.tipo] = cb.checked;
          self._aplicar();
        });
      });
      self._aplicar();
    },

    _cartao(c, m) {
      var self = this;
      clearTimeout(self._tFecho);
      if (self._tt) MU.map.closeTooltip(self._tt);
      var tt = L.tooltip({ direction: 'top', offset: [0, -16], className: 'caso-hover', opacity: 1, interactive: true })
        .setLatLng(m.getLatLng()).setContent(cartaoHover(c));
      self._tt = tt;
      MU.map.openTooltip(tt);
      var el = tt.getElement();
      if (el) {
        el.addEventListener('mouseenter', function () { clearTimeout(self._tFecho); });
        el.addEventListener('mouseleave', function () { self._agendarFecho(); });
      }
    },

    _agendarFecho() {
      var self = this;
      clearTimeout(self._tFecho);
      self._tFecho = setTimeout(function () { self._fecharCartao(); }, 300);
    },

    _fecharCartao() {
      clearTimeout(this._tFecho);
      if (this._tt) { MU.map.closeTooltip(this._tt); this._tt = null; }
    },

    _aplicar() {
      var f = this._filtro, g = this._grupo;
      this._entradas.forEach(function (e) {
        var vis = f.galeria[e.c.galeria] && f.tipo[e.c.tipo], tem = g.hasLayer(e.m);
        if (vis && !tem) g.addLayer(e.m); else if (!vis && tem) g.removeLayer(e.m);
      });
    },

    _abrir(c, centrar) {
      MU.ficha({
        titulo: c.titulo, cor: COR[c.galeria], sub: (ROTULO[c.tipo] || '') + ' · ' + c.ano,
        linhas: (c.estado === 'outro' ? [] : [['Estado', ESTADO[c.estado] || c.estado]]).concat([['Local', c.freguesia + (c.aproximada ? ' (aprox.)' : '')]]),
        topo: '<a class="ver-caso" href="' + attr(c.url) + '">Abrir a página completa →</a>',
        corpo: corpoFicha(c)
      });
      document.querySelector('#ficha .x').addEventListener('click', this._limpar);
      MU.setHash({ tema: 'casos', caso: c.slug });
      if (centrar) MU.map.setView([c.lat, c.lon], Math.max(MU.map.getZoom(), 16), { animate: false });
    },

    _limpar() {   // ficha fechada: o caso sai do hash (o hash só guarda o que está aberto)
      if (MU.tema === 'casos' && MU.param('caso')) MU.setHash({ tema: 'casos' });
    },

    _doHash() {
      var s = MU.param('caso');
      var e = s && (this._entradas || []).filter(function (x) { return x.c.slug === s; })[0];
      if (e) { if (!this._grupo.hasLayer(e.m)) this._grupo.addLayer(e.m); this._abrir(e.c, true); }
    },

    aoHash() { this._doHash(); },

    activar() {
      this._grupo.addTo(MU.map);
      MU.map.on('click', this._limpar);
      this._doHash();
    },
    desactivar() {
      this._fecharCartao();
      MU.map.removeLayer(this._grupo);
      MU.map.off('click', this._limpar);
    }
  });
})();
