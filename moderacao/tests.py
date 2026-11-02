"""
Testes de moderação: denúncia de conteúdo (RF-025 / CU14) e decisão do
administrador (CU22).

Cobre também:
  - a pós-condição do CU14 ("o conteúdo denunciado permanece visível até a
    conclusão da análise");
  - o RF-024 na decisão: a denúncia e a eventual suspensão ficam registradas
    em `log_alteracao` com a identificação do administrador;
  - a suspensão de conta pelo RF-025 ("aplica suspensão de conta"), que bloqueia
    o login do infrator;
  - a fila de avaliações (CU22 A1) — uma tela própria porque `Avaliacao` tem
    chave primária composta e o Django Admin recusa registrá-la.
"""

from django.contrib.messages import get_messages
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import CategoriaInsumo, LogAlteracao
from demandas.models import Demanda
from moderacao.models import Denuncia
from moderacao.services import julgar_denuncia, resumo_do_conteudo, suspender_conta
from portfolio.models import Produto
from usuarios.models import Usuario

SENHA = "SenhaForte#123"

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00"
    b"\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class BaseModeracao(TestCase):
    def setUp(self):
        self.categoria = CategoriaInsumo.objects.create(nome="Bebidas")

        self.fornecedor = Usuario.objects.create_user(
            email="for@x.com", password=SENHA, nome="Distribuidora Vale",
            cpf_cnpj="111.111.111-11", tipo_perfil="fornecedor",
        )
        self.comerciante = Usuario.objects.create_user(
            email="com@x.com", password=SENHA, nome="Bar do Zé",
            cpf_cnpj="222.222.222-22", tipo_perfil="comerciante",
        )

        self.produto = Produto.objects.create(
            id_fornecedor=self.fornecedor, id_categoria=self.categoria,
            nome="Refrigerante lata", preco="4.50", whatsapp_contato="(19) 99999-1111",
        )
        self.demanda = Demanda.objects.create(
            id_comerciante=self.comerciante, id_categoria=self.categoria,
            descricao_produto="Cerveja long neck", quantidade_produto="200 caixas",
        )

        self.admin_settings = override_settings(ADMIN_EMAILS={"admin@exemplo.com"})
        self.admin_settings.enable()
        self.addCleanup(self.admin_settings.disable)

        self.admin = Usuario.objects.create_user(
            email="admin@exemplo.com", password=SENHA, nome="Equipe Gestora",
            cpf_cnpj="999.999.999-99", tipo_perfil="comerciante",
        )


