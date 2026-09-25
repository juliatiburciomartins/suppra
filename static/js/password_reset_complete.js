
document.addEventListener("DOMContentLoaded", function () {
  var linkLogin = document.querySelector("[data-login-url]");
  if (!linkLogin) return;

  var destino = linkLogin.getAttribute("href");
  var TEMPO_REDIRECIONAMENTO_MS = 4000;

  setTimeout(function () {
    window.location.href = destino;
  }, TEMPO_REDIRECIONAMENTO_MS);
});