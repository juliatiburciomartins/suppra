from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from usuarios.managers import UsuarioManager


class Usuario(AbstractBaseUser):
    """
    Tabela central de autenticação/perfil (fornecedor ou comerciante).
    Mapeia 1:1 a tabela `usuario` do banco.sql (RF-001 a RF-004, RF-016, RF-026).

    É o AUTH_USER_MODEL do projeto: login por e-mail, senha com
    `set_password`/`check_password` (PBKDF2/SHA256 — RNF-002).

    Decisões de compatibilidade com o banco.sql (que NÃO pode ser alterado):
      - `password` (AbstractBaseUser) é gravado na coluna existente `senha`;
      - `last_login` é removido (a tabela não tem essa coluna);
      - não usa PermissionsMixin (exigiria as colunas is_superuser e as tabelas
        de grupos/permissões por usuário, que não existem no MER/DER). As
        propriedades `is_staff`/`is_superuser` são derivadas de ADMIN_EMAILS;
      - não existe coluna `data_exclusao`: a exclusão de conta (RF-016) é um
        soft delete por anonimização + `status_conta='suspensa'`
        (ver usuarios/services.py).
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
    # AbstractBaseUser.password, mapeado na coluna `senha` do banco.sql.
    password = models.CharField(max_length=255, db_column="senha")
    cpf_cnpj = models.CharField(max_length=18, unique=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    tipo_perfil = models.CharField(max_length=11, choices=TIPO_PERFIL_CHOICES)
    status_conta = models.CharField(
        max_length=8, choices=STATUS_CONTA_CHOICES, default="ativa", blank=True, null=True
    )

    # A tabela `usuario` não tem last_login.
    last_login = None

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nome", "cpf_cnpj", "tipo_perfil"]

    class Meta:
        managed = True
        db_table = "usuario"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.nome} ({self.tipo_perfil})"

    # --- Estado da conta ----------------------------------------------------
    @property
    def is_active(self):
        """Conta suspensa (moderação) ou excluída (RF-016) não autentica."""
        return self.status_conta != "suspensa"

    @property
    def conta_excluida(self):
        """True se a conta passou por `anonimizar_usuario` (RF-016)."""
        from usuarios.services import EMAIL_DOMINIO_ANONIMIZADO

        return (self.email or "").endswith(f"@{EMAIL_DOMINIO_ANONIMIZADO}")

    # --- Perfis -------------------------------------------------------------
    @property
    def is_fornecedor(self):
        return self.tipo_perfil == "fornecedor"

    @property
    def is_comerciante(self):
        return self.tipo_perfil == "comerciante"

    # --- Administrador (Django Admin / RF-017) -------------------------------
    @property
    def is_admin(self):
        return self.is_active and (self.email or "").lower() in settings.ADMIN_EMAILS

    @property
    def is_staff(self):
        return self.is_admin

    @property
    def is_superuser(self):
        return self.is_admin

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_perms(self, perm_list, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin
