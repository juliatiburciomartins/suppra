"""
Testes de planos e assinaturas (RF-020, RF-021, RF-022 / CU12, CU13).

Cobre a listagem de planos com os dados vindos do banco (não de constantes no
código), a contratação com data de início e vencimento, o cancelamento que
mantém os benefícios até o fim do período, e a expiração automática.
"""

from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assinaturas.models import Assinatura, PlanoAssinatura
from assinaturas.services import (
    assinatura_em_vigor,
    cancelar,
    contratar,
    expirar_vencidas,
    planos_disponiveis,
)
from usuarios.models import Usuario

SENHA = "SenhaForte#123"


class BaseAssinaturas(TestCase):
    def setUp(self):
        self.fornecedor = Usuario.objects.create_user(
            email="for@x.com", password=SENHA, nome="Distribuidora Vale",
            cpf_cnpj="111.111.111-11", tipo_perfil="fornecedor",
        )
        self.comerciante = Usuario.objects.create_user(
            email="com@x.com", password=SENHA, nome="Bar do Zé",
            cpf_cnpj="222.222.222-22", tipo_perfil="comerciante",
        )
        # `core.0002_dados_iniciais` (a migration de seed) já cria Silver e Gold
        # em qualquer banco novo — inclusive o banco de teste. Por isso os planos
        # são reaproveitados (`get_or_create`) em vez de duplicados.
        self.silver, _ = PlanoAssinatura.objects.get_or_create(
            nome_plano="Plano Fornecedor Silver",
            defaults={
                "descricao": "Destaque intermediário, selo de verificado e relatórios básicos.",
                "valor": "29.90",
            },
        )
        self.gold, _ = PlanoAssinatura.objects.get_or_create(
            nome_plano="Plano Fornecedor Gold",
            defaults={
                "descricao": "Destaque prioritário, selo premium, relatórios completos e suporte dedicado.",
                "valor": "59.90",
            },
        )
        self.client.force_login(self.fornecedor)


class ServicosDeAssinaturaTests(BaseAssinaturas):
    """Regras em `assinaturas/services.py`."""

    def test_planos_disponiveis_ordenados_por_valor(self):
        # Cria um plano mais barato: o serviço precisa devolver em ordem de valor.
        PlanoAssinatura.objects.create(
            nome_plano="Plano Promo", descricao="x", valor="10.00"
        )
        ordenados = list(planos_disponiveis())
        self.assertEqual(ordenados[0].nome_plano, "Plano Promo")
        self.assertEqual(
            [p.valor for p in ordenados], sorted(p.valor for p in ordenados)
        )

    def test_contratar_registra_inicio_e_vencimento(self):
        assinatura = contratar(self.fornecedor, self.silver)

        hoje = timezone.localdate()
        self.assertEqual(assinatura.data_inicio, hoje)
        self.assertEqual(
            assinatura.data_vencimento, hoje + timedelta(days=Assinatura.DIAS_POR_CICLO)
        )
        self.assertEqual(assinatura.status, "ativa")

    def test_contratar_encerra_a_assinatura_anterior(self):
        contratar(self.fornecedor, self.silver)
        segunda = contratar(self.fornecedor, self.gold)

        self.assertEqual(Assinatura.objects.count(), 2)
        primeira = Assinatura.objects.exclude(pk=segunda.pk).first()
        self.assertEqual(primeira.status, "expirada")
        self.assertEqual(assinatura_em_vigor(self.fornecedor), segunda)

    def test_assinatura_em_vigor_considera_cancelada_ate_o_vencimento(self):
        assinatura = contratar(self.fornecedor, self.silver)
        cancelar(self.fornecedor)

        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, "cancelada")
        # CU13 A1: os benefícios permanecem até o fim do período vigente.
        self.assertTrue(assinatura.em_vigor)
        self.assertEqual(assinatura_em_vigor(self.fornecedor), assinatura)

    def test_assinatura_vencida_nao_vale_mais(self):
        assinar = contratar(self.fornecedor, self.silver)
        Assinatura.objects.filter(pk=assinar.pk).update(
            data_vencimento=timezone.localdate() - timedelta(days=1)
        )

        self.assertIsNone(assinatura_em_vigor(self.fornecedor))

    def test_cancelar_sem_assinatura_devolve_none(self):
        self.assertIsNone(cancelar(self.fornecedor))

    def test_expirar_vencidas_marca_como_expirada(self):
        antiga = contratar(self.fornecedor, self.silver)
        Assinatura.objects.filter(pk=antiga.pk).update(
            data_vencimento=timezone.localdate() - timedelta(days=1)
        )

        self.assertEqual(expirar_vencidas(), 1)

        antiga.refresh_from_db()
        self.assertEqual(antiga.status, "expirada")

    def test_dias_restantes_e_rotulo_de_status(self):
        assinatura = contratar(self.fornecedor, self.silver)
        self.assertEqual(assinatura.dias_restantes, Assinatura.DIAS_POR_CICLO)
        self.assertEqual(assinatura.get_status_exibicao(), "Ativa")

        Assinatura.objects.filter(pk=assinatura.pk).update(
            data_vencimento=timezone.localdate() - timedelta(days=1)
        )
        assinatura.refresh_from_db()
        self.assertTrue(assinatura.vencida)
        self.assertEqual(assinatura.get_status_exibicao(), "Expirada")


