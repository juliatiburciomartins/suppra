from django.db import models
from simple_history.models import HistoricalRecords
from usuarios.models import Usuario
from core.models import CategoriaInsumo


class Demanda(models.Model):
    """
    Demanda de insumo publicada por um comerciante. RF-009, RF-011, RF-013.
    Histórico de alterações via simple_history atende ao RF-024.
    """

    STATUS_CHOICES = [
        ("publicada", "Publicada"),
        ("encerrada", "Encerrada"),
    ]

    id_demanda = models.AutoField(primary_key=True)
    id_comerciante = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="id_comerciante", related_name="demandas",
        limit_choices_to={"tipo_perfil": "comerciante"},
    )
    id_categoria = models.ForeignKey(
        CategoriaInsumo, on_delete=models.PROTECT, db_column="id_categoria", related_name="demandas"
    )
    descricao_produto = models.TextField()
    quantidade_produto = models.CharField(max_length=100)
    data_publicacao = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    status = models.CharField(max_length=9, choices=STATUS_CHOICES, default="publicada", blank=True, null=True)

    history = HistoricalRecords(user_model="usuarios.Usuario")

    class Meta:
        managed = True
        db_table = "demanda"
        verbose_name = "Demanda"
        verbose_name_plural = "Demandas"

    def __str__(self):
        return f"{self.descricao_produto[:40]} - {self.id_comerciante.nome}"

    def get_status_css_class(self):
        return "supplier-portfolio-item__status--ativo" if self.status == "publicada" else "supplier-portfolio-item__status--inativo"