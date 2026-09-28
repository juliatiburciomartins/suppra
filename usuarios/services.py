"""
Serviço de exclusão de conta / anonimização de dados pessoais (RF-016, LGPD).

Centralizado aqui de propósito: tanto a exclusão de conta pelo próprio
usuário (`usuarios/views.py::excluir_conta_view`) quanto uma eventual ação de
moderação devem chamar a MESMA função.

SOFT DELETE sem alterar o banco.sql
-----------------------------------
O schema (MER/DER) não tem a coluna `data_exclusao`, e as FKs de
produto/demanda/avaliação/assinatura/etc. impedem um DELETE em `usuario`.
Por isso a exclusão é modelada com as colunas que já existem:

  1) nome, e-mail, cpf_cnpj, telefone e whatsapp são substituídos por valores
     anônimos e únicos (para não violar os UNIQUE de email e cpf_cnpj);
  2) a senha vira um hash inutilizável (`set_unusable_password`);
  3) `status_conta` vira 'suspensa', o que bloqueia o login
     (`Usuario.is_active` é False) e derruba sessões abertas.

"Dados associados" (RF-016): o conteúdo público do titular sai do ar — produtos
do fornecedor ficam inativos e sem telefone/WhatsApp de contato, demandas do
comerciante são encerradas e assinaturas ativas são canceladas.

O momento da exclusão fica registrado em `log_alteracao` (RF-024), feito pela
view antes de chamar esta função. O registro em `usuario` é mantido para
preservar a integridade referencial do histórico da plataforma.
"""

from django.db import transaction
from django.utils.crypto import get_random_string

from usuarios.models import Usuario

NOME_ANONIMIZADO = "Usuário Removido"
EMAIL_DOMINIO_ANONIMIZADO = "anonimizado.hubfecc.local"


def _desativar_conteudo_associado(usuario: Usuario) -> None:
    # imports locais: evita dependência circular entre os apps
    from assinaturas.models import Assinatura
    from demandas.models import Demanda
    from portfolio.models import Produto

    # save() individual (e não update()) para o simple_history registrar (RF-024)
    for produto in Produto.objects.filter(id_fornecedor=usuario):
        produto.status = "inativo"
        produto.telefone_contato = None
        produto.whatsapp_contato = None
        produto.save()

    for demanda in Demanda.objects.filter(id_comerciante=usuario, status="publicada"):
        demanda.status = "encerrada"
        demanda.save()

    Assinatura.objects.filter(id_fornecedor=usuario, status="ativa").update(status="cancelada")


@transaction.atomic
def anonimizar_usuario(usuario: Usuario) -> Usuario:
    """
    Anonimiza os dados pessoais de `usuario`, bloqueia o login e salva.

    Idempotente: chamar duas vezes não quebra nada (só gera novos
    placeholders de e-mail/cpf_cnpj).
    """
    sufixo = get_random_string(12).lower()

    usuario.nome = NOME_ANONIMIZADO
    usuario.email = f"removido.{usuario.pk}.{sufixo}@{EMAIL_DOMINIO_ANONIMIZADO}"
    # cpf_cnpj é VARCHAR(18) no banco.sql: o pk já garante unicidade e cabe.
    usuario.cpf_cnpj = f"ANON-{usuario.pk}"
    usuario.telefone = None
    usuario.whatsapp = None
    usuario.set_unusable_password()
    usuario.status_conta = "suspensa"
    usuario.save(
        update_fields=[
            "nome",
            "email",
            "cpf_cnpj",
            "telefone",
            "whatsapp",
            "password",
            "status_conta",
        ]
    )
    _desativar_conteudo_associado(usuario)
    return usuario
