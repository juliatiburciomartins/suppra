"""
Testes do app `core`: telas públicas (CU18 / FAQ e documentos legais), os
indicadores do painel (CU24) e a consulta ao log de auditoria (CU21 / RF-024).

O painel de categorias (CU20 / RF-031 a RF-034) é testado aqui via Django Admin,
porque é onde ele vive.
"""

from datetime import timedelta

from django.contrib import admin as dj_admin
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.admin import CategoriaInsumoAdmin, LogAlteracaoAdmin
from core.indicadores import indicadores_de_qualidade, indicadores_gerais
from core.models import CategoriaInsumo, LogAlteracao, TermoAceite, TermoUso
from usuarios.models import Usuario

SENHA = "SenhaForte#123"


def criar(perfil, email, cpf, nome="Fulano", **extra):
    return Usuario.objects.create_user(
        email=email, password=SENHA, nome=nome, cpf_cnpj=cpf,
        tipo_perfil=perfil, **extra,
    )


class TelasPublicasTests(TestCase):
    """CU18 (FAQ) e RNF-007/RNF-015 (documentos legais)."""

    def test_home_do_visitante(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "home_visitante.html")

    def test_home_autenticado(self):
        comerciante = criar("comerciante", "com@x.com", "111.111.111-11")
        self.client.force_login(comerciante)

        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 302)  # vai para o tutorial (RF-014/CU17)
        self.assertTrue(r.url.startswith(reverse("tutorial")))

    def test_faq_publica(self):
        r = self.client.get(reverse("faq"))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "core/faq.html")

    def test_termos_de_uso_publicos(self):
        r = self.client.get(reverse("termos_uso"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Termos de Uso")

    def test_politica_de_privacidade_publica(self):
        r = self.client.get(reverse("politica_privacidade"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Política de Privacidade")

    def test_termos_mostra_a_versao_vigente(self):
        # A versão exibida é a de maior `data_vigencia` (a que a equipe publica
        # por último). A migration de seed cria a v1.0; aqui entra uma mais nova.
        TermoUso.objects.create(
            versao="9.9",
            texto="Texto da versão vigente.",
            data_vigencia=timezone.localdate() + timedelta(days=1),
        )
        r = self.client.get(reverse("termos_uso"))

        self.assertContains(r, "Versão 9.9")
        self.assertContains(r, "Texto da versão vigente.")

    def test_termos_sem_versao_cadastrada_usa_o_texto_estatico(self):
        TermoUso.objects.all().delete()
        r = self.client.get(reverse("termos_uso"))

        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["termo"])
        self.assertContains(r, "Isenção de Responsabilidade")

    def test_termos_apontam_para_a_versao_publicada_pela_equipe(self):
        r = self.client.get(reverse("termos_uso"))
        self.assertEqual(r.context["termo"].versao, "1.0")


class IndicadoresTests(TestCase):
    """CU24 — os quatro indicadores exigidos."""

    def setUp(self):
        self.bebidas = CategoriaInsumo.objects.create(nome="Bebidas")
        self.fornecedor = criar("fornecedor", "for@x.com", "111.111.111-11")
        self.comerciante = criar("comerciante", "com@x.com", "222.222.222-22")

        from portfolio.models import Produto

        self.produto = Produto.objects.create(
            id_fornecedor=self.fornecedor, id_categoria=self.bebidas,
            nome="Coca", preco="4.50",
        )

    def test_conta_cada_categoria(self):
        from demandas.models import Demanda

        Demanda.objects.create(
            id_comerciante=self.comerciante, id_categoria=self.bebidas,
            descricao_produto="Cerveja", quantidade_produto="100",
        )

        indicadores = indicadores_gerais()
        self.assertEqual(indicadores["fornecedores"], 1)
        self.assertEqual(indicadores["comerciantes"], 1)
        self.assertEqual(indicadores["produtos_ativos"], 1)
        self.assertEqual(indicadores["demandas_publicadas"], 1)

    def test_produto_inativo_nao_conta(self):
        from portfolio.models import Produto

        Produto.objects.filter(pk=self.produto.pk).update(status="inativo")
        self.assertEqual(indicadores_gerais()["produtos_ativos"], 0)

    def test_demanda_encerrada_nao_conta(self):
        from demandas.models import Demanda

        Demanda.objects.create(
            id_comerciante=self.comerciante, id_categoria=self.bebidas,
            descricao_produto="Cerveja", quantidade_produto="100", status="encerrada",
        )
        self.assertEqual(indicadores_gerais()["demandas_publicadas"], 0)

    def test_conta_suspensa_nao_entra(self):
        self.fornecedor.status_conta = "suspensa"
        self.fornecedor.save()

        self.assertEqual(indicadores_gerais()["fornecedores"], 0)

    def test_consulta_nao_altera_nada(self):
        """Pós-condição do CU24."""
        antes = LogAlteracao.objects.count()
        indicadores_gerais()
        self.assertEqual(LogAlteracao.objects.count(), antes)

    def test_distribuicao_de_notas(self):
        from avaliacoes.models import Avaliacao

        Avaliacao.objects.create(
            id_comerciante=self.comerciante, id_fornecedor=self.fornecedor, nota=5
        )

        qualidade = indicadores_de_qualidade()
        self.assertEqual(qualidade["media"], 5)
        self.assertEqual(qualidade["total"], 1)
        self.assertEqual(len(qualidade["distribuicao"]), 6)
        self.assertEqual(qualidade["distribuicao"][5]["total"], 1)


class TelaDoPainelTests(TestCase):
    """CU24 — a tela do painel."""

    def setUp(self):
        self.settings = override_settings(ADMIN_EMAILS={"admin@exemplo.com"})
        self.settings.enable()
        self.addCleanup(self.settings.disable)

        self.admin = criar("comerciante", "admin@exemplo.com", "999.999.999-99", "Equipe")
        self.comum = criar("comerciante", "com@x.com", "111.111.111-11")

    def test_admin_acessa(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("painel_admin"))

        self.assertEqual(r.status_code, 200)
        self.assertIn("indicadores", r.context)
        self.assertContains(r, "Indicadores gerais")
        self.assertContains(r, "Fornecedores cadastrados")
        self.assertContains(r, "Produtos ativos")
        self.assertContains(r, "Comerciantes ativos")
        self.assertContains(r, "Demandas publicadas")

    def test_usuario_comum_recebe_403(self):
        self.client.force_login(self.comum)
        self.assertEqual(self.client.get(reverse("painel_admin")).status_code, 403)

    def test_visitante_vai_para_o_login(self):
        r = self.client.get(reverse("painel_admin"))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("login")))


class LogAuditoriaTests(TestCase):
    """CU21 — consultar o log, com filtros por usuário, modelo e período."""

    def setUp(self):
        self.settings = override_settings(ADMIN_EMAILS={"admin@exemplo.com"})
        self.settings.enable()
        self.addCleanup(self.settings.disable)

        self.admin = criar("comerciante", "admin@exemplo.com", "999.999.999-99", "Equipe")
        self.usuario = criar("comerciante", "com@x.com", "111.111.111-11", "Bar do Zé")

        self.hoje = LogAlteracao.objects.create(
            id_usuario=self.usuario, acao="UPDATE",
            modelo_afetado="Usuario", id_registro_afetado=self.usuario.pk,
            conteudo_anterior="status_conta=ativa",
        )
        self.antigo = LogAlteracao.objects.create(
            id_usuario=self.usuario, acao="DELETE",
            modelo_afetado="Demanda", id_registro_afetado=42,
            conteudo_anterior="demanda removida",
        )
        # `auto_now_add` não deixa escolher a data: ajusta direto no banco.
        LogAlteracao.objects.filter(pk=self.antigo.pk).update(
            data_alteracao=timezone.now() - timedelta(days=40)
        )

        self.client.force_login(self.admin)
        self.url = reverse("log_auditoria")

    def test_admin_lista_o_log(self):
        r = self.client.get(self.url)

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["total"], 2)
        self.assertContains(r, "Bar do Zé")
        self.assertContains(r, "Usuario")
        self.assertContains(r, "status_conta=ativa")

    def test_filtro_por_modelo(self):
        r = self.client.get(self.url, {"modelo": "Demanda"})
        self.assertEqual(len(r.context["registros"]), 1)
        self.assertEqual(r.context["registros"][0], self.antigo)

    def test_filtro_por_acao(self):
        r = self.client.get(self.url, {"acao": "DELETE"})
        self.assertEqual(len(r.context["registros"]), 1)

    def test_filtro_por_usuario(self):
        r = self.client.get(self.url, {"usuario": self.usuario.pk})
        self.assertEqual(len(r.context["registros"]), 2)

    def test_filtro_por_periodo_hoje(self):
        r = self.client.get(self.url, {"periodo": "hoje"})
        self.assertEqual([x.pk for x in r.context["registros"]], [self.hoje.pk])

    def test_filtro_por_periodo_30_dias(self):
        r = self.client.get(self.url, {"periodo": "30dias"})
        self.assertEqual([x.pk for x in r.context["registros"]], [self.hoje.pk])

    def test_filtros_combinados(self):
        r = self.client.get(self.url, {"modelo": "Usuario", "periodo": "hoje"})
        self.assertEqual(len(r.context["registros"]), 1)

    def test_e1_sem_resultados(self):
        """CU21, fluxo de exceção E1."""
        r = self.client.get(self.url, {"modelo": "Inexistente"})

        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["sem_resultados"])
        self.assertContains(r, "Nenhum registro encontrado")

    def test_log_vazio_nao_e_erro(self):
        LogAlteracao.objects.all().delete()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["sem_resultados"])
        self.assertContains(r, "Ainda não há alterações registradas")

    def test_detalhe_do_registro(self):
        r = self.client.get(reverse("detalhe_log", args=[self.hoje.pk]))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "status_conta=ativa")
        self.assertContains(r, "Bar do Zé")

    def test_registro_inexistente(self):
        self.assertEqual(self.client.get(reverse("detalhe_log", args=[999])).status_code, 404)

    def test_usuario_comum_recebe_403(self):
        comum = criar("comerciante", "outro@x.com", "222.222.222-22")
        self.client.force_login(comum)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_visitante_vai_para_o_login(self):
        self.client.logout()
        r = self.client.get(self.url)
        self.assertTrue(r.url.startswith(reverse("login")))


