document.addEventListener('DOMContentLoaded', function () {
  var openButtons = document.querySelectorAll('.js-open-modal');
  var closeButtons = document.querySelectorAll('.js-close-modal');
  var overlays = document.querySelectorAll('.modal-overlay');

  function openModal(modal) {
    if (!modal) return;
    modal.classList.add('is-open');
    document.body.classList.add('modal-open');
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove('is-open');
    document.body.classList.remove('modal-open');
  }

  openButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var modal = document.getElementById(button.dataset.modal);
      openModal(modal);
    });
  });

  closeButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      closeModal(button.closest('.modal-overlay'));
    });
  });

  overlays.forEach(function (overlay) {
    overlay.addEventListener('click', function (event) {
      if (event.target === overlay) {
        closeModal(overlay);
      }
    });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      var openModalEl = document.querySelector('.modal-overlay.is-open');
      closeModal(openModalEl);
    }
  });

  
  if (document.querySelector('.modal-overlay.is-open')) {
    document.body.classList.add('modal-open');
  }
});