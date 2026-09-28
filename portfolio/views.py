from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.decorators import fornecedor_logado
from portfolio.models import Produto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            "nome",
            "id_categoria",
            "preco",
            "telefone_contato",
            "whatsapp_contato",
        ]

        labels = {
            "nome": "Nome do produto ou serviço",
            "id_categoria": "Categoria de insumo",
            "preco": "Preço unitário",
            "telefone_contato": "Telefone de contato",
            "whatsapp_contato": "WhatsApp de contato",
        }


@fornecedor_logado
def gerenciar_portfolio(request):
    produtos = Produto.objects.filter(
        id_fornecedor=request.user
    ).select_related("id_categoria")

    produtos_com_form = [
        (produto, ProdutoForm(instance=produto))
        for produto in produtos
    ]

    return render(
        request,
        "portfolio/gerenciar_portfolio.html",
        {
            "produtos_com_form": produtos_com_form,
            "tipo_menu": "fornecedor",
        },
    )


@fornecedor_logado
def cadastrar_produto(request):
    form = ProdutoForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        produto = form.save(commit=False)
        produto.id_fornecedor = request.user
        produto.save()

        messages.success(
            request,
            "Produto cadastrado com sucesso."
        )

        return redirect("dashboard_fornecedor")

    return render(
        request,
        "produtos/produto_form.html",
        {
            "form": form,
            "tipo_menu": "fornecedor",
        },
    )


@fornecedor_logado
def editar_produto(request, produto_id):
    produto = get_object_or_404(
        Produto,
        id_produto=produto_id,
        id_fornecedor=request.user,
    )

    form = ProdutoForm(
        request.POST or None,
        instance=produto
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        messages.success(
            request,
            "Produto atualizado com sucesso."
        )

        return redirect("dashboard_fornecedor")

    produtos = Produto.objects.filter(
        id_fornecedor=request.user
    ).select_related("id_categoria")

    produtos_com_form = [
        (item, ProdutoForm(instance=item))
        for item in produtos
    ]

    return render(
        request,
        "portfolio/gerenciar_portfolio.html",
        {
            "produtos_com_form": produtos_com_form,
            "modal_aberto": produto.id_produto,
            "form": form,
            "tipo_menu": "fornecedor",
        },
    )


@fornecedor_logado
def alternar_status_produto(request, produto_id):
    produto = get_object_or_404(
        Produto,
        id_produto=produto_id,
        id_fornecedor=request.user,
    )

    if request.method == "POST":
        if produto.status == "ativo":
            produto.status = "inativo"
        else:
            produto.status = "ativo"

        produto.save(update_fields=["status"])

    return redirect("dashboard_fornecedor")