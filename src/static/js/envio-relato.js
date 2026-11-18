// RNF03 — envio do relato com conexão instável.
//
// O formulário é enviado por HTMX. Quando a requisição não chega ao servidor
// (sem sinal, metrô subterrâneo) ou demora demais, nada é trocado na página:
// os campos continuam preenchidos e aqui só se mostra o aviso.
(function () {
  "use strict";

  var MENSAGENS = {
    "htmx:sendError":
      "Sem conexão: seu relato não foi enviado. O que você preencheu continua aqui; toque em Enviar quando o sinal voltar.",
    "htmx:timeout":
      "A conexão está lenta e o envio não terminou. O que você preencheu continua aqui; tente enviar de novo.",
    "htmx:responseError":
      "Não conseguimos salvar o relato agora. O que você preencheu continua aqui; tente de novo em instantes.",
  };

  function formularioDo(evento) {
    var alvo = evento.detail && evento.detail.elt;
    return alvo && alvo.closest ? alvo.closest("#formulario-relato") : null;
  }

  function avisar(formulario, texto) {
    var aviso = formulario.querySelector("#erro-envio");
    if (!aviso) return;
    aviso.textContent = texto || "";
    aviso.hidden = !texto;
  }

  Object.keys(MENSAGENS).forEach(function (nome) {
    document.body.addEventListener(nome, function (evento) {
      var formulario = formularioDo(evento);
      if (formulario) avisar(formulario, MENSAGENS[nome]);
    });
  });

  document.body.addEventListener("htmx:beforeRequest", function (evento) {
    var formulario = formularioDo(evento);
    if (formulario) avisar(formulario, "");
  });

  // Se a sessão expirou, a resposta é a página de login, que não tem o
  // formulário: em vez de trocar o formulário por nada, abre a página inteira
  // (o login volta ao formulário depois, RF01).
  document.body.addEventListener("htmx:beforeSwap", function (evento) {
    var formulario = formularioDo(evento);
    if (!formulario || evento.detail.isError) return;
    var resposta = evento.detail.serverResponse || "";
    if (resposta.indexOf('id="formulario-relato"') === -1) {
      evento.detail.shouldSwap = false;
      window.location.assign(evento.detail.xhr.responseURL || window.location.href);
    }
  });
})();
