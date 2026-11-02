"""
Denúncia de conteúdo (RF-025 / CU14) e moderação pelo painel (RF-025 / CU22).

- `denunciar_view` — a tela que o comerciante ou fornecedor usa para denunciar
  (CU14). Qualquer usuário **autenticado** pode denunciar um portfólio ou uma
  demanda.
- `fila_avaliacoes_view` / `decidir_avaliacao_view` — o fluxo alternativo A1 do
  CU22 (manter ou remover uma avaliação). Não roda no Django Admin porque
  `Avaliacao` tem chave primária composta, que o Admin recusa registrar; por
  isso é uma view com `@admin_required` (o mesmo público do `/admin/`).

A decisão sobre denúncias (CU22, fluxo principal) fica em
`moderacao/services.py` e é disparada pelas ações do Django Admin
(`moderacao/admin.py`).
"""

import os

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.services import registrar_log
from demandas.models import Demanda
from moderacao.forms import DenunciaForm
from moderacao.models import Denuncia
from portfolio.models import Produto
from usuarios.decorators import admin_required, login_usuario_requerido
from usuarios.models import Usuario

TEMPLATE_DENUNCIAR = "usuarios/denunciar.html"


def _salvar_evidencia(arquivo):
    """
    Grava a imagem enviada em MEDIA_ROOT e devolve o caminho relativo.

    O banco.sql guarda `evidencia VARCHAR(500)`, então o que vai para o banco é
    o caminho, não os bytes. O nome do arquivo é gerado com `uuid4` para não
    sobrescrever o arquivo de outra denúncia nem vazar o nome original do
    upload na URL pública.
    """
    from uuid import uuid4

    extensao = os.path.splitext(arquivo.name)[1].lower() or ".jpg"
    nome = f"denuncia_{uuid4().hex}{extensao}"

    destino = os.path.join(settings.MEDIA_ROOT, "denuncias")
    os.makedirs(destino, exist_ok=True)

    caminho_absoluto = os.path.join(destino, nome)
    with open(caminho_absoluto, "wb") as arquivo_saida:
        for pedaco in arquivo.chunks():
            arquivo_saida.write(pedaco)

    # Caminho relativo ao MEDIA_ROOT: é o que a URL de mídia resolve.
    return f"denuncias/{nome}"


def _resolver_alvo(tipo_conteudo, produto_id, demanda_id):
    """
    Descobre qual conteúdo está sendo denunciado.

    O `banco.sql` não tem CHECK que amarre `tipo_conteudo` ao campo preenchido
    (`id_produto` ou `id_demanda`), então a combinação é validada aqui: exigir a
    coerência evita uma denúncia órfã, que a CU22 não conseguiria julgar (o
    `_autor_do_conteudo` não acharia infrator).

    Devolve (produto, demanda), com um dos dois preenchido.
    """
    if tipo_conteudo == "portfolio":
        produto = get_object_or_404(Produto, pk=produto_id)
        return produto, None

    if tipo_conteudo == "demanda":
        demanda = get_object_or_404(Demanda, pk=demanda_id)
        return None, demanda

    return None, None


@login_usuario_requerido
def denunciar_view(request):
    """
    CU14 — Denunciar conteúdo (portfólio ou demanda).

    Recebe por POST o tipo e o id do conteúdo (``tipo_conteudo`` +
    ``id_produto`` OU ``id_demanda``). A página de formulário permite corrigir o
    tipo antes de confirmar.
    """
    tipo_conteudo = request.POST.get("tipo_conteudo") or request.GET.get("tipo_conteudo")
    produto_id = request.POST.get("id_produto") or request.GET.get("id_produto")
    demanda_id = request.POST.get("id_demanda") or request.GET.get("id_demanda")

    # Sem alvo definido ainda: abre a tela para o usuário escolher. Na prática
    # as telas de portfólio e demanda já mandam o alvo pronto.
    if tipo_conteudo not in ("portfolio", "demanda"):
        return render(request, TEMPLATE_DENUNCIAR, {"form": DenunciaForm()})

    produto, demanda = _resolver_alvo(tipo_conteudo, produto_id, demanda_id)

    contexto = {
        "tipo_conteudo": tipo_conteudo,
        "produto": produto,
        "demanda": demanda,
        # O botão "Denunciar Conteúdo" da tela de origem manda `next` para
        # devolver o usuário ao portfólio/demanda depois do envio (CU05 A1 e
        # CU11 A1).
        "next": request.POST.get("next") or request.GET.get("next") or "",
    }

    if request.method == "POST":
        form = DenunciaForm(request.POST, request.FILES)

        if form.is_valid():
            denuncia = form.save(commit=False)
            denuncia.id_denunciante = request.user
            denuncia.tipo_conteudo = tipo_conteudo
            denuncia.id_produto = produto
            denuncia.id_demanda = demanda
            denuncia.status = "pendente"  # fila da equipe gestora (CU22)

            evidencia = form.cleaned_data.get("evidencia")
            if evidencia is not None:
                denuncia.evidencia = _salvar_evidencia(evidencia)

            denuncia.save()

            messages.success(
                request,
                "Denúncia recebida. A equipe gestora vai analisar e retornar "
                "pelo canal de suporte.",
            )
            voltar = request.POST.get("next")
            if voltar:
                return redirect(voltar)
            return redirect("home")

        messages.error(request, "Confira os campos destacados antes de enviar.")
    else:
        form = DenunciaForm()

    contexto["form"] = form
    return render(request, TEMPLATE_DENUNCIAR, contexto)