class AdminEhSomenteLeituraTests(TestCase):
    """
    CU21: "Nenhuma alteração é realizada no log durante a consulta".
    RF-007 (LGPD): o aceite dos termos também não é editável pelo painel.
    """

    def setUp(self):
        self.admin = criar("comerciante", "admin@exemplo.com", "999.999.999-99")
        self.request = RequestFactory().get("/admin/")
        self.request.user = self.admin

    def test_log_nao_pode_ser_criado_editado_ou_removido(self):
        model_admin = dj_admin.site._registry[LogAlteracao]

        self.assertFalse(model_admin.has_add_permission(self.request))
        self.assertFalse(model_admin.has_change_permission(self.request))
        self.assertFalse(model_admin.has_delete_permission(self.request))

    def test_aceite_de_termos_nao_pode_ser_criado_nem_editado(self):
        model_admin = dj_admin.site._registry[TermoAceite]

        self.assertFalse(model_admin.has_add_permission(self.request))
        self.assertFalse(model_admin.has_change_permission(self.request))
        self.assertFalse(model_admin.has_delete_permission(self.request))

    def test_denuncia_nao_pode_ser_criada_pelo_painel(self):
        from moderacao.models import Denuncia

        model_admin = dj_admin.site._registry[Denuncia]
        self.assertFalse(model_admin.has_add_permission(self.request))


