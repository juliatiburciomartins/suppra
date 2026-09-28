document.addEventListener("DOMContentLoaded", function () {
    // Elementos principais do menu lateral (drawer)
    const menuButton = document.querySelector("[data-mobile-nav-toggle]");
    const drawer = document.querySelector("[data-mobile-drawer]");
    const backdrop = document.querySelector("[data-mobile-drawer-backdrop]");
    const closeButton = document.querySelector("[data-mobile-nav-close]");
    const toggleIcon = menuButton ? menuButton.querySelector("i") : null;

    // Se o botão ou o drawer não existirem na página, o script para aqui
    if (!menuButton || !drawer) return;

    function openDrawer() {
        drawer.classList.add("is-open");
        drawer.setAttribute("aria-hidden", "false");

        menuButton.classList.add("is-active");
        menuButton.setAttribute("aria-expanded", "true");

        if (toggleIcon) {
            toggleIcon.classList.remove("bi-list");
            toggleIcon.classList.add("bi-x-lg");
        }

        document.body.classList.add("drawer-open");
    }

    function closeDrawer() {
        drawer.classList.remove("is-open");
        drawer.setAttribute("aria-hidden", "true");

        menuButton.classList.remove("is-active");
        menuButton.setAttribute("aria-expanded", "false");

        if (toggleIcon) {
            toggleIcon.classList.remove("bi-x-lg");
            toggleIcon.classList.add("bi-list");
        }

        document.body.classList.remove("drawer-open");
    }

    function toggleDrawer() {
        if (drawer.classList.contains("is-open")) {
            closeDrawer();
        } else {
            openDrawer();
        }
    }

    // Clique nas 3 barras: abre/fecha o menu lateral
    menuButton.addEventListener("click", toggleDrawer);

    // Clique no botão "X" dentro do drawer
    if (closeButton) {
        closeButton.addEventListener("click", closeDrawer);
    }

    // Clique fora do painel (na área escurecida) fecha o menu
    if (backdrop) {
        backdrop.addEventListener("click", closeDrawer);
    }

    // Clicar em qualquer link do drawer fecha o menu automaticamente
    drawer.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", closeDrawer);
    });

    // Tecla ESC fecha o menu
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeDrawer();
        }
    });

    // Se a tela for redimensionada para desktop, garante que o drawer feche
    window.addEventListener("resize", function () {
        if (window.innerWidth > 768) {
            closeDrawer();
        }
    });
});