"""
Demandas de insumo (RF-009, RF-011, RF-012, RF-013, RF-027 / CU04, CU07, CU11).

Áreas:
  - comerciante: minhas demandas, publicar, editar, encerrar, remover (CU07);
  - público/fornecedor: listagem com filtro por categoria e detalhe com contato
    (RF-011 / RF-027 / CU11).

O dado de contato do comerciante só é montado para usuário autenticado
(RF-012 / RF-027) — ver `core/contato.py`.

Auditoria (RF-024): o histórico de alterações de Demanda é gravado
automaticamente pelo `django-simple-history` (ver `demandas/models.py`), que
registra data, usuário responsável e conteúdo anterior. Por isso este módulo não
chama `core.services.registrar_log` para Demanda.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.contato import montar_canais, pode_ver_contato
from demandas.forms import DemandaForm
from demandas.models import Demanda
from demandas.services import (
    categorias_com_demandas,
    demandas_por_categoria,
    demandas_publicadas,
    pode_acessar_detalhe,
)
from usuarios.decorators import comerciante_required

TEMPLATE_MINHAS = "demandas/minhas_demandas.html"
TEMPLATE_FORM = "demandas/demanda_form.html"
TEMPLATE_LISTA = "demandas/listar_demandas.html"
TEMPLATE_DETALHE = "demandas/detalhes_demanda.html"


# --------------------------------------------------------------------------
# CU07 — Gestão da demanda pelo comerciante (RF-009)
# --------------------------------------------------------------------------

@comerciante_required
def minhas_demandas_view(request):
    """Lista as demandas do comerciante, incluindo as encerradas (histórico)."""
    demandas = (
        Demanda.objects.filter(id_comerciante=request.user)
        .select_related("id_categoria")
        .order_by("-data_publicacao")
    )
    return render(
        request,
        TEMPLATE_MINHAS,
        {
            "tipo_menu": "comerciante",
            "demandas": demandas,
            "total_demandas": demandas.count(),
            "demandas_publicadas": demandas.filter(status="publicada").count(),
        },
    )


@comerciante_required
def publicar_demanda_view(request):
    """
    CU07 fluxo principal / RF-009: registra a demanda com status 'publicada',
    visível para fornecedores autenticados e para o público (RF-027).
    """
    if request.method == "POST":
        form = DemandaForm(request.POST)
        if form.is_valid():
            demanda = form.save(commit=False)
            demanda.id_comerciante = request.user
            demanda.status = "publicada"
            demanda.save()

            messages.success(request, "Demanda publicada com sucesso.")
            return redirect("minhas_demandas")
    else:
        form = DemandaForm()

    return render(
        request,
        TEMPLATE_FORM,
        {
            "tipo_menu": "comerciante",
            "form": form,
            "modo": "publicar",
        },
    )


@comerciante_required
def editar_demanda_view(request, pk):
    """
    CU07 fluxo alternativo A1: edita a demanda já publicada. As alterações ficam
    registradas no histórico (RF-024).
    """
    demanda = get_object_or_404(Demanda, pk=pk, id_comerciante=request.user)

    if request.method == "POST":
        form = DemandaForm(request.POST, instance=demanda)
        if form.is_valid():
            form.save()
            messages.success(request, "Demanda atualizada com sucesso.")
            return redirect("minhas_demandas")
    else:
        form = DemandaForm(instance=demanda)

    return render(
        request,
        TEMPLATE_FORM,
        {
            "tipo_menu": "comerciante",
            "form": form,
            "modo": "editar",
            "demanda": demanda,
        },
    )


@comerciante_required
def encerrar_demanda_view(request, pk):
    """
    CU07 fluxo alternativo A2 / primeira opção: ENCERRAR.

    Mantém o registro com status 'encerrada' (some da listagem pública, continua
    no histórico do comerciante).
    """
    demanda = get_object_or_404(Demanda, pk=pk, id_comerciante=request.user)

    if request.method == "POST":
        if demanda.status == "encerrada":
            messages.info(request, "Esta demanda já está encerrada.")
        else:
            demanda.status = "encerrada"
            demanda.save(update_fields=["status"])
            messages.success(request, "Demanda encerrada. O registro foi mantido no seu histórico.")

    return redirect("minhas_demandas")


@comerciante_required
def remover_demanda_view(request, pk):
    """
    CU07 fluxo alternativo A2 / segunda opção: REMOVER.

    Diferente do encerramento, aqui a demanda é excluída de definitivo da
    plataforma. O histórico da alteração permanece no log de auditoria
    (RF-024), porque o `django-simple-history` grava o registro da remoção antes
    de o registro sumir.
    """
    demanda = get_object_or_404(Demanda, pk=pk, id_comerciante=request.user)

    if request.method == "POST":
        descricao = demanda.descricao_produto[:40]
        demanda.delete()
        messages.success(request, f"Demanda “{descricao}” removida definitivamente.")

    return redirect("minhas_demandas")


# --------------------------------------------------------------------------
# RF-011 / RF-027 — Listagem pública e detalhe (CU04, CU11)
# --------------------------------------------------------------------------

def listar_demandas(request):
    """
    CU04 (visitante) e CU11 (fornecedor autenticado) na mesma tela.

    O CU11 descreve a visualização agrupada por categoria e o filtro por
    categoria; o CU04 diz que o público sem cadastro também pode ver as
    demandas publicadas. Por isso não há decorator de perfil: muda o conteúdo
    (contato e denúncia), não o acesso à página.

    Filtros via query string (mesmo padrão do portfólio):
      ?categoria=<id_categoria>   RF-013 / CU11
      ?busca=<termo>             RF-013
    """
    categorias = categorias_com_demandas()

    categoria_id = request.GET.get("categoria") or None
    categoria = None
    if categoria_id:
        categoria = categorias.filter(pk=categoria_id).first()

    busca = request.GET.get("busca", "").strip()

    demandas = demandas_publicadas(categoria=categoria, busca=busca)
    grupos = demandas_por_categoria(demandas)

    contexto = {
        "demandas": demandas,
        "grupos": grupos,
        "categorias": categorias,
        "categoria_selecionada": categoria,
        "busca": busca,
        "tem_filtro": bool(categoria or busca),
        "total_demandas": demandas.count(),
        "sem_resultados": not demandas.exists(),
        "tipo_menu": (
            request.user.tipo_perfil if request.user.is_authenticated else None
        ),
    }
    return render(request, TEMPLATE_LISTA, contexto)


def detalhes_demanda(request, pk):
    """
    CU04 (visitante) e CU11 (fornecedor autenticado).

    Exibe, conforme o RF-011: nome do comerciante, categoria do insumo
    solicitado, descrição do produto desejado, quantidade demandada e data de
    publicação. Para usuário autenticado, também os dados de contato do
    comerciante (RF-012).
    """
    demanda = get_object_or_404(
        Demanda.objects.select_related("id_comerciante", "id_categoria"),
        pk=pk,
    )

    # Demanda encerrada continua acessível por link direto (o comerciante pode
    # conferir o histórico), mas avisa que não está mais ativa.
    mostrar_contato = pode_ver_contato(request) and pode_acessar_detalhe(
        demanda, request.user
    )

    contexto = {
        "demanda": demanda,
        "comerciante": demanda.id_comerciante,
        "pode_ver_contato": mostrar_contato,
        "canais": (
            montar_canais(
                demanda.id_comerciante,
                mensagem_whatsapp=(
                    "Olá! Vi sua demanda publicada no suppra e tenho oferta."
                ),
            )
            if mostrar_contato
            else []
        ),
        "tipo_menu": (
            request.user.tipo_perfil if request.user.is_authenticated else None
        ),
    }
    return render(request, TEMPLATE_DETALHE, contexto)