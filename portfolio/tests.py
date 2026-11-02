"""
Testes do portfólio do fornecedor e das listagens públicas.

Cobre:
  - CU10 / RF-005 a RF-008: cadastrar, editar, alternar status e remover produto;
  - CU04 / RF-027: listagem e detalhe acessíveis sem autenticação;
  - CU05 / RF-012: dados de contato visíveis só para autenticado;
  - CU06 / RF-013: busca textual e filtro por categoria, incluindo o E1;
  - RF-004 / RNF-006: um fornecedor não toca no portfólio de outro;
  - RF-024: histórico das alterações gravado pelo django-simple-history.

O log de auditoria manual (`log_alteracao`) não é verificado aqui de propósito:
`core/services.py` delega Produto e Demanda ao simple_history, para não duplicar
a mesma informação nas duas tabelas.
"""

from django.contrib.auth.models import AnonymousUser
from django.contrib.messages import get_messages
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.models import CategoriaInsumo
from portfolio.models import Produto
from usuarios.models import Usuario

SENHA = "SenhaForte#123"


def criar_fornecedor(email="for@x.com", cpf="111.111.111-11", **extra):
    return Usuario.objects.create_user(
        email=email, password=SENHA, nome=extra.pop("nome", "Fornecedor Teste"),
        cpf_cnpj=cpf, tipo_perfil="fornecedor", **extra,
    )


def criar_comerciante(email="com@x.com", cpf="222.222.222-22", **extra):
    return Usuario.objects.create_user(
        email=email, password=SENHA, nome=extra.pop("nome", "Comerciante Teste"),
        cpf_cnpj=cpf, tipo_perfil="comerciante", **extra,
    )


class BasePortugues(TestCase):
    """Um fornecedor, um comerciante, duas categorias e um produto padrão."""

    def setUp(self):
        self.fornecedor = criar_fornecedor()
        self.comerciante = criar_comerciante()
        self.bebidas = CategoriaInsumo.objects.create(nome="Bebidas")
        self.laticinios = CategoriaInsumo.objects.create(nome="Laticínios")
        # Produto padrão, exposto também como `self.produto` nas subclasses.
        self.refri = self.produto = self.novo_produto()

    def novo_produto(self, **extra):
        """
        Cria um produto. O nome tem `_` de propósito: `produto` puro é
        o atributo do produto padrão (ver `setUp`), e um método com esse
        nome o sobrescreveria.
        """
        dados = dict(
            id_fornecedor=self.fornecedor,
            id_categoria=self.bebidas,
            nome="Refrigerante lata",
            preco="4.50",
            whatsapp_contato="(19) 99999-1111",
        )
        dados.update(extra)
        return Produto.objects.create(**dados)


