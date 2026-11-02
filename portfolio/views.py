"""
Portfólio do fornecedor (RF-005 a RF-008, RF-010, RF-012, RF-013, RF-027 / CU05, CU06, CU10)
e listagem pública de fornecedores (RF-027 / CU04).

Divisão por perfil (RF-004 / RNF-006):
  - `@fornecedor_required`: gerenciar o próprio portfólio (CU10);
  - sem decorator: listagem e detalhe do fornecedor, que o CU04 define como
    acesso público. O que muda entre visitante e autenticado é o *conteúdo*
    (dados de contato e ações interativas), decidido por
    `core.contato.pode_ver_contato`, não o acesso à página.

Auditoria (RF-024): as alterações de Produto são gravadas automaticamente pelo
`django-simple-history` (ver `portfolio/models.py`), que é quem registra data,
usuário responsável e conteúdo anterior. Por isso este módulo **não** chama
`core.services.registrar_log` para Produto — ver a nota em `core/services.py`.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.contato import montar_canais, pode_ver_contato
from portfolio.forms import ProdutoForm
from portfolio.models import Produto
from portfolio.services import (
    categorias_ativas,
    fornecedores_publicados,
    nota_media,
    percentual_avaliacao,
    produtos_ativos,
    selo_plano,
)
from usuarios.decorators import fornecedor_required
from usuarios.models import Usuario

TEMPLATE_GERENCIAR = "produtos/gerenciar_portfolio.html"
TEMPLATE_FORM = "produtos/produto_form.html"
TEMPLATE_LISTA = "portfolio/listar_fornecedores.html"
TEMPLATE_DETALHE = "portfolio/detalhes_fornecedor.html"


# --------------------------------------------------------------------------
# CU10 — Gerenciar portfólio (RF-005 a RF-008)
# --------------------------------------------------------------------------

@fornecedor_required
def gerenciar_portfolio(request):
    """
    Fluxo principal do CU10, passo 2: lista os produtos já cadastrados com o
    status (ativo/inativo) e a opção de adicionar novo produto.
    """
    produtos = Produto.objects.filter(id_fornecedor=request.user).select_related(
        "id_categoria"
    ).order_by("-data_cadastro")

    produtos_com_form = [(produto, ProdutoForm(instance=produto)) for produto in produtos]

    return render(
        request,
        TEMPLATE_GERENCIAR,
        {
            "produtos": produtos,
            "produtos_com_form": produtos_com_form,
            "total_produtos": produtos.count(),
            "produtos_ativos": produtos.filter(status="ativo").count(),
            "tipo_menu": "fornecedor",
        },
    )


@fornecedor_required
def cadastrar_produto(request):
    """CU10 fluxo principal: registra o produto com status ativo (RF-005)."""
    form = ProdutoForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        produto = form.save(commit=False)
        produto.id_fornecedor = request.user
        produto.status = "ativo"
        produto.save()

        messages.success(request, "Produto cadastrado com sucesso.")
        return redirect("gerenciar_portfolio")

    return render(
        request,
        TEMPLATE_FORM,
        {
            "form": form,
            "modo": "cadastrar",
            "meus_produtos": produtos_ativos(request.user),
            "tipo_menu": "fornecedor",
        },
    )


@fornecedor_required
def editar_produto(request, produto_id):
    """
    CU10 fluxo alternativo A1: carrega o formulário com os dados atuais e salva
    as alterações. O `get_object_or_404` já trava em `id_fornecedor=request.user`,
    então um fornecedor não edita produto de outro (RNF-006).
    """
    produto = get_object_or_404(
        Produto, id_produto=produto_id, id_fornecedor=request.user
    )

    form = ProdutoForm(request.POST or None, instance=produto)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produto atualizado com sucesso.")
        return redirect("gerenciar_portfolio")

    # O template abre o modal de edição sobre a própria listagem.
    produtos = Produto.objects.filter(id_fornecedor=request.user).select_related(
        "id_categoria"
    ).order_by("-data_cadastro")

    return render(
        request,
        TEMPLATE_GERENCIAR,
        {
            "produtos": produtos,
            "produtos_com_form": [(p, ProdutoForm(instance=p)) for p in produtos],
            "modal_aberto": produto.id_produto,
            "form": form,
            "modo": "editar",
            "tipo_menu": "fornecedor",
        },
    )


@fornecedor_required
def alternar_status_produto(request, produto_id):
    """
    CU10 fluxo alternativo A2 / RF-007: alterna ativo <-> inativo e reflete
    imediatamente na listagem pública (a listagem só expõe produtos ativos).
    """
    produto = get_object_or_404(
        Produto, id_produto=produto_id, id_fornecedor=request.user
    )

    if request.method == "POST":
        produto.status = "inativo" if produto.status == "ativo" else "ativo"
        produto.save(update_fields=["status"])
        messages.success(
            request,
            f"Produto marcado como {produto.get_status_display().lower()}.",
        )

    return redirect("gerenciar_portfolio")


@fornecedor_required
def remover_produto(request, produto_id):
    """
    CU10 fluxo alternativo A3 / RF-008: remoção **permanente** do portfólio.

    Só por POST — a tela de confirmação é o próprio botão dentro de um form
    (o CSS `confirmação` já traz o aviso "ação permanente e irreversível").
    O histórico da remoção fica no simple_history (RF-024), porque a linha sai
    do banco mas o registro de auditoria permanece.
    """
    produto = get_object_or_404(
        Produto, id_produto=produto_id, id_fornecedor=request.user
    )

    if request.method == "POST":
        nome = produto.nome
        produto.delete()
        messages.success(request, f"Produto “{nome}” removido do portfólio.")

    return redirect("gerenciar_portfolio")


# --------------------------------------------------------------------------
# RF-027 / CU04 — Listagem e detalhe públicos
# --------------------------------------------------------------------------

def listar_fornecedores(request):
    """
    CU04 (público) + CU05 (autenticado) + CU06 (busca/filtro) na mesma tela.

    Filtros via query string para o filtro sobreviver ao F5 e ser compartilhável:
      ?categoria=<id_categoria>   RF-013 / CU06 (filtro por categoria)
      ?busca=<termo>             RF-013 / CU06 A1 (busca textual)
      ?sem_resultados=1          CU06 E1, quando nada casou
    """
    categorias = categorias_ativas()

    categoria_id = request.GET.get("categoria") or None
    categoria = None
    if categoria_id:
        categoria = categorias.filter(pk=categoria_id).first()

    busca = request.GET.get("busca", "").strip()

    fornecedores = fornecedores_publicados(categoria=categoria, busca=busca)

    # `percentual` para o componente de estrelas (RF-010/RF-018).
    for fornecedor in fornecedores:
        fornecedor.nota_percent = percentual_avaliacao(fornecedor.nota_media)

    contexto = {
        "fornecedores": fornecedores,
        "categorias": categorias,
        "categoria_selecionada": categoria,
        "busca": busca,
        "tem_filtro": bool(categoria or busca),
        "sem_resultados": not fornecedores.exists(),
    }
    return render(request, TEMPLATE_LISTA, contexto)


def detalhes_fornecedor(request, fornecedor_id):
    """
    CU04 (visitante) e CU05 (comerciante autenticado) — mesma URL.

    Visitante: vê produtos, categorias, preços e a nota média, mais o aviso de
    que contato e funções interativas exigem cadastro (passo 5 do CU04).
    Autenticado: vê também os canais de contato do RF-012 e as ações de
    favoritos (RF-029) e avaliação (RF-018).
    """
    fornecedor = get_object_or_404(
        Usuario, pk=fornecedor_id, tipo_perfil="fornecedor"
    )

    categoria_id = request.GET.get("categoria") or None
    categoria = None
    if categoria_id:
        categoria = categorias_ativas().filter(pk=categoria_id).first()

    produtos = produtos_ativos(fornecedor, categoria=categoria)

    media = nota_media(fornecedor)
    total_avaliacoes = fornecedor.avaliacoes_recebidas.filter(status_moderacao="ativa").count()
    mostrar_contato = pode_ver_contato(request)

    # Um fornecedor não deve avaliar a si mesmo nem ser avaliado por outro
    # fornecedor: a avaliação é de comerciante (RF-018).
    pode_avaliar = (
        request.user.is_authenticated
        and request.user.is_comerciante
        and request.user.pk != fornecedor.pk
    )
    pode_favoritar = (
        request.user.is_authenticated
        and request.user.is_comerciante
        and request.user.pk != fornecedor.pk
    )

    contexto = {
        "fornecedor": fornecedor,
        "produtos": produtos,
        "total_produtos": produtos.count(),
        "media": media,
        "percentagem": percentual_avaliacao(media),
        "media_arredondada": _nota_visual(media),
        "total_avaliacoes": total_avaliacoes,
        # Avaliações exibidas no detalhe. Traz todas (inclusive as removidas pela
        # moderação) para que o autor da avaliação removida ainda veja o próprio
        # registro; o template decide o que cada perfil enxerga.
        "avaliacoes": _avaliacoes_com_percentual(fornecedor),
        "categorias_do_fornecedor": (
            produtos.values_list("id_categoria", flat=True).distinct()
        ),
        "pode_ver_contato": mostrar_contato,
        "canais": (
            montar_canais(
                fornecedor,
                mensagem_whatsapp=f"Olá! Vi seu portfólio no suppra e gostaria de negociar.",
            )
            if mostrar_contato
            else []
        ),
        "pode_avaliar": pode_avaliar,
        "pode_favoritar": pode_favoritar,
        "favoritado": False,
        "minha_avaliacao": None,
        "plano": selo_plano(fornecedor),
        "tipo_menu": getattr(request.user, "tipo_perfil", None)
        if request.user.is_authenticated
        else None,
    }

    # Estados de favorito/avaliação só interessam a comerciante logado
    # (RF-018, RF-029, RF-030).
    if pode_favoritar:
        from avaliacoes.models import Avaliacao, Favorito

        contexto["favoritado"] = Favorito.objects.filter(
            id_comerciante=request.user, id_fornecedor=fornecedor
        ).exists()
        avaliacao = Avaliacao.objects.filter(
            id_comerciante=request.user, id_fornecedor=fornecedor
        ).first()
        contexto["minha_avaliacao"] = avaliacao

    return render(request, TEMPLATE_DETALHE, contexto)


def _nota_visual(media):
    """
    Nota arredondada para exibir em estrelas (RF-010/RF-018: "0 a 5 estrelas").

    `media` pode ser None (sem avaliação ainda) -> 0 estrelas.
    """
    if not media:
        return 0
    return int(round(float(media)))


def _avaliacoes_com_percentual(fornecedor):
    """Avaliações do fornecedor com `nota_percent` já calculado para o template."""
    from avaliacoes.models import Avaliacao

    avaliacoes = (
        Avaliacao.objects.filter(id_fornecedor=fornecedor)
        .select_related("id_comerciante")
        .order_by("-data_avaliacao")
    )

    for avaliacao in avaliacoes:
        avaliacao.nota_percent = percentual_avaliacao(avaliacao.nota)

    return avaliacoes