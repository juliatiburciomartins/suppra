from django.db import models
from usuarios.models import Usuario


class Suporte(models.Model):
    """Canal de suporte interno. RF-019."""

    STATUS_CHOICES = [
        ("aberto", "Aberto"),
        ("em_atendimento", "Em atendimento"),
        ("encerrado", "Encerrado"),
    ]

    id_suporte = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="id_usuario", related_name="chamados"
    )
    assunto = models.CharField(max_length=200)
    descricao = models.TextField()
    img = models.CharField(max_length=500, blank=True, null=True)  # caminho da imagem (MEDIA_ROOT)
    status = models.CharField(max_length=14, choices=STATUS_CHOICES, default="aberto", blank=True, null=True)
    data_abertura = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "suporte"
        verbose_name = "Chamado de Suporte"
        verbose_name_plural = "Chamados de Suporte"

    def __str__(self):
        return f"#{self.id_suporte} - {self.assunto}"