# --------------------------------------------------------------------------
# CU22, fluxo alternativo A1 — fila de avaliações (admin)
# --------------------------------------------------------------------------

@admin_required
def fila_avaliacoes_view(request):
    """
    CU22 A1 — "O administrador acessa a fila de avaliações sinalizadas para
    moderação", que exibe "a avaliação, o comentário e os dados das partes
    envolvidas (comerciante avaliador e fornecedor avaliado)".

    Filtros: `?status=ativa|removida|Todas` e `?nota=0..5`. Como
    `Avaliacao` tem PK composta, a view monta o queryset direto em vez de usar
    um `ModelAdmin`.
    """
    from avaliacoes.models import Avaliacao
    from portfolio.services import percentual_avaliacao

    avaliacoes = Avaliacao.objects.select_related(
        "id_comerciante", "id_fornecedor"
    ).order_by("-data_avaliacao")

    status = request.GET.get("status", "ativa")
    if status in ("ativa", "removida"):
        avaliacoes = avaliacoes.filter(status_moderacao=status)

    nota = request.GET.get("nota", "")
    if nota in {str(n) for n in range(0, 6)}:
        avaliacoes = avaliacoes.filter(nota=int(nota))

    avaliacoes = list(avaliacoes)

    # Percentual de preenchimento das estrelas, para o componente compartilhado.
    for avaliacao in avaliacoes:
        avaliacao.nota_percent = percentual_avaliacao(avaliacao.nota)

    contexto = {
        "avaliacoes": avaliacoes,
        "status_filtro": status,
        "nota_filtro": nota,
        "total": len(avaliacoes),
        "tipo_menu": "admin",
    }
    return render(request, "moderacao/fila_avaliacoes.html", contexto)


@admin_required
def decidir_avaliacao_view(request, id_comerciante, id_fornecedor):
    """
    CU22 A1 — "O sistema registra a decisão e atualiza a exibição da avaliação
    na plataforma conforme a ação tomada": manter ou remover.

    A remoção põe `status_moderacao='removida'`, o que a faz sair da média e da
    listagem pública (RF-018). A decisão vai para `log_alteracao` (RF-024).
    """
    from avaliacoes.models import Avaliacao

    avaliacao = get_object_or_404(
        Avaliacao, id_comerciante=id_comerciante, id_fornecedor=id_fornecedor
    )

    if request.method == "POST":
        decisao = request.POST.get("decisao")

        if decisao == "remover":
            novo_status = "removida"
        elif decisao == "manter":
            novo_status = "ativa"
        else:
            messages.error(request, "Decisão inválida. Use 'manter' ou 'remover'.")
            return redirect("fila_avaliacoes")

        status_anterior = avaliacao.status_moderacao

        if novo_status != status_anterior:
            avaliacao.status_moderacao = novo_status
            avaliacao.save(update_fields=["status_moderacao"])

            # `id_registro_afetado` é INT na tabela `log_alteracao`, e Avaliacao
            # não tem id próprio (PK composta). Registra-se o id do fornecedor
            # avaliado e o par completo vai no `conteudo_anterior`, que é o
            # campo de texto livre do banco.
            registrar_log(
                usuario=request.user,
                acao="UPDATE",
                modelo_afetado="Avaliacao",
                id_registro_afetado=int(id_fornecedor),
                conteudo_anterior=(
                    f"avaliacao(comerciante={id_comerciante}, "
                    f"fornecedor={id_fornecedor}): "
                    f"status_moderacao={status_anterior} -> {novo_status}."
                ),
            )

            messages.success(
                request,
                "Avaliação removida da exibição."
                if novo_status == "removida"
                else "Avaliação mantida.",
            )

    return redirect("fila_avaliacoes")