/* folha.js — numera a folha de levantamento (assets/css/folha.css).
   Cada .fila visível recebe o seu número nas duas margens (.zm) e cada etiqueta <code data-ref="A-E"> passa a «A4–E4»
   (data-ref="G" → «G4»). Filas escondidas não contam: o número segue sempre a ordem do que se vê.
   As páginas que mostram ou escondem filas depois de carregar chamam window.folhaNumerar(). */
(function () {
  'use strict';
  function numerar() {
    var n = 0, primeira = true;
    document.querySelectorAll('.folha .int > .fila').forEach(function (f) {
      f.querySelectorAll(':scope > .zm').forEach(function (z) { z.remove(); });
      f.classList.remove('primeira');
      if (f.hidden) return;
      n++;
      if (primeira) { f.classList.add('primeira'); primeira = false; }
      ['', ' dir'].forEach(function (lado) {
        var z = document.createElement('span');
        z.className = 'zm' + lado; z.setAttribute('aria-hidden', 'true'); z.textContent = n;
        f.insertBefore(z, f.firstChild);
      });
      f.querySelectorAll('code[data-ref]').forEach(function (c) {
        var r = c.getAttribute('data-ref').split('-');
        c.textContent = r.length > 1 ? r[0] + n + '–' + r[1] + n : r[0] + n;
      });
    });
  }
  window.folhaNumerar = numerar;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', numerar);
  else numerar();
})();
