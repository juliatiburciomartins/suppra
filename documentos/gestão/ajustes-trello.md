# Ajustes nas descrições dos cards do Trello

Regra seguida: **a documentação manda** (`requisitos.md`, MER, DER, diagrama de casos de uso) e o
`banco.sql` **não foi alterado** (nenhuma linha, nenhuma coluna). Onde o card entrava em conflito com
isso, o card foi reescrito. Abaixo: o que mudou e o texto pronto para colar.

## Resumo dos conflitos encontrados

| Trecho do card | Conflito | Decisão |
|---|---|---|
| `data_exclusao` + `ALTER TABLE usuario ADD COLUMN...` (cards Refatoração e CU15) | A coluna não existe no `banco.sql`, no MER nem no DER, e o banco não pode ser alterado. | Removido. Soft delete usa só colunas existentes: `status_conta='suspensa'` + anonimização. |
| `status_conta` "inativa" (CU15) | O ENUM do banco é `('ativa','suspensa')`. | Usa-se `'suspensa'`. |
| `PermissionsMixin` (Refatoração) | Adiciona a coluna `is_superuser` em `usuario` e as tabelas `usuario_groups`/`usuario_user_permissions`; nada disso está no DER. | Removido. Só `AbstractBaseUser`. |
| `AbstractBaseUser` traz `last_login` | A tabela `usuario` não tem essa coluna. | `last_login` é removido do model. |
| `senha (via set_password)` | `AbstractBaseUser` chama o campo de `password`; a coluna do banco é `senha`. | Campo Python `password` com `db_column="senha"`. |
| Nome `CustomUser` | MER/DER/documentação chamam a entidade de **Usuario**; renomear quebraria FKs/migrations dos outros apps. | Model continua `Usuario`; manager `UsuarioManager`. |
| `admin_required` "por `tipo_perfil`" (Acesso) | RF-004 define **dois** perfis (Fornecedor/Comerciante); o ENUM `tipo_perfil` e a especialização do DER não têm "admin". A equipe gestora (RF-017) não é um perfil de `usuario`. | `admin_required` usa `Usuario.is_admin` (e-mail em `ADMIN_EMAILS`, no `.env`). |
| "rodar `makemigrations`/`migrate`" (Refatoração) | `migrate` puro tentaria recriar tabelas do `banco.sql`. | Fluxo oficial: importar `banco.sql` + `migrate --fake-initial`. A migration `usuarios/0002` não emite SQL (`sqlmigrate` = no-op). |

---

## Card 1 — Implementar Edição de Dados Cadastrais (CU16) — RF-026

Sem conflito com a documentação; foram apenas explicitados os critérios que RF-001/RF-002/RF-026/RNF-010 já pedem.

> Criar `EditarPerfilForm` (ModelForm de `Usuario`) com campos editáveis: **nome/razão social, CNPJ/CPF, telefone e/ou WhatsApp** (ao menos um dos dois contatos — RF-026).
>
> * Exibir o **e-mail apenas para consulta**: campo `disabled`/`readonly`. Por ser `disabled`, o Django ignora o valor enviado no POST (não altera nem forjando a requisição). RF-026: "o e-mail de acesso não pode ser alterado".
> * Validar obrigatoriedade/formato (E1) e **destacar o erro em cada campo** (RNF-010: a mensagem indica o campo e a correção): nome obrigatório; CPF (11 dígitos) ou CNPJ (14 dígitos), gravado com máscara (cabe no `VARCHAR(18)`) e único; telefone/WhatsApp com 10 a 13 dígitos; ao menos um contato.
> * Opção **"Descartar alterações"** (A1): botão que volta aos dados originais sem salvar, com mensagem informativa.
> * Mensagem de sucesso ao salvar.
> * **Não** alterar a tabela `usuario`/`banco.sql`.
> * Arquivos afetados: `usuarios/forms.py`, `usuarios/views.py` (`editar_perfil_view`), `templates/usuarios/editar_perfil.html`.

## Card 2 — Implementar Controle de Acesso por Perfil — RF-004, RNF-006

Ajuste: `admin_required` não pode se basear em `tipo_perfil` (o banco/DER só têm fornecedor e comerciante).

