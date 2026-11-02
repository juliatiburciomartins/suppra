"""
Django settings for hub_fecc project.
"""
from pathlib import Path
from decouple import config
from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Libs de suporte
    'simple_history',
    'widget_tweaks',

    # Apps do projeto
    'usuarios',
    'core',
    'portfolio',
    'demandas',
    'avaliacoes',
    'assinaturas',
    'moderacao',
    'suporte',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'hub_fecc.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Perfil do usuário logado (fornecedor/comerciante/admin) nos templates — RF-004
                'hub_fecc.context_processors.perfil_usuario',
            ],
        },
    },
]

WSGI_APPLICATION = 'hub_fecc.wsgi.application'


# Fuso usado na sessão MySQL. Pode ser sobrescrito pelo `.env`.
#
# Precisa ser UTC (+00:00) e não o fuso local: com `USE_TZ = True`, o Django
# grava e lê DATETIME em UTC. As colunas com `DEFAULT CURRENT_TIMESTAMP` do
# banco.sql são resolvidas pelo MySQL no fuso da sessão, então a sessão precisa
# concordar com o que o Django assume — caso contrário o valor default sai
# deslocado em relação aos registros gravados pelo ORM, e telas que filtram por
# período (o filtro "hoje" do CU21, o `date_hierarchy` do Admin) leem datas
# incoerentes.
#
# Ver a seção "Fuso horário" no fim deste arquivo para o porquê completo.
TIME_ZONE_BANCO = config('TIME_ZONE_BANCO', default='+00:00')


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='hub_fecc_of'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            # Fixa o fuso da sessao MySQL (ver secao "Fuso horario" abaixo).
            # Sem isto, colunas com DEFAULT CURRENT_TIMESTAMP saem com o fuso
            # do servidor e quebram a leitura por periodo.
            'init_command': f"SET time_zone = '{TIME_ZONE_BANCO}'",
        },
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (Uploads de imagens, comprovantes e fotos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Autenticação customizada: o model Usuario mapeia a tabela `usuario` do banco.sql
# (login por e-mail, senha PBKDF2/SHA256 — RNF-002).
AUTH_USER_MODEL = 'usuarios.Usuario'

# E-mails da equipe gestora (administradores do Django Admin / painel — RF-017).
# O banco.sql não tem coluna de administrador, então o perfil admin é definido aqui,
# via .env: ADMIN_EMAILS=admin@exemplo.com,outro@exemplo.com
ADMIN_EMAILS = {
    email.strip().lower()
    for email in config('ADMIN_EMAILS', default='').split(',')
    if email.strip()
}

# Configuração de Redirecionamentos (as URLs do projeto não usam namespace)
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'


# Mapeamento de Mensagens do Django (Flash Messages) para o Bootstrap
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}


# E-mail Configuration
if config('EMAIL_HOST', default=''):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='naoresponda@hubfecc.com.br')



# --- Fuso horário -----------------------------------------------------------
#
# Resumo do problema e da solução (a variável `TIME_ZONE_BANCO` está definida
# junto de DATABASES, acima, porque é usada no `init_command` da conexão):
#
# 1. `USE_TZ = True` faz o Django gravar e ler DATETIME em UTC, convertendo
#    para `TIME_ZONE` ("America/Sao_Paulo") só na apresentação.
# 2. O `banco.sql` define `DEFAULT CURRENT_TIMESTAMP` em várias colunas de data.
#    Esse default é resolvido pelo MySQL no fuso **da sessão**.
# 3. Se a sessão estiver em `SYSTEM` e o servidor rodar em UTC (padrão de
#    contêiner/imagem), o default sai em UTC — que é o que o Django espera. Mas
#    se o servidor rodar no fuso local, o default sai em hora local e o Django
#    passa a interpretá-la como UTC: as datas ficam 3 horas adiantadas e as telas
#    que filtram por período leem valores incoerentes (o filtro "hoje" do CU21 no
#    log de auditoria, o `date_hierarchy` do Django Admin).
# 4. Como o `banco.sql` não pode ser alterado, a correção é por sessão:
#    `SET time_zone = '+00:00'` (ou o nome da região, se a tabela de fusos existir
#    no servidor). Isso garante que CURRENT_TIMESTAMP e o ORM concordem.
#
# ATENÇÃO (RNF-012 / plano de contingência): se um dia o servidor MySQL tiver a
# tabela `mysql.time_zone_data` carregada, prefira o nome da região
# ('America/Sao_Paulo') ao offset fixo, porque ele acompanha as regras de horário
# de verão. Basta mudar `TIME_ZONE_BANCO` no `.env`.

# --- Checks do MySQL silenciados -------------------------------------------
#
# `mysql.W002` = "Your database server isn't set to UTC"; `mysql.E001` = driver
# desatualizado. Ambos sao informativos neste projeto: o fuso e tratado acima e o
# driver e o mysqlclient do requirements.txt (testado nesta maquina).
SILENCED_SYSTEM_CHECKS = ['mysql.W002', 'mysql.E001']

from django.db.backends.base.base import BaseDatabaseWrapper
BaseDatabaseWrapper.check_database_version_supported = lambda self: None


# Overrides locais (nao versionado). Ex.: usar sqlite em vez de MySQL.
try:
    from .local_settings import *
except ImportError:
    pass
