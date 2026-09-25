"""
Serviço de anonimização de dados pessoais do Usuario (RF-016 / LGPD).

Centralizado aqui de propósito: tanto a exclusão de conta pelo próprio
usuário (RF-016, `usuarios/views.py::excluir_conta_view`) quanto uma
eventual ação de moderação (suspensão/expulsão) devem chamar a MESMA
função, em vez de cada view reimplementar "apagar dados pessoais" com
pequenas diferenças.

Decisão de design (documentada aqui para não se perder): como o schema
(`banco.sql`) não tem uma coluna "excluida" separada, o "apagar conta"
é modelado como:
  1) todos os campos de identificação pessoal são substituídos por
     valores anônimos, únicos (pra não violar as constraints UNIQUE de
     email/cpf_cnpj);
  2) a senha vira um hash inutilizável (ninguém consegue logar de novo
     com a senha antiga, nem com senha nenhuma);
  3) status_conta vira 'suspensa', para bloquear login definitivamente
     (ver UsuarioSessionMiddleware, que já derruba sessões de conta
     suspensa).

O registro em si (id_usuario) é mantido — de propósito — porque FKs de
Produto/Demanda/Avaliação/etc. apontam para ele com on_delete=CASCADE ou
PROTECT; apagar a linha de fato removeria em cascata todo o histórico da
plataforma. Anonimizar preserva a integridade referencial mantendo a
privacidade do titular dos dados.
"""

from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string

from usuarios.models import Usuario

NOME_ANONIMIZADO = "Usuário Removido"


def anonimizar_usuario(usuario: Usuario) -> Usuario:
    """
    Anonimiza os dados pessoais de `usuario` e salva.

    Idempotente: chamar duas vezes não quebra nada (só gera um novo
    placeholder de email/cpf_cnpj/senha).
    """
    sufixo = get_random_string(12).lower()

    usuario.nome = NOME_ANONIMIZADO
    usuario.email = f"removido.{usuario.pk}.{sufixo}@anonimizado.hubfecc.local"
    usuario.cpf_cnpj = f"ANONIMIZADO-{usuario.pk}-{sufixo}"
    usuario.telefone = None
    usuario.whatsapp = None
    usuario.senha = make_password(get_random_string(32))
    usuario.status_conta = "suspensa"
    usuario.save(
        update_fields=[
            "nome",
            "email",
            "cpf_cnpj",
            "telefone",
            "whatsapp",
            "senha",
            "status_conta",
        ]
    )
    return usuario
