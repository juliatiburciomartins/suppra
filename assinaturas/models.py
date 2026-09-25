from django.db import models
from usuarios.models import Usuario


class PlanoAssinatura(models.Model):
    """Planos Silver / Gold disponíveis para fornecedores. RF-020."""

    id_plano = models.AutoField(primary_key=True)
    nome_plano = models.CharField(max_length=100)
    descricao = models.TextField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = True
        db_table = "plano_assinatura"
        verbose_name = "Plano de Assinatura"
        verbose_name_plural = "Planos de Assinatura"

    def __str__(self):
        return self.nome_plano


class Assinatura(models.Model):
    """Contratação de um plano por um fornecedor. RF-021, RF-022."""

    STATUS_CHOICES = [
        ("ativa", "Ativa"),
        ("suspensa", "Suspensa"),
        ("cancelada", "Cancelada"),
        ("expirada", "Expirada"),
    ]

    id_assinatura = models.AutoField(primary_key=True)
    id_fornecedor = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column="id_fornecedor",
        related_name="assinaturas",
        limit_choices_to={"tipo_perfil": "fornecedor"},
    )
    id_plano = models.ForeignKey(
        PlanoAssinatura,
        on_delete=models.PROTECT,
        db_column="id_plano",
        related_name="assinaturas",
    )
    data_inicio = models.DateField()
    data_vencimento = models.DateField()
    status = models.CharField(
        max_length=9, choices=STATUS_CHOICES, default="ativa", blank=True, null=True
    )

    class Meta:
        managed = True
        db_table = "assinatura"
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"

    def __str__(self):
        return f"{self.id_fornecedor.nome} - {self.id_plano.nome_plano}"


class Plano(models.Model):
    nome = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    codigo = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.nome