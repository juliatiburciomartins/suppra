function initPasswordToggle() {
  var botoes = document.querySelectorAll("[data-login-eye], [data-reset-eye]");

  botoes.forEach(function (botao) {
    botao.addEventListener("click", function (event) {
      event.preventDefault(); // Evita comportamentos indesejados no formulário

      var targetId = botao.getAttribute("aria-controls");
      var campo = document.getElementById(targetId);

      if (!campo) return;

      var icone = botao.querySelector("i");
      var mostrar = campo.type === "password";

      campo.type = mostrar ? "text" : "password";

      if (icone) {
        icone.classList.toggle("bi-eye", !mostrar);
        icone.classList.toggle("bi-eye-slash", mostrar);
      }

      botao.setAttribute("aria-pressed", String(mostrar));
      botao.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
    });
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initPasswordToggle);
} else {
  initPasswordToggle();
}