class CadastrarProdutoTests(BasePortugues):
    """RF-005 / CU10 fluxo principal."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.fornecedor)

    def dados_validos(self, **extra):
        dados = {
            "nome": "Cerveja long neck",
            "id_categoria": self.bebidas.pk,
            "preco": "12.90",
            "telefone_contato": "",
            "whatsapp_contato": "(19) 99999-1111",
        }
        dados.update(extra)
        return dados

    def test_get_formulario_abre(self):
        self.assertEqual(self.client.get(reverse("cadastrar_produto")).status_code, 200)

    def test_cadastra_com_status_ativo_e_registra_historico(self):
        r = self.client.post(reverse("cadastrar_produto"), self.dados_validos())
        self.assertEqual(r.status_code, 302)

        produto = Produto.objects.get(nome="Cerveja long neck")
        self.assertEqual(produto.id_fornecedor, self.fornecedor)
        self.assertEqual(produto.status, "ativo")

        # RF-024: o simple_history registra quem fez a alteração.
        historico = Produto.history.filter(id_produto=produto.pk)
        self.assertEqual(historico.count(), 1)
        self.assertEqual(historico.first().history_user, self.fornecedor)

    def test_exige_uma_forma_de_contato(self):
        """
        CU10 passo 6: telefone e/ou WhatsApp.

        `self.refri` já existe no setUp, então a asserção é sobre a ausência
        do *novo* produto que a tentativa de cadastro deveria ter criado.
        """
        dados = self.dados_validos(telefone_contato="", whatsapp_contato="")
        r = self.client.post(reverse("cadastrar_produto"), dados)

        self.assertEqual(r.status_code, 200)
        self.assertIn("telefone_contato", r.context["form"].errors)
        self.assertFalse(
            Produto.objects.filter(nome="Cerveja long neck").exists()
        )

    def test_exige_categoria_e_nome_e_preco(self):
        """CU10 E1 — erro por campo, com mensagem."""
        r = self.client.post(
            reverse("cadastrar_produto"),
            {"nome": "", "id_categoria": "", "preco": "", "whatsapp_contato": "(19) 99999-1111"},
        )
        self.assertEqual(r.status_code, 200)
        erros = r.context["form"].errors
        self.assertTrue({"nome", "id_categoria", "preco"} <= set(erros))
        self.assertIn("Informe o nome do produto ou serviço.", erros["nome"])

    def test_preco_zero_ou_negativo_e_recusado(self):
        r = self.client.post(reverse("cadastrar_produto"), self.dados_validos(preco="0"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("preco", r.context["form"].errors)

    def test_categoria_inativa_nao_oferecida(self):
        inativa = CategoriaInsumo.objects.create(nome="Descontinuada", status="inativa")
        form = self.client.get(reverse("cadastrar_produto")).context["form"]
        self.assertNotIn(inativa.pk, [c.pk for c in form.fields["id_categoria"].queryset])

    def test_visitante_e_comerciante_nao_cadastram(self):
        for usuario in (None, self.comerciante):
            self.client.logout()
            if usuario:
                self.client.force_login(usuario)
            r = self.client.post(reverse("cadastrar_produto"), self.dados_validos())
            self.assertEqual(r.status_code, 302, usuario)
            self.assertFalse(
                Produto.objects.filter(nome="Cerveja long neck").exists(), usuario
            )


class EditarProdutoTests(BasePortugues):
    """RF-006 / CU10 A1."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.fornecedor)
        self.url = reverse("editar_produto", args=[self.produto.pk])

    def test_get_preenche_o_formulario_com_os_dados_atuais(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["form"].initial["nome"], "Refrigerante lata")

    def test_salva_e_registra_o_conteudo_anterior(self):
        r = self.client.post(self.url, {
            "nome": "Refrigerante lata 350ml",
            "id_categoria": self.laticinios.pk,
            "preco": "5.00",
            "telefone_contato": "(19) 3232-1010",
            "whatsapp_contato": "",
        })
        self.assertEqual(r.status_code, 302)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.nome, "Refrigerante lata 350ml")
        self.assertEqual(self.produto.id_categoria, self.laticinios)
        self.assertEqual(self.produto.preco, 5)

        # RF-024: histórico com o valor anterior recuperável.
        alteracao = Produto.history.filter(
            id_produto=self.produto.pk
        ).order_by("-history_date").first()
        self.assertEqual(alteracao.history_type, "~")
        self.assertEqual(alteracao.history_user, self.fornecedor)
        self.assertIn("Refrigerante lata", str(alteracao.instance))

    def test_fornecedor_nao_edita_produto_de_outro(self):
        outro = criar_fornecedor("outro@x.com", "333.333.333-33")
        r = self.client.post(reverse("editar_produto", args=[outro.pk]))
        self.assertEqual(r.status_code, 404)

    def test_post_invalido_nao_altera_o_registro(self):
        self.client.post(self.url, {"nome": "", "id_categoria": self.bebidas.pk, "preco": "1.00"})
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.nome, "Refrigerante lata")


