"""
Canal de suporte interno (RF-019 / CU19).

Qualquer usuário **autenticado** (fornecedor ou comerciante) abre um chamado com
assunto, descrição e evidência opcional. O pedido é vinculado ao perfil do
usuário (`suporte.id_usuario`) e fica na fila da equipe gestora, que o acompanha
pelo `status` ('aberto' -> 'em_atendimento' -> 'encerrado') no Django Admin.

Pós-condição do CU19: "O usuário recebe confirmação do recebimento e pode
acompanhar o andamento pelo canal indicado" — daí a tela `meus_chamados_view`,
que mostra ao usuário o status atual do próprio chamado.
"""

import os

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from uuid import uuid4

from suporte.forms import SuporteForm
from suporte.models import Suporte
from usuarios.decorators import login_usuario_requerido


def _salvar_evidencia(arquivo):
    """
    Grava a evidência em MEDIA_ROOT e devolve o caminho relativo.

    O banco.sql guarda `img VARCHAR(500)` (o caminho, não os bytes). O nome usa
    `uuid4` para não sobrescrever o arquivo de outro chamado e para não expor o
    nome original do upload na URL pública.
    """
    extensao = os.path.splitext(arquivo.name)[1].lower() or ".jpg"
    nome = f"suporte_{uuid4().hex}{extensao}"

    destino = os.path.join(settings.MEDIA_ROOT, "suporte")
    os.makedirs(destino, exist_ok=True)

    with open(os.path.join(destino, nome), "wb") as arquivo_saida:
        for pedaco in arquivo.chunks():
            arquivo_saida.write(pedaco)

    return f"suporte/{nome}"


@login_usuario_requerido
def suporte_view(request):
    """
    CU19 — abertura de chamado (fluxo principal).

    E1 do CU19: assunto ou descrição vazios -> erro por campo e retorno ao passo 2.
    """
    if request.method == "POST":
        form = SuporteForm(request.POST, request.FILES)

        if form.is_valid():
            chamado = form.save(commit=False)
            chamado.id_usuario = request.user
            chamado.status = "aberto"

            evidencia = form.cleaned_data.get("img")
            if evidencia is not None:
                chamado.img = _salvar_evidencia(evidencia)

            chamado.save()

            messages.success(
                request,
                f"Solicitação #{chamado.id_suporte} registrada. Nossa equipe "
                "entrará em contato pelo canal informado no seu cadastro.",
            )
            return redirect("meus_chamados")
    else:
        form = SuporteForm()

    return render(
        request,
        "suporte/suporte_form.html",
        {
            "form": form,
            "tipo_menu": request.user.tipo_perfil,
        },
    )


@login_usuario_requerido
def meus_chamados_view(request):
    """
    Acompanhamento dos chamados próprios (pós-condição do CU19).

    Cada usuário vê apenas os próprios chamados — nunca os de outros.
    """
    chamados = Suporte.objects.filter(id_usuario=request.user).order_by(
        "-data_abertura"
    )

    return render(
        request,
        "suporte/meus_chamados.html",
        {
            "chamados": chamados,
            "total": chamados.count(),
            "abertos": chamados.exclude(status="encerrado").count(),
            "tipo_menu": request.user.tipo_perfil,
        },
    )