"""
Testes do canal de suporte interno (RF-019 / CU19).

Cobre o formulário (assunto e descrição obrigatórios, anexo opcional), o
vínculo com o perfil do usuário, o acompanhamento dos próprios chamados e a
isolamento entre usuários.
"""

import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from suporte.models import Suporte
from usuarios.models import Usuario

SENHA = "SenhaForte#123"

# PNG 1x1 transparente, suficiente para o Pillow validar.
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00"
    b"\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class BaseSuporte(TestCase):
    def setUp(self):
        self.fornecedor = Usuario.objects.create_user(
            email="for@x.com", password=SENHA, nome="Distribuidora",
            cpf_cnpj="111.111.111-11", tipo_perfil="fornecedor",
        )
        self.comerciante = Usuario.objects.create_user(
            email="com@x.com", password=SENHA, nome="Bar do Zé",
            cpf_cnpj="222.222.222-22", tipo_perfil="comerciante",
        )
        self.url = reverse("suporte")

    def dados_validos(self, **extra):
        dados = {
            "assunto": "Não consigo publicar uma demanda",
            "descricao": "O botão de publicar demanda não responde ao clique.",
        }
        dados.update(extra)
        return dados


class AbrirChamadoTests(BaseSuporte):
    """CU19 — fluxo principal."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comerciante)

    def test_get_formulario_abre(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_registra_o_chamado_vinculado_ao_usuario(self):
        r = self.client.post(self.url, self.dados_validos())
        self.assertEqual(r.status_code, 302)

        chamado = Suporte.objects.get()
        self.assertEqual(chamado.id_usuario, self.comerciante)
        self.assertEqual(chamado.status, "aberto")
        self.assertEqual(chamado.assunto, "Não consigo publicar uma demanda")
        self.assertIsNotNone(chamado.data_abertura)

    def test_redireciona_para_o_acompanhamento(self):
        r = self.client.post(self.url, self.dados_validos())
        self.assertRedirects(r, reverse("meus_chamados"))

    def test_anexo_e_opcional(self):
        self.client.post(self.url, self.dados_validos())
        self.assertIsNone(Suporte.objects.get().img)

    def test_fornecedor_tambem_pode_abrir(self):
        """RF-019 serve aos dois perfis."""
        self.client.force_login(self.fornecedor)
        r = self.client.post(self.url, self.dados_validos())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Suporte.objects.get().id_usuario, self.fornecedor)

    def test_visitante_vai_para_o_login(self):
        self.client.logout()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("login")))


class ValidacaoChamadoTests(BaseSuporte):
    """CU19 E1 — assunto e descrição são obrigatórios."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comerciante)

    def test_assunto_e_descricao_vazios(self):
        r = self.client.post(self.url, {"assunto": "", "descricao": ""})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.context["form"].errors), {"assunto", "descricao"})
        self.assertEqual(Suporte.objects.count(), 0)

    def test_mensagens_sao_obrigatorias(self):
        r = self.client.post(self.url, self.dados_validos(descricao="curto"))
        self.assertIn("descricao", r.context["form"].errors)
        self.assertEqual(
            "Descreva o problema com pelo menos 15 caracteres, para que a equipe "
            "consiga ajudar.",
            r.context["form"].errors["descricao"][0],
        )

    def test_assunto_curto(self):
        r = self.client.post(self.url, self.dados_validos(assunto="oi"))
        self.assertIn("assunto", r.context["form"].errors)

    def test_campos_validos_nao_apresentam_erro(self):
        r = self.client.post(self.url, self.dados_validos())
        self.assertEqual(r.status_code, 302)


