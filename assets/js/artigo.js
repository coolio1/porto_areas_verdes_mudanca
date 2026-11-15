/* artigo.js — capítulos coloridos, índice, régua graduada e barra de progresso dos artigos (_layouts/post.html).
   Só lê o DOM do artigo: h2 = capítulos; nada é gerado à mão por artigo. */
(function () {
  'use strict';
  var art = document.querySelector('article.post');
  if (!art) return;
  var corpo = art.querySelector('.corpo');
  var h2s = [].slice.call(corpo.querySelectorAll(':scope > h2'));
  var NS = 'http://www.w3.org/2000/svg';

  // cor por capítulo (6 tons em rotação) e numeração §n; os elementos até ao h2 seguinte herdam a cor
  var k = -1, n = 0;
  [].slice.call(corpo.children).forEach(function (e) {
    if (e.tagName === 'H2') {
      n++; k = (n - 1) % 6;
      if (!e.id) e.id = 's' + n;
      e.dataset.n = n; e.dataset.t = e.textContent.trim();
      var no = document.createElement('span'); no.className = 'no'; no.textContent = '§' + n; e.insertBefore(no, e.firstChild);
    }
    if (k >= 0) e.classList.add('cap-' + k);
  });

  // tabelas num contentor com scroll horizontal próprio (telemóvel)
  [].slice.call(corpo.querySelectorAll('table')).forEach(function (t) {
    var w = document.createElement('div'); w.className = 'tw'; t.parentNode.insertBefore(w, t); w.appendChild(t);
  });

  // índice de capítulos no bloco de título
  var cart = art.querySelector('.cart');
  if (cart && h2s.length >= 3) {
    var toc = document.createElement('nav'); toc.className = 'toc'; toc.setAttribute('aria-label', 'Capítulos');
    toc.innerHTML = h2s.map(function (h, i) {
      return '<a class="cap-' + (i % 6) + '" href="#' + h.id + '"><b>§' + (i + 1) + '</b><span>' +
        h.dataset.t.replace(/^\s*(?:\d+[.)]?|[IVX]+\.)\s*/, '') + '</span></a>';
    }).join('');
    cart.appendChild(toc);
  }

  // barras-legenda das figuras: crescem uma vez ao entrar no ecrã
  var bars = [].slice.call(document.querySelectorAll('.share.anim'));
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }); }, { threshold: .4 });
    bars.forEach(function (b) { io.observe(b); });
  } else bars.forEach(function (b) { b.classList.add('in'); });

  // régua de leitura (≥ 900 px) e barra de progresso (telemóvel)
  var prog = document.createElement('div'); prog.className = 'prog'; prog.setAttribute('aria-hidden', 'true'); prog.innerHTML = '<i></i>';
  document.body.insertBefore(prog, art.closest('main'));
  var ruler = document.createElement('aside'); ruler.className = 'ruler'; ruler.setAttribute('aria-label', 'Índice e progresso de leitura');
  var svg = document.createElementNS(NS, 'svg'); ruler.appendChild(svg);
  var lbl = document.createElement('div'); lbl.className = 'lbl';
  [].slice.call(art.querySelectorAll('.cart dl div')).forEach(function (d) {
    var dt = d.querySelector('dt');
    if (dt && /Leitura/.test(dt.textContent)) lbl.textContent = d.querySelector('dd').textContent.replace(' minutos', ' min');
  });
  ruler.appendChild(lbl); document.body.appendChild(ruler);

  function el(name, a) { var e = document.createElementNS(NS, name); for (var q in a) e.setAttribute(q, a[q]); return e; }
  var links = [], pf = null;
  function draw() {
    if (getComputedStyle(ruler).display === 'none') return;
    while (svg.firstChild) svg.removeChild(svg.firstChild); links = [];
    var H = svg.clientHeight, doc = document.documentElement.scrollHeight - innerHeight;
    if (doc <= 0 || !H) return;
    svg.appendChild(el('line', { x1: 75, y1: 0, x2: 75, y2: H, stroke: '#10212C', 'stroke-width': 1 }));
    for (var i = 0; i <= 50; i++) {
      var y = H * i / 50, L = i % 10 === 0 ? 16 : (i % 5 === 0 ? 10 : 6);
      svg.appendChild(el('line', { x1: 75 - L, y1: y, x2: 75, y2: y, stroke: '#10212C', 'stroke-width': 1, opacity: .55 }));
    }
    pf = el('rect', { 'class': 'fill', x: 72, y: 0, width: 4, height: 0 }); svg.appendChild(pf);
    h2s.forEach(function (h) {
      var top = h.getBoundingClientRect().top + scrollY, f = Math.min(1, Math.max(0, (top - 90) / doc)), y = H * f;
      var a = el('a', { href: '#' + h.id }); var t = el('title', {}); t.textContent = h.dataset.n + '. ' + h.dataset.t; a.appendChild(t);
      a.appendChild(el('line', { x1: 40, y1: y, x2: 75, y2: y, stroke: getComputedStyle(h).getPropertyValue('--ct') || '#0B5232', 'stroke-width': 2.5 }));
      var tx = el('text', { x: 16, y: y + 4, fill: '#10212C' }); tx.textContent = '§' + h.dataset.n; a.appendChild(tx);
      svg.appendChild(a); links.push([h, a]);
    });
    upd();
  }
  function upd() {
    var doc = document.documentElement.scrollHeight - innerHeight, f = doc > 0 ? Math.min(1, Math.max(0, scrollY / doc)) : 0;
    if (pf) pf.setAttribute('height', svg.clientHeight * f);
    var bar = prog.querySelector('i'); if (bar) bar.style.width = (f * 100) + '%';
    var on = null; links.forEach(function (l) { if (l[0].getBoundingClientRect().top < innerHeight * .35) on = l; });
    links.forEach(function (l) { l[1].classList.toggle('on', l === on); });
    if (on) prog.style.setProperty('--pc', getComputedStyle(on[0]).getPropertyValue('--ct'));
  }
  addEventListener('scroll', upd, { passive: true }); addEventListener('resize', draw);
  if (document.fonts) document.fonts.ready.then(draw);
  addEventListener('load', draw); draw();
})();
