from django.contrib.auth import authenticate
from django.contrib.messages import get_messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.views import View

from core.models import CategoriaInsumo, LogAlteracao
from demandas.models import Demanda
from hub_fecc.context_processors import perfil_usuario
from portfolio.models import Produto
from usuarios.decorators import admin_required, comerciante_required, fornecedor_required, perfil_required
from usuarios.mixins import AdminRequiredMixin, ComercianteRequiredMixin, FornecedorRequiredMixin
from usuarios.models import Usuario

SENHA = "SenhaForte#123"


def criar_usuario(email, perfil="comerciante", cpf_cnpj="529.982.247-25", **extra):
    return Usuario.objects.create_user(
        email=email, password=SENHA, nome=extra.pop("nome", "Fulano de Tal"),
        cpf_cnpj=cpf_cnpj, tipo_perfil=perfil, telefone=extra.pop("telefone", "(19) 3333-3333"), **extra,
    )


class UsuarioModelTests(TestCase):
    def test_senha_e_gravada_com_pbkdf2_sha256_na_coluna_senha(self):
        u = criar_usuario("a@a.com")
        self.assertTrue(u.password.startswith("pbkdf2_sha256$"))  # RNF-002
        self.assertTrue(u.check_password(SENHA))
        self.assertEqual(Usuario._meta.get_field("password").column, "senha")
        self.assertEqual(Usuario._meta.db_table, "usuario")

    def test_username_field_e_email_e_sem_last_login(self):
        self.assertEqual(Usuario.USERNAME_FIELD, "email")
        self.assertFalse(hasattr(Usuario._meta, "last_login") and "last_login" in [f.name for f in Usuario._meta.get_fields()])

    def test_tabela_nao_ganha_colunas_alem_do_banco_sql(self):
        colunas = {f.column for f in Usuario._meta.concrete_fields}
        self.assertEqual(colunas, {
            "id_usuario", "nome", "email", "senha", "cpf_cnpj", "telefone", "whatsapp",
            "tipo_perfil", "status_conta",
        })

    def test_authenticate_por_email_ignora_caixa(self):
        criar_usuario("Maria@Exemplo.com")
        self.assertIsNotNone(authenticate(username="maria@exemplo.com", password=SENHA))
        self.assertIsNone(authenticate(username="maria@exemplo.com", password="errada"))

    def test_conta_suspensa_nao_autentica(self):
        criar_usuario("s@s.com", status_conta="suspensa")
        self.assertIsNone(authenticate(username="s@s.com", password=SENHA))

    @override_settings(ADMIN_EMAILS={"gestor@hub.com"})
    def test_create_superuser_exige_email_em_admin_emails(self):
        with self.assertRaises(ValueError):
            Usuario.objects.create_superuser("outro@hub.com", SENHA, nome="X", cpf_cnpj="1", tipo_perfil="comerciante")
        adm = Usuario.objects.create_superuser("gestor@hub.com", SENHA, nome="G", cpf_cnpj="2", tipo_perfil="comerciante")
        self.assertTrue(adm.is_staff and adm.is_superuser and adm.has_perm("x.y"))

    def test_usuario_comum_nao_e_admin(self):
        u = criar_usuario("c@c.com")
        self.assertFalse(u.is_staff)
        self.assertFalse(u.has_perm("x.y"))


