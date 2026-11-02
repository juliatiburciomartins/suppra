"""
Canais de contato direto entre as partes (RF-012, CU05 passo 5, CU11 passo 8).

A plataforma é apenas intermediária (RNF-008 / Marco Civil da Internet): não
processa pagamento nem fecha negócio. O que ela faz é **expor os dados de
contato** (telefone, e-mail e/ou WhatsApp) para quem já está autenticado e
montar o link do canal escolhido, para a negociação acontecer fora da
plataforma.

Por que os dados ficam ocultos para visitante (RF-027 / CU04): o contato é
dado pessoal (RNF-007). Um visitante sem cadastro vê produtos e preços, mas
não o telefone nem o e-mail. A regra é aplicada no template
(`portfolio/detalhes_fornecedor.html` e `demandas/detalhes_demanda.html`)
usando `pode_ver_contato`, e nenhuma view entrega o contato a não autenticado
— a view monta os canais só quando o usuário passa pelo critério.
"""

import re


def _somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def link_whatsapp(numero, mensagem=None):
    """
    Monta o link `https://wa.me/<DDD+NUMBER>` de um número de WhatsApp.

    O número brasileiro vem com DDD: (19) 99999-9999 -> 5519999999999. Sem DDD
    não dá para montar um link válido, então devolve None.
    """
    digitos = _somente_digitos(numero)
    if len(digitos) == 11:  # DDD + 9 dígitos (celular)
        digitos = f"55{digitos}"
    elif len(digitos) == 10:  # DDD + 8 dígitos (fixo)
        digitos = f"55{digitos}"
    else:
        return None

    url = f"https://wa.me/{digitos}"
    if mensagem:
        from urllib.parse import quote

        url = f"{url}?text={quote(mensagem)}"
    return url


def montar_canais(usuario, mensagem_whatsapp=None):
    """
    Canais de contato de um usuário, prontos para o template.

    Devolve uma lista de dicionários com `tipo`, `icone`, `rotulo`, `valor`
    (o que aparece na tela) e `url` (quando dá para abrir direto). Canais sem
    número configurado simplesmente não entram na lista.

    `mensagem_whatsapp` é o texto de abertura do WhatsApp, montado pela view
    conforme o contexto (RF-012 é sobre o canal de um fornecedor ou de um
    comerciante).
    """
    canais = []

    if usuario.telefone:
        telefone = _somente_digitos(usuario.telefone)
        canais.append(
            {
                "tipo": "telefone",
                "icone": "bi-telephone",
                "rotulo": "Telefone",
                "valor": usuario.telefone,
                "url": f"tel:{telefone}" if telefone else None,
            }
        )

    if usuario.whatsapp:
        canais.append(
            {
                "tipo": "whatsapp",
                "icone": "bi-whatsapp",
                "rotulo": "WhatsApp",
                "valor": usuario.whatsapp,
                "url": link_whatsapp(usuario.whatsapp, mensagem_whatsapp),
            }
        )

    if usuario.email:
        canais.append(
            {
                "tipo": "email",
                "icone": "bi-envelope",
                "rotulo": "E-mail",
                "valor": usuario.email,
                "url": f"mailto:{usuario.email}",
            }
        )

    return canais


def pode_ver_contato(request):
    """
    RF-027 / CU04: dados de contato e funcionalidades interativas só para
    usuário autenticado (RF-003). Qualquer perfil autenticado — comerciante,
    fornecedor ou administrador — tem acesso (RF-012 fala em "usuários
    autenticados", sem restringir perfil).
    """
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated)