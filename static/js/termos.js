// Controla os modais de "Termos de Uso" e "Política de Privacidade" no cadastro.
// Cada par [botão-de-abrir, id-do-modal, botão-de-fechar] é tratado da mesma forma,
// para não duplicar a lógica de abrir/fechar quando um novo modal for adicionado.
const modaisLegais = [
  { abrir: "abrir-termos", modal: "termos-modal", fechar: "fechar-termos" },
  { abrir: "abrir-politica", modal: "politica-modal", fechar: "fechar-politica" },
];

modaisLegais.forEach(function (config) {
  const botaoAbrir = document.getElementById(config.abrir);
  const botaoFechar = document.getElementById(config.fechar);
  const modal = document.getElementById(config.modal);

  if (!botaoAbrir || !botaoFechar || !modal) {
    return;
  }

  const abrirModal = function () {
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
  };

  const fecharModal = function () {
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
  };

  botaoAbrir.addEventListener("click", abrirModal);
  botaoFechar.addEventListener("click", fecharModal);

  modal.addEventListener("click", function (evento) {
    if (evento.target === modal) {
      fecharModal();
    }
  });

  document.addEventListener("keydown", function (evento) {
    if (evento.key === "Escape" && modal.classList.contains("open")) {
      fecharModal();
    }
  });
});