class ControleDeAcessoTests(TestCase):
    def setUp(self):
        self.comerciante = criar_usuario("com@x.com", "comerciante", "111.111.111-11")
        self.fornecedor = criar_usuario("for@x.com", "fornecedor", "222.222.222-22")

    def test_visitante_e_redirecionado_para_login(self):
        for url in ("dashboard_fornecedor", "dashboard_comerciante", "editar_perfil", "excluir_conta"):
            r = self.client.get(reverse(url))
            self.assertEqual(r.status_code, 302, url)
            self.assertTrue(r.url.startswith(reverse("login")), url)

    def test_comerciante_nao_acessa_view_de_fornecedor(self):
        self.client.force_login(self.comerciante)
        r = self.client.get(reverse("dashboard_fornecedor"))
        self.assertRedirects(r, reverse("dashboard_comerciante"), fetch_redirect_response=False)
        msgs = [str(m) for m in get_messages(r.wsgi_request)]
        self.assertIn("Esta área é exclusiva para fornecedores.", msgs)
        self.assertEqual(self.client.get(reverse("gerenciar_portfolio")).status_code, 302)

    def test_fornecedor_nao_acessa_view_de_comerciante(self):
        self.client.force_login(self.fornecedor)
        r = self.client.get(reverse("minhas_demandas"))
        self.assertRedirects(r, reverse("dashboard_fornecedor"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("publicar_demanda")).status_code, 302)

    def test_cada_perfil_acessa_o_proprio_painel(self):
        self.client.force_login(self.comerciante)
        self.assertEqual(self.client.get(reverse("dashboard_comerciante")).status_code, 200)
        self.client.force_login(self.fornecedor)
        self.assertEqual(self.client.get(reverse("dashboard_fornecedor")).status_code, 200)

    def test_perfil_required_com_raise_exception_devolve_403(self):
        @perfil_required("fornecedor", raise_exception=True)
        def view(request):
            return HttpResponse("ok")

        rf = RequestFactory()
        req = rf.get("/x/")
        req.user = self.comerciante
        with self.assertRaises(PermissionDenied):
            view(req)

    def _request(self, user):
        req = RequestFactory().get("/x/")
        req.user = user
        req.session = {}
        from django.contrib.messages.storage.fallback import FallbackStorage
        req._messages = FallbackStorage(req)
        return req

    def test_decorators_direto(self):
        ok = lambda request: HttpResponse("ok")  # noqa: E731
        self.assertEqual(fornecedor_required(ok)(self._request(self.fornecedor)).status_code, 200)
        self.assertEqual(fornecedor_required(ok)(self._request(self.comerciante)).status_code, 302)
        self.assertEqual(comerciante_required(ok)(self._request(self.comerciante)).status_code, 200)
        self.assertEqual(comerciante_required(ok)(self._request(self.fornecedor)).status_code, 302)

    @override_settings(ADMIN_EMAILS={"adm@x.com"})
    def test_admin_required_403_para_usuario_comum_e_200_para_admin(self):
        adm = criar_usuario("adm@x.com", "comerciante", "333.333.333-33")
        ok = lambda request: HttpResponse("ok")  # noqa: E731
        with self.assertRaises(PermissionDenied):
            admin_required(ok)(self._request(self.comerciante))
        self.assertEqual(admin_required(ok)(self._request(adm)).status_code, 200)

    def test_admin_required_visitante_vai_para_login(self):
        from django.contrib.auth.models import AnonymousUser
        r = admin_required(lambda request: HttpResponse("ok"))(self._request(AnonymousUser()))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("login")))

    @override_settings(ADMIN_EMAILS={"adm@x.com"})
    def test_mixins(self):
        class V(View):
            def get(self, request):
                return HttpResponse("ok")

        class VF(FornecedorRequiredMixin, V):
            pass

        class VC(ComercianteRequiredMixin, V):
            pass

        class VA(AdminRequiredMixin, V):
            pass

        adm = criar_usuario("adm@x.com", "comerciante", "333.333.333-33")
        self.assertEqual(VF.as_view()(self._request(self.fornecedor)).status_code, 200)
        self.assertEqual(VF.as_view()(self._request(self.comerciante)).status_code, 302)
        self.assertEqual(VC.as_view()(self._request(self.comerciante)).status_code, 200)
        self.assertEqual(VC.as_view()(self._request(self.fornecedor)).status_code, 302)
        self.assertEqual(VA.as_view()(self._request(adm)).status_code, 200)
        with self.assertRaises(PermissionDenied):
            VA.as_view()(self._request(self.comerciante))

    def test_pagina_403_renderiza(self):
        from django.views.defaults import permission_denied
        r = permission_denied(self._request(self.comerciante), PermissionDenied())
        self.assertEqual(r.status_code, 403)
        self.assertIn("Acesso negado", r.content.decode())

    @override_settings(ADMIN_EMAILS={"adm@x.com"})
    def test_context_processor_expoe_perfil(self):
        adm = criar_usuario("adm@x.com", "comerciante", "333.333.333-33")
        ctx = perfil_usuario(self._request(self.fornecedor))
        self.assertEqual((ctx["perfil_atual"], ctx["is_fornecedor"], ctx["is_comerciante"], ctx["tipo_menu"]),
                         ("fornecedor", True, False, "fornecedor"))
        ctx = perfil_usuario(self._request(self.comerciante))
        self.assertEqual((ctx["is_comerciante"], ctx["tipo_menu"]), (True, "comerciante"))
        self.assertEqual(perfil_usuario(self._request(adm))["tipo_menu"], "admin")
        from django.contrib.auth.models import AnonymousUser
        self.assertEqual(perfil_usuario(self._request(AnonymousUser()))["perfil_atual"], None)

    @override_settings(ADMIN_EMAILS={"adm@x.com"})
    def test_admin_do_django_admin_consegue_entrar_e_usuario_comum_nao(self):
        criar_usuario("adm@x.com", "comerciante", "333.333.333-33")
        self.client.login(username="adm@x.com", password=SENHA)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.client.logout()
        self.client.login(username="com@x.com", password=SENHA)
        self.assertEqual(self.client.get("/admin/").status_code, 302)


