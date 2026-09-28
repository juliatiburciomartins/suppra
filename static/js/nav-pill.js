document.addEventListener('DOMContentLoaded', function () {
  const list = document.querySelector('[data-navigation-list]');
  const pill = document.querySelector('[data-nav-active-pill]');
  if (!list || !pill) return;

  function positionPill() {
    const active = list.querySelector('.navigation-item.is-active');
    if (!active) {
      pill.classList.remove('is-visible');
      return;
    }
    const listRect = list.getBoundingClientRect();
    const activeRect = active.getBoundingClientRect();
    pill.style.left = (activeRect.left - listRect.left) + 'px';
    pill.style.width = activeRect.width + 'px';
    pill.classList.add('is-visible');
  }

  positionPill();
  window.addEventListener('resize', positionPill);
});