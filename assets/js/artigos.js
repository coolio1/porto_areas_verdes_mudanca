/* artigos.js — filtro por tema na página /artigos/. Sem JavaScript a lista completa continua visível. */
(function () {
  var raiz = document.querySelector('.artigos');
  if (!raiz) return;
  var chips = raiz.querySelectorAll('.chip');
  var linhas = raiz.querySelectorAll('.lin');
  var anos = raiz.querySelectorAll('.ano');
  var n = raiz.querySelector('.cab .n');
  var vazio = raiz.querySelector('.vazio');
  function aplicar(tema) {
    var vistos = 0;
    linhas.forEach(function (l) { var ok = !tema || l.dataset.tema === tema; l.hidden = !ok; if (ok) vistos++; });
    anos.forEach(function (a) {
      var seg = a.nextElementSibling, algum = false;
      while (seg && !seg.classList.contains('ano')) { if (seg.classList.contains('lin') && !seg.hidden) algum = true; seg = seg.nextElementSibling; }
      a.hidden = !algum;
    });
    chips.forEach(function (c) { c.setAttribute('aria-pressed', String((c.dataset.f || '') === (tema || ''))); });
    if (n) n.textContent = vistos + ' de ' + linhas.length + ' · mais recente primeiro';
    if (vazio) vazio.hidden = vistos > 0;
  }
  chips.forEach(function (c) { c.addEventListener('click', function () { aplicar(c.dataset.f || ''); }); });
})();
