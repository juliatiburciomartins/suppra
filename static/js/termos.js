// Modais de "Termos de Uso" e "Política de Privacidade" no cadastro.
//
// Contrato com o HTML (templates/usuarios/cadastro.html):
//   - abrir:   <a data-modal="ID">          (classe .auth-terms-link)
//   - modal:   <div class="custom-modal-overlay" id="ID">
//   - fechar:  <button data-fechar-modal>    ou clique no fundo (o próprio overlay)
//   - estado:  classe "open" no overlay (ver static/css/usuarios/cadastro.css)
//
// É o CU01, passo 4 ("o sistema exibe a Política de Privacidade e os Termos de
// Uso") e o fluxo de exceção E4: sem aceite explícito o cadastro não conclui —
// o checkbox continua sendo obrigatório no formulário.
(function () {
  'use strict';

  var overlays = document.querySelectorAll('.custom-modal-overlay');

  overlays.forEach(function (modal) {
    var id = modal.id;
    if (!id) return;

    function abrir() {
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('modal-open');

      var foco = modal.querySelector('[data-fechar-modal]');
      if (foco) foco.focus();
    }

    function fechar() {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('modal-open');
    }

    // Todos os links que apontam para este modal (no cadastro são .auth-terms-link)
    document.querySelectorAll('[data-modal="' + id + '"]').forEach(function (gatilho) {
      gatilho.addEventListener('click', function (evento) {
        evento.preventDefault(); // não deixa o "#" do href mexer na rolagem
        abrir();
      });
    });

    modal.querySelectorAll('[data-fechar-modal]').forEach(function (botao) {
      botao.addEventListener('click', fechar);
    });

    // Clique no fundo (fora da caixa) fecha.
    modal.addEventListener('click', function (evento) {
      if (evento.target === modal) fechar();
    });

    modal.setAttribute('aria-hidden', 'true');
  });

  document.addEventListener('keydown', function (evento) {
    if (evento.key !== 'Escape') return;
    document.querySelectorAll('.custom-modal-overlay.open').forEach(function (modal) {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    });
    document.body.classList.remove('modal-open');
  });
})();