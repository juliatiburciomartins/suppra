/*
  Modal de confirmação reutilizável.

  Uso: adicione data-confirmar no <form>. {campo} é trocado pelo valor do
  campo com esse name (em <select>, pelo texto da opção escolhida).

    <form method="POST" data-confirmar="Você deseja cadastrar {id_categoria}?"
          data-confirmar-sim="Sim, cadastrar">

  Opcionais: data-confirmar-sim (padrão "Sim") e data-confirmar-nao (padrão "Não").
*/
document.addEventListener('submit', function (event) {
  var form = event.target;
  var mensagem = form.dataset.confirmar;
  if (!mensagem || form.dataset.confirmado) return;

  var campoVazio = false;
  mensagem = mensagem.replace(/\{(\w+)\}/g, function (_, nome) {
    var campo = form.elements[nome];
    var valor = !campo ? '' : campo.tagName === 'SELECT'
      ? (campo.value ? campo.options[campo.selectedIndex].text : '')
      : campo.value;
    if (!valor.trim()) campoVazio = true;
    return valor.trim();
  });
  if (campoVazio) return; // deixa o servidor mostrar o erro do campo

  event.preventDefault();

  var dialog = document.createElement('dialog');
  dialog.className = 'confirmar-modal';
  dialog.innerHTML =
    '<p></p><div><button type="button" class="confirmar-nao"></button>' +
    '<button type="button" class="confirmar-sim"></button></div>';
  dialog.querySelector('p').textContent = mensagem;
  dialog.querySelector('.confirmar-nao').textContent = form.dataset.confirmarNao || 'Não';
  dialog.querySelector('.confirmar-sim').textContent = form.dataset.confirmarSim || 'Sim';

  dialog.querySelector('.confirmar-nao').onclick = function () { dialog.close(); };
  dialog.querySelector('.confirmar-sim').onclick = function () {
    form.dataset.confirmado = '1';
    this.disabled = true;
    form.requestSubmit();
  };
  dialog.onclick = function (e) { if (e.target === dialog) dialog.close(); };
  dialog.onclose = function () { dialog.remove(); };

  document.body.appendChild(dialog);
  dialog.showModal();
});
