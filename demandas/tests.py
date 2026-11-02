"""
Testes de demandas: gestão pelo comerciante (RF-009 / CU07) e a listagem pública
com filtro e contato (RF-011, RF-012, RF-013, RF-027 / CU04, CU11).

Cobre também o RF-024: toda alteração de Demanda fica no histórico do
django-simple-history com o usuário responsável.
"""

from django.test import TestCase
from django.urls import reverse

from core.models import CategoriaInsumo
from demandas.models import Demanda
from usuarios.models import Usuario

SENHA = "SenhaForte#123"


def criar(perfil, email, cpf):
    return Usuario.objects.create_user(
        email=email, password=SENHA, nome=f"Usuário {perfil}",
        cpf_cnpj=cpf, tipo_perfil=perfil, whatsapp="(19) 99999-1111",
    )


class BaseDemanda(TestCase):
    def setUp(self):
        self.comerciante = criar("comerciante", "com@x.com", "111.111.111-11")
        self.fornecedor = criar("fornecedor", "for@x.com", "222.222.222-22")
        self.bebidas = CategoriaInsumo.objects.create(nome="Bebidas")
        self.descartaveis = CategoriaInsumo.objects.create(nome="Descartáveis")

    def demanda(self, **extra):
        dados = dict(
            id_comerciante=self.comerciante,
            id_categoria=self.bebidas,
            descricao_produto="Cerveja long neck",
            quantidade_produto="200 caixa/mês",
        )
        dados.update(extra)
        return Demanda.objects.create(**dados)

    def dados_validos(self, **extra):
        dados = {
            "id_categoria": self.bebidas.pk,
            "descricao_produto": "Cerveja long neck, latinha 350ml",
            "quantidade_produto": "200 caixas por mês",
        }
        dados.update(extra)
        return dados


