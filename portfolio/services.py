"""
Consultas do portfólio de fornecedores (RF-010, RF-012, RF-013, RF-027).

Separado das views para que a listagem pública e o detalhe do fornecedor
montem exatamente a mesma consulta de nota média e produtos — assim a avaliação
mostrada na listagem (RF-010: "avaliação média do fornecedor em estrelas, de 0
a 5") é sempre a mesma que aparece no detalhe (RF-018).

Regra de privacidade aplicada aqui (RF-027, CU04):
  - só entram na listagem pública fornecedores com conta ativa e **ao menos um
    produto ativo**;
  - os dados de contato NÃO são selecionados aqui. Eles só são montados por
    `core.contato.montar_canais` quando o visitante está autenticado.
"""

from django.db.models import Avg, Count, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce

from portfolio.models import Produto
from usuarios.models import Usuario


def categorias_ativas():
    """Categorias ativas para os filtros de categoria (RF-013)."""
    from core.models import CategoriaInsumo

    return CategoriaInsumo.objects.filter(status="ativa").order_by("nome")


def fornecedores_publicados(categoria=None, busca=None, somente_com_produtos_ativos=True):
    """
    Queryset de fornecedores com portfólio visível, com nota média e total de
    produtos ativos.

    - `categoria` (RF-013): id de CategoriaInsumo, filtra os fornecedores que
      têm produto ativo naquela categoria;
    - `busca` (RF-013, fluxo alternativo A1 do CU06): termo livre, casa em nome
      do produto, nome da categoria e nome do fornecedor (RF-006 fala em "nomes
      de produtos e categorias"; incluir o nome do fornecedor é o que o usuário
      realmente digita ao procurar "distribuidora X");
    - `somente_com_produtos_ativos`: a listagem pública (CU04) só mostra quem tem
      o que oferecer. A lista de favoritos (RF-028) desliga esse filtro, porque
      um fornecedor favoritado não sai da lista só por estar sem produto ativo
      agora.

    `nota_media` vem de um Subquery para não ser afetado pela multiplicação das
    junções com produto (um fornecedor com 5 produtos e 2 avaliações geraria
    10 linhas e falsearia a média).
    """
    from avaliacoes.models import Avaliacao

    nota_media = Avaliacao.objects.filter(
        id_fornecedor=OuterRef("pk"),
        status_moderacao="ativa",
    ).values("id_fornecedor").annotate(media=Avg("nota")).values("media")

    filtros = {
        "tipo_perfil": "fornecedor",
        "status_conta": "ativa",
    }
    if somente_com_produtos_ativos:
        filtros["produtos__status"] = "ativo"

    qs = Usuario.objects.filter(**filtros).annotate(
        nota_media=Coalesce(Subquery(nota_media), 0.0),
        total_produtos=Count("produtos", filter=Q(produtos__status="ativo"), distinct=True),
        # `distinct=True` contaria a chave primária, e Avaliacao tem PK
        # composta — o Django/MySQL recusam ("COUNT(DISTINCT) doesn't support
        # composite primary keys"). Contar a coluna id_comerciante dá o mesmo
        # resultado: um comerciante avalia um fornecedor no máximo uma vez.
        total_avaliacoes=Count(
            "avaliacoes_recebidas__id_comerciante",
            filter=Q(avaliacoes_recebidas__status_moderacao="ativa"),
            distinct=True,
        ),
    ).distinct()

    if categoria:
        qs = qs.filter(produtos__id_categoria=categoria, produtos__status="ativo")

    if busca:
        termo = busca.strip()
        if termo:
            qs = qs.filter(
                Q(nome__icontains=termo)
                | Q(produtos__nome__icontains=termo)
                | Q(produtos__id_categoria__nome__icontains=termo)
            ).distinct()

    # `produtos_ativos_cache` alimenta a amostra de itens do card na listagem
    # (RF-010 mostra nome, categoria e preço de cada produto ofertado).
    # `assinaturas__id_plano` dá o selo Silver/Gold (RF-020).
    qs = qs.prefetch_related(
        Prefetch(
            "produtos",
            queryset=Produto.objects.filter(status="ativo").select_related("id_categoria"),
            to_attr="produtos_ativos_cache",
        ),
        "assinaturas__id_plano",
    )

    return qs.order_by("nome")


def produtos_ativos(fornecedor, categoria=None, busca=None):
    """Produtos ativos de um fornecedor, com a categoria junto e busca opcional."""
    qs = Produto.objects.filter(
        id_fornecedor=fornecedor, status="ativo"
    ).select_related("id_categoria")

    if categoria:
        qs = qs.filter(id_categoria=categoria)

    if busca:
        termo = busca.strip()
        if termo:
            qs = qs.filter(
                Q(nome__icontains=termo) | Q(id_categoria__nome__icontains=termo)
            )

    return qs.order_by("nome")


def nota_media(fornecedor):
    """Média das avaliações ativas de um fornecedor (RF-018)."""
    from avaliacoes.models import Avaliacao

    return (
        Avaliacao.objects.filter(
            id_fornecedor=fornecedor, status_moderacao="ativa"
        ).aggregate(media=Avg("nota"))["media"]
    )


def percentual_avaliacao(nota):
    """
    Porcentagem (0 a 100) que a barra de estrelas deve preencher.

    O RF-018 define a escala de 0 a 5, então 3 estrelas = 60%. Calculado aqui
    (e não no template) para manter o `componentes/estrelas.html` sem aritmética.
    Sem nota nenhuma -> 0.
    """
    if not nota:
        return 0
    return max(0, min(100, round(float(nota) / 5 * 100)))


def selo_plano(fornecedor):
    """
    Nome do plano de assinatura vigente do fornecedor (RF-020/CU13), ou None
    para quem está no plano gratuito.

    Só retorna plano com status 'ativa' e vencimento no futuro: assinatura
    suspensa, cancelada ou vencida não selo mais o portfólio.
    """
    from django.utils import timezone

    from assinaturas.models import Assinatura

    assinatura = (
        Assinatura.objects.filter(id_fornecedor=fornecedor, status="ativa")
        .select_related("id_plano")
        .filter(data_vencimento__gte=timezone.localdate())
        .order_by("-data_vencimento")
        .first()
    )
    return assinatura.id_plano if assinatura else None