"""
Indicadores da plataforma para a equipe gestora (RF-017 / CU24).

CU24, passo 3: "o sistema exibe os indicadores gerais atualizados: número de
fornecedores cadastrados, número de produtos ativos, número de comerciantes
ativos e número de demandas publicadas".

Pós-condição do CU24: "Nenhuma alteração é realizada nos dados durante a
consulta" — por isso tudo aqui é só `count()`/`aggregate()`, nada grava.

Cada número tem uma regra explícita de "ativo", porque o painel precisa refletir
a plataforma em operação, e não o histórico dela:

  - **fornecedores cadastrados**: perfil fornecedor com conta ativa. Um
    fornecedor suspenso pela moderação (RF-025) ou excluído (RF-016) não conta
    como fornecedor cadastrado ativo.
  - **produtos ativos**: `status='ativo'` (RF-007), já que produto inativo não
    aparece na listagem pública.
  - **comerciantes ativos**: perfil comerciante com conta ativa.
  - **demandas publicadas**: `status='publicada'` (RF-009); encerradas saem da
    listagem, então ficam de fora.

Os números de apoio (denúncias pendentes, chamados abertos, planos ativos) não
são exigidos pelo CU24, mas aparecem na tela de apoio à moderação do CU22 e do
CU19 — são apenas contagens, sem efeito colateral.
"""

from django.db.models import Avg, Count

from assinaturas.models import Assinatura
from demandas.models import Demanda
from moderacao.models import Denuncia
from portfolio.models import Produto
from suporte.models import Suporte
from usuarios.models import Usuario


def indicadores_gerais():
    """Os quatro indicadores exigidos pelo CU24, passo 3."""
    from django.utils import timezone

    hoje = timezone.localdate()

    assinaturas_ativas = Assinatura.objects.filter(
        status="ativa", data_vencimento__gte=hoje
    ).count()

    return {
        "fornecedores": Usuario.objects.filter(
            tipo_perfil="fornecedor", status_conta="ativa"
        ).count(),
        "produtos_ativos": Produto.objects.filter(status="ativo").count(),
        "comerciantes": Usuario.objects.filter(
            tipo_perfil="comerciante", status_conta="ativa"
        ).count(),
        "demandas_publicadas": Demanda.objects.filter(status="publicada").count(),
        # Apoio à operação (CU22 moderação / CU19 suporte / CU23 assinaturas).
        "assinaturas_ativas": assinaturas_ativas,
        "denuncias_pendentes": Denuncia.objects.filter(status="pendente").count(),
        "chamados_abertos": Suporte.objects.exclude(status="encerrado").count(),
    }


def indicadores_de_qualidade():
    """
    Distribuição de notas e média geral das avaliações ativas (apoio ao CU24).

    O CU24 só pede os quatro contadores; a média entra como informação auxiliar
    do mesmo painel, sem gerar tela nova.
    """
    from avaliacoes.models import Avaliacao

    ativas = Avaliacao.objects.filter(status_moderacao="ativa")
    media = ativas.aggregate(media=Avg("nota"))["media"]

    distribuicao = list(
        ativas.values("nota").annotate(total=Count("nota")).order_by("nota")
    )
    por_nota = {linha["nota"]: linha["total"] for linha in distribuicao}

    return {
        "media": media,
        "total": sum(por_nota.values()),
        "distribuicao": [
            {"nota": nota, "total": por_nota.get(nota, 0)} for nota in range(0, 6)
        ],
    }