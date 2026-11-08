(function () {
  var API = window.CHAT_API || "https://portoverde-chat.portoverde.workers.dev/api/chat";
  var SITEKEY = window.CHAT_SITEKEY || "0x4AAAAAAF4wz2mk_g-mGarz"; // chave pública do Turnstile (pode estar na página)
  var ERROS = {
    vazia: "Escreva uma pergunta.",
    longa: "A pergunta tem mais de 500 caracteres. Encurte-a.",
    turnstile: "Não foi possível confirmar que é uma pessoa. Recarregue a página e tente de novo.",
    limite_dia: "Já fez 10 perguntas hoje. Volte amanhã.",
    tecto_mes: "O limite de perguntas deste mês foi atingido. O chat volta no dia 1.",
    sem_fontes: "Não encontrei isto nas fontes da nota. Tente reformular a pergunta.",
    limite_servico: "O limite diário do serviço foi atingido. Volte amanhã.",
    indisponivel: "O serviço está indisponível neste momento. Tente daqui a pouco.",
    rede: "Não foi possível ligar ao serviço. Verifique a ligação e tente de novo."
  };
  var $ = function (id) { return document.getElementById(id); };
  var ta = $("pergunta"), btn = $("enviar"), tokenWidget = null;

  ta.addEventListener("input", function () { $("n").textContent = ta.value.length; });
  Array.prototype.forEach.call(document.querySelectorAll(".exemplos button"), function (b) {
    b.addEventListener("click", function () { ta.value = b.textContent; $("n").textContent = ta.value.length; ta.focus(); });
  });

  if (SITEKEY) {
    btn.disabled = true; btn.textContent = "A verificar…";
    var pronto = function () { btn.disabled = false; btn.textContent = "Perguntar"; };
    var espera = function () { btn.disabled = true; btn.textContent = "A verificar…"; };
    window.__tsPronto = function () {
      tokenWidget = turnstile.render("#turnstile", {
        sitekey: SITEKEY, size: "flexible", appearance: "interaction-only", // só aparece se for preciso um clique
        callback: pronto, "expired-callback": espera, "timeout-callback": espera,
        "error-callback": function () { btn.textContent = "Verificação falhou: recarregue"; }
      });
    };
    var s = document.createElement("script");
    s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=__tsPronto";
    s.async = true; document.head.appendChild(s);
  }

  function mostrarErro(c) { var e = $("erro"); e.textContent = ERROS[c] || ERROS.indisponivel; e.hidden = false; }
  function limpar() { $("erro").hidden = true; $("fontes").hidden = true; $("resposta").textContent = ""; }

  // Texto com [n] -> parágrafos com citações em expoente ligadas à lista de fontes
  function desenhar(texto, citadas) {
    var r = $("resposta"); r.textContent = "";
    texto.split(/\n{2,}/).forEach(function (par) {
      if (!par.trim()) return;
      var p = document.createElement("p"), ultimo = 0, m, re = /\[(\d+(?:, \d+)*)\]/g;
      while ((m = re.exec(par))) {
        p.appendChild(document.createTextNode(par.slice(ultimo, m.index).replace(/\s+$/, "")));
        var sup = document.createElement("sup"); sup.className = "cit";
        m[1].split(", ").forEach(function (n, i) {
          if (i) sup.appendChild(document.createTextNode(","));
          var a = document.createElement("a"); a.href = "#f-" + n; a.textContent = n; sup.appendChild(a); citadas[n] = true;
        });
        p.appendChild(sup); ultimo = re.lastIndex;
      }
      p.appendChild(document.createTextNode(par.slice(ultimo)));
      r.appendChild(p);
    });
  }
  function listarFontes(fontes, citadas) {
    var ol = $("lista"); ol.textContent = ""; var algum = false;
    fontes.forEach(function (f) {
      if (!citadas[f.n]) return; algum = true;
      var li = document.createElement("li"); li.id = "f-" + f.n; li.value = f.n;
      if (f.url) { var a = document.createElement("a"); a.href = f.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = f.titulo; li.appendChild(a); }
      else li.textContent = f.titulo;
      ol.appendChild(li);
    });
    $("fontes").hidden = !algum;
  }

  function ler(corpo, aoEvento) {
    var leitor = corpo.getReader(), dec = new TextDecoder(), buf = "";
    return leitor.read().then(function passo(r) {
      if (r.done) return;
      buf += dec.decode(r.value, { stream: true });
      var blocos = buf.split("\n\n"); buf = blocos.pop();
      blocos.forEach(function (b) {
        var ev = "mensagem", dados = "";
        b.split("\n").forEach(function (l) { if (l.indexOf("event:") === 0) ev = l.slice(6).trim(); else if (l.indexOf("data:") === 0) dados += l.slice(5).trim(); });
        if (dados) aoEvento(ev, dados);
      });
      return leitor.read().then(passo);
    });
  }

  $("form").addEventListener("submit", function (e) {
    e.preventDefault();
    var pergunta = ta.value.trim(); if (!pergunta) return mostrarErro("vazia");
    limpar(); $("exemplos").hidden = true;
    $("feita").textContent = pergunta; $("feita").hidden = false;
    btn.disabled = true; btn.textContent = "A procurar…"; $("saida").setAttribute("aria-busy", "true");
    var token = (tokenWidget !== null && window.turnstile) ? turnstile.getResponse(tokenWidget) : "";
    var texto = "", fontes = [], terminou = false;
    fetch(API, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ pergunta: pergunta, token: token }) })
      .then(function (r) {
        var tipo = r.headers.get("content-type") || "";
        if (tipo.indexOf("event-stream") === -1) return r.json().then(function (j) { mostrarErro(j.erro); }, function () { mostrarErro("indisponivel"); });
        return ler(r.body, function (ev, d) {
          if (ev === "fontes") fontes = JSON.parse(d);
          else if (ev === "erro") mostrarErro(JSON.parse(d).erro);
          else if (d === "[FIM]") terminou = true;
          else { texto += JSON.parse(d).t; desenhar(texto, {}); }
        }).then(function () {
          var citadas = {}; desenhar(texto, citadas); listarFontes(fontes, citadas);
          if (!texto.trim() && !terminou) mostrarErro("indisponivel");
        });
      })
      .catch(function () { mostrarErro("rede"); })
      .then(function () {
        btn.disabled = false; btn.textContent = "Perguntar"; $("saida").removeAttribute("aria-busy");
        if (tokenWidget !== null && window.turnstile) { turnstile.reset(tokenWidget); espera(); }
      });
  });
})();
