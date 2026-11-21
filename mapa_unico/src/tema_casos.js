/* Tema «Casos»: horrores e sucessos urbanísticos, patrimoniais e de verde do Porto, com fonte e fotos antes/depois.
   Dados de mapa_unico.py (`dados_casos`, texto já escapado). Hover = cartão; clique = ficha fixa (MU.ficha com `corpo`);
   `#tema=casos&caso=<slug>` abre um caso. Forma do marcador = tipo; cor = galeria (vermelho horrores, azul sucessos). */
(function () {
  var TIPOS = [
    ['arvores', 'Árvores e verde'], ['demolicao', 'Demolições'], ['patrimonio_alterado', 'Património alterado'],
    ['interiores_destruidos', 'Interiores destruídos'], ['descaracterizacao', 'Descaracterizações']
  ];
  var ROTULO = {}; TIPOS.forEach(function (t) { ROTULO[t[0]] = t[1]; });
  var COR = { horrores: '#B42F2F', sucessos: '#3E6AB3' };
  var GAL = { horrores: 'Horrores', sucessos: 'Sucessos' };
  var ESTADO = { demolido: 'Demolido', alterado: 'Alterado', abatido: 'Abatido', revertido: 'Revertido', outro: 'Outro' };
  var PAPEL = { antes: 'Antes', depois: 'Depois', outra: 'Foto' };
  var FORMA = {
    arvores: '<circle cx="11" cy="11" r="7"/>',
    demolicao: '<rect x="4" y="4" width="14" height="14"/>',
    patrimonio_alterado: '<polygon points="11,3 19,11 11,19 3,11"/>',
    interiores_destruidos: '<polygon points="11,3.5 19,18 3,18"/>',
    descaracterizacao: '<path d="M8 3h6v5h5v6h-5v5H8v-5H3V8h5z"/>'
  };

  function svg(tipo, cor, aprox, tam) {   // aproximada = contorno tracejado e miolo branco
    var at = aprox ? 'fill="#fff" stroke="' + cor + '" stroke-width="2" stroke-dasharray="2.5 2"'
                   : 'fill="' + cor + '" stroke="#fff" stroke-width="1.5"';
    return '<svg viewBox="0 0 22 22" width="' + tam + '" height="' + tam + '" aria-hidden="true" ' + at + '>' + FORMA[tipo] + '</svg>';
  }
  // só http(s) nas ligações vindas dos dados
  function seguro(u) { return /^https?:\/\//i.test(u) ? u : '#'; }
  function attr(v) { return String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }
  function texto(h) { var t = document.createElement('textarea'); t.innerHTML = h; return t.value; }
  function foto0(c) {
    return c.fotos.filter(function (f) { return f.papel === 'depois'; })[0] || c.fotos[0];
  }
  function cartaoHover(c) {
    var f = foto0(c);
    return '<div class="hv">' + (f ? '<img src="' + attr(f.src) + '" alt="" loading="lazy">' : '') +
      '<div class="t">' + c.titulo + '</div><div class="s">' + c.ano + ' · ' + ROTULO[c.tipo] + '</div></div>';
  }
  function corpoFicha(c) {
    var h = '';
    if (c.fotos.length) {
      h += '<div class="fotos n' + Math.min(c.fotos.length, 2) + '">' + c.fotos.map(function (f) {
        return '<figure><img src="' + attr(f.src) + '" alt="' + PAPEL[f.papel] + ': ' + c.titulo + '" loading="lazy"><figcaption>' +
          PAPEL[f.papel] + (f.ano ? ' · ' + f.ano : '') + ' · <a href="' + seguro(f.url) + '" target="_blank" rel="noopener noreferrer">' +
          (f.fonte || 'fonte') + '</a></figcaption></figure>';
      }).join('') + '</div>';
    }
    h += c.corpo_html;
    h += '<p class="cont"><b>Contestação.</b> ' + c.contestacao + '</p>';
    if (c.criterio === 'editorial') h += '<p class="nota-ed"><b>Avaliação do Porto Verde.</b> ' + c.nota_editorial + '</p>';
    h += '<ol class="refs">' + c.referencias.map(function (r) {
      return '<li><a href="' + seguro(r.url) + '" target="_blank" rel="noopener noreferrer">' + r.titulo + '</a>' +
        (r.data ? ' <span>' + r.data + '</span>' : '') + '</li>';
    }).join('') + '</ol>';
    h += '<a class="ver-caso" href="' + c.url + '">Ver página do caso →</a>';
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
          return '<label><input type="checkbox" data-galeria="' + g + '" checked><span class="sw">' + svg('arvores', COR[g], false, 16) +
            '</span>' + GAL[g] + ' <em>' + N.por_galeria[g] + '</em></label>';
        }).join('') +
        MU.cab2('Tipo', 'forma do marcador') + TIPOS.map(function (t) {
          return '<label><input type="checkbox" data-tipo="' + t[0] + '" checked><span class="sw">' + svg(t[0], '#10212C', false, 16) +
            '</span>' + t[1] + ' <em>' + N.por_tipo[t[0]] + '</em></label>';
        }).join('') +
        '<p class="tema-sub">Contorno tracejado: localização aproximada.</p></div>';
      D.casos.forEach(function (c) {
        var m = L.marker([c.lat, c.lon], {
          icon: L.divIcon({ className: 'caso-mk', html: svg(c.tipo, COR[c.galeria], c.aproximada, 22), iconSize: [22, 22], iconAnchor: [11, 11] }),
          pane: MU.pane('mu-casos', 480), keyboard: true, riseOnHover: true
        });
        m.on('add', function () {
          var e = m.getElement(); e.dataset.slug = c.slug;
          e.setAttribute('role', 'button'); e.setAttribute('aria-label', texto(c.titulo) + ', ' + ROTULO[c.tipo]);
        });
        m.bindTooltip(cartaoHover(c), { direction: 'top', offset: [0, -10], className: 'caso-hover', opacity: 1 });
        m.on('click', function (e) { L.DomEvent.stopPropagation(e); m.closeTooltip(); self._abrir(c, false); });
        m.on('keypress', function (e) { if (e.originalEvent.key === 'Enter') { m.closeTooltip(); self._abrir(c, false); } });
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

    _aplicar() {
      var f = this._filtro, g = this._grupo;
      this._entradas.forEach(function (e) {
        var vis = f.galeria[e.c.galeria] && f.tipo[e.c.tipo], tem = g.hasLayer(e.m);
        if (vis && !tem) g.addLayer(e.m); else if (!vis && tem) g.removeLayer(e.m);
      });
    },

    _abrir(c, centrar) {
      MU.ficha({
        titulo: c.titulo, cor: COR[c.galeria], sub: ROTULO[c.tipo] + ' · ' + c.ano,
        linhas: [['Estado', ESTADO[c.estado] || c.estado], ['Local', c.freguesia + (c.aproximada ? ' (aprox.)' : '')]],
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
      MU.map.removeLayer(this._grupo);
      MU.map.off('click', this._limpar);
    }
  });
})();
