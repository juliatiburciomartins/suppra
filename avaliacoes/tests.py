"""
Testes de avaliação de fornecedores (RF-018 / CU09) e de favoritos
(RF-028, RF-029, RF-030 / CU08).

Os dois models usam chave primária composta `(id_comerciante, id_fornecedor)`,
igual ao `banco.sql`. Por isso estes testes cobrem também o comportamento que essa
chave impõe: uma segunda avaliação do mesmo par **atualiza** a anterior em vez de
criar outra linha (pós-condição do CU09).
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from avaliacoes.forms import AvaliacaoForm
from avaliacoes.models import Avaliacao, Favorito
from portfolio.models import Produto
from usuarios.models import Usuario

SENHA = "SenhaForte#123"


def criar(perfil, email, cpf, nome="Fulano de Tal"):
    return Usuario.objects.create_user(
        email=email, password=SENHA, nome=nome, cpf_cnpj=cpf, tipo_perfil=perfil
    )


class BaseAvaliacoes(TestCase):
    def setUp(self):
        self.comerciante = criar("comerciante", "com@x.com", "111.111.111-11")
        self.fornecedor = criar("fornecedor", "for@x.com", "222.222.222-22", "Distribuidora Vale")
        self.outro_fornecedor = criar("fornecedor", "for2@x.com", "333.333.333-33", "Outra Casa")
        self.url = reverse("avaliar_fornecedor", args=[self.fornecedor.pk])

    def avaliar(self, **extra):
        dados = dict(
            id_comerciante=self.comerciante,
            id_fornecedor=self.fornecedor,
            nota=5,
        )
        dados.update(extra)
        return Avaliacao.objects.create(**dados)


class AvaliacaoFormTests(BaseAvaliacoes):
    """Validação da escala 0 a 5 (RF-018)."""

    def test_escala_vai_de_zero_a_cinco(self):
        form = AvaliacaoForm()
        valores = [str(v) for v, _ in form.fields["nota"].choices]
        self.assertEqual(valores, ["0", "1", "2", "3", "4", "5"])

    def test_aceita_todas_as_notas_validas(self):
        for nota in range(0, 6):
            form = AvaliacaoForm(data={"nota": nota, "comentario": ""})
            self.assertTrue(form.is_valid(), nota)

    def test_recusa_nota_fora_da_escala(self):
        for nota in (-1, 6, 10):
            form = AvaliacaoForm(data={"nota": nota})
            self.assertFalse(form.is_valid(), nota)
            self.assertIn("nota", form.errors)

    def test_nota_e_obrigatoria(self):
        form = AvaliacaoForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("nota", form.errors)

    def test_comentario_e_opcional(self):
        form = AvaliacaoForm(data={"nota": 4})
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["comentario"])

    def test_comentario_so_espacos_vira_nulo(self):
        form = AvaliacaoForm(data={"nota": 4, "comentario": "   "})
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["comentario"])


class AvaliarFornecedorTests(BaseAvaliacoes):
    """CU09 — registrar e editar avaliação."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comerciante)

    def test_get_abre_o_formulario(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["fornecedor"], self.fornecedor)
        self.assertFalse(r.context["editando"])

    def test_registra_a_avaliacao(self):
        r = self.client.post(self.url, {"nota": "4", "comentario": "Bom preço"})
        self.assertEqual(r.status_code, 302)

        avaliacao = Avaliacao.objects.get()
        self.assertEqual((avaliacao.nota, avaliacao.comentario), (4, "Bom preço"))
        self.assertEqual(avaliacao.status_moderacao, "ativa")

    def test_segunda_avaliacao_atualiza_a_existente(self):
        """Pós-condição do CU09: não se submete nova avaliação sem editar a existente."""
        self.avaliar(nota=2)
        self.client.post(self.url, {"nota": "5", "comentario": "Melhorou"})

        self.assertEqual(Avaliacao.objects.count(), 1)
        avaliacao = Avaliacao.objects.get()
        self.assertEqual(avaliacao.nota, 5)
        self.assertEqual(avaliacao.comentario, "Melhorou")

    def test_get_mostra_a_edicao_quando_ja_avaliou(self):
        self.avaliar(nota=3)
        r = self.client.get(self.url)
        self.assertTrue(r.context["editando"])
        self.assertEqual(r.context["nota_atual"], 3)
        self.assertEqual(r.context["form"].initial["nota"], 3)

    def test_reavaliacao_reabre_como_ativa(self):
        avaliacao = self.avaliar(nota=3, status_moderacao="removida")
        self.client.post(self.url, {"nota": "4"})

        avaliacao.refresh_from_db()
        self.assertEqual(avaliacao.nota, 4)
        self.assertEqual(avaliacao.status_moderacao, "ativa")

    def test_nota_invalida_nao_grava(self):
        r = self.client.post(self.url, {"nota": "9"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("nota", r.context["form"].errors)
        self.assertEqual(Avaliacao.objects.count(), 0)

    def test_fornecedor_inexistente(self):
        r = self.client.get(reverse("avaliar_fornecedor", args=[999]))
        self.assertEqual(r.status_code, 404)

    def test_comerciante_nao_avaliar_a_si_mesmo(self):
        """A view exige perfil fornecedor, então nem chega ao portfolios."""
        r = self.client.post(reverse("avaliar_fornecedor", args=[self.comerciante.pk]), {"nota": "5"})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Avaliacao.objects.count(), 0)

    def test_fornecedor_nao_avalia_a_si_mesmo(self):
        """
        O `@comerciante_required` age antes da checagem de "avaliar a si
        mesmo": um fornecedor é barrado na porta da view.
        """
        self.client.force_login(self.fornecedor)
        r = self.client.post(
            reverse("avaliar_fornecedor", args=[self.fornecedor.pk]), {"nota": "5"}
        )
        self.assertRedirects(
            r, reverse("dashboard_fornecedor"), fetch_redirect_response=False
        )
        self.assertEqual(Avaliacao.objects.count(), 0)

    def test_fornecedor_nao_avalia(self):
        """RF-004 / RNF-006: avaliação é de comerciante."""
        self.client.force_login(self.fornecedor)
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse("dashboard_fornecedor"), fetch_redirect_response=False)
        self.assertEqual(Avaliacao.objects.count(), 0)

    def test_visitante_vai_para_o_login(self):
        self.client.logout()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("login")))


class FavoritosTests(BaseAvaliacoes):
    """RF-029 e RF-030 / CU08 — favoritar e desfavoritar."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comerciante)
        self.alternar = reverse("alternar_favorito")

    def favoritar(self, fornecedor=None):
        return self.client.post(
            self.alternar, {"fornecedor_id": (fornecedor or self.fornecedor).pk}
        )

    def test_favoritar_cria_o_registro(self):
        r = self.favoritar()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            Favorito.objects.filter(
                id_comerciante=self.comerciante, id_fornecedor=self.fornecedor
            ).exists()
        )

    def test_favoritar_de_novo_remove(self):
        """Mesma ação serve para os dois estados (RF-029 e RF-030)."""
        self.favoritar()
        self.favoritar()
        self.assertEqual(Favorito.objects.count(), 0)

    def test_get_nao_altera_nada(self):
        self.client.get(self.alternar, {"fornecedor_id": self.fornecedor.pk})
        self.assertEqual(Favorito.objects.count(), 0)

    def test_remover_pela_lista(self):
        self.favoritar()
        r = self.client.post(reverse("remover_favorito", args=[self.fornecedor.pk]))
        self.assertRedirects(r, reverse("lista_favoritos"))
        self.assertEqual(Favorito.objects.count(), 0)

    def test_favoritar_fornecedor_inexistente(self):
        r = self.client.post(self.alternar, {"fornecedor_id": 999})
        self.assertEqual(r.status_code, 404)

    def test_comerciante_nao_favorita_a_si_mesmo_pela_view_de_detalhe(self):
        """A ação direta é bloqueada; o botão nem aparece na tela."""
        r = self.client.post(self.alternar, {"fornecedor_id": self.comerciante.pk})
        self.assertEqual(r.status_code, 404)

    def test_fornecedor_nao_tem_lista_de_favoritos(self):
        self.client.force_login(self.fornecedor)
        r = self.client.get(reverse("lista_favoritos"))
        self.assertRedirects(r, reverse("dashboard_fornecedor"), fetch_redirect_response=False)

    def test_visitante_vai_para_o_login(self):
        self.client.logout()
        r = self.client.get(reverse("lista_favoritos"))
        self.assertTrue(r.url.startswith(reverse("login")))


class ListaFavoritosTests(BaseAvaliacoes):
    """RF-028 / CU08 A1 — nome, categorias ofertadas e avaliação média."""

    def setUp(self):
        super().setUp()
        from core.models import CategoriaInsumo

        self.bebidas = CategoriaInsumo.objects.create(nome="Bebidas")
        self.laticinios = CategoriaInsumo.objects.create(nome="Laticínios")

        Produto.objects.create(
            id_fornecedor=self.fornecedor, id_categoria=self.bebidas,
            nome="Coca", preco="4.50",
        )
        Produto.objects.create(
            id_fornecedor=self.fornecedor, id_categoria=self.bebidas,
            nome="Fanta", preco="4.50",
        )
        Produto.objects.create(
            id_fornecedor=self.fornecedor, id_categoria=self.laticinios,
            nome="Leite", preco="6.00",
        )

        Favorito.objects.create(
            id_comerciante=self.comerciante, id_fornecedor=self.fornecedor
        )
        self.client.force_login(self.comerciante)

    def test_lista_o_favoritado_com_nome_e_categorias(self):
        r = self.client.get(reverse("lista_favoritos"))

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["total_favoritos"], 1)

        fornecedor = r.context["fornecedores"].first()
        self.assertEqual(fornecedor.nome, "Distribuidora Vale")

        # Categoria repetida em dois produtos aparece uma vez só (RF-028).
        nomes = [c.nome for c in fornecedor.categorias_ofertadas]
        self.assertEqual(nomes, ["Bebidas", "Laticínios"])

    def test_exibe_a_avaliacao_media(self):
        avaliador = criar("comerciante", "com2@x.com", "444.444.444-44")
        Avaliacao.objects.create(
            id_comerciante=avaliador, id_fornecedor=self.fornecedor, nota=5
        )
        Avaliacao.objects.create(
            id_comerciante=self.comerciante, id_fornecedor=self.fornecedor, nota=4
        )

        r = self.client.get(reverse("lista_favoritos"))
        fornecedor = r.context["fornecedores"].first()
        self.assertEqual(fornecedor.nota_media, 4.5)
        self.assertEqual(fornecedor.nota_percent, 90)

    def test_nao_lista_quem_nao_e_favorito(self):
        r = self.client.get(reverse("lista_favoritos"))
        self.assertNotIn(
            self.outro_fornecedor, list(r.context["fornecedores"])
        )

    def test_favorito_sem_produto_ativo_continua_na_lista(self):
        Produto.objects.filter(id_fornecedor=self.fornecedor).update(status="inativo")
        r = self.client.get(reverse("lista_favoritos"))
        self.assertEqual(r.context["total_favoritos"], 1)

    def test_favorito_de_conta_suspensa_some(self):
        self.fornecedor.status_conta = "suspensa"
        self.fornecedor.save()

        r = self.client.get(reverse("lista_favoritos"))
        self.assertEqual(r.context["total_favoritos"], 0)

    def test_lista_vazia_mensagem(self):
        Favorito.objects.all().delete()
        r = self.client.get(reverse("lista_favoritos"))
        self.assertEqual(r.context["total_favoritos"], 0)
        self.assertContains(r, "Sua lista de favoritos está vazia")