document.addEventListener('DOMContentLoaded', function () {
  const text = 'Aumente Oportunidades!';
  const el = document.getElementById('typed');
  
  if (!el) return;

  let i = 0;
  function type() {
    if (i <= text.length) {
      el.textContent = text.slice(0, i);
      i++;
      setTimeout(type, 110);
    }
  }
  type();
});

document.addEventListener('DOMContentLoaded', function () {
  const menus = document.querySelectorAll('.site-header, .nav-wrap');
  const heroes = document.querySelectorAll('.hero');
  let ticking = false;
  let isSticky = false;

  function updateMenuState() {
    const shouldStick = window.scrollY > 100;

    if (shouldStick === isSticky) {
      ticking = false;
      return;
    }

    isSticky = shouldStick;

    menus.forEach(function (menu) {
      if (shouldStick) {
        menu.classList.add('is-sticky');
        requestAnimationFrame(function () {
          menu.classList.add('show');
        });
      } else {
        menu.classList.remove('show', 'is-sticky');
      }
    });

    heroes.forEach(function (hero) {
      hero.classList.toggle('scrolled', shouldStick);
    });

    ticking = false;
  }

  window.addEventListener('scroll', function () {
    if (!ticking) {
      requestAnimationFrame(updateMenuState);
      ticking = true;
    }
  }, { passive: true });

  updateMenuState();
});