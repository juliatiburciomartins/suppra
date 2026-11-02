"""
Regras de assinatura (RF-020, RF-021, RF-022 / CU12, CU13).

Separado das views porque valem para mais de um lugar: a contratação (CU13), o
cancelamento (CU13 A1) e a expiração automática. Uma assinatura vencida precisa
mudar de 'ativa' para 'expirada' sem ninguém clicar em nada, e é aqui que isso
acontece.

O `banco.sql` não tem campo "em atraso" nem "data de cancelamento" — o
cancelamento usa o `status` que já existe, e o vencimento é comparado com a data
de hoje.
"""

from datetime import timedelta

from django.utils import timezone

from assinaturas.models import Assinatura, PlanoAssinatura


def planos_disponiveis():
    """Planos que a equipe cadastrou no painel (CU23), em ordem de valor."""
    return PlanoAssinatura.objects.all().order_by("valor")


def assinatura_em_vigor(fornecedor):
    """
    Assinatura cujo plano está valendo agora (RF-022).

    Cancelada ainda vale até o fim do período (CU13 A1). Vencida ou suspensa
    não vale mais.
    """
    hoje = timezone.localdate()

    assinatura = (
        Assinatura.objects.filter(id_fornecedor=fornecedor)
        .filter(status__in=("ativa", "cancelada"))
        .filter(data_vencimento__gte=hoje)
        .select_related("id_plano")
        .order_by("-data_vencimento")
        .first()
    )

    return assinatura


def tem_assinatura_ativa(fornecedor):
    return assinatura_em_vigor(fornecedor) is not None


def contratar(fornecedor, plano):
    """
    RF-021 / CU13 — registra a assinatura e ativa os benefícios na hora.

    Passos do CU13: registra com data de início e data de vencimento, atualiza
    o status do fornecedor (aqui o status é derivado da assinatura, sem coluna
    extra) e ativa os benefícios do plano.

    Se o fornecedor já tiver assinatura em vigor, ela é encerrada como
    'expirada' primeiro — assim o histórico no painel (CU23 A2) continua
    correto em vez de acumular duas linhas 'ativa' para a mesma pessoa.
    """
    hoje = timezone.localdate()
    vencimento = hoje + timedelta(days=Assinatura.DIAS_POR_CICLO)

    assinatura_anterior = assinatura_em_vigor(fornecedor)
    if assinatura_anterior is not None:
        assinatura_anterior.status = "expirada"
        assinatura_anterior.save(update_fields=["status"])

    assinatura = Assinatura.objects.create(
        id_fornecedor=fornecedor,
        id_plano=plano,
        data_inicio=hoje,
        data_vencimento=vencimento,
        status="ativa",
    )

    return assinatura


def cancelar(fornecedor):
    """
    RF-022 / CU13 A1 — cancela a assinatura.

    O CU13 A1 é explícito: "o sistema registra o cancelamento e encerra a
    assinatura ao final do período vigente". Então o status vira 'cancelada' e a
    data de vencimento **não** é alterada — os benefícios continuam valendo
    (`em_vigor` considera 'cancelada' com vencimento futuro).

    Devolve a assinatura cancelada, ou None se não havia nenhuma em vigor.
    """
    assinatura = assinatura_em_vigor(fornecedor)

    if assinatura is None:
        return None

    assinatura.status = "cancelada"
    assinatura.save(update_fields=["status"])
    return assinatura


def expirar_vencidas():
    """
    Marca como 'expirada' toda assinatura ativa cuja data já passou.

    Chamado em toda leitura do painel do fornecedor e na listagem. Sem cron job
    (o projeto não tem), o estado é resolvido na leitura — o painel nunca mostra
    uma assinatura vencida como ativa.
    """
    hoje = timezone.localdate()
    return Assinatura.objects.filter(status="ativa", data_vencimento__lt=hoje).update(
        status="expirada"
    )