class DenunciarTests(BaseModeracao):
    """CU14 — registrar denúncia de portfólio ou demanda."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comerciante)
        self.url = reverse("denunciar")

    def denunciar_portfolio(self, **extra):
        dados = {
            "tipo_conteudo": "portfolio",
            "id_produto": self.produto.pk,
            "descricao": "O preço anunciado não corresponde ao valor cobrado.",
        }
        dados.update(extra)
        return self.client.post(self.url, dados)

    def denunciar_demanda(self, **extra):
        dados = {
            "tipo_conteudo": "demanda",
            "id_demanda": self.demanda.pk,
            "descricao": "A demanda pede um volume que não existe no mercado.",
        }
        dados.update(extra)
        return self.client.post(self.url, dados)

    def test_denuncia_de_portfolio(self):
        r = self.denunciar_portfolio()
        self.assertEqual(r.status_code, 302)

        denuncia = Denuncia.objects.get()
        self.assertEqual(denuncia.id_denunciante, self.comerciante)
        self.assertEqual(denuncia.tipo_conteudo, "portfolio")
        self.assertEqual(denuncia.id_produto, self.produto)
        self.assertIsNone(denuncia.id_demanda)
        self.assertEqual(denuncia.status, "pendente")
        self.assertIsNotNone(denuncia.data_denuncia)

    def test_denuncia_de_demanda(self):
        self.denunciar_demanda()
        denuncia = Denuncia.objects.get()
        self.assertEqual(denuncia.tipo_conteudo, "demanda")
        self.assertEqual(denuncia.id_demanda, self.demanda)
        self.assertIsNone(denuncia.id_produto)

    def test_mensagem_de_confirmacao(self):
        r = self.denunciar_portfolio()
        msgs = [str(m) for m in get_messages(r.wsgi_request)]
        self.assertTrue(any("Denúncia recebida" in m for m in msgs))

    def test_conteudo_permanece_visivel(self):
        """Pós-condição do CU14."""
        self.denunciar_portfolio()

        self.produto.refresh_from_db()
        self.demanda.refresh_from_db()

        self.assertEqual(self.produto.status, "ativo")
        self.assertEqual(self.demanda.status, "publicada")
        self.assertEqual(Produto.objects.count(), 1)
        self.assertEqual(Demanda.objects.count(), 1)

    def test_e1_descricao_vazia(self):
        r = self.denunciar_portfolio(descricao="")
        self.assertEqual(r.status_code, 200)
        self.assertIn("descricao", r.context["form"].errors)
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_descricao_curta_e_recusada(self):
        r = self.denunciar_portfolio(descricao="ruim")
        self.assertEqual(r.status_code, 200)
        self.assertIn("descricao", r.context["form"].errors)

    def test_tipo_e_alvo_devem_coincidir(self):
        """O banco.sql não amarra `tipo_conteudo` ao campo preenchido."""
        r = self.denunciar_portfolio(tipo_conteudo="demanda")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_tipo_desconhecido_abre_o_formulario(self):
        r = self.client.post(self.url, {"descricao": "x" * 20})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_fornecedor_tambem_pode_denunciar(self):
        """A CU11 A1 descreve o fornecedor denunciando uma demanda."""
        self.client.force_login(self.fornecedor)
        self.denunciar_demanda()
        self.assertEqual(Denuncia.objects.first().id_denunciante, self.fornecedor)

    def test_visitante_vai_para_o_login(self):
        self.client.logout()
        r = self.client.post(self.url, {"tipo_conteudo": "portfolio"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("login")))
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_producao_inexistente(self):
        r = self.denunciar_portfolio(id_produto=999999)
        self.assertEqual(r.status_code, 404)

    def test_evidencia_opcional_e_guardada_como_caminho(self):
        import shutil
        import tempfile

        from django.test import override_settings as override

        media = tempfile.mkdtemp(prefix="denuncia-media-")
        ativa = override(MEDIA_ROOT=media)
        ativa.enable()
        self.addCleanup(ativa.disable)
        self.addCleanup(shutil.rmtree, media, True)

        evidencia = SimpleUploadedFile("print.png", PNG_1X1, content_type="image/png")
        self.denunciar_portfolio(evidencia=evidencia)

        denuncia = Denuncia.objects.get()
        self.assertTrue(denuncia.evidencia.startswith("denuncias/"))
        self.assertTrue(denuncia.evidencia.endswith(".png"))


class JulgarDenunciaTests(BaseModeracao):
    """CU22 — arquivar ou suspender o infrator."""

    def criar_denuncia(self, tipo="portfolio"):
        dados = dict(
            id_denunciante=self.comerciante,
            tipo_conteudo=tipo,
            descricao="Relato detalhado do problema encontrado no conteúdo.",
            status="pendente",
        )
        if tipo == "portfolio":
            dados["id_produto"] = self.produto
        else:
            dados["id_demanda"] = self.demanda
        return Denuncia.objects.create(**dados)

    def test_arquivar_marca_como_arquivada(self):
        denuncia = self.criar_denuncia()
        julgada, infrator = julgar_denuncia(denuncia, self.admin, "arquivar", "Improcedente")

        self.assertEqual(julgada.status, "arquivada")
        self.assertIsNone(infrator)

    def test_procedente_suspende_o_autor_do_portfolio(self):
        denuncia = self.criar_denuncia()
        _, infrator = julgar_denuncia(denuncia, self.admin, "procedente", "Preço enganoso")

        self.assertEqual(denuncia.status, "procedente")
        self.assertEqual(infrator, self.fornecedor)

        self.fornecedor.refresh_from_db()
        self.assertEqual(self.fornecedor.status_conta, "suspensa")

    def test_procedente_suspende_o_autor_da_demanda(self):
        denuncia = self.criar_denuncia(tipo="demanda")
        _, infrator = julgar_denuncia(denuncia, self.admin, "procedente")

        self.assertEqual(infrator, self.comerciante)
        self.comerciante.refresh_from_db()
        self.assertEqual(self.comerciante.status_conta, "suspensa")

    def test_decisao_invalida(self):
        with self.assertRaises(ValueError):
            julgar_denuncia(self.criar_denuncia(), self.admin, "qualquer")

    def test_registra_a_decisao_no_log(self):
        """RF-024 — data, hora e identificação do administrador."""
        denuncia = self.criar_denuncia()
        julgar_denuncia(denuncia, self.admin, "arquivar", "Sem procedência")

        log = LogAlteracao.objects.get(modelo_afetado="Denuncia")
        self.assertEqual(log.id_usuario, self.admin)
        self.assertEqual(log.acao, "UPDATE")
        self.assertIn("status=pendente", log.conteudo_anterior)
        self.assertIn("arquivar", log.conteudo_anterior)

    def test_suspensao_tambem_vai_para_o_log(self):
        denuncia = self.criar_denuncia()
        julgar_denuncia(denuncia, self.admin, "procedente", "Preço enganoso")

        log = LogAlteracao.objects.get(modelo_afetado="Usuario")
        self.assertEqual(log.id_usuario, self.admin)
        self.assertEqual(log.id_registro_afetado, self.fornecedor.pk)
        # O log guarda o estado ANTERIOR (RF-024: "conteúdo anterior"), e o motivo.
        self.assertIn("status_conta=ativa", log.conteudo_anterior)
        self.assertIn("Preço enganoso", log.conteudo_anterior)

    def test_conta_suspensa_nao_autentica(self):
        """RF-025: a suspensão impede o acesso."""
        suspender_conta(self.fornecedor, self.admin, "Teste")

        self.client.force_login(self.fornecedor)
        self.client.logout()
        self.client.login(username="for@x.com", password=SENHA)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_conteudo_do_infrator_sai_do_ar(self):
        """Suspender tira o infrator do ar, como na exclusão de conta (RF-025)."""
        from usuarios.services import anonimizar_usuario

        suspender_conta(self.fornecedor, self.admin, "Teste")
        anonimizar_usuario(self.fornecedor)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.status, "inativo")

    def test_resumo_do_conteudo_denunciado(self):
        titulo, autor, _ = resumo_do_conteudo(self.criar_denuncia())
        self.assertEqual(titulo, "Refrigerante lata")
        self.assertEqual(autor, "Distribuidora Vale")

        titulo, autor, _ = resumo_do_conteudo(self.criar_denuncia(tipo="demanda"))
        self.assertIn("Cerveja long neck", titulo)
        self.assertEqual(autor, "Bar do Zé")

    def test_resumo_de_conteudo_removido(self):
        """
        O conteúdo pode sumir da plataforma enquanto a denúncia está pendente.
        O admin precisa enxergar a denúncia mesmo assim — daí o marcador.
        """
        denuncia = self.criar_denuncia()
        pk_produto = self.produto.pk  # o delete() zera o pk do objeto
        self.produto.delete()

        titulo, autor, referencia = resumo_do_conteudo(denuncia)
        self.assertEqual(titulo, "(produto removido)")
        self.assertEqual(autor, "—")
        self.assertEqual(referencia, str(pk_produto))


class FilaAvaliacoesTests(BaseModeracao):
    """CU22 A1 — manter ou remover uma avaliação."""

    def setUp(self):
        super().setUp()
        from avaliacoes.models import Avaliacao

        self.Avaliacao = Avaliacao
        self.avaliacao = Avaliacao.objects.create(
            id_comerciante=self.comerciante, id_fornecedor=self.fornecedor,
            nota=5, comentario="Ótimo prazo de entrega.",
        )
        self.url = reverse("fila_avaliacoes")

    def test_visitor_e_redirecionado_para_o_login(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("login")))

    def test_usuario_comum_recebe_403(self):
        """
        `admin_required` levanta `PermissionDenied`; o Django transforma em
        403 pelo handler padrão (que usa `templates/403.html`).
        """
        self.client.force_login(self.comerciante)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_admin_lista_a_avaliacao_com_as_partes(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.url)

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Bar do Zé")
        self.assertContains(r, "Distribuidora Vale")
        self.assertContains(r, "Ótimo prazo de entrega.")

    def test_filtro_por_status(self):
        self.client.force_login(self.admin)

        r = self.client.get(self.url, {"status": "ativa"})
        self.assertEqual(len(r.context["avaliacoes"]), 1)

        r = self.client.get(self.url, {"status": "removida"})
        self.assertEqual(len(r.context["avaliacoes"]), 0)

        r = self.client.get(self.url, {"status": "todas"})
        self.assertEqual(len(r.context["avaliacoes"]), 1)

    def test_filtro_por_nota(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.url, {"nota": "4"})
        self.assertEqual(len(r.context["avaliacoes"]), 0)

        r = self.client.get(self.url, {"nota": "5"})
        self.assertEqual(len(r.context["avaliacoes"]), 1)

    def test_remover_avaliacao(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            reverse("decidir_avaliacao", args=[self.comerciante.pk, self.fornecedor.pk]),
            {"decisao": "remover"},
        )
        self.assertEqual(r.status_code, 302)

        self.avaliacao.refresh_from_db()
        self.assertEqual(self.avaliacao.status_moderacao, "removida")

    def test_manter_avaliacao(self):
        self.avaliacao.status_moderacao = "removida"
        self.avaliacao.save()

        self.client.force_login(self.admin)
        self.client.post(
            reverse("decidir_avaliacao", args=[self.comerciante.pk, self.fornecedor.pk]),
            {"decisao": "manter"},
        )

        self.avaliacao.refresh_from_db()
        self.assertEqual(self.avaliacao.status_moderacao, "ativa")

    def test_decisao_invalida(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("decidir_avaliacao", args=[self.comerciante.pk, self.fornecedor.pk]),
            {"decisao": "talvez"},
        )
        self.avaliacao.refresh_from_db()
        self.assertEqual(self.avaliacao.status_moderacao, "ativa")

    def test_decisao_registrada_no_log(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("decidir_avaliacao", args=[self.comerciante.pk, self.fornecedor.pk]),
            {"decisao": "remover"},
        )

        log = LogAlteracao.objects.get(modelo_afetado="Avaliacao")
        self.assertEqual(log.id_usuario, self.admin)
        self.assertIn(f"fornecedor={self.fornecedor.pk}", log.conteudo_anterior)

    def test_avaliacao_removida_sai_da_media(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("decidir_avaliacao", args=[self.comerciante.pk, self.fornecedor.pk]),
            {"decisao": "remover"},
        )

        r = self.client.get(reverse("detalhes_fornecedor", args=[self.fornecedor.pk]))
        self.assertFalse(r.context["media"])