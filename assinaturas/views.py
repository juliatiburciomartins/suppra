from django.shortcuts import render


def planos_assinatura(request):
    return render(
        request,
        "assinaturas/lista_planos.html"
    )


def confirmar_contratacao(request, plano):

    planos = {
        "silver": {
            "nome": "Fornecedor Silver",
            "valor": "29,90",
            "classe": "plan-silver",
            "beneficios": [
                "Cadastro de perfil de fornecedor",
                "Visualização de demandas",
                "Relatórios básicos de visualizações",
                "Selo de verificado",
            ],
        },
        "gold": {
            "nome": "Fornecedor Gold",
            "valor": "59,90",
            "classe": "plan-gold",
            "beneficios": [
                "Cadastro de perfil de fornecedor",
                "Visualização de demandas",
                "Relatórios completos",
                "Selo premium",
                "Suporte dedicado",
            ],
        },
    }

    plano_selecionado = planos.get(plano)

    if not plano_selecionado:
        return render(
            request,
            "assinaturas/lista_planos.html"
        )

    return render(
        request,
        "assinaturas/confirmar_contratacao.html",
        {
            "plano": plano_selecionado
        }
    )