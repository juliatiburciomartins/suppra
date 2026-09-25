"""
Serviço de log de auditoria manual (RF-024).

Divisão de responsabilidade combinada para o projeto:
  - `Produto` e `Demanda` já têm HistoricalRecords() do django-simple-history
    (ver portfolio/models.py e demandas/models.py) — NÃO chame
    `registrar_log` pra esses dois, o simple_history já cobre sozinho.
  - Todo o resto que precisa de auditoria manual (suspender usuário,
    excluir/anonimizar conta, julgar denúncia, etc.) usa esta função,
    que grava em `LogAlteracao` (core/models.py, tabela `log_alteracao`
    do banco.sql).

Uso típico, dentro de uma view de moderação:

    from core.services import registrar_log

    registrar_log(
        usuario=request.user,           # quem executou a ação
        acao="UPDATE",                  # 'INSERT' | 'UPDATE' | 'DELETE'
        modelo_afetado="Usuario",
        id_registro_afetado=usuario_alvo.pk,
        conteudo_anterior=f"status_conta antes: {status_anterior}",
    )
"""

from core.models import LogAlteracao


def registrar_log(usuario, acao, modelo_afetado, id_registro_afetado, conteudo_anterior=None):
    """
    Cria um registro de auditoria em LogAlteracao.

    - usuario: instância de Usuario que executou a ação (autor do log,
      não necessariamente o "dono" do registro afetado).
    - acao: um de LogAlteracao.ACAO_CHOICES ('INSERT', 'UPDATE', 'DELETE').
    - modelo_afetado: nome do model afetado, ex. "Usuario", "Denuncia".
    - id_registro_afetado: PK do registro afetado.
    - conteudo_anterior: snapshot/descrição opcional do estado anterior,
      útil pra auditoria (texto livre).
    """
    return LogAlteracao.objects.create(
        id_usuario=usuario,
        acao=acao,
        modelo_afetado=modelo_afetado,
        id_registro_afetado=id_registro_afetado,
        conteudo_anterior=conteudo_anterior,
    )
