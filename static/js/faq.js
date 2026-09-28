document.addEventListener("DOMContentLoaded", function () {
    const buttons = document.querySelectorAll(".faq-nav-item");
    const categories = document.querySelectorAll(".faq-category");

    function showCategory(categoryName) {
        buttons.forEach(function (button) {
            button.classList.toggle(
                "active",
                button.dataset.category === categoryName
            );
        });

        categories.forEach(function (category) {
            category.classList.toggle(
                "is-hidden",
                category.dataset.categoryContent !== categoryName
            );
        });
    }

    buttons.forEach(function (button) {
        button.addEventListener("click", function () {
            showCategory(button.dataset.category);
        });
    });

    showCategory("sobre");
});