"""
Avaliação de fornecedores (RF-018 / CU09) e lista de favoritos
(RF-028, RF-029, RF-030 / CU08).

Ambos os models (`Avaliacao` e `Favorito`) usam chave primária composta
`(id_comerciante, id_fornecedor)`, exatamente como no banco.sql. Isso muda duas
coisas na implementação:

  1. `get_or_create` no par resolve o "criar ou atualizar" do RF-018: a pós
     condição do CU09 diz que o comerciante "não pode submeter uma nova avaliação
     para o mesmo fornecedor sem editar a existente" — ou seja, uma segunda
     avaliação para o mesmo par **atualiza** a anterior, não cria outra linha;
  2. não existe campo `id` próprio, então a view de detalhe recebe o
     `id_fornecedor` pela URL e monta a tela a partir dele.

Por isso estes dois models não aparecem no Django Admin: o Admin recusa o
registro de models com chave primária composta (`ImproperlyConfigured: The model
Avaliacao has a composite primary key`), como o próprio `README.md` já registra.
A gestão fica nestas views e, para moderação, na fila de avaliações de
`moderacao/views.py` (CU22 A1).
"""

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from avaliacoes.forms import AvaliacaoForm
from avaliacoes.models import Avaliacao, Favorito
from core.models import CategoriaInsumo
from portfolio.models import Produto
from portfolio.services import fornecedores_publicados
from usuarios.decorators import comerciante_required
from usuarios.models import Usuario

TEMPLATE_AVALIAR = "avaliacoes/avaliar_fornecedor.html"
TEMPLATE_FAVORITOS = "avaliacoes/lista_favoritos.html"


# --------------------------------------------------------------------------
# CU09 — Avaliar fornecedor (RF-018)
# --------------------------------------------------------------------------

@comerciante_required
def avaliar_fornecedor(request, fornecedor_id):
    """
    Registrar (fluxo principal) ou editar (já avaliado antes) a avaliação de um
    fornecedor.

    - E3 do RF-018 é o "falha técnica": o `IntegrityError` do banco é capturado
      e vira mensagem pedindo para tentar de novo, sem derrubar a página (500).
    - A pós-condição do CU09 (recalcular a média) acontece na tela seguinte, já
      que `detalhes_fornecedor` lê a média do banco a cada requisição.
    """
    fornecedor = get_object_or_404(
        Usuario, pk=fornecedor_id, tipo_perfil="fornecedor"
    )

    if fornecedor.pk == request.user.pk:
        messages.error(request, "Você não pode avaliar a si mesmo.")
        return redirect("detalhes_fornecedor", fornecedor_id=fornecedor.pk)

    avaliacao_existente = Avaliacao.objects.filter(
        id_comerciante=request.user, id_fornecedor=fornecedor
    ).first()

    if request.method == "POST":
        form = AvaliacaoForm(request.POST, instance=avaliacao_existente)

        if form.is_valid():
            try:
                with transaction.atomic():
                    avaliacao = form.save(commit=False)
                    avaliacao.id_comerciante = request.user
                    avaliacao.id_fornecedor = fornecedor
                    # Reavaliado entra como 'ativa': se estava removida pela
                    # moderação (RF-025), um novo parecer do mesmo comerciante
                    # começa limpo no filtro de exibição.
                    avaliacao.status_moderacao = "ativa"
                    avaliacao.save()
            except IntegrityError:
                # RF-018, fluxo de exceção E1: falha técnica ao registrar.
                messages.error(request, "Não foi possível registrar sua avaliação. Tente novamente.")
                return redirect("avaliar_fornecedor", fornecedor_id=fornecedor.pk)

            messages.success(request, "Avaliação registrada com sucesso.")
            return redirect("detalhes_fornecedor", fornecedor_id=fornecedor.pk)
    else:
        form = AvaliacaoForm(instance=avaliacao_existente)

    return render(
        request,
        TEMPLATE_AVALIAR,
        {
            "form": form,
            "fornecedor": fornecedor,
            "editando": avaliacao_existente is not None,
            "nota_atual": avaliacao_existente.nota if avaliacao_existente else None,
            "tipo_menu": "comerciante",
        },
    )


# --------------------------------------------------------------------------
# CU08 — Favoritos (RF-028, RF-029, RF-030)
# --------------------------------------------------------------------------

