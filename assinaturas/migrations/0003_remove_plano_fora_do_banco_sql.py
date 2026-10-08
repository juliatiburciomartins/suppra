"""
Remove o model `Plano`, que NÃO existe no `banco.sql`.

Histórico: a migration `0002_plano` criava a tabela `assinaturas_plano` — uma
tabela a mais do que o schema documentado no TCC. Como o `banco.sql` é a fonte
da verdade do schema e não pode ser alterado, essa tabela está fora do projeto:
o plano do fornecedor é `PlanoAssinatura` (tabela `plano_assinatura`), que já
existe no `banco.sql` e cobre o RF-020/CU23.

Por que `SeparateDatabaseAndState`:

  - a parte de **banco** é um `RunPython` que só derruba a tabela se ela existir
    (ambientes que rodaram a `0002_plano`);
  - a parte de **estado** é um `DeleteModel` sem operação de banco, para o
    Django parar de enxergar o model.

Se fosse só um `DeleteModel`, o Django emitiria `DROP TABLE` e quebraria nos
dois cenários opostos: banco novo importado do `banco.sql` (tabela nunca existiu)
e banco antigo (a tabela já foi removida aqui). Com `RunPython` protegido, os
dois funcionam.
"""

from django.db import migrations


def remover_tabela_plano_extra(apps, schema_editor):
    """Apaga `assinaturas_plano` se ela existir; não faz nada se não existir."""
    conexao = schema_editor.connection
    with conexao.cursor() as cursor:
        if "assinaturas_plano" in conexao.introspection.table_names(cursor):
            cursor.execute("DROP TABLE `assinaturas_plano`")


def nao_fazer_nada(apps, schema_editor):
    """Reverse: a tabela é extra do schema documentado, não há o que restaurar."""
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("assinaturas", "0002_plano"),
    ]

    operations = [
        migrations.RunPython(
            remover_tabela_plano_extra,
            nao_fazer_nada,
            elidable=True,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name="Plano")],
            database_operations=[],
        ),
    ]