class StatusProdutoTests(BasePortugues):
    """RF-007 / CU10 A2 — alternar disponibilidade."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.fornecedor)
        self.url = reverse("alternar_status_produto", args=[self.produto.pk])

    def test_alterna_ativo_para_inativo_e_volta(self):
        self.client.post(self.url)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.status, "inativo")

        self.client.post(self.url)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.status, "ativo")

    def test_get_nao_altera_nada(self):
        """A ação muda estado: só POST faz sentido."""
        self.client.get(self.url)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.status, "ativo")

    def test_fornecedor_nao_altera_produto_de_outro(self):
        outro = criar_fornecedor("outro@x.com", "333.333.333-33")
        produto = Produto.objects.create(
            id_fornecedor=outro, id_categoria=self.bebidas, nome="X", preco="1.00"
        )
        self.client.post(reverse("alternar_status_produto", args=[produto.pk]))
        produto.refresh_from_db()
        self.assertEqual(produto.status, "ativo")


class RemoverProdutoTests(BasePortugues):
    """RF-008 / CU10 A3 — remoção permanente."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.fornecedor)
        self.url = reverse("remover_produto", args=[self.produto.pk])

    def test_post_remove_o_produto(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Produto.objects.filter(pk=self.produto.pk).exists())

    def test_get_nao_remove(self):
        """A tela de confirmação é um form POST; GET não pode apagar nada."""
        self.client.get(self.url)
        self.assertTrue(Produto.objects.filter(pk=self.produto.pk).exists())

    def test_remocao_fica_registrada_no_historico(self):
        """RF-024: o registro some, mas a auditoria permanece."""
        self.client.post(self.url)
        self.assertEqual(Produto.objects.count(), 0)
        self.assertEqual(Produto.history.filter(id_produto=self.produto.pk).count(), 2)
        self.assertEqual(Produto.history.first().history_type, "-")

    def test_fornecedor_nao_remove_produto_de_outro(self):
        outro = criar_fornecedor("outro@x.com", "333.333.333-33")
        produto = Produto.objects.create(
            id_fornecedor=outro, id_categoria=self.bebidas, nome="X", preco="1.00"
        )
        self.client.post(reverse("remover_produto", args=[produto.pk]))
        self.assertTrue(Produto.objects.filter(pk=produto.pk).exists())


