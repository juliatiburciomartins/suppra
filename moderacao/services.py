"""
Denúncia de conteúdo (RF-025 / CU14) e services de moderação.

Separação de responsabilidades:

- `views.py` — a tela que o comerciante ou fornecedor usa para denunciar
  (CU14). É pública no sentido do RF-025: qualquer usuário **autenticado** pode
  denunciar um portfólio ou uma demanda.
- `julgar_denuncia()` — a decisão do administrador (CU22, fluxo principal). Vive
  aqui porque é chamada tanto pelas ações do Django Admin quanto por qualquer
  tela futura de moderação, e precisa auditar (RF-024) e suspender a conta
  (RF-025) do mesmo jeito nos dois caminhos.
- `suspender_conta()` — também em `views.py`? Não: está aqui porque CU22 chama a
  suspensão "aplicar suspensão de conta ao infrator", que é a mesma rotina usada
  pela exclusão de conta por Voluntariedade, com uma única diferença de
  irreversibilidade. Ver `usuarios/services.py::anonimizar_usuario`.
"""

from core.services import registrar_log
from demandas.models import Demanda
from moderacao.models import Denuncia
from portfolio.models import Produto


def _autor_do_conteudo(denuncia):
    """
    Descobre quem publicou o conteúdo denunciado.

    O banco.sql não tem uma FK única "autor do conteúdo": `denuncia` aponta
    para `id_produto` OU `id_demanda`. O autor é o fornecedor do produto ou o
    comerciante da demanda.

    Devolve a **instância** de `Usuario` (não só o id): `suspender_conta` precisa
    do objeto para gravar e devolver, e o produto pode ter sido removido da
    plataforma enquanto a denúncia pendente aguardava análise — nesse caso o
    `id_produto` ainda existe na denúncia mas a linha em `produto` não, e o autor
    volta como None.
    """
    from usuarios.models import Usuario

    if denuncia.tipo_conteudo == "portfolio" and denuncia.id_produto_id:
        fornecedor_id = (
            Produto.objects.filter(pk=denuncia.id_produto_id)
            .values_list("id_fornecedor", flat=True)
            .first()
        )
        return Usuario.objects.filter(pk=fornecedor_id).first()

    if denuncia.tipo_conteudo == "demanda" and denuncia.id_demanda_id:
        id_comerciante = (
            Demanda.objects.filter(pk=denuncia.id_demanda_id)
            .values_list("id_comerciante", flat=True)
            .first()
        )
        return Usuario.objects.filter(pk=id_comerciante).first()

    return None


def suspender_conta(usuario, admin, motivo):
    """
    Suspende a conta do usuário infrator (RF-025 / CU22).

    `status_conta='suspensa'` já é o que bloqueia o login
    (`Usuario.is_active` é False) e derruba sessões abertas — sem precisar
    mexer na senha. O log de auditoria (RF-024) registra a decisão com data,
    hora e identificação do administrador (exigência do CU22).
    """
    status_anterior = usuario.status_conta

    usuario.status_conta = "suspensa"
    usuario.save(update_fields=["status_conta"])

    registrar_log(
        usuario=admin,
        acao="UPDATE",
        modelo_afetado="Usuario",
        id_registro_afetado=usuario.pk,
        conteudo_anterior=(
            f"status_conta={status_anterior}. Motivo da suspensão: {motivo}"
        ),
    )

    return usuario


def julgar_denuncia(denuncia, admin, decisão, motivo=""):
    """
    CU22 — Revisão de denúncia pelo administrador.

    `decisão` pode ser:
      - "arquivar"  → status 'arquivada'    (improcedente)
      - "procedente" → status 'procedente' + suspensão de conta do autor

    Devolve `(denuncia_atualizada, usuario_suspenso|None)`.
    """
    if decisão not in ("arquivar", "procedente"):
        raise ValueError("decisão inválida: use 'arquivar' ou 'procedente'")

    status_anterior = denuncia.status
    denuncia.status = "arquivada" if decisão == "arquivar" else "procedente"
    denuncia.save(update_fields=["status"])

    registrar_log(
        usuario=admin,
        acao="UPDATE",
        modelo_afetado="Denuncia",
        id_registro_afetado=denuncia.id_denuncia,
        conteudo_anterior=(
            f"status={status_anterior}; decisão={decisão}. Motivo: {motivo or 'não informado'}"
        ),
    )

    infrator = None
    if decisão == "procedente":
        autor = _autor_do_conteudo(denuncia)
        if autor is not None:
            infrator = suspender_conta(
                autor,
                admin,
                motivo=motivo or "Denúncia confirmada pela equipe gestora.",
            )

    return denuncia, infrator


def resumo_do_conteudo(denuncia):
    """
    Resumo curto do conteúdo denunciado, usado na listagem do admin.

    Devolve (titulo, autor, referencia) para o admin saber o que está vendo sem
    abrir o formulário. Se o conteúdo já tiver sumido da plataforma (pode
    acontecer enquanto a denúncia estava pendente), os campos vêm preenchidos
    com marcador — o admin precisa enxergar a denúncia mesmo assim.
    """
    if denuncia.tipo_conteudo == "portfolio" and denuncia.id_produto_id:
        produto = (
            Produto.objects.select_related("id_fornecedor")
            .filter(pk=denuncia.id_produto_id)
            .first()
        )
        if produto is None:
            return ("(produto removido)", "—", str(denuncia.id_produto_id))
        return (produto.nome, produto.id_fornecedor.nome, str(produto.pk))

    if denuncia.tipo_conteudo == "demanda" and denuncia.id_demanda_id:
        demanda = (
            Demanda.objects.select_related("id_comerciante")
            .filter(pk=denuncia.id_demanda_id)
            .first()
        )
        if demanda is None:
            return ("(demanda removida)", "—", str(denuncia.id_demanda_id))
        return (
            demanda.descricao_produto[:60],
            demanda.id_comerciante.nome,
            str(demanda.pk),
        )

    return ("(conteúdo removido)", "—", "—")