"""
Serviços de consulta das demandas (RF-011, RF-013, RF-027 / CU04, CU11).

Mesma philosophy de `portfolio/services.py`: as views só montam o contexto, a
consulta mora aqui para que a listagem pública e a área do fornecedor mostrem
exatamente os mesmos dados.

Regra de visibilidade aplicada aqui (RF-027, CU04 e CU11):
  - a listagem pública mostra apenas demandas com status 'publicada' — as
    encerradas saem do ar mas ficam no histórico do comerciante (CU07 A2);
  - os dados de contato do comerciante NÃO são selecionados aqui. São montados
    por `core.contato.montar_canais` somente quando o visitante está
    autenticado (RF-012).
"""

from django.db.models import Q

from demandas.models import Demanda


def demandas_publicadas(categoria=None, busca=None):
    """
    Demandas publicadas, com filtro opcional.

    - `categoria` (RF-011 / RF-013): id de CategoriaInsumo;
    - `busca` (RF-013): termo livre em nome do comerciante, descrição do produto
      e nome da categoria.

    Filtros de perfil (RF-012): a restriction de perfil fica nas views, não aqui,
    porque muda conforme quem está vendo (o comerciante vê as próprias demandas
    inclusive encerradas).
    """
    qs = Demanda.objects.filter(status="publicada").select_related(
        "id_comerciante", "id_categoria"
    )

    if categoria:
        qs = qs.filter(id_categoria=categoria)

    if busca:
        termo = busca.strip()
        if termo:
            qs = qs.filter(
                Q(descricao_produto__icontains=termo)
                | Q(id_comerciante__nome__icontains=termo)
                | Q(id_categoria__nome__icontains=termo)
            )

    return qs.order_by("-data_publicacao")


def demandas_por_categoria(qs=None):
    """
    Agrupa as demandas por categoria de insumo (RF-011: "organizadas por
    categoria de insumo").

    Devolve uma lista de tuplas (categoria, [demandas]) para o template iterar
    sem repetir query por grupo.
    """
    from core.models import CategoriaInsumo

    if qs is None:
        qs = demandas_publicadas()

    por_id = {}
    for demanda in qs:
        por_id.setdefault(demanda.id_categoria_id, []).append(demanda)

    categorias = CategoriaInsumo.objects.filter(pk__in=por_id).order_by("nome")

    return [(categoria, por_id[categoria.pk]) for categoria in categorias]


def categorias_com_demandas():
    """
    Categorias que efetivamente têm demanda publicada, para o filtro lateral da
    listagem (RF-013). Não lista categorias vazias — o filtro oferece o que
    devolve resultado.
    """
    from core.models import CategoriaInsumo

    ids = Demanda.objects.filter(status="publicada").values_list(
        "id_categoria", flat=True
    ).distinct()

    return CategoriaInsumo.objects.filter(pk__in=ids, status="ativa").order_by("nome")


def pode_acessar_detalhe(demanda, user):
    """
    Quem pode ver o detalhe com dados de contato de uma demanda (RF-012).

    - visitante anônimo: vê o conteúdo público, sem contato;
    - comerciante logado: vê sempre (é o próprio mercado de quem publica);
    - fornecedor logado: vê sempre — é o público-alvo do RF-011/CU11;
    - o próprio comerciante: vê sempre.

    Em todos os casos o contato só é montado se `pode_ver_contato` permitir
    (usuário autenticado).
    """
    return user.is_authenticated