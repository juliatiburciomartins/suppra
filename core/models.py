from django.db import models
from usuarios.models import Usuario


class CategoriaInsumo(models.Model):
    """Categorias de insumo (bebidas, laticínios, descartáveis...). RF-031 a RF-034."""

    STATUS_CHOICES = [
        ("ativa", "Ativa"),
        ("inativa", "Inativa"),
    ]

    id_categoria = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    status = models.CharField(max_length=7, choices=STATUS_CHOICES, default="ativa", blank=True, null=True)

    class Meta:
        managed = True
        db_table = "categoria_insumo"
        verbose_name = "Categoria de Insumo"
        verbose_name_plural = "Categorias de Insumo"

    def __str__(self):
        return self.nome


class TermoUso(models.Model):
    """Versões dos Termos de Uso / Política de Privacidade. RNF-015."""

    id_termo_uso = models.AutoField(primary_key=True)
    versao = models.CharField(max_length=20)
    texto = models.TextField()
    data_vigencia = models.DateField()

    class Meta:
        managed = True
        db_table = "termo_uso"
        verbose_name = "Termo de Uso"
        verbose_name_plural = "Termos de Uso"

    def __str__(self):
        return f"Termo v{self.versao}"


class TermoAceite(models.Model):
    """Registro do aceite dos Termos de Uso por usuário (RF-001, RF-002, LGPD)."""

    id_aceite = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, db_column="id_usuario", related_name="aceites"
    )
    id_termo_uso = models.ForeignKey(
        TermoUso, on_delete=models.PROTECT, db_column="id_termo_uso", related_name="aceites"
    )
    data_aceite = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "termo_aceite"
        verbose_name = "Aceite de Termo"
        verbose_name_plural = "Aceites de Termo"


class LogAlteracao(models.Model):
    """
    Log de auditoria manual (RF-024).

    ATENÇÃO EQUIPE: o projeto também tem django-simple-history instalado
    e registrado em MIDDLEWARE/INSTALLED_APPS. O simple_history já cria
    automaticamente uma tabela histórica por model que usar HistoricalRecords()
    (recomendado nos models Produto e Demanda). Decidam em equipe se vão:
      (a) usar SOMENTE simple_history e não gravar mais nesta tabela; ou
      (b) manter esta tabela manual como está definida no banco.sql.
    Mantive o model para não quebrar o schema já entregue no TCC, mas o ideal
    é não duplicar a função de auditoria nas duas soluções ao mesmo tempo.
    """

    ACAO_CHOICES = [
        ("INSERT", "Inserção"),
        ("UPDATE", "Atualização"),
        ("DELETE", "Remoção"),
    ]

    id_log = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, db_column="id_usuario", related_name="logs"
    )
    acao = models.CharField(max_length=6, choices=ACAO_CHOICES)
    modelo_afetado = models.CharField(max_length=50)
    id_registro_afetado = models.IntegerField()
    conteudo_anterior = models.TextField(blank=True, null=True)
    data_alteracao = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "log_alteracao"
        verbose_name = "Log de Alteração"
        verbose_name_plural = "Logs de Alteração"
