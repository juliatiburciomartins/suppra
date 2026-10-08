"""
Dados iniciais necessários para a plataforma funcionar (sem alterar schema).

Por que uma migration de dados: o CU01 exige que o aceite aos Termos de Uso seja
gravado em `termo_aceite`, e essa tabela tem FK para `termo_uso`. Se nenhuma
versão do termo existisse, o aceite não teria onde ser registrado. Pelo mesmo
motivo, o RF-020/CU12 descreve **dois** planos (Fornecedor Silver e Fornecedor
Gold) — sem essas linhas a tela de planos nasceria vazia.

Nenhuma tabela é criada ou alterada aqui: é `RunPython` sobre tabelas que já
existem no `banco.sql`. Tudo é idempotente (`get_or_create`), então rodar de
novo não duplica nada, e a equipe pode editar os textos e os valores pelo painel
(CU23) sem que o seed sobrescreva nada.

Os benefícios dos planos são os descritos no RF-020 e no CU12; os valores mensais
(R$ 29,90 Silver / R$ 59,90 Gold) são os que o projeto já usava na tela de
planos antes desta migration.
"""

from django.db import migrations
from django.utils import timezone

# --- Termos de Uso (RNF-015) ----------------------------------------------

VERSAO_TERMOS = "1.0"
DATA_VIGENCIA = "2026-09-04"

TEXTO_TERMOS = """
1. Objeto e Âmbito da Plataforma

O suppra (Hub de Fornecedores para Microempreendedores) é uma plataforma digital
voltada para conectar microempreendedores, comerciantes locais e fornecedores de
insumos de forma ágil e segura.

2. Cadastro e Conta de Acesso

O usuário compromete-se a fornecer dados verdadeiros, completos e atualizados no
momento do cadastro (incluindo CPF/CNPJ, e-mail e telefones válidos). A senha de
acesso é pessoal, intransferível e de total responsabilidade do usuário.

3. Conduta e Regras da Comunidade

É estritamente proibida a publicação de conteúdos falsos, enganosos,
difamatórios ou que violem os direitos de terceiros. Contas que descumprirem as
normas da comunidade estarão sujeitas a suspensão imediata ou banimento
permanente.

4. Isenção de Responsabilidade

A plataforma atua exclusivamente como um canal digital de aproximação comercial e
vitrine de portfólios, não participando diretamente das negociações financeiras,
pagamentos ou entregas realizadas externamente entre as partes.

5. Política de Suspensão de Conta

Confirmadas informações enganosas ou descumprimento destes Termos, a equipe
gestora pode suspender a conta do infrator, impedindo seu acesso à plataforma.
"""

# --- Planos de assinatura (RF-020 / CU12) ----------------------------------

PLANOS = [
    {
        "nome_plano": "Plano Fornecedor Silver",
        "valor": "29.90",
        "descricao": (
            "Destaque intermediário do portfólio na listagem, selo de fornecedor "
            "verificado e acesso a relatórios básicos de visualizações."
        ),
    },
    {
        "nome_plano": "Plano Fornecedor Gold",
        "valor": "59.90",
        "descricao": (
            "Destaque prioritário do portfólio na listagem, selo de fornecedor "
            "premium, acesso a relatórios completos de visualizações e contatos "
            "recebidos, e suporte dedicado."
        ),
    },
]


def semear(apps, schema_editor):
    """
    Cria os registros iniciais de forma idempotente.

    `apps.get_model` é usado em vez dos models reais porque a migration precisa
    refletir o estado histórico do schema — é a forma correta de escrever
    migration de dados.
    """
    TermoUso = apps.get_model("core", "TermoUso")
    PlanoAssinatura = apps.get_model("assinaturas", "PlanoAssinatura")

    # Termo de Uso vigente (RNF-015): alvo dos registros de `termo_aceite`.
    if not TermoUso.objects.filter(versao=VERSAO_TERMOS).exists():
        TermoUso.objects.create(
            versao=VERSAO_TERMOS,
            texto=TEXTO_TERMOS.strip(),
            data_vigencia=DATA_VIGENCIA,
        )

    # Planos Silver e Gold (RF-020 / CU12).
    for plano in PLANOS:
        PlanoAssinatura.objects.get_or_create(
            nome_plano=plano["nome_plano"],
            defaults={
                "descricao": plano["descricao"],
                "valor": plano["valor"],
            },
        )



def nao_fazer_nada(apps, schema_editor):
    """
    Reverse: apagar o seed apagaria dados que a equipe pode ter editado no
    painel (CU23). A reversão é mantida como no-op de propósito.
    """
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("assinaturas", "0003_remove_plano_fora_do_banco_sql"),
    ]

    operations = [
        migrations.RunPython(semear, nao_fazer_nada, elidable=True),
    ]