class AdminCategoriaTests(TestCase):
    """
    CU20 / RF-031 a RF-034 — gerenciar categorias de insumo.

    O CU20 A2 (e o RF-034) exigem que a exclusão seja bloqueada quando há
    produtos vinculados.
    """

    def setUp(self):
        from portfolio.models import Produto

        self.admin = criar("comerciante", "admin@exemplo.com", "999.999.999-99")
        self.request = RequestFactory().get("/admin/")
        self.request.user = self.admin

        self.fornecedor = criar("fornecedor", "for@x.com", "111.111.111-11")

        self.com_produtos = CategoriaInsumo.objects.create(nome="Bebidas")
        self.sem_produtos = CategoriaInsumo.objects.create(nome="Serviços")

        self.produto = Produto.objects.create(
            id_fornecedor=self.fornecedor, id_categoria=self.com_produtos,
            nome="Coca", preco="4.50",
        )

    def test_lista_mostra_nome_status_e_contagens(self):
        model_admin = dj_admin.site._registry[CategoriaInsumo]
        self.assertEqual(
            model_admin.list_display,
            ("id_categoria", "nome", "status", "total_produtos", "total_demandas"),
        )

    def test_filtro_e_busca(self):
        model_admin = dj_admin.site._registry[CategoriaInsumo]
        self.assertEqual(model_admin.list_filter, ("status",))
        self.assertEqual(model_admin.search_fields, ("nome",))

    def test_exclui_categoria_sem_produto(self):
        model_admin = dj_admin.site._registry[CategoriaInsumo]
        self.assertTrue(model_admin.has_delete_permission(self.request, self.sem_produtos))
        self.sem_produtos.delete()
        self.assertFalse(CategoriaInsumo.objects.filter(pk=self.sem_produtos.pk).exists())

    def test_bloqueia_exclusao_com_produto_vinculado(self):
        """RF-034 / CU20 A2-E2."""
        model_admin = dj_admin.site._registry[CategoriaInsumo]
        self.assertFalse(model_admin.has_delete_permission(self.request, self.com_produtos))
        self.assertTrue(CategoriaInsumo.objects.filter(pk=self.com_produtos.pk).exists())

    def test_contagens_na_listagem(self):
        model_admin = dj_admin.site._registry[CategoriaInsumo]
        self.assertEqual(model_admin.total_produtos(self.com_produtos), 1)
        self.assertEqual(model_admin.total_demandas(self.com_produtos), 0)


class SementeDeDadosTests(TestCase):
    """
    A migration `core.0002_dados_iniciais` cria o mínimo para a plataforma
    funcionar: uma versão dos Termos de Uso (alvo do aceite do CU01), os dois
    planos do RF-020 e as categorias citadas no RF-013.
    """

    def test_termo_de_uso_vigente(self):
        self.assertTrue(TermoUso.objects.filter(versao="1.0").exists())

    def test_planos_do_rf020(self):
        from assinaturas.models import PlanoAssinatura

        nomes = list(
            PlanoAssinatura.objects.values_list("nome_plano", flat=True)
        )
        self.assertIn("Plano Fornecedor Silver", nomes)
        self.assertIn("Plano Fornecedor Gold", nomes)

    def test_categorias_do_rf013(self):
        nomes = list(CategoriaInsumo.objects.values_list("nome", flat=True))
        for esperada in ("Bebidas", "Laticínios", "Descartáveis"):
            self.assertIn(esperada, nomes)