class AnexoEvidenciaTests(BaseSuporte):
    """Evidência opcional, gravada em disco com caminho relativo (RF-019)."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comerciante)
        self.media = tempfile.mkdtemp(prefix="suporte-media-")
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media, True)

    def test_anexo_valido_e_aceito(self):
        evidencia = SimpleUploadedFile("print.png", PNG_1X1, content_type="image/png")
        r = self.client.post(self.url, {**self.dados_validos(), "img": evidencia})

        self.assertEqual(r.status_code, 302)
        chamado = Suporte.objects.get()

        self.assertIsNotNone(chamado.img)
        self.assertTrue(chamado.img.startswith("suporte/"))
        self.assertTrue(chamado.img.endswith(".png"))

    def test_arquivo_que_nao_e_imagem_e_recusado(self):
        falso = SimpleUploadedFile("malware.exe", b"MZ\x90\x00", content_type="application/x-msdownload")
        r = self.client.post(self.url, {**self.dados_validos(), "img": falso})

        self.assertEqual(r.status_code, 200)
        self.assertIn("img", r.context["form"].errors)
        self.assertEqual(Suporte.objects.count(), 0)


class MeusChamadosTests(BaseSuporte):
    """Pós-condição do CU19 — acompanhar o andamento pelo canal indicado."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comerciante)
        self.meu = Suporte.objects.create(
            id_usuario=self.comerciante, assunto="Meu chamado",
            descricao="Descrição suficientemente longa do problema relatado.",
        )

    def test_lista_apenas_os_proprios(self):
        Suporte.objects.create(
            id_usuario=self.fornecedor, assunto="De outro",
            descricao="Descrição suficientemente longa do problema relatado.",
        )

        r = self.client.get(reverse("meus_chamados"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual([c.pk for c in r.context["chamados"]], [self.meu.pk])
        self.assertEqual(r.context["total"], 1)

    def test_conta_os_em_andamento(self):
        Suporte.objects.create(
            id_usuario=self.comerciante, assunto="Encerrado",
            descricao="Descrição suficientemente longa do problema relatado.",
            status="encerrado",
        )
        r = self.client.get(reverse("meus_chamados"))
        self.assertEqual(r.context["total"], 2)
        self.assertEqual(r.context["abertos"], 1)

    def test_lista_vazia_mensagem(self):
        Suporte.objects.all().delete()
        r = self.client.get(reverse("meus_chamados"))
        self.assertContains(r, "Nenhum chamado aberto")

    def test_visitante_vai_para_o_login(self):
        self.client.logout()
        r = self.client.get(reverse("meus_chamados"))
        self.assertTrue(r.url.startswith(reverse("login")))


class AdminChamadoTests(BaseSuporte):
    """
    O Django Admin opera o chamado (CU19 — encaminhar à equipe gestora).

    A equipe trampa tem acesso via `ADMIN_EMAILS` (ver `Usuario.is_admin`).
    """

    def setUp(self):
        super().setUp()
        self.chamado = Suporte.objects.create(
            id_usuario=self.comerciante, assunto="Assunto de teste",
            descricao="Descrição suficientemente longa do problema relatado.",
        )
        self.admin_settings = override_settings(ADMIN_EMAILS={"admin@exemplo.com"})
        self.admin_settings.enable()
        self.addCleanup(self.admin_settings.disable)

        self.gestor = Usuario.objects.create_user(
            email="admin@exemplo.com", password=SENHA, nome="Equipe Gestora",
            cpf_cnpj="999.999.999-99", tipo_perfil="comerciante",
        )
        self.client.force_login(self.gestor)

    def test_tela_do_admin_abre(self):
        self.assertEqual(self.client.get("/admin/suporte/suporte/").status_code, 200)

    def test_marca_como_em_atendimento(self):
        from django.contrib import messages

        self.client.post(
            "/admin/suporte/suporte/",
            {
                "action": "marcar_em_atendimento",
                "_selected_action": [str(self.chamado.pk)],
            },
            follow=True,
        )
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, "em_atendimento")

    def test_encerrar_chamado(self):
        self.client.post(
            "/admin/suporte/suporte/",
            {
                "action": "encerrar_chamados",
                "_selected_action": [str(self.chamado.pk)],
            },
            follow=True,
        )
        self.chamado.refresh_from_db()
        self.assertEqual(self.chamado.status, "encerrado")

    def test_admin_nao_cria_chamado(self):
        """Chamado é aberto pelo usuário (CU19), não pelo painel."""
        from django.contrib import admin as dj_admin

        model_admin = dj_admin.site._registry[Suporte]
        request = type("R", (), {"user": self.gestor})()
        self.assertFalse(model_admin.has_add_permission(request))