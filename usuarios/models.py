from django.db import models


class Usuario(models.Model):
    """
    Tabela central de autenticação/perfil (fornecedor ou comerciante).
    Mapeia 1:1 a tabela `usuario` do banco.sql (RF-001, RF-002, RF-003, RF-004, RF-026).

    OBS. dev: a senha deve sempre ser gravada com um hash seguro
    (django.contrib.auth.hashers.make_password), nunca em texto puro,
    para atender ao RNF-002.
    """

    TIPO_PERFIL_CHOICES = [
        ("fornecedor", "Fornecedor"),
        ("comerciante", "Comerciante"),
    ]
    STATUS_CONTA_CHOICES = [
        ("ativa", "Ativa"),
        ("suspensa", "Suspensa"),
    ]

    id_usuario = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=150)
    email = models.EmailField(max_length=254, unique=True)
    senha = models.CharField(max_length=255)
    cpf_cnpj = models.CharField(max_length=18, unique=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    tipo_perfil = models.CharField(max_length=11, choices=TIPO_PERFIL_CHOICES)
    status_conta = models.CharField(
        max_length=8, choices=STATUS_CONTA_CHOICES, default="ativa", blank=True, null=True
    )

    class Meta:
        managed = True
        db_table = "usuario"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.nome} ({self.tipo_perfil})"

    # --- Contrato de sessão/autenticação -----------------------------------
    # Os templates (base.html, menus.html, painel.html, dashboards, etc.)
    # foram construídos esperando a interface padrão do Django
    # (`user.is_authenticated`, `user.is_anonymous`), mesmo não usando
    # django.contrib.auth. O UsuarioSessionMiddleware injeta uma instância
    # de Usuario (autenticado) ou de UsuarioAnonimo (não autenticado) em
    # `request.user`, e essas duas propriedades abaixo fecham o contrato.
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
