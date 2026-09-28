from django.db import models
from simple_history.models import HistoricalRecords
from usuarios.models import Usuario
from core.models import CategoriaInsumo


class Produto(models.Model):
    """
    Item do portfólio de um fornecedor. RF-005 a RF-008, RF-010, RF-013.
    Histórico de alterações via simple_history atende ao RF-024.
    """

    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("inativo", "Inativo"),
    ]

    id_produto = models.AutoField(primary_key=True)
    id_fornecedor = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="id_fornecedor", related_name="produtos",
        limit_choices_to={"tipo_perfil": "fornecedor"},
    )
    id_categoria = models.ForeignKey(
        CategoriaInsumo, on_delete=models.PROTECT, db_column="id_categoria", related_name="produtos"
    )
    nome = models.CharField(max_length=150)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    telefone_contato = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_contato = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=7, choices=STATUS_CHOICES, default="ativo", blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    history = HistoricalRecords(user_model="usuarios.Usuario")

    class Meta:
        managed = True
        db_table = "produto"
        verbose_name = "Produto"
        verbose_name_plural = "Produtos (Portfólio)"

    def __str__(self):
        return f"{self.nome} - {self.id_fornecedor.nome}"
