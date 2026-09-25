from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from demandas.forms import DemandaForm
from demandas.models import Demanda
from usuarios.decorators import comerciante_logado


@comerciante_logado
def minhas_demandas_view(request):
    demandas = (
        Demanda.objects.filter(id_comerciante=request.user)
        .select_related("id_categoria")
        .order_by("-data_publicacao")
    )
    return render(request, "demandas/minhas_demandas.html", {
        "tipo_menu": "comerciante",
        "demandas": demandas,
    })


@comerciante_logado
def publicar_demanda_view(request):
    if request.method == "POST":
        form = DemandaForm(request.POST)
        if form.is_valid():
            demanda = form.save(commit=False)
            demanda.id_comerciante = request.user
            demanda.save()
            messages.success(request, "Demanda publicada com sucesso.")
            return redirect("minhas_demandas")
    else:
        form = DemandaForm()

    return render(request, "demandas/demanda_form.html", {
        "tipo_menu": "comerciante",
        "form": form,
        "modo": "publicar",
    })


@comerciante_logado
def editar_demanda_view(request, pk):
    demanda = get_object_or_404(Demanda, pk=pk, id_comerciante=request.user)

    if request.method == "POST":
        form = DemandaForm(request.POST, instance=demanda)
        if form.is_valid():
            form.save()
            messages.success(request, "Demanda atualizada com sucesso.")
            return redirect("minhas_demandas")
    else:
        form = DemandaForm(instance=demanda)

    return render(request, "demandas/demanda_form.html", {
        "tipo_menu": "comerciante",
        "form": form,
        "modo": "editar",
        "demanda": demanda,
    })


@comerciante_logado
def encerrar_demanda_view(request, pk):
    demanda = get_object_or_404(Demanda, pk=pk, id_comerciante=request.user)
    demanda.status = "encerrada"
    demanda.save(update_fields=["status"])
    messages.success(request, "Demanda encerrada.")
    return redirect("minhas_demandas")