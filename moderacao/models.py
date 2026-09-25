from django.db import models
from usuarios.models import Usuario
from portfolio.models import Produto
from demandas.models import Demanda


class Denuncia(models.Model):
    """Fluxo de denúncia de conteúdo (portfólio ou demanda). RF-025."""

    TIPO_CONTEUDO_CHOICES = [
        ("portfolio", "Portfólio"),
        ("demanda", "Demanda"),
    ]
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("arquivada", "Arquivada"),
        ("procedente", "Procedente"),
    ]

    id_denuncia = models.AutoField(primary_key=True)
    id_denunciante = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="id_denunciante", related_name="denuncias_feitas"
    )
    tipo_conteudo = models.CharField(max_length=9, choices=TIPO_CONTEUDO_CHOICES)
    id_produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, db_column="id_produto", related_name="denuncias",
        blank=True, null=True,
    )
    id_demanda = models.ForeignKey(
        Demanda, on_delete=models.CASCADE, db_column="id_demanda", related_name="denuncias",
        blank=True, null=True,
    )
    descricao = models.TextField()
    evidencia = models.CharField(max_length=500, blank=True, null=True)  # caminho da imagem (RF-025, MEDIA_ROOT)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente", blank=True, null=True)
    data_denuncia = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "denuncia"
        verbose_name = "Denúncia"
        verbose_name_plural = "Denúncias"

    def __str__(self):
        return f"Denúncia #{self.id_denuncia} ({self.tipo_conteudo})"
