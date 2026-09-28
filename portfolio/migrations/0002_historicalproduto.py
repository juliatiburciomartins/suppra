# Migration separada: cria a tabela historicalproduto (django-simple-history),
# que NAO existe no banco.sql original - por isso fica fora da fake-initial.
import django.db.models.deletion
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('usuarios', '0001_initial'),
        ('portfolio', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalProduto',
            fields=[
                ('id_produto', models.IntegerField(blank=True, db_index=True)),
                ('nome', models.CharField(max_length=150)),
                ('preco', models.DecimalField(decimal_places=2, max_digits=10)),
                ('telefone_contato', models.CharField(blank=True, max_length=20, null=True)),
                ('whatsapp_contato', models.CharField(blank=True, max_length=20, null=True)),
                ('status', models.CharField(blank=True, choices=[('ativo', 'Ativo'), ('inativo', 'Inativo')], default='ativo', max_length=7, null=True)),
                ('data_cadastro', models.DateTimeField(blank=True, editable=False, null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('id_categoria', models.ForeignKey(blank=True, db_column='id_categoria', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.categoriainsumo')),
                ('id_fornecedor', models.ForeignKey(blank=True, db_column='id_fornecedor', db_constraint=False, limit_choices_to={'tipo_perfil': 'fornecedor'}, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='usuarios.usuario')),
            ],
            options={
                'verbose_name': 'historical Produto',
                'verbose_name_plural': 'historical Produtos (Portfólio)',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
