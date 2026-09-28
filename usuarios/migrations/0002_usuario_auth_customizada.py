"""
Refatoração do model Usuario para autenticação customizada (AbstractBaseUser).

NENHUMA alteração de schema: a tabela `usuario` do banco.sql permanece
exatamente como está. O campo Python `senha` passa a se chamar `password`
(exigido por AbstractBaseUser) continuando mapeado na coluna `senha`, e o
`objects` passa a ser o UsuarioManager. Confirmável com:

    python manage.py sqlmigrate usuarios 0002     # não emite nenhum ALTER
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name="usuario",
                    old_name="senha",
                    new_name="password",
                ),
                migrations.AlterField(
                    model_name="usuario",
                    name="password",
                    field=models.CharField(db_column="senha", max_length=255),
                ),
            ],
        ),
    ]