@comerciante_required
def alternar_favorito(request):
    """
    Adiciona (RF-029) ou remove (RF-030) o fornecedor da lista de favoritos.

    Uma única ação para os dois casos: o botão no portfólio e o da lista de
    favoritos mandam o mesmo POST e a view decide pelo estado atual. Isso
    satisfaz o CU08, que descreve o par "adicionar" e "remover" a partir dos
    mesmos lugares.

    Só por POST: alternar estado por GET permitiria que um link colado no chat de
    um comerciante favoritasse um fornecedor sem ele querer.
    """
    fornecedor_id = request.POST.get("fornecedor_id")
    fornecedor = get_object_or_404(
        Usuario, pk=fornecedor_id, tipo_perfil="fornecedor"
    )

    if request.method != "POST":
        return redirect("detalhes_fornecedor", fornecedor_id=fornecedor.pk)

    favorito, criado = Favorito.objects.get_or_create(
        id_comerciante=request.user, id_fornecedor=fornecedor
    )

    if criado:
        messages.success(request, f"{fornecedor.nome} foi adicionado aos seus favoritos.")
    else:
        favorito.delete()
        messages.info(request, f"{fornecedor.nome} foi removido dos seus favoritos.")

    voltar = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if voltar:
        return redirect(voltar)
    return redirect("detalhes_fornecedor", fornecedor_id=fornecedor.pk)


@comerciante_required
def remover_favorito(request, fornecedor_id):
    """Remoção explícita pela lista de favoritos (CU08, fluxo alternativo A2)."""
    fornecedor = get_object_or_404(
        Usuario, pk=fornecedor_id, tipo_perfil="fornecedor"
    )

    if request.method == "POST":
        Favorito.objects.filter(
            id_comerciante=request.user, id_fornecedor=fornecedor
        ).delete()
        messages.info(request, f"{fornecedor.nome} foi removido dos seus favoritos.")

    return redirect("lista_favoritos")


@comerciante_required
def lista_favoritos(request):
    """
    RF-028 / CU08 A1: lista dos fornecedores favoritados com nome, categorias de
    insumo ofertadas e avaliação média em estrelas de 0 a 5.

    Reaproveita `portfolio.services.fornecedores_publicados` para que a nota
    média exibida aqui seja exatamente a mesma do portfólio. A diferença é que
    um fornecedor favoritado continua na lista mesmo sem produto ativo no
    momento (o favorito não "desfavorita" sozinho) — por isso o filtro de
    "precisa ter produto ativo" fica desligado.
    """
    from portfolio.services import percentual_avaliacao

    ids_favoritos = list(
        Favorito.objects.filter(id_comerciante=request.user).values_list(
            "id_fornecedor", flat=True
        )
    )

    fornecedores = fornecedores_publicados(somente_com_produtos_ativos=False).filter(
        pk__in=ids_favoritos
    )

    # Categorias de insumo ofertadas por cada favorito (RF-028). Montado aqui
    # para não repetir a mesma categoria quando o fornecedor tem vários produtos
    # na mesma categoria — algo que o template não consegue deduplicar.
    # O dicionário é {id_fornecedor: {id_categoria: categoria}}.
    categorias_por_fornecedor = {}

    if ids_favoritos:
        for produto in Produto.objects.filter(
            id_fornecedor__in=ids_favoritos, status="ativo"
        ).select_related("id_categoria"):
            categorias_por_fornecedor.setdefault(produto.id_fornecedor_id, {})[
                produto.id_categoria_id
            ] = produto.id_categoria

    for fornecedor in fornecedores:
        fornecedor.nota_percent = percentual_avaliacao(fornecedor.nota_media)
        fornecedor.categorias_ofertadas = sorted(
            categorias_por_fornecedor.get(fornecedor.pk, {}).values(),
            key=lambda categoria: categoria.nome,
        )

    return render(
        request,
        TEMPLATE_FAVORITOS,
        {
            "fornecedores": fornecedores,
            "total_favoritos": fornecedores.count(),
            "categorias_ofertadas": CategoriaInsumo.objects.filter(
                pk__in={
                    id_f
                    for categorias in categorias_por_fornecedor.values()
                    for id_f in categorias
                },
                status="ativa",
            ).order_by("nome"),
            "tipo_menu": "comerciante",
        },
    )