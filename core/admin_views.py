"""
Painel administrativo da equipe gestora (RF-017 / CU20 a CU24).

Este módulo é a "casca" do painel: rotas e acesso. O trabalho de cada tela está
distribuído onde faz mais sentido no Django:

  - CU24 (indicadores) e CU20 (categorias) e CU21 (log) e CU23 (planos/
    assinaturas) ficam no **Django Admin**, que já é o painel da equipe no
    projeto (veja README, seção "Painel administrativo"). São `ModelAdmin` com
    os filtros e ações que a documentação pede;
  - CU22 (moderação de denúncias) tem as ações em `moderacao/admin.py`. A fila
    de avaliações é uma view porque `Avaliacao` tem chave primária composta e o
    Django Admin recusa registrá-la;
  - aqui ficam os indicadores do CU24 (RF-017) e o log de auditoria do RF-024
    legível em tela, já que o CU21 é explicitamente uma tela de consulta.

Controle de acesso: `@admin_required` (equipe gestora definida por
`ADMIN_EMAILS` no `.env`), mesma regra do Django Admin — usuário comum recebe
HTTP 403, visitante vai para o login.
"""

from datetime import timedelta

from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.indicadores import indicadores_de_qualidade, indicadores_gerais
from usuarios.decorators import admin_required
from usuarios.models import Usuario

TEMPLATE_PAINEL = "core/painel_admin.html"
TEMPLATE_LOG = "core/log_auditoria.html"


@admin_required
def painel_admin_view(request):
    """
    CU24 — "o administrador acessa o painel administrativo da plataforma" e o
    sistema exibe os indicadores gerais atualizados.

    Também reúne os atalhos para as demais telas de gestão (CU20 a CU23), que é o
    que o RF-017 chama de "painel interno para a equipe gestora".
    """
    contexto = {
        "tipo_menu": "admin",
        "indicadores": indicadores_gerais(),
        "qualidade": indicadores_de_qualidade(),
    }
    return render(request, TEMPLATE_PAINEL, contexto)


@admin_required
def log_auditoria_view(request):
    """
    CU21 — "O administrador acessa a área de log de auditoria no painel
    administrativo" e "aplica filtros disponíveis (por usuário, por modelo ou por
    período)".

    O mesmo log também está no Django Admin (`core/admin.py`); esta tela é a
    versão com os três filtros juntos, que é o que o CU21 descreve.
    """
    from core.models import LogAlteracao

    registros = LogAlteracao.objects.select_related("id_usuario").order_by(
        "-data_alteracao"
    )

    modelo = request.GET.get("modelo", "").strip()
    acao = request.GET.get("acao", "").strip()
    usuario_id = request.GET.get("usuario", "").strip()
    periodo = request.GET.get("periodo", "").strip()

    if modelo:
        registros = registros.filter(modelo_afetado__iexact=modelo)
    if acao in dict(LogAlteracao.ACAO_CHOICES):
        registros = registros.filter(acao=acao)
    if usuario_id.isdigit():
        registros = registros.filter(id_usuario_id=int(usuario_id))

    # Filtro por período (CU21).
    #
    # Com `USE_TZ = True`, `data_alteracao` é gravado em UTC. Comparar com
    # `__date=<data local>` não funciona: o Django converte a data para a
    # fronteira do dia *na timezone configurada*, enquanto o valor no banco está
    # em UTC — o resultado é um intervalo deslocado e o filtro não acha nada.
    # A forma correta é calcular os limites do dia como datetimes conscientes e
    # filtrar por intervalo fechado à esquerda e aberto à direita.
    if periodo:
        agora = timezone.localtime()

        if periodo == "hoje":
            inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
            fim = inicio + timedelta(days=1)
            registros = registros.filter(data_alteracao__gte=inicio, data_alteracao__lt=fim)
        elif periodo == "7dias":
            registros = registros.filter(data_alteracao__gte=agora - timedelta(days=7))
        elif periodo == "30dias":
            registros = registros.filter(data_alteracao__gte=agora - timedelta(days=30))

    registros = list(registros)

    contexto = {
        "tipo_menu": "admin",
        "registros": registros,
        "total": len(registros),
        "filtros": {
            "modelo": modelo,
            "acao": acao,
            "usuario": usuario_id,
            "periodo": periodo,
        },
        "opcoes_modelo": sorted(
            LogAlteracao.objects.values_list("modelo_afetado", flat=True).distinct()
        ),
        "opcoes_acao": LogAlteracao.ACAO_CHOICES,
        # Lista de usuários para o filtro "por usuário" do CU21.
        "usuarios": Usuario.objects.filter(logs__isnull=False)
        .distinct()
        .order_by("nome"),
        # Resultado do filtro que não casou com nada (CU21, fluxo de exceção E1).
        "sem_resultados": bool(
            (modelo or acao or usuario_id or periodo) and not registros
        ),
    }
    return render(request, TEMPLATE_LOG, contexto)


@admin_required
def detalhe_log_view(request, log_id):
    """
    CU21 — "O administrador consulta o registro de interesse", que exibe "data e
    hora, usuário responsável, modelo afetado e conteúdo anterior à alteração".

    Somente leitura: a pós-condição do CU21 é "Nenhuma alteração é realizada no
    log durante a consulta".
    """
    from core.models import LogAlteracao

    registro = get_object_or_404(
        LogAlteracao.objects.select_related("id_usuario"), pk=log_id
    )

    return render(
        request,
        "core/log_detalhe.html",
        {"tipo_menu": "admin", "registro": registro},
    )