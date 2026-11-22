/* Filtro de ano «tipo Power BI»: histograma de casos por ano + intervalo com dois cursores.
   Única fonte: usada pela lista (/casos/lista/) e embutida no mapa (/casos/) por mapa_unico.py.
   FiltroAno.criar(elemento, anos[], aoMudar(de, ate)) → { de, ate }. Clicar numa barra escolhe esse ano; clicar outra vez repõe tudo. */
(function (g) {
  'use strict';
  function criar(el, anos, aoMudar) {
    var n = anos.map(Number).filter(isFinite);
    if (!n.length) return null;
    var a0 = Math.min.apply(null, n), a1 = Math.max.apply(null, n);
    if (a0 === a1) return null;
    var cont = {}, max = 1, i;
    n.forEach(function (a) { cont[a] = (cont[a] || 0) + 1; max = Math.max(max, cont[a]); });
    var barras = '';
    for (i = a0; i <= a1; i++) {
      var c = cont[i] || 0, tit = i + ': ' + c + (c === 1 ? ' caso' : ' casos');
      barras += '<button type="button" class="fa-b" data-a="' + i + '" style="height:' + (c ? 14 + Math.round(86 * c / max) : 4) + '%" title="' + tit + '" aria-label="' + tit + '"></button>';
    }
    el.innerHTML = '<div class="fa"><div class="fa-barras">' + barras + '</div>' +
      '<div class="fa-trilho"><div class="fa-sel"></div>' +
      '<input type="range" min="' + a0 + '" max="' + a1 + '" step="1" value="' + a0 + '" data-ano="de" aria-label="Ano inicial">' +
      '<input type="range" min="' + a0 + '" max="' + a1 + '" step="1" value="' + a1 + '" data-ano="ate" aria-label="Ano final"></div>' +
      '<div class="fa-eixo"><span>' + a0 + '</span><output class="fa-out"></output><span>' + a1 + '</span></div></div>';
    var rde = el.querySelector('input[data-ano=de]'), rate = el.querySelector('input[data-ano=ate]'),
        sel = el.querySelector('.fa-sel'), out = el.querySelector('.fa-out'), bs = el.querySelectorAll('.fa-b');
    var estado = { de: a0, ate: a1 };
    function pintar() {
      var p = function (v) { return (v - a0) / (a1 - a0) * 100; };
      sel.style.left = p(estado.de) + '%'; sel.style.right = (100 - p(estado.ate)) + '%';
      out.textContent = estado.de === estado.ate ? estado.de : estado.de + ' – ' + estado.ate;
      Array.prototype.forEach.call(bs, function (b) { var a = +b.dataset.a; b.classList.toggle('on', a >= estado.de && a <= estado.ate); });
    }
    function mudou() { pintar(); if (aoMudar) aoMudar(estado.de, estado.ate); }
    function definir(de, ate) { rde.value = de; rate.value = ate; estado.de = +de; estado.ate = +ate; mudou(); }
    [rde, rate].forEach(function (r) {
      r.addEventListener('input', function () {   // os cursores não se cruzam: o que mexe arrasta o outro
        if (r === rde && +rde.value > +rate.value) rate.value = rde.value;
        if (r === rate && +rate.value < +rde.value) rde.value = rate.value;
        estado.de = +rde.value; estado.ate = +rate.value; mudou();
      });
    });
    Array.prototype.forEach.call(bs, function (b) {
      b.addEventListener('click', function () {
        var a = +b.dataset.a;
        if (estado.de === a && estado.ate === a) definir(a0, a1); else definir(a, a);
      });
    });
    pintar();
    return estado;
  }
  g.FiltroAno = { criar: criar };
})(window);