class PublicarDemandaTests(BaseDemanda):
    """RF-009 / CU07 fluxo principal."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comerciante)

    def test_get_formulario_abre(self):
        self.assertEqual(self.client.get(reverse("publicar_demanda")).status_code, 200)

    def test_publica_com_status_publicada(self):
        r = self.client.post(reverse("publicar_demanda"), self.dados_validos())
        self.assertEqual(r.status_code, 302)

        demanda = Demanda.objects.get()
        self.assertEqual(demanda.id_comerciante, self.comerciante)
        self.assertEqual(demanda.status, "publicada")
        self.assertIsNotNone(demanda.data_publicacao)

    def test_registra_o_autor_no_historico(self):
        """RF-024."""
        self.client.post(reverse("publicar_demanda"), self.dados_validos())
        self.assertEqual(Demanda.history.count(), 1)
        self.assertEqual(Demanda.history.first().history_user, self.comerciante)

    def test_e1_campos_obrigatorios(self):
        r = self.client.post(reverse("publicar_demanda"), {})
        self.assertEqual(r.status_code, 200)
        erros = r.context["form"].errors
        self.assertEqual(
            set(erros), {"id_categoria", "descricao_produto", "quantidade_produto"}
        )

    def test_descricao_curta_e_recusada(self):
        r = self.client.post(reverse("publicar_demanda"), self.dados_validos(descricao_produto="abc"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("descricao_produto", r.context["form"].errors)

    def test_categoria_inativa_nao_oferecida(self):
        inativa = CategoriaInsumo.objects.create(nome="Descontinuada", status="inativa")
        form = self.client.get(reverse("publicar_demanda")).context["form"]
        self.assertNotIn(inativa.pk, [c.pk for c in form.fields["id_categoria"].queryset])

    def test_fornecedor_e_visitante_nao_publicam(self):
        self.client.force_login(self.fornecedor)
        r = self.client.post(reverse("publicar_demanda"), self.dados_validos())
        self.assertRedirects(r, reverse("dashboard_fornecedor"), fetch_redirect_response=False)
        self.assertEqual(Demanda.objects.count(), 0)

        self.client.logout()
        r = self.client.post(reverse("publicar_demanda"), self.dados_validos())
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("login")))
        self.assertEqual(Demanda.objects.count(), 0)


class MinhasDemandasTests(BaseDemanda):
    def test_lista_apenas_as_do_usuario(self):
        minha = self.demanda()
        outro = criar("comerciante", "com2@x.com", "333.333.333-33")
        Demanda.objects.create(
            id_comerciante=outro, id_categoria=self.bebidas,
            descricao_produto="De outro", quantidade_produto="1",
        )

        self.client.force_login(self.comerciante)
        r = self.client.get(reverse("minhas_demandas"))

        self.assertEqual(r.status_code, 200)
        self.assertEqual([d.pk for d in r.context["demandas"]], [minha.pk])

    def test_inclui_as_encerradas_no_historico(self):
        """CU07 A2: encerrar mantém o registro."""
        encerrada = self.demanda(status="encerrada")
        publicada = self.demanda(descricao_produto="Ainda ativa")

        self.client.force_login(self.comerciante)
        r = self.client.get(reverse("minhas_demandas"))

        self.assertEqual(r.context["total_demandas"], 2)
        self.assertEqual(r.context["demandas_publicadas"], 1)
        self.assertIn(encerrada, list(r.context["demandas"]))
        self.assertIn(publicada, list(r.context["demandas"]))


class EditarDemandaTests(BaseDemanda):
    """RF-009 / CU07 A1."""

    def setUp(self):
        super().setUp()
        self.demanda_ = self.demanda()
        self.client.force_login(self.comerciante)
        self.url = reverse("editar_demanda", args=[self.demanda_.pk])

    def test_get_preenche_o_formulario(self):
        r = self.client.get(self.url)
        self.assertEqual(r.context["form"].initial["descricao_produto"], "Cerveja long neck")

    def test_salva_e_grava_o_historico(self):
        r = self.client.post(self.url, self.dados_validos(quantidade_produto="500 caixas"))
        self.assertEqual(r.status_code, 302)

        self.demanda_.refresh_from_db()
        self.assertEqual(self.demanda_.quantidade_produto, "500 caixas")

        alteracao = Demanda.history.order_by("-history_date").first()
        self.assertEqual(alteracao.history_type, "~")
        self.assertEqual(alteracao.history_user, self.comerciante)
        # A descrição também mudou no mesmo POST, então é o `__str__` do model.
        self.assertIn("latinha 350ml", str(alteracao.instance))

    def test_comerciante_nao_edita_demanda_de_outro(self):
        outro = criar("comerciante", "com2@x.com", "333.333.333-33")
        alheia = Demanda.objects.create(
            id_comerciante=outro, id_categoria=self.bebidas,
            descricao_produto="Alheia", quantidade_produto="1",
        )
        r = self.client.post(reverse("editar_demanda", args=[alheia.pk]), self.dados_validos())
        self.assertEqual(r.status_code, 404)


class EncerrarDemandaTests(BaseDemanda):
    """CU07 A2, primeira opção — encerrar mantém o registro."""

    def setUp(self):
        super().setUp()
        self.demanda_ = self.demanda()
        self.client.force_login(self.comerciante)
        self.url = reverse("encerrar_demanda", args=[self.demanda_.pk])

    def test_post_encerra_e_mantem_o_registro(self):
        self.client.post(self.url)
        self.demanda_.refresh_from_db()
        self.assertEqual(self.demanda_.status, "encerrada")
        self.assertTrue(Demanda.objects.filter(pk=self.demanda_.pk).exists())

    def test_get_nao_altera_nada(self):
        self.client.get(self.url)
        self.demanda_.refresh_from_db()
        self.assertEqual(self.demanda_.status, "publicada")

    def test_demanda_encerrada_sai_da_listagem_publica(self):
        self.client.post(self.url)
        r = self.client.get(reverse("listar_demandas"))
        self.assertEqual(r.context["demandas"].count(), 0)

    def test_nao_encerra_demanda_de_outro(self):
        outro = criar("comerciante", "com2@x.com", "333.333.333-33")
        alheia = Demanda.objects.create(
            id_comerciante=outro, id_categoria=self.bebidas,
            descricao_produto="Alheia", quantidade_produto="1",
        )
        self.client.post(reverse("encerrar_demanda", args=[alheia.pk]))
        alheia.refresh_from_db()
        self.assertEqual(alheia.status, "publicada")


class RemoverDemandaTests(BaseDemanda):
    """CU07 A2, segunda opção — remover exclui de definitivo."""

    def setUp(self):
        super().setUp()
        self.demanda_ = self.demanda()
        self.client.force_login(self.comerciante)
        self.url = reverse("remover_demanda", args=[self.demanda_.pk])

    def test_post_remove(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Demanda.objects.filter(pk=self.demanda_.pk).exists())

    def test_get_nao_remove(self):
        self.client.get(self.url)
        self.assertTrue(Demanda.objects.filter(pk=self.demanda_.pk).exists())

    def test_remocao_fica_no_historico(self):
        """RF-024: o registro some, mas a auditoria fica."""
        self.client.post(self.url)
        self.assertEqual(Demanda.objects.count(), 0)
        self.assertEqual(Demanda.history.filter(id_demanda=self.demanda_.pk).count(), 2)
        self.assertEqual(Demanda.history.first().history_type, "-")

    def test_nao_remove_demanda_de_outro(self):
        outro = criar("comerciante", "com2@x.com", "333.333.333-33")
        alheia = Demanda.objects.create(
            id_comerciante=outro, id_categoria=self.bebidas,
            descricao_produto="Alheia", quantidade_produto="1",
        )
        self.client.post(reverse("remover_demanda", args=[alheia.pk]))
        self.assertTrue(Demanda.objects.filter(pk=alheia.pk).exists())


class ListarDemandasTests(BaseDemanda):
    """RF-027 / CU04 e RF-011 / CU11."""

    def setUp(self):
        super().setUp()
        self.demanda_ = self.demanda()
        self.outra = self.demanda(
            descricao_produto="Copos descartáveis",
            id_categoria=self.descartaveis,
            quantidade_produto="1000 un",
        )

    def test_listagem_abre_sem_login(self):
        self.assertEqual(self.client.get(reverse("listar_demandas")).status_code, 200)

    def test_agrupada_por_categoria(self):
        """RF-011: organizadas por categoria de insumo."""
        r = self.client.get(reverse("listar_demandas"))

        nomes = [categoria.nome for categoria, _ in r.context["grupos"]]
        self.assertEqual(nomes, ["Bebidas", "Descartáveis"])
        self.assertEqual(len(r.context["grupos"][0][1]), 1)

    def test_filtro_por_categoria(self):
        r = self.client.get(reverse("listar_demandas"), {"categoria": self.descartaveis.pk})
        self.assertEqual(len(r.context["demandas"]), 1)
        self.assertEqual(r.context["demandas"].first(), self.outra)

    def test_busca_por_texto(self):
        r = self.client.get(reverse("listar_demandas"), {"busca": "copos"})
        self.assertEqual(len(r.context["demandas"]), 1)

    def test_busca_por_nome_do_comerciante(self):
        r = self.client.get(reverse("listar_demandas"), {"busca": "Usuário comerciante"})
        self.assertEqual(len(r.context["demandas"]), 2)

    def test_categoria_sem_demanda_nao_e_oferecida(self):
        CategoriaInsumo.objects.create(nome="Sem nenhuma", status="ativa")
        r = self.client.get(reverse("listar_demandas"))
        self.assertNotIn("Sem nenhuma", [c.nome for c in r.context["categorias"]])

    def test_sem_resultado_mensagem_e_sugestao(self):
        """CU11 E1."""
        r = self.client.get(reverse("listar_demandas"), {"busca": "inexistente-xyz"})
        self.assertTrue(r.context["sem_resultados"])
        self.assertContains(r, "Nenhuma demanda encontrada")


class DetalheDemandaTests(BaseDemanda):
    """RF-012 / CU04 e CU11."""

    def setUp(self):
        super().setUp()
        self.demanda_ = self.demanda()
        self.comerciante.telefone = "(19) 3232-1010"
        self.comerciante.save()
        self.url = reverse("detalhes_demanda", args=[self.demanda_.pk])

    def test_abre_sem_login(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        # RF-011: nome, categoria, descrição, quantidade e data.
        self.assertContains(r, "Usuário comerciante")
        self.assertContains(r, "Bebidas")
        self.assertContains(r, "Cerveja long neck")
        self.assertContains(r, "200 caixa/mês")

    def test_visitante_nao_ve_o_contato(self):
        r = self.client.get(self.url)
        self.assertFalse(r.context["pode_ver_contato"])
        self.assertNotIn("(19) 3232-1010", r.content.decode())
        self.assertIn("apenas para usuários autenticados", r.content.decode())

    def test_fornecedor_autenticado_ve_o_contato(self):
        self.client.force_login(self.fornecedor)
        r = self.client.get(self.url)

        self.assertTrue(r.context["pode_ver_contato"])
        tipos = {canal["tipo"] for canal in r.context["canais"]}
        self.assertEqual(tipos, {"telefone", "whatsapp", "email"})
        self.assertIn("tel:1932321010", r.content.decode())

    def test_comerciante_tambem_ve_o_contato(self):
        self.client.force_login(self.comerciante)
        self.assertTrue(self.client.get(self.url).context["pode_ver_contato"])

    def test_demanda_inexistente(self):
        self.assertEqual(self.client.get(reverse("detalhes_demanda", args=[999])).status_code, 404)

    def test_demanda_encerrada_avisa(self):
        self.demanda_.status = "encerrada"
        self.demanda_.save()
        r = self.client.get(self.url)
        self.assertContains(r, "foi encerrada")