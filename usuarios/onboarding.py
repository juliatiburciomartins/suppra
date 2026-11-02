"""
Tutorial de onboarding (RF-014 / CU17).

O CU17 é explícito na pós-condição: "o sistema registra que o usuário concluiu ou
ignorou o tutorial, de modo que o fluxo de onboarding não seja reexibido
automaticamente em acessos subsequentes".

Onde esse estado fica
--------------------
A tabela `usuario` do `banco.sql` não tem nenhuma coluna sobrando (as nove colunas
são id_usuario, nome, email, senha, cpf_cnpj, telefone, whatsapp, tipo_perfil e
status_conta — ver `usuarios/models.py`), e o schema documentado no TCC não pode
ser alterado. Como não existe campo para persistir "já viu o tutorial", o estado
é guardado **na sessão do Django** (`request.session`).

Consequência honesta dessa escolha: o tutorial não é reexibido nas visitas
seguintes do mesmo navegador. Se a pessoa limpar os cookies ou trocar de
aparelho, ele aparece de novo — é o limite do schema, não uma escolha de produto.
Se um dia o `banco.sql` ganhar uma coluna para isso, basta trocar as quatro
funções abaixo por leituras/escritas no model, sem mudar nenhuma view.
"""

CHAVE_SESSAO = "onboarding_verificacao"


def _chave(usuario):
    """Uma chave por usuário, para o estado não vazar entre contas no mesmo navegador."""
    return f"{CHAVE_SESSAO}:{usuario.pk}"


def ja_visualizou(request, usuario):
    """True se o usuário já concluiu ou ignorou o tutorial nesta sessão."""
    if not request.user.is_authenticated:
        return False

    return bool(request.session.get(_chave(usuario)))


def registrar_conclusao(request, usuario):
    """Usuário percorreu todas as etapas (CU17, fluxo principal, último passo)."""
    request.session[_chave(usuario)] = "concluido"
    request.session.modified = True


def registrar_ignoracao(request, usuario):
    """
    Usuário optou por pular o onboarding em qualquer etapa (CU17, fluxo
    alternativo A1).
    """
    request.session[_chave(usuario)] = "ignorado"
    request.session.modified = True


def situacao(request, usuario):
    """
    Rótulo do estado atual, para a tela do painel oferecer "ver tutorial de novo".

    Devolve 'pendente', 'concluido', 'ignorado' ou None (visitante).
    """
    if not request.user.is_authenticated:
        return None

    return request.session.get(_chave(usuario))