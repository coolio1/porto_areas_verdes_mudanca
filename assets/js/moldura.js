/* moldura.js — a moldura comum do site: menu, abas da Mobilidade e rodapé. ÚNICA fonte.
   Mudar o menu, as abas ou as fontes dos dados = editar só este ficheiro (nada se regenera).
   Uso, numa página:
     <script src="<raiz>/assets/js/moldura.js" data-pagina="Mobilidade/analise.html"></script>
   data-pagina  caminho da página a partir da raiz do site (nas páginas Jekyll: a URL, ou «artigos/» num artigo)
   data-menu    «flutuante» (por defeito; botões fixos no canto) ou «barra» (Jekyll: barra de filete com o logo, no topo)
   data-rodape  «mapa» (por defeito; etiqueta fixa em baixo) ou «leitura» (fim da página)
   data-fontes  fontes dos dados desta página (sobrepõe a tabela FONTES)
   Abas da Mobilidade: vão para o elemento [data-abas] da página, se existir (folha.css); senão, fixas sob o menu.
   A raiz do site deduz-se do próprio src do script; o CSS (porto-verde.css) é ligado aqui. */
(function () {
  'use strict';
  var S = document.currentScript;
  if (!S) return;
  var RAIZ = S.getAttribute('src').replace(/assets\/js\/moldura\.js.*$/, '');
  var P = (S.dataset.pagina || '').replace(/^\/+/, '').replace(/[?#].*$/, '');
  var MENU = S.dataset.menu || 'flutuante';
  var RODAPE = S.dataset.rodape || 'mapa';

  // ---- dados (a única lista) ----
  var PAGINAS = [
    ['index.html', 'Início'],
    ['mapa_unico/mapa_unico.html', 'Mapas e uso do solo'],
    ['50espacos/', '50 Espaços Verdes'],
    ['Mobilidade/autocarros.html', 'Mobilidade'],
    ['artigos/', 'Artigos'],
    ['sobre/', 'Sobre']
  ];
  var ABAS = [
    ['Mobilidade/autocarros.html', 'Autocarros: mapa'],
    ['Mobilidade/analise.html', 'Autocarros: análise'],
    ['atropelamentos/dashboard_atropelamentos.html', 'Atropelamentos']
  ];
  var ALIAS = { // páginas sem item próprio no menu: acendem o item indicado
    'Mobilidade/analise.html': 'Mobilidade/autocarros.html',
    'atropelamentos/dashboard_atropelamentos.html': 'Mobilidade/autocarros.html'
  };
  var ABAS_NO_FUNDO_MOVEL = ['atropelamentos/dashboard_atropelamentos.html']; // título por baixo do menu
  var FONTES_PADRAO = 'Sentinel-2, Landsat, OSM, PDM Porto';
  var FONTES = {
    'mapa_unico/mapa_unico.html': 'Sentinel-2, Landsat, GHS-POP, OpenStreetMap, PDM do Porto, CAOP',
    'Mobilidade/autocarros.html': 'Porto Digital, OSM',
    'Mobilidade/analise.html': 'Porto Digital, STCP, CM Porto, OSM',
    'atropelamentos/dashboard_atropelamentos.html': 'ANSR, INE'
  };

  // ---- ajudantes ----
  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (html) e.innerHTML = html;
    return e;
  }
  function esc(t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
  function ativo(c) {
    var p = ALIAS[P] || P;
    if (c === 'index.html') return p === '' || p === 'index.html';
    if (c.slice(-1) === '/') return p.indexOf(c) === 0;
    return p === c;
  }
  function ligacoes(lista, marca, aTudo) {
    return lista.map(function (i) {
      var on = aTudo ? i[0] === P : ativo(i[0]);
      return '<a href="' + RAIZ + i[0] + '"' + (on ? ' class="' + marca + '"' : '') + '>' + i[1] + '</a>';
    }).join('');
  }

  // ---- CSS comum (ligado já, no <head>) ----
  var href = RAIZ + 'assets/css/porto-verde.css';
  if (!document.querySelector('link[href="' + href + '"]')) {
    document.head.appendChild(el('link', { rel: 'stylesheet', href: href }));
  }
  if (MENU === 'barra') { // IBM Plex (barra e artigos), alojada em assets/fonts
    var plex = RAIZ + 'assets/css/plex.css';
    document.head.appendChild(el('link', { rel: 'stylesheet', href: plex }));
  }

  function montar() {
    // menu
    var menu;
    if (MENU === 'barra') {
      // barra de filete com o logo (páginas Jekyll); a mesma lista de PAGINAS, também no menu de telemóvel
      // na entrada só o emblema: o logótipo grande já está na página
      var entrada = P === '' || P === 'index.html';
      var marca = '<a class="pv-barra__marca" href="' + RAIZ + 'index.html" aria-label="Porto Verde, início">' +
        '<img class="pv-barra__mini" src="' + RAIZ + 'assets/images/mini-logo.png" alt="" width="34" height="34">' +
        (entrada ? '' : '<img class="pv-barra__nome" src="' + RAIZ + 'assets/images/wordmark.png" alt="Porto Verde" width="150" height="31">') +
        '</a>';
      menu = el('header', { 'class': 'pv-barra' },
        marca + '<nav class="pv-barra__links" aria-label="Menu">' + ligacoes(PAGINAS, 'active') + '</nav>' +
        '<details class="pv-barra__menu"><summary>Menu</summary><nav aria-label="Menu (telemóvel)">' +
        ligacoes(PAGINAS, 'active') + '</nav></details>');
      document.body.insertBefore(menu, document.body.firstChild);
    } else {
      menu = el('div', { id: 'nav' }, ligacoes(PAGINAS, 'active'));
      document.body.insertBefore(menu, document.body.firstChild);
    }
    // abas da Mobilidade (só nas páginas que as têm)
    if (ABAS.some(function (a) { return a[0] === P; })) {
      var abas = el('div', { id: 'abas-mobilidade' }, ligacoes(ABAS, 'on', true));
      var lugar = document.querySelector('[data-abas]'); // a página pode reservar o lugar das abas (folha.css)
      if (lugar) lugar.appendChild(abas);
      else {
        if (ABAS_NO_FUNDO_MOVEL.indexOf(P) >= 0) abas.className = 'no-fundo';
        document.body.insertBefore(abas, menu.nextSibling);
      }
    }
    // rodapé
    var fontes = S.dataset.fontes || FONTES[P] || FONTES_PADRAO;
    var logo = (P === '' && RODAPE === 'leitura') ? '' :
      '<a class="pv-rodape__logo" href="' + RAIZ + 'index.html"><img src="' + RAIZ + 'favicon.png" alt="Porto Verde"></a>';
    document.body.appendChild(el('footer', { 'class': 'pv-rodape pv-rodape--' + RODAPE },
      logo + '<p><span class="pv-rodape__nome">Porto Verde</span><br><span class="pv-rodape__fontes">Dados abertos: ' +
      esc(fontes) + '</span></p>'));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', montar);
  else montar();
})();