class AcessoPublicoTests(BasePortugues):
    """RF-027 / CU04 — visitante sem cadastro."""

    def setUp(self):
        super().setUp()

    def test_listagem_e_detalhe_abrem_sem_login(self):
        for url in (
            reverse("listar_fornecedores"),
            reverse("detalhes_fornecedor", args=[self.fornecedor.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_detalhe_de_fornecedor_inexistente(self):
        r = self.client.get(reverse("detalhes_fornecedor", args=[999999]))
        self.assertEqual(r.status_code, 404)

    def test_detalhe_de_um_comerciante_nao_e_portfolio(self):
        r = self.client.get(reverse("detalhes_fornecedor", args=[self.comerciante.pk]))
        self.assertEqual(r.status_code, 404)

    def test_visitante_nao_ve_o_telefone_e_o_email(self):
        """RF-027 / CU04 passo 5: contato só para autenticado."""
        self.fornecedor.telefone = "(19) 3232-1010"
        self.fornecedor.save()

        r = self.client.get(reverse("detalhes_fornecedor", args=[self.fornecedor.pk]))
        html = r.content.decode()

        self.assertFalse(r.context["pode_ver_contato"])
        self.assertNotIn("(19) 3232-1010", html)
        self.assertNotIn("(19) 99999-1111", html)
        self.assertIn("apenas para usuários autenticados", html)

    def test_visitante_ve_o_aviso_de_cadastro(self):
        r = self.client.get(reverse("detalhes_fornecedor", args=[self.fornecedor.pk]))
        self.assertContains(r, reverse("cadastro"))
        self.assertContains(r, reverse("login"))


class ContatoDiretoTests(BasePortugues):
    """RF-012 / CU05 passo 5 — canais de contato para autenticado."""

    def setUp(self):
        super().setUp()
        self.fornecedor.telefone = "(19) 3232-1010"
        self.fornecedor.whatsapp = "(19) 99999-1111"
        self.fornecedor.save()

    def test_autenticado_ve_os_tres_canais(self):
        self.client.force_login(self.comerciante)
        r = self.client.get(reverse("detalhes_fornecedor", args=[self.fornecedor.pk]))

        self.assertTrue(r.context["pode_ver_contato"])
        tipos = {canal["tipo"] for canal in r.context["canais"]}
        self.assertEqual(tipos, {"telefone", "whatsapp", "email"})

        html = r.content.decode()
        self.assertIn("tel:1932321010", html)
        # O WhatsApp Brazilian leva o DDD com o prefixo 55: (19) 99999-1111
        # -> 551999999111 (11 dígitos + 55 = 13).
        self.assertIn("wa.me/5519999991111", html)
        self.assertIn("Entrar em Contato", html)

    def test_canal_ausente_simplesmente_nao_aparece(self):
        self.fornecedor.whatsapp = None
        self.fornecedor.save()

        self.client.force_login(self.comerciante)
        r = self.client.get(reverse("detalhes_fornecedor", args=[self.fornecedor.pk]))

        tipos = {canal["tipo"] for canal in r.context["canais"]}
        self.assertNotIn("whatsapp", tipos)

    def test_mensagem_de_whatsapp_e_incluida_no_link(self):
        self.client.force_login(self.comerciante)
        r = self.client.get(reverse("detalhes_fornecedor", args=[self.fornecedor.pk]))

        whatsapp = next(c for c in r.context["canais"] if c["tipo"] == "whatsapp")
        self.assertIn("?text=", whatsapp["url"])


class BuscaEFiltroTests(BasePortugues):
    """RF-013 / CU06 — busca textual e filtro por categoria."""

    def setUp(self):
        super().setUp()
        self.outro = self.novo_produto(nome="Leite integral 1L", id_categoria=self.laticinios,
                                 preco="6.00")

    def test_filtro_por_categoria(self):
        r = self.client.get(reverse("listar_fornecedores"), {"categoria": self.laticinios.pk})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["categoria_selecionada"], self.laticinios)
        self.assertEqual(len(r.context["fornecedores"]), 1)

    def test_busca_por_nome_do_produto(self):
        r = self.client.get(reverse("listar_fornecedores"), {"busca": "leite"})
        self.assertEqual(len(r.context["fornecedores"]), 1)

    def test_busca_por_nome_da_categoria(self):
        r = self.client.get(reverse("listar_fornecedores"), {"busca": "laticínios"})
        self.assertEqual(len(r.context["fornecedores"]), 1)

    def test_busca_por_nome_do_fornecedor(self):
        r = self.client.get(reverse("listar_fornecedores"), {"busca": "Fornecedor Teste"})
        self.assertEqual(len(r.context["fornecedores"]), 1)

    def test_busca_sem_resultado_mensagem_e_sugestao(self):
        """CU06 E1."""
        r = self.client.get(reverse("listar_fornecedores"), {"busca": "inexistente-xyz"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["sem_resultados"])
        self.assertContains(r, "Nenhum fornecedor encontrado")
        self.assertContains(r, "Ver todos os fornecedores")

    def test_categoria_desconhecida_cai_em_todos(self):
        r = self.client.get(reverse("listar_fornecedores"), {"categoria": "999999"})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["categoria_selecionada"])

    def test_apenas_categorias_ativas_sao_oferecidas(self):
        inativa = CategoriaInsumo.objects.create(nome="Descontinuada", status="inativa")
        r = self.client.get(reverse("listar_fornecedores"))
        self.assertNotIn(inativa, r.context["categorias"])


class VisibilidadeDaListagemTests(BasePortugues):
    """Regras de visibilidade aplicadas na listagem pública."""

    def test_fornecedor_sem_produto_ativo_nao_aparece(self):
        Produto.objects.all().update(status="inativo")
        r = self.client.get(reverse("listar_fornecedores"))
        self.assertEqual(r.context["fornecedores"].count(), 0)

    def test_fornecedor_suspenso_nao_aparece(self):
        self.fornecedor.status_conta = "suspensa"
        self.fornecedor.save()
        self.assertEqual(self.client.get(reverse("listar_fornecedores")).context["fornecedores"].count(), 0)

    def test_produto_inativo_sai_da_listagem(self):
        self.produto.status = "inativo"
        self.produto.save()
        self.assertEqual(self.client.get(reverse("listar_fornecedores")).context["fornecedores"].count(), 0)

    def test_produto_inativo_sai_do_detalhe(self):
        self.produto.status = "inativo"
        self.produto.save()
        r = self.client.get(reverse("detalhes_fornecedor", args=[self.fornecedor.pk]))
        self.assertEqual(r.context["total_produtos"], 0)


class NotaMediaTests(BasePortugues):
    """RF-010 / RF-018 — a média exibida vem das avaliações ativas."""

    def setUp(self):
        super().setUp()
        from avaliacoes.models import Avaliacao

        self.Avaliacao = Avaliacao

    def avaliar(self, comerciante, nota):
        return self.Avaliacao.objects.create(
            id_comerciante=comerciante, id_fornecedor=self.fornecedor, nota=nota
        )

    def test_sem_avaliacao_a_media_e_zero(self):
        self.assertEqual(self.client.get(reverse("listar_fornecedores")).context["fornecedores"]
                         .first().nota_media, 0)

    def test_media_e_a_das_avaliacoes_ativas(self):
        segundo = criar_comerciante("com2@x.com", "444.444.444-44")
        self.avaliar(self.comerciante, 4)
        self.avaliar(segundo, 5)

        fornecedor = self.client.get(reverse("listar_fornecedores")).context["fornecedores"].first()
        self.assertEqual(fornecedor.nota_media, 4.5)
        self.assertEqual(fornecedor.total_avaliacoes, 2)

    def test_media_nao_conta_avaliacao_removida(self):
        avaliacao = self.avaliar(self.comerciante, 5)
        avaliacao.status_moderacao = "removida"
        avaliacao.save()

        fornecedor = self.client.get(reverse("listar_fornecedores")).context["fornecedores"].first()
        self.assertEqual(fornecedor.nota_media, 0)
        self.assertEqual(fornecedor.total_avaliacoes, 0)

    def test_percentagem_de_estrelas(self):
        from portfolio.services import percentual_avaliacao

        self.assertEqual(percentual_avaliacao(0), 0)
        self.assertEqual(percentual_avaliacao(3), 60)
        self.assertEqual(percentual_avaliacao(5), 100)
        self.assertEqual(percentual_avaliacao(None), 0)


class GerenciarPortfolioTests(BasePortugues):
    """RF-005 a RF-008: a tela de gestão lista os produtos do fornecedor."""

    def test_lista_apenas_os_produtos_do_dono(self):
        outro = criar_fornecedor("outro@x.com", "333.333.333-33")
        Produto.objects.create(
            id_fornecedor=outro, id_categoria=self.bebidas, nome="De outro", preco="1.00"
        )
        meu = self.produto

        self.client.force_login(self.fornecedor)
        r = self.client.get(reverse("gerenciar_portfolio"))

        self.assertEqual(r.status_code, 200)
        self.assertEqual([p.pk for p in r.context["produtos"]], [meu.pk])
        self.assertEqual(r.context["total_produtos"], 1)
        self.assertEqual(r.context["produtos_ativos"], 1)

    def test_visitante_vai_para_o_login(self):
        r = self.client.get(reverse("gerenciar_portfolio"))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("login")))

    def test_comerciante_volta_para_o_painho_dele(self):
        self.client.force_login(self.comerciante)
        r = self.client.get(reverse("gerenciar_portfolio"))
        self.assertRedirects(r, reverse("dashboard_comerciante"), fetch_redirect_response=False)
        msgs = [str(m) for m in get_messages(r.wsgi_request)]
        self.assertIn("Esta área é exclusiva para fornecedores.", msgs)