"""
Manager do model Usuario (autenticação customizada).

`Usuario` é a tabela `usuario` do banco.sql (MER/DER). O login é feito por
e-mail (USERNAME_FIELD) e a senha é sempre gravada via `set_password`
(PBKDF2 + SHA256, padrão do Django — RNF-002).
"""

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager


class UsuarioManager(BaseUserManager):
    use_in_migrations = False

    def get_by_natural_key(self, username):
        # E-mail não diferencia maiúsculas/minúsculas no login.
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        if not password:
            raise ValueError("A senha é obrigatória.")

        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **extra_fields)
        usuario.set_password(password)  # RNF-002: nunca texto puro
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("status_conta", "ativa")
        extra_fields.setdefault("tipo_perfil", "comerciante")
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """
        O banco.sql não tem colunas is_staff/is_superuser (e `tipo_perfil`
        só aceita fornecedor/comerciante), então "administrador" é definido
        pelo e-mail listado em `settings.ADMIN_EMAILS` (ver Usuario.is_staff).
        """
        email_normalizado = self.normalize_email(email or "").lower()
        if email_normalizado not in settings.ADMIN_EMAILS:
            raise ValueError(
                f"'{email_normalizado}' não está em ADMIN_EMAILS. Adicione o e-mail "
                "à variável ADMIN_EMAILS do .env antes de criar o administrador."
            )
        extra_fields.setdefault("status_conta", "ativa")
        extra_fields.setdefault("tipo_perfil", "comerciante")
        return self._create_user(email, password, **extra_fields)
