from django.db import models
from usuarios.models import Usuario


class PlanoAssinatura(models.Model):
    """
    Planos Silver / Gold disponíveis para fornecedores. RF-020.

    Mapeia a tabela `plano_assinatura` do banco.sql (id_plano, nome_plano,
    descricao, valor). Os benefícios descritos no RF-020 (destaque na listagem,
    selo de verificado/premium, relatórios e suporte dedicado) ficam no campo
    `descricao`, que a equipe gestora edita pelo painel (CU23).

    NÃO existe um model "Plano" aqui: o banco.sql não tem essa tabela. O que
    houve antes foi uma migration que criava `assinaturas_plano`, fora do
    schema do TCC — ela foi removida. Use sempre `PlanoAssinatura`.
    """

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

    @property
    def eh_gold(self):
        """Distingue o plano Gold (RF-020) para selo e destaque na listagem."""
        return "gold" in (self.nome_plano or "").lower()

    @property
    def eh_silver(self):
        return "silver" in (self.nome_plano or "").lower()

    @property
    def nivel(self):
        """'gold', 'silver' ou None — usado no selo do template."""
        if self.eh_gold:
            return "gold"
        if self.eh_silver:
            return "silver"
        return None


class Assinatura(models.Model):
    """
    Contratação de um plano por um fornecedor. RF-021, RF-022.

    O CU13 grava a assinatura "com a data de início e a data de vencimento" e o
    CU13 A1 (cancelar) diz que os benefícios "permanecem ativos até o fim do
    período vigente" — por isso o cancelamento marca `status='cancelada'` e NÃO
    apaga a linha: o vencimento continua sendo a data real de término.

    `on_delete=PROTECT` no plano significa que um plano com assinaturas não pode
    ser excluído pelo painel — é o mesmo cuidado do RF-034 com categorias.
    """

    STATUS_CHOICES = [
        ("ativa", "Ativa"),
        ("suspensa", "Suspensa"),
        ("cancelada", "Cancelada"),
        ("expirada", "Expirada"),
    ]

    # Período de um mês corrido a partir da contratação (CU13).
    DIAS_POR_CICLO = 30

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

    @property
    def vencida(self):
        """True quando a data de vencimento já passou."""
        from django.utils import timezone

        return self.data_vencimento < timezone.localdate()

    @property
    def em_vigor(self):
        """
        Benefícios ativos: assinatura 'ativa' e ainda dentro do período.

        Cancelada continua válida até o vencimento (CU13 A1: "os benefícios
        permanecem ativos até o fim do período vigente").
        """
        return self.status in ("ativa", "cancelada") and not self.vencida

    @property
    def dias_restantes(self):
        from django.utils import timezone

        return (self.data_vencimento - timezone.localdate()).days

    def get_status_exibicao(self):
        """
        Rótulo de status para a tela do fornecedor (RF-022: "o status atual
        (ativa/suspensa)").
        """
        if self.status == "ativa" and self.vencida:
            return "Expirada"
        return self.get_status_display()