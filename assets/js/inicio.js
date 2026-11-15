/* inicio.js — página de entrada (index.html): régua <-> palco, temas do mapa e uma volta automática.
   O conteúdo (figuras, artigos, contagens) vem já escrito no HTML pelo Jekyll; aqui só se troca o que se vê. */
(function () {
  'use strict';
  var raiz = document.querySelector('.inicio');
  var stage = document.getElementById('stage');
  if (!raiz || !stage) return;
  var figuras = [].slice.call(stage.querySelectorAll('.fg'));

  /* altura fixa do palco = a da figura mais alta (a régua não salta ao trocar de área) */
  function alturaPalco() {
    stage.style.minHeight = '';
    var m = 0;
    figuras.forEach(function (f) { f.style.display = 'block'; m = Math.max(m, f.offsetHeight); f.style.display = ''; });
    stage.style.minHeight = m + 'px';
  }
  alturaPalco();
  addEventListener('resize', alturaPalco);
  addEventListener('load', alturaPalco);
  if (document.fonts) document.fonts.ready.then(alturaPalco);

  /* mapas: o tema sob o cursor/foco troca o mapa */
  var temas = [].slice.call(stage.querySelectorAll('.temas a'));
  temas.forEach(function (a) {
    function f() {
      var t = a.dataset.t;
      stage.querySelectorAll('[data-k="mapas"] .mp-alt').forEach(function (x) { x.classList.toggle('on', x.dataset.t === t); });
      temas.forEach(function (x) { x.setAttribute('aria-current', String(x === a)); });
    }
    a.addEventListener('mouseenter', f);
    a.addEventListener('focus', f);
  });

  /* régua <-> palco; uma volta automática por separador do browser */
  var regua = [].slice.call(document.querySelectorAll('#regua a'));
  var nome = document.getElementById('palco-n');
  var parar = document.getElementById('parar');
  function mostra(a) {
    regua.forEach(function (x) { x.classList.toggle('on', x === a); });
    figuras.forEach(function (f) { f.classList.toggle('on', f.dataset.k === a.dataset.k); });
    nome.textContent = a.querySelector('b').textContent;
  }
  var volta = null;
  function acaba() {
    if (volta === null) return;
    clearTimeout(volta); volta = null;
    raiz.classList.remove('correr'); parar.hidden = true;
    ['pointerdown', 'keydown', 'focusin'].forEach(function (e) { document.removeEventListener(e, acaba, true); });
  }
  function passo(i) {
    mostra(regua[i]);
    raiz.classList.remove('correr'); void raiz.offsetWidth; raiz.classList.add('correr');  // reinicia a barra do item activo
    var ms = parseFloat(getComputedStyle(raiz).getPropertyValue('--volta')) * 1000;
    volta = setTimeout(function () {
      if (i + 1 < regua.length) passo(i + 1);
      else { acaba(); mostra(regua[0]); }
    }, ms);
  }
  function comeca() {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    try { if (sessionStorage.getItem('pv-volta')) return; sessionStorage.setItem('pv-volta', '1'); } catch (e) { /* sem armazenamento: dá a volta na mesma */ }
    parar.hidden = false;
    ['pointerdown', 'keydown', 'focusin'].forEach(function (e) { document.addEventListener(e, acaba, true); });
    passo(0);
  }
  regua.forEach(function (a) {
    function f() { acaba(); mostra(a); }
    a.addEventListener('mouseenter', f);
    a.addEventListener('focus', f);
  });
  document.getElementById('palco').addEventListener('pointerenter', acaba);
  parar.addEventListener('click', acaba);
  document.addEventListener('visibilitychange', function () { if (document.hidden) acaba(); });
  setTimeout(comeca, 900);
})();
