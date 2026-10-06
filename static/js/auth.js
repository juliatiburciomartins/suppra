document.querySelectorAll(".auth-eye").forEach(function (botao) {
    botao.addEventListener("click", function () {
        var campo = botao.parentNode.querySelector("input");
        var icone = botao.querySelector("i");

        if (campo.type === "password") {
            campo.type = "text";
            icone.className = "bi bi-eye-slash";
        } else {
            campo.type = "password";
            icone.className = "bi bi-eye";
        }
    });
});