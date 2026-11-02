from django.urls import path
from usuarios import views

# Sem app_name/namespace de propósito: os templates chamam {% url 'login' %},
# {% url 'cadastro' %}, etc. sem prefixo, então os names abaixo precisam
# ficar no namespace global (ver hub_fecc/urls.py).

urlpatterns = [
    # Autenticação
    path("login/", views.login_view, name="login"),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path("logout/", views.logout_view, name="logout"),

    # Recuperação de senha (RF-023 / CU03)
    path("recuperar-senha/", views.recuperar_senha_view, name="recuperar_senha"),
    path("recuperar-senha/enviado/", views.redefinicao_senha_enviado_view, name="recuperar_senha_enviado"),
    path("recuperar-senha/completo/", views.redefinicao_senha_concluida_view, name="password_reset_complete"),
    # Link do e-mail: precisa de uidb64 + token (nome usado por usuarios/password_reset.py)
    path("recuperar-senha/confirmar/<str:uidb64>/<str:token>/", views.redefinir_senha_view, name="redefinir_senha"),
    # Atalho sem token: usada quando o link chegou truncado. Renderiza a mesma
    # tela de "link inválido" do CU03 E1/E2.
    path("recuperar-senha/confirmar/", views.redefinir_senha_preview_view, name="redefinir_senha_preview"),
    path("link-expirado/", views.link_expirado_view, name="link_expirado"),

    # Painéis
    path("painel/fornecedor/", views.dashboard_fornecedor_view, name="dashboard_fornecedor"),
    path("painel/comerciante/", views.dashboard_comerciante_view, name="dashboard_comerciante"),

    # RF-014 / CU17 — Tutorial de onboarding
    path("tutorial/", views.tutorial_view, name="tutorial"),
    # Só por POST: pular precisa registrar a decisão (não pode ser link GET).
    path("tutorial/pular/", views.pular_tutorial_view, name="pular_tutorial"),

    # Perfil e conta
    path("perfil/editar/", views.editar_perfil_view, name="editar_perfil"),
    path("conta/excluir/", views.excluir_conta_view, name="excluir_conta"),
]