class LoginCadastroTests(TestCase):
    def test_login_e_logout(self):
        criar_usuario("l@l.com")
        r = self.client.post(reverse("login"), {"username": "L@L.com", "password": SENHA})
        self.assertRedirects(r, reverse("dashboard_comerciante"), fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)
        self.client.get(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_com_senha_errada(self):
        criar_usuario("l@l.com")
        r = self.client.post(reverse("login"), {"username": "l@l.com", "password": "x"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_conta_suspensa_bloqueado(self):
        criar_usuario("s@s.com", status_conta="suspensa")
        r = self.client.post(reverse("login"), {"username": "s@s.com", "password": SENHA})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["conta_suspensa"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sessao_aberta_cai_quando_conta_e_suspensa(self):
        u = criar_usuario("s@s.com")
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("dashboard_comerciante")).status_code, 200)
        Usuario.objects.filter(pk=u.pk).update(status_conta="suspensa")
        self.assertEqual(self.client.get(reverse("dashboard_comerciante")).status_code, 302)

    def test_next_externo_e_ignorado(self):
        criar_usuario("l@l.com")
        r = self.client.post(reverse("login") + "?next=https://evil.com/", {"username": "l@l.com", "password": SENHA})
        self.assertRedirects(r, reverse("dashboard_comerciante"), fetch_redirect_response=False)

    def test_cadastro_grava_hash_e_cpf_mascarado(self):
        r = self.client.post(reverse("cadastro"), {
            "nome": "Loja", "email": "N@Loja.com", "senha": SENHA, "confirmar_senha": SENHA,
            "cpf_cnpj": "52998224725", "telefone": "(19) 3333-3333", "whatsapp": "",
            "tipo_perfil": "comerciante", "aceite_termos": "on",
        })
        self.assertEqual(r.status_code, 302)
        u = Usuario.objects.get(email="n@loja.com")
        self.assertTrue(u.password.startswith("pbkdf2_sha256$"))
        self.assertEqual(u.cpf_cnpj, "529.982.247-25")

    @override_settings(ADMIN_EMAILS={"adm@x.com"})
    def test_cadastro_nao_aceita_email_de_admin(self):
        r = self.client.post(reverse("cadastro"), {
            "nome": "Loja", "email": "adm@x.com", "senha": SENHA, "confirmar_senha": SENHA,
            "cpf_cnpj": "52998224725", "tipo_perfil": "comerciante", "aceite_termos": "on",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email="adm@x.com").exists())

    def test_recuperar_senha_com_token(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        u = criar_usuario("r@r.com")
        uid, token = urlsafe_base64_encode(force_bytes(u.pk)), default_token_generator.make_token(u)
        url = reverse("redefinir_senha", kwargs={"uidb64": uid, "token": token})
        self.assertEqual(self.client.post(url, {"new_password1": "NovaSenha#456", "new_password2": "NovaSenha#456"}).status_code, 302)
        u.refresh_from_db()
        self.assertTrue(u.check_password("NovaSenha#456"))
        self.assertFalse(default_token_generator.check_token(u, token))  # uso único


class EditarPerfilTests(TestCase):
    def setUp(self):
        self.u = criar_usuario("perfil@x.com", "fornecedor", "529.982.247-25", nome="Nome Antigo", whatsapp="(19) 99999-9999")
        self.client.force_login(self.u)
        self.url = reverse("editar_perfil")
        self.dados = {"nome": "Novo Nome Ltda", "cpf_cnpj": "11222333000181", "telefone": "(19) 3333-4444", "whatsapp": ""}

    def test_get_exibe_email_disabled_e_readonly(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("perfil@x.com", html)
        campo = r.context["form"].fields["email"]
        self.assertTrue(campo.disabled)
        self.assertRegex(html, r'<input[^>]*name="email"[^>]*disabled')
        self.assertIn('name="descartar"', html)  # botão A1 presente

    def test_salvar_atualiza_dados_e_mostra_mensagem_de_sucesso(self):
        r = self.client.post(self.url, self.dados, follow=True)
        self.u.refresh_from_db()
        self.assertEqual(self.u.nome, "Novo Nome Ltda")
        self.assertEqual(self.u.cpf_cnpj, "11.222.333/0001-81")
        self.assertEqual(self.u.telefone, "(19) 3333-4444")
        self.assertIsNone(self.u.whatsapp)
        self.assertContains(r, "Dados cadastrais atualizados com sucesso.")

    def test_email_nao_pode_ser_alterado_nem_forjando_o_post(self):
        self.client.post(self.url, {**self.dados, "email": "invasor@x.com"})
        self.u.refresh_from_db()
        self.assertEqual(self.u.email, "perfil@x.com")
        self.assertEqual(self.u.nome, "Novo Nome Ltda")

    def test_e1_erro_por_campo(self):
        r = self.client.post(self.url, {"nome": "", "cpf_cnpj": "123", "telefone": "12", "whatsapp": "abc"})
        self.assertEqual(r.status_code, 200)
        erros = r.context["form"].errors
        self.assertEqual(set(erros), {"nome", "cpf_cnpj", "telefone", "whatsapp"})
        self.assertContains(r, "has-error")
        self.u.refresh_from_db()
        self.assertEqual(self.u.nome, "Nome Antigo")

    def test_e1_exige_telefone_ou_whatsapp(self):
        r = self.client.post(self.url, {**self.dados, "telefone": "", "whatsapp": ""})
        self.assertIn("telefone", r.context["form"].errors)
        r = self.client.post(self.url, {**self.dados, "telefone": "", "whatsapp": "(19) 98888-7777"})
        self.assertEqual(r.status_code, 302)

    def test_cpf_cnpj_duplicado_de_outro_usuario(self):
        criar_usuario("outro@x.com", "comerciante", "11.222.333/0001-81")
        r = self.client.post(self.url, self.dados)
        self.assertIn("cpf_cnpj", r.context["form"].errors)

    def test_manter_o_proprio_cpf_cnpj_e_permitido(self):
        r = self.client.post(self.url, {**self.dados, "cpf_cnpj": "52998224725"})
        self.assertEqual(r.status_code, 302)

    def test_a1_descartar_nao_salva_e_volta_aos_dados_originais(self):
        r = self.client.post(self.url, {**self.dados, "descartar": "1"}, follow=True)
        self.u.refresh_from_db()
        self.assertEqual(self.u.nome, "Nome Antigo")
        self.assertEqual(r.context["form"].initial["nome"], "Nome Antigo")
        self.assertContains(r, "Alterações descartadas")

    def test_post_invalido_nao_altera_request_user_em_memoria(self):
        r = self.client.post(self.url, {**self.dados, "nome": "Alterado", "cpf_cnpj": "1"})
        self.assertEqual(r.wsgi_request.user.nome, "Nome Antigo")

    def test_visitante_nao_edita(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, self.dados).status_code, 302)


class ExcluirContaTests(TestCase):
    def setUp(self):
        self.u = criar_usuario("del@x.com", "fornecedor", "529.982.247-25", nome="Fornecedor Real", whatsapp="(19) 99999-9999")
        self.cat = CategoriaInsumo.objects.create(nome="Bebidas")
        self.produto = Produto.objects.create(
            id_fornecedor=self.u, id_categoria=self.cat, nome="Suco", preco="5.00",
            telefone_contato="(19) 3333-3333", whatsapp_contato="(19) 99999-9999",
        )
        self.client.force_login(self.u)
        self.url = reverse("excluir_conta")

    def test_get_exibe_confirmacao(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_e1_senha_incorreta_nao_exclui(self):
        r = self.client.post(self.url, {"senha": "errada"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Senha incorreta")
        self.u.refresh_from_db()
        self.assertEqual(self.u.nome, "Fornecedor Real")
        self.assertEqual(self.u.status_conta, "ativa")
        self.assertFalse(LogAlteracao.objects.exists())
        self.assertEqual(self.client.get(reverse("dashboard_fornecedor")).status_code, 200)  # segue logado

    def test_confirmacao_faz_soft_delete_sem_delete_fisico(self):
        pk = self.u.pk
        r = self.client.post(self.url, {"senha": SENHA}, follow=True)
        self.assertEqual(r.redirect_chain[-1][0], reverse("home"))
        self.assertContains(r, "Sua conta foi excluída")

        u = Usuario.objects.get(pk=pk)  # a linha continua existindo (FKs RESTRICT)
        self.assertEqual(u.status_conta, "suspensa")
        self.assertEqual(u.nome, "Usuário Removido")
        self.assertNotIn("del@x.com", u.email)
        self.assertTrue(u.conta_excluida)
        self.assertLessEqual(len(u.cpf_cnpj), 18)
        self.assertNotEqual(u.cpf_cnpj, "529.982.247-25")
        self.assertIsNone(u.telefone)
        self.assertIsNone(u.whatsapp)
        self.assertFalse(u.has_usable_password())

    def test_sessao_encerrada_e_login_bloqueado(self):
        self.client.post(self.url, {"senha": SENHA})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get(reverse("dashboard_fornecedor")).status_code, 302)
        r = self.client.post(reverse("login"), {"username": "del@x.com", "password": SENHA})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(r.status_code, 200)

    def test_dados_associados_saem_do_ar(self):
        self.client.post(self.url, {"senha": SENHA})
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.status, "inativo")
        self.assertIsNone(self.produto.telefone_contato)
        self.assertIsNone(self.produto.whatsapp_contato)

    def test_demandas_do_comerciante_sao_encerradas(self):
        c = criar_usuario("com@x.com", "comerciante", "111.111.111-11")
        d = Demanda.objects.create(id_comerciante=c, id_categoria=self.cat, descricao_produto="x", quantidade_produto="10")
        self.client.force_login(c)
        self.client.post(self.url, {"senha": SENHA})
        d.refresh_from_db()
        self.assertEqual(d.status, "encerrada")

    def test_log_de_auditoria_nao_guarda_dados_pessoais(self):
        self.client.post(self.url, {"senha": SENHA})
        log = LogAlteracao.objects.get()
        self.assertEqual((log.acao, log.modelo_afetado, log.id_registro_afetado), ("UPDATE", "Usuario", self.u.pk))
        self.assertNotIn("del@x.com", log.conteudo_anterior)

    def test_dados_do_titular_podem_ser_reutilizados_apos_exclusao(self):
        self.client.post(self.url, {"senha": SENHA})
        novo = criar_usuario("del@x.com", "comerciante", "529.982.247-25")  # mesmo e-mail e CPF
        self.assertNotEqual(novo.pk, self.u.pk)

    def test_visitante_nao_exclui(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {"senha": SENHA}).status_code, 302)
