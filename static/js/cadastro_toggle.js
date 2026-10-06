document.addEventListener("DOMContentLoaded", function () {
  // ---------- Seletor Fornecedor / Comerciante ----------
  var segContainer = document.querySelector(".auth-seg");
  if (segContainer) {
    var radios = segContainer.querySelectorAll('input[type="radio"]');
    var slider = segContainer.querySelector(".auth-seg-slider");

    var updateSlider = function () {
      radios.forEach(function (radio, index) {
        if (radio.checked && slider) {
          slider.style.transform = "translateX(" + index * 100 + "%)";
        }
      });
    };

    radios.forEach(function (radio) {
      radio.addEventListener("change", updateSlider);
    });
    updateSlider();
  }

  // ---------- Olhinho de mostrar/ocultar ----------
  function atualizarIcone(btn, input) {
    var icon = btn.querySelector("i");
    if (!icon) return;
    var visivel = input.type === "text";
    icon.classList.toggle("bi-eye", !visivel);
    icon.classList.toggle("bi-eye-slash", visivel);
    btn.setAttribute("aria-pressed", visivel ? "true" : "false");
  }

  document.querySelectorAll(".auth-eye[data-target]").forEach(function (btn) {
    var input = document.getElementById(btn.dataset.target);
    if (!input) return;

    atualizarIcone(btn, input);

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      input.type = input.type === "password" ? "text" : "password";
      atualizarIcone(btn, input);
    });
  });
});