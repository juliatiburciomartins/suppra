from django.db import models
from usuarios.models import Usuario


class Avaliacao(models.Model):
    """
    Avaliação (0 a 5 estrelas) de um comerciante sobre um fornecedor. RF-018.
    Chave primária composta (id_comerciante, id_fornecedor), igual ao banco.sql.
    """

    STATUS_MODERACAO_CHOICES = [
        ("ativa", "Ativa"),
        ("removida", "Removida"),
    ]

    pk = models.CompositePrimaryKey("id_comerciante", "id_fornecedor")
    id_comerciante = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="id_comerciante", related_name="avaliacoes_feitas",
        limit_choices_to={"tipo_perfil": "comerciante"},
    )
    id_fornecedor = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="id_fornecedor", related_name="avaliacoes_recebidas",
        limit_choices_to={"tipo_perfil": "fornecedor"},
    )
    nota = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True, null=True)
    data_avaliacao = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    status_moderacao = models.CharField(
        max_length=8, choices=STATUS_MODERACAO_CHOICES, default="ativa", blank=True, null=True
    )

    class Meta:
        managed = True
        db_table = "avaliacao"
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"

    def __str__(self):
        return f"{self.id_comerciante.nome} -> {self.id_fornecedor.nome}: {self.nota}"


class Favorito(models.Model):
    """
    Fornecedor favoritado por um comerciante. RF-028, RF-029, RF-030.
    Chave primária composta (id_comerciante, id_fornecedor), igual ao banco.sql.
    """

    pk = models.CompositePrimaryKey("id_comerciante", "id_fornecedor")
    id_comerciante = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="id_comerciante", related_name="favoritos",
        limit_choices_to={"tipo_perfil": "comerciante"},
    )
    id_fornecedor = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="id_fornecedor", related_name="favoritado_por",
        limit_choices_to={"tipo_perfil": "fornecedor"},
    )
    data_favoritado = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "favorito"
        verbose_name = "Favorito"
        verbose_name_plural = "Favoritos"