class ListaDePlanosTests(BaseAssinaturas):
    """CU12 / RF-020."""

    def test_mostra_nome_beneficios_e_valor_mensal(self):
        r = self.client.get(reverse("planos_assinatura"))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Plano Fornecedor Silver")
        self.assertContains(r, "Plano Fornecedor Gold")
        self.assertContains(r, "29,90")
        self.assertContains(r, "59,90")
        self.assertContains(r, self.silver.descricao)
        self.assertContains(r, self.gold.descricao)

    def test_beneficios_do_seed_batem_com_o_rf020(self):
        """
        Os planos criados pela migration de seed precisam ter os benefícios
        descritos no RF-020/CU12 — é isso que o fornecedor lê na tela.
        """
        self.assertIn("selo de fornecedor verificado", self.silver.descricao.lower())
        self.assertIn("relatórios básicos", self.silver.descricao.lower())

        self.assertIn("selo de fornecedor premium", self.gold.descricao.lower())
        self.assertIn("suporte dedicado", self.gold.descricao.lower())

    def test_lista_vem_do_banco(self):
        """O plano cadastrado pela equipe aparece sem tocar em código."""
        PlanoAssinatura.objects.create(
            nome_plano="Plano Especial", descricao="Benefício novo.", valor="99.90"
        )
        r = self.client.get(reverse("planos_assinatura"))
        self.assertContains(r, "Plano Especial")

    def test_plano_gratuito_aparece_sempre(self):
        r = self.client.get(reverse("planos_assinatura"))
        self.assertContains(r, "Gratuito")

    def test_marca_o_plano_atual(self):
        contratar(self.fornecedor, self.gold)
        r = self.client.get(reverse("planos_assinatura"))
        self.assertTrue(r.context["ja_assinante"])
        self.assertContains(r, "Plano atual")

    def test_sem_planos_cadastrados_nao_quebra(self):
        PlanoAssinatura.objects.all().delete()
        r = self.client.get(reverse("planos_assinatura"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Nenhum plano disponível")

    def test_comerciante_nao_acessa(self):
        self.client.force_login(self.comerciante)
        r = self.client.get(reverse("planos_assinatura"))
        self.assertRedirects(r, reverse("dashboard_comerciante"), fetch_redirect_response=False)

    def test_visitante_vai_para_o_login(self):
        self.client.logout()
        r = self.client.get(reverse("planos_assinatura"))
        self.assertTrue(r.url.startswith(reverse("login")))


class ConfirmarContratacaoTests(BaseAssinaturas):
    """CU13, passo 2 — resumo do plano antes de confirmar."""

    def test_mostra_o_resumo_do_plano(self):
        r = self.client.get(reverse("confirmar_contratacao", args=[self.gold.pk]))

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["plano"], self.gold)
        self.assertContains(r, "Plano Fornecedor Gold")
        self.assertContains(r, "59,90")
        self.assertContains(r, "Confirmar contratação")

    def test_plano_inexistente(self):
        r = self.client.get(reverse("confirmar_contratacao", args=[999]))
        self.assertEqual(r.status_code, 404)

    def test_com_assinatura_em_vigor_redireciona(self):
        """Pré-condição do CU13: "não possui assinatura ativa"."""
        contratar(self.fornecedor, self.silver)
        r = self.client.get(reverse("confirmar_contratacao", args=[self.gold.pk]))

        self.assertRedirects(r, reverse("planos_assinatura"))
        msgs = [str(m) for m in get_messages(r.wsgi_request)]
        self.assertTrue(any("já tem o plano" in m for m in msgs))

    def test_com_assinatura_cancelada_ainda_bloqueia(self):
        """Cancelada vale até o fim do período: ainda não pode contratar outro."""
        contratar(self.fornecedor, self.silver)
        cancelar(self.fornecedor)

        r = self.client.get(reverse("confirmar_contratacao", args=[self.gold.pk]))
        self.assertRedirects(r, reverse("planos_assinatura"))

    def test_com_assinatura_expirada_permite_trocar(self):
        antiga = contratar(self.fornecedor, self.silver)
        Assinatura.objects.filter(pk=antiga.pk).update(
            data_vencimento=timezone.localdate() - timedelta(days=1)
        )

        r = self.client.get(reverse("confirmar_contratacao", args=[self.gold.pk]))
        self.assertEqual(r.status_code, 200)


class ContratarPlanoTests(BaseAssinaturas):
    """CU13, passo 4 — registrar a assinatura e ativar os benefícios."""

    def test_contrata_e_confirma(self):
        r = self.client.post(reverse("contratar_plano", args=[self.silver.pk]))
        self.assertEqual(r.status_code, 302)

        assinatura = Assinatura.objects.get()
        self.assertEqual(assinatura.id_fornecedor, self.fornecedor)
        self.assertEqual(assinatura.id_plano, self.silver)
        self.assertEqual(assinatura.status, "ativa")

        msgs = [str(m) for m in get_messages(r.wsgi_request)]
        self.assertTrue(any("Assinatura confirmada" in m for m in msgs))

    def test_o_plano_aparece_no_painel(self):
        contratar(self.fornecedor, self.gold)
        r = self.client.get(reverse("dashboard_fornecedor"))

        self.assertEqual(r.context["plano_nome"], "Plano Fornecedor Gold")
        self.assertEqual(r.context["plano_nivel"], "gold")
        self.assertContains(r, "Plano Fornecedor Gold")

    def test_o_selo_aparece_no_portfolio(self):
        """RF-020: selo de fornecedor verificado / premium."""
        contratar(self.fornecedor, self.gold)
        Produto = __import__("portfolio.models", fromlist=["Produto"]).Produto
        CategoriaInsumo = __import__("core.models", fromlist=["CategoriaInsumo"]).CategoriaInsumo

        categoria = CategoriaInsumo.objects.create(nome="Bebidas")
        Produto.objects.create(
            id_fornecedor=self.fornecedor, id_categoria=categoria,
            nome="Coca", preco="4.50",
        )

        r = self.client.get(reverse("detalhes_fornecedor", args=[self.fornecedor.pk]))
        self.assertEqual(r.context["plano"].nome_plano, "Plano Fornecedor Gold")
        self.assertContains(r, "plan-badge--gold")

    def test_get_nao_contrata(self):
        self.client.get(reverse("contratar_plano", args=[self.silver.pk]))
        self.assertEqual(Assinatura.objects.count(), 0)

    def test_plano_inexistente(self):
        r = self.client.post(reverse("contratar_plano", args=[999]))
        self.assertEqual(r.status_code, 404)

    def test_comerciante_nao_contrata(self):
        self.client.force_login(self.comerciante)
        r = self.client.post(reverse("contratar_plano", args=[self.silver.pk]))
        self.assertRedirects(r, reverse("dashboard_comerciante"), fetch_redirect_response=False)
        self.assertEqual(Assinatura.objects.count(), 0)


class MeuPlanoTests(BaseAssinaturas):
    """RF-022 / CU13 A1 — ver e cancelar a assinatura."""

    def test_mostra_plano_vencimento_e_status(self):
        assinar = contratar(self.fornecedor, self.silver)

        r = self.client.get(reverse("meu_plano"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["assinatura"], assinar)
        self.assertContains(r, "Plano Fornecedor Silver")
        self.assertContains(r, assinar.data_vencimento.strftime("%d/%m/%Y"))

    def test_sem_assinatura_mostra_o_plano_gratuito(self):
        r = self.client.get(reverse("meu_plano"))
        self.assertIsNone(r.context["assinatura"])
        self.assertContains(r, "Gratuito")

    def test_historico_traz_a_assinatura_anterior(self):
        antiga = contratar(self.fornecedor, self.silver)
        contratar(self.fornecedor, self.gold)

        r = self.client.get(reverse("meu_plano"))
        self.assertEqual(list(r.context["historico"]), [antiga])

    def test_cancelar_mantem_os_beneficios_ate_o_vencimento(self):
        assinar = contratar(self.fornecedor, self.silver)

        r = self.client.post(reverse("cancelar_assinatura"))
        self.assertEqual(r.status_code, 302)

        assinar.refresh_from_db()
        self.assertEqual(assinar.status, "cancelada")
        self.assertTrue(assinar.em_vigor)

        msgs = [str(m) for m in get_messages(r.wsgi_request)]
        self.assertTrue(any("benefícios permanecem" in m for m in msgs))

    def test_tela_mostra_o_aviso_de_cancelamento(self):
        assinar = contratar(self.fornecedor, self.silver)
        cancelar(self.fornecedor)

        r = self.client.get(reverse("meu_plano"))
        self.assertContains(r, "foi cancelada")
        self.assertContains(r, assinar.data_vencimento.strftime("%d/%m/%Y"))

    def test_cancelar_sem_assinatura(self):
        r = self.client.post(reverse("cancelar_assinatura"))
        self.assertEqual(r.status_code, 302)
        msgs = [str(m) for m in get_messages(r.wsgi_request)]
        self.assertTrue(any("Não há assinatura" in m for m in msgs))

    def test_get_nao_cancela(self):
        """Cancelar muda estado: só o POST pode hacerlo."""
        r = self.client.post(reverse("cancelar_assinatura"))
        self.assertEqual(r.status_code, 302)

        assinar = contratar(self.fornecedor, self.silver)
        self.client.get(reverse("cancelar_assinatura"))
        assinar.refresh_from_db()
        self.assertEqual(assinar.status, "ativa")

    def test_assinatura_vencida_e_mostrada_como_expirada(self):
        assinar = contratar(self.fornecedor, self.silver)
        Assinatura.objects.filter(pk=assinar.pk).update(
            data_vencimento=timezone.localdate() - timedelta(days=1)
        )

        r = self.client.get(reverse("meu_plano"))
        self.assertIsNone(r.context["assinatura"])
        self.assertEqual(list(r.context["historico"]), [assinar])
        self.assertContains(r, "Expirada")


class ModeloPlanoTests(BaseAssinaturas):
    """`PlanoAssinatura` mapeia `plano_assinatura` do banco.sql."""

    def test_tabela_e_nivel(self):
        self.assertEqual(PlanoAssinatura._meta.db_table, "plano_assinatura")
        self.assertEqual(Assinatura._meta.db_table, "assinatura")

        self.assertEqual(self.silver.nivel, "silver")
        self.assertEqual(self.gold.nivel, "gold")

    def test_plano_generico_sem_nivel(self):
        outro = PlanoAssinatura.objects.create(
            nome_plano="Plano Genérico", descricao="x", valor="5.00"
        )
        self.assertIsNone(outro.nivel)

    def test_assinatura_com_plano_protegido(self):
        """`on_delete=PROTECT`: plano em uso não pode ser apagado."""
        contratar(self.fornecedor, self.silver)
        with self.assertRaises(Exception):
            self.silver.delete()