> Criar decorators (`usuarios/decorators.py`) e mixins (`usuarios/mixins.py`): `comerciante_required`, `fornecedor_required` (por `tipo_perfil` — RF-004) e `admin_required` (equipe gestora — RF-017; **por `Usuario.is_admin`, e-mail em `ADMIN_EMAILS` do `.env`**, pois o banco não tem perfil "admin").
>
> * Views de fornecedor inacessíveis a comerciantes (e vice-versa) e a usuários não autenticados (RNF-006): visitante → login (`?next=`); perfil errado → redireciona ao painel do próprio perfil com mensagem; `admin_required` → HTTP 403 para usuário comum.
> * Criar `context_processor` (`hub_fecc/context_processors.py`, registrado em `settings.py`) expondo `perfil_atual`, `is_fornecedor`, `is_comerciante`, `is_admin` e `tipo_menu` padrão para os menus específicos.
> * Testes automatizados de acesso indevido (302 com mensagem / 403).
> * Arquivos afetados: `usuarios/decorators.py`, `usuarios/mixins.py`, `hub_fecc/context_processors.py`, `hub_fecc/settings.py`, `templates/403.html`.

## Card 3 — Refatoração Model Usuario (Autenticação Customizada)

Ajustes: sem `data_exclusao`, sem `PermissionsMixin`, sem `last_login`, nome `Usuario`, migrations sem DDL.

> Refatorar `Usuario` para estender **`AbstractBaseUser`** (sem `PermissionsMixin`), mapeando a tabela `usuario` do `banco.sql` **sem alterá-la**: `nome`, `email` (`USERNAME_FIELD`, unique), `password` → coluna **`senha`** (`db_column`, gravada com `set_password`, PBKDF2/SHA256 — RNF-002), `cpf_cnpj` (unique), `telefone`, `whatsapp`, `tipo_perfil` (fornecedor/comerciante), `status_conta` (ativa/suspensa).
>
> * Remover `last_login` do model (a tabela não tem essa coluna).
> * Criar `UsuarioManager` (`create_user`, `create_superuser`; login por e-mail sem diferenciar maiúsculas).
> * `is_active` = `status_conta != 'suspensa'`; `is_staff`/`is_superuser` derivados de `ADMIN_EMAILS` (o banco não tem essas colunas).
> * Configurar `AUTH_USER_MODEL = 'usuarios.Usuario'` em `settings.py`; remover o `UsuarioSessionMiddleware` (passa a valer o `AuthenticationMiddleware` padrão); ajustar login/logout/cadastro/recuperação de senha para `login()`/`logout()`/`set_password()`.
> * Registrar no Django Admin (senha só leitura; sem exclusão física).
> * **Não** adicionar `data_exclusao` nem rodar `ALTER TABLE`. Migration `usuarios/0002` só muda o estado do Django (`sqlmigrate` = no-op). Fluxo: importar `banco.sql` + `python manage.py migrate --fake-initial`. Quem já tinha o banco da versão anterior deve recriá-lo (a FK de `django_admin_log` mudou de `auth_user` para `usuario`).
> * Arquivos afetados: `usuarios/models.py`, `usuarios/managers.py`, `usuarios/admin.py`, `usuarios/migrations/0002_usuario_auth_customizada.py`, `hub_fecc/settings.py`, `.env.example`. **`banco.sql` intocado.**

## Card 4 — Implementar Exclusão de Conta (CU15) — RF-016

Ajuste principal: sem `data_exclusao`; status `suspensa`; bloqueio de login pelo status.

> Criar view "Excluir minha conta" (`excluir_conta_view`).
>
> * Validar a senha (E1): se incorreta, mostrar o erro no campo e **não excluir**.
> * Ao confirmar: **não** fazer DELETE em `usuario` (FKs sem cascade). Fazer **soft delete com as colunas existentes**: `status_conta = 'suspensa'` e anonimizar `nome`, `email`, `cpf_cnpj` (placeholder que cabe em `VARCHAR(18)`), `telefone` e `whatsapp`; senha inutilizável (`set_unusable_password`). (RF-016 / LGPD)
> * "Dados associados" (RF-016): produtos do fornecedor ficam `inativo` e sem telefone/WhatsApp de contato; demandas publicadas do comerciante ficam `encerrada`; assinatura `ativa` vira `cancelada`.
> * Registrar em `log_alteracao` (RF-024) **sem gravar e-mail/CPF** do titular.
> * Login bloqueado: conta `suspensa` não autentica (`is_active` = False) e sessões abertas caem.
> * Encerrar a sessão (logout) e redirecionar para a home com mensagem de confirmação.
> * Arquivos afetados: `usuarios/views.py`, `usuarios/services.py`, `templates/usuarios/excluir_conta.html`. **`banco.sql` intocado.**
