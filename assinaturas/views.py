"""
Planos e assinaturas do fornecedor (RF-020, RF-021, RF-022 / CU12, CU13).

- `planos_assinatura` — CU12: lista os planos que a equipe cadastrou, com nome,
  descrição dos benefícios e valor mensal.
- `confirmar_contratacao` — CU13: resumo do plano + confirmação.
- `contratar` — CU13: grava a assinatura e ativa os benefícios.
- `cancelar_assinatura` — CU13 A1 / RF-022: cancela mantendo os benefícios até o
  fim do período vigente.
- `meu_plano` — RF-022: plano contratado, data de vencimento e status atual.

Todas exigem perfil fornecedor (RF-004 / RNF-006) e os dados vêm do banco — não
de constantes no código: quem gerencia os planos é a equipe gestora pelo painel
(CU23), então o que o fornecedor vê reflete o que foi cadastrado.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from assinaturas.models import Assinatura, PlanoAssinatura
from assinaturas.services import (
    assinatura_em_vigor,
    cancelar,
    contratar,
    expirar_vencidas,
    planos_disponiveis,
)
from usuarios.decorators import fornecedor_required

TEMPLATE_PLANOS = "assinaturas/lista_planos.html"
TEMPLATE_CONFIRMAR = "assinaturas/confirmar_contratacao.html"
TEMPLATE_MEU_PLANO = "assinaturas/meu_plano.html"


@fornecedor_required
def planos_assinatura(request):
    """CU12 — "Para cada plano, o sistema exibe: nome, descrição e valor mensal"."""
    expirar_vencidas()

    assinatura = assinatura_em_vigor(request.user)

    return render(
        request,
        TEMPLATE_PLANOS,
        {
            "planos": planos_disponiveis(),
            "assinatura": assinatura,
            "ja_assinante": assinatura is not None,
            "tipo_menu": "fornecedor",
        },
    )


@fornecedor_required
def confirmar_contratacao(request, plano_id):
    """
    CU13, passo 2 — "o sistema exibe o resumo do plano selecionado, com nome,
    benefícios e valor mensal, e solicita confirmação da contratação".

    A pré-condição do CU13 é "não possui assinatura ativa"; nesse caso o
    fornecedor é levado de volta à lista de planos em vez de ver a tela de
    confirmação.
    """
    expirar_vencidas()

    plano = get_object_or_404(PlanoAssinatura, pk=plano_id)
    assinatura_atual = assinatura_em_vigor(request.user)

    if assinatura_atual is not None:
        messages.info(
            request,
            f"Você já tem o plano {assinatura_atual.id_plano.nome_plano} em vigor. "
            "Escolha outro plano para trocar.",
        )
        return redirect("planos_assinatura")

    return render(
        request,
        TEMPLATE_CONFIRMAR,
        {
            "plano": plano,
            "tipo_menu": "fornecedor",
        },
    )


@fornecedor_required
def contratar_plano(request, plano_id):
    """CU13, passo 4 — grava a assinatura e confirma o plano ativo e o vencimento."""
    expirar_vencidas()

    if request.method != "POST":
        return redirect("planos_assinatura")

    plano = get_object_or_404(PlanoAssinatura, pk=plano_id)

    assinatura = contratar(request.user, plano)

    messages.success(
        request,
        f"Assinatura confirmada! Seu plano {plano.nome_plano} está ativo até "
        f"{assinatura.data_vencimento.strftime('%d/%m/%Y')}.",
    )
    return redirect("meu_plano")


@fornecedor_required
def meu_plano(request):
    """
    RF-022 — "visualizar o plano contratado, a data de vencimento e o status
    atual (ativa/suspensa)".
    """
    expirar_vencidas()

    assinatura = assinatura_em_vigor(request.user)
    historico = (
        Assinatura.objects.filter(id_fornecedor=request.user)
        .exclude(pk=assinatura.pk if assinatura else None)
        .select_related("id_plano")
        .order_by("-data_vencimento")
    )

    return render(
        request,
        TEMPLATE_MEU_PLANO,
        {
            "assinatura": assinatura,
            "historico": historico,
            "tipo_menu": "fornecedor",
        },
    )


@fornecedor_required
def cancelar_assinatura(request):
    """
    RF-022 / CU13 A1 — cancela a assinatura em vigor.

    Só por POST, e o botão na tela pede a confirmação informando que os
    benefícios permanecem até o fim do período.
    """
    expirar_vencidas()

    if request.method != "POST":
        return redirect("meu_plano")

    assinatura = cancelar(request.user)

    if assinatura is None:
        messages.info(request, "Não há assinatura em vigor para cancelar.")
    else:
        messages.success(
            request,
            f"Assinatura do plano {assinatura.id_plano.nome_plano} cancelada. "
            f"Seus benefícios permanecem até {assinatura.data_vencimento.strftime('%d/%m/%Y')}.",
        )

    return redirect("meu_plano")