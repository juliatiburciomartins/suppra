# Hub FECC — Projeto Django (Escopo Base v2)

Este é o **novo escopo base** do projeto, já com:

- Os 8 apps do Django criados: `usuarios`, `core`, `portfolio`, `demandas`, `avaliacoes`, `assinaturas`, `moderacao`, `suporte`.
- **`models.py` de todos os apps já escritos**, espelhando fielmente as tabelas do `banco.sql` do TCC (mesmos nomes de tabela e de coluna).
- **Migrations do Django já geradas e testadas**, sincronizadas com o `banco.sql` via `--fake-initial` (ver seção "Como isso funciona" abaixo).
- `django-simple-history` ativo em `Produto` e `Demanda`, atendendo ao **RF-024** (log de alterações).
- `django-widget-tweaks` e `Pillow` instalados e prontos.
- Painel `/admin/` já com todos os models registrados (exceto `Avaliacao`/`Favorito`, que usam chave composta — ver observação no final).
- Versões de biblioteca **travadas** no `requirements.txt` (testadas e validadas de ponta a ponta nesta máquina).

Além da base, **todas as telas e casos de uso dos 34 requisitos funcionais estão
implementados**: acesso público, listagem e detalhe de fornecedores e demandas,
busca e filtro por categoria, avaliação em estrelas, favoritos, denúncia e
moderação, suporte interno, planos/assinaturas, tutorial de onboarding e o painel
da equipe gestora. O mapa requisito a requisito está na seção
**"Mapa da documentação"** no fim deste arquivo.

---

## Como isso funciona (leiam antes de mexer)

O time já tinha um `banco.sql` pronto e validado (schema do TCC, com ENUMs, FKs etc.). Em vez de deixar o Django criar as tabelas do zero a partir dos models (o que poderia gerar um schema levemente diferente do que está documentado no MER/DER), o fluxo foi:

1. Importar o `banco.sql` num banco `hub_fecc_of` vazio.
2. Rodar `python manage.py inspectdb` para o Django "ler" essa estrutura exata.
3. Organizar esses models nos 8 apps certos, adicionar `choices`, `related_name`, `on_delete`, etc.
4. Gerar as migrations normalmente (`makemigrations`).
5. Aplicá-las com `migrate --fake-initial` — isso diz ao Django "essas tabelas já existem, não recrie, só marque como aplicadas".

**Resultado:** o `banco.sql` continua sendo a fonte da verdade do schema definido no TCC, mas agora o Django e o ORM enxergam e controlam essas tabelas normalmente, incluindo o controle de versão (migrations) para qualquer mudança futura de campo.

**Isso significa, na prática:** cada programador pode importar o `banco.sql` direto (do jeito que o time já documentou no TCC) e rodar `migrate --fake-initial` — **não precisam rodar `migrate` puro**, pois isso tentaria recriar tabelas que já existem e vai dar erro de "tabela já existe".

---

## Passo a passo para cada programador (do zero)

### 1. Clonar o repositório e entrar na pasta

```bash
git clone <url-do-repositorio>
cd hub_fecc
```

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar as dependências (versões travadas, testadas)

```bash
pip install -r requirements.txt
```

> Se der erro no `mysqlclient` no Windows (falta de compilador), troquem por PyMySQL:
> ```bash
> pip uninstall mysqlclient
> pip install PyMySQL
> ```
> E adicionem no topo de `hub_fecc/__init__.py`:
> ```python
> import pymysql
> pymysql.install_as_MySQLdb()
> ```

### 4. Instalar e subir o MySQL/MariaDB local

Cada um usa o MySQL que já tem instalado (Workbench, XAMPP, MariaDB nativo etc.) — não precisa ser igual entre os dois.

### 5. Criar o banco e importar o schema

```sql
CREATE DATABASE hub_fecc_of CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
mysql -u root -p hub_fecc_of < banco.sql
```

### 6. Configurar o `.env`

```bash
cp .env.example .env      # Linux/Mac
copy .env.example .env    # Windows (cmd)
```

Editem o `.env` com a senha real do MySQL de cada um (e o e-mail da equipe gestora em `ADMIN_EMAILS`):

```env
DEBUG=True
SECRET_KEY=gerem-uma-chave-nova-aqui
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=hub_fecc_of
DB_USER=root
DB_PASSWORD=sua_senha_local
DB_HOST=localhost
DB_PORT=3306

# e-mails da equipe gestora (acesso ao /admin/ e às views admin_required)
ADMIN_EMAILS=admin@exemplo.com
```

O `.env.example` da raiz tem o mesmo conteúdo comentado, incluindo
`TIME_ZONE_BANCO` (fuso da sessão MySQL, ver observação 7 abaixo) e as opções de
e-mail. Se você importou o `banco.sql` com outro nome de schema, ajuste o
`DB_NAME` para o nome que você usou — o Django só precisa apontar para a base que
tem as tabelas.

### 7. Sincronizar o Django com o banco já importado

```bash
python manage.py migrate --fake-initial
```

Isso vai:
- Marcar como "aplicadas" as migrations das tabelas que já vieram do `banco.sql` (usuario, produto, demanda, avaliacao, favorito, etc.).
- Criar de verdade as tabelas que são só do Django (`django_admin_log`, `django_session`, `auth_group`/`auth_permission`, e as tabelas de histórico `demandas_historicaldemanda` / `portfolio_historicalproduto`). **Nenhuma tabela do `banco.sql` é alterada.**

> **Atualizando de uma versão anterior deste projeto?** O `AUTH_USER_MODEL` passou a ser `usuarios.Usuario`
> (antes era o `auth.User` padrão). Bancos já migrados pela versão antiga ficam com a FK de `django_admin_log`
> apontando para `auth_user`. Recriem o banco do zero: `DROP DATABASE hub_fecc_of;`, reimportem o `banco.sql`
> (passo 5) e rodem `python manage.py migrate --fake-initial` de novo.

### 8. Criar o administrador (equipe gestora) para acessar o `/admin/`

O `banco.sql` não tem coluna de administrador (`tipo_perfil` só aceita `fornecedor`/`comerciante`), então
**administrador = e-mail listado em `ADMIN_EMAILS`** no `.env`. O e-mail precisa estar lá antes de criar a conta:

```bash
python manage.py createsuperuser   # use o mesmo e-mail que está em ADMIN_EMAILS
```

O cadastro público não aceita e-mails de `ADMIN_EMAILS`.

### 9. Rodar o servidor

```bash
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/admin/

Se aparecerem os 8 apps na tela do admin (`Usuarios`, `Core`, `Portfolio`, `Demandas`, `Avaliacoes`, `Assinaturas`, `Moderacao`, `Suporte`), a base está funcionando.

---

## Se algum programador já tem o banco criado de outra forma

Se em vez de importar o `.sql` a pessoa preferir deixar o Django criar tudo do zero (banco vazio, sem `banco.sql`), aí sim rodam:

```bash
python manage.py migrate
```

(sem `--fake-initial`) — o Django vai criar as tabelas puramente a partir dos `models.py`. **Atenção:** nesse caminho, sempre confirmem que a estrutura final bate com o `banco.sql` documentado no TCC (nomes de tabela, ENUMs etc.), porque são dois caminhos que devem chegar no mesmo lugar.

**Recomendação:** usem sempre o caminho do passo 5-7 acima (importar `banco.sql` + `--fake-initial`), para garantir 100% de fidelidade ao schema documentado.

---

## Observações técnicas importantes

1. **`Avaliacao` e `Favorito` usam chave primária composta** (`id_comerciante` + `id_fornecedor`, sem coluna `id` própria), usando o recurso `models.CompositePrimaryKey` do Django 6.1. Isso é fiel ao `banco.sql`, mas o Django Admin **não suporta registrar models com PK composta** — por isso não aparecem em `/admin/`. Se quiserem gerenciar esses dados visualmente, precisam de uma view custom (não `admin.register`).

2. **`log_alteracao` (tabela manual do banco.sql) x `django-simple-history` (tabelas automáticas)**: o projeto agora tem as duas coisas ativas ao mesmo tempo — decidam em equipe se vão usar só o `simple_history` (recomendado, é automático) ou se vão gravar manualmente em `log_alteracao` também. Ver comentário detalhado em `core/models.py`.

3. **Autenticação (`Usuario` = `AUTH_USER_MODEL`)**: `Usuario` estende `AbstractBaseUser` e mapeia a tabela `usuario` do `banco.sql`. Login por e-mail (`USERNAME_FIELD`), senha sempre via `set_password()` / `check_password()` (PBKDF2/SHA256 — RNF-002); o campo `password` é gravado na coluna `senha`. Usem `login()`/`logout()`/`authenticate()` do Django normalmente. Como o schema não pode mudar: **não há** `last_login`, `is_superuser`/`is_staff`, `PermissionsMixin` nem `data_exclusao` — administrador é definido por `ADMIN_EMAILS` e a exclusão de conta (RF-016) é soft delete por anonimização + `status_conta='suspensa'` (`usuarios/services.py`).

4. **Controle de acesso por perfil (RF-004 / RNF-006)**: em views de função usem `@fornecedor_required`, `@comerciante_required`, `@login_usuario_requerido` ou `@admin_required` (`usuarios/decorators.py`); em views de classe, `FornecedorRequiredMixin`, `ComercianteRequiredMixin`, `AdminRequiredMixin` (`usuarios/mixins.py`). Visitante vai ao login; perfil errado volta ao próprio painel com mensagem; `admin_required` devolve HTTP 403. O context processor `hub_fecc.context_processors.perfil_usuario` expõe `perfil_atual`, `is_fornecedor`, `is_comerciante`, `is_admin` e um `tipo_menu` padrão aos templates.

5. **Testes**: `python manage.py test` (precisa do MySQL configurado; o Django cria um banco `test_<DB_NAME>` à parte — o `.env` deste projeto aponta para `hub_fcc`, então o banco de teste é `test_hub_fcc`). Para um app só, `python manage.py test portfolio`. Use `--noinput` se o banco de teste já existir e o Django perguntar se pode apagá-lo.

6. **`django-simple-history==3.13.0`**: essa versão renomeou a middleware de `HistoricalRecordsMiddleware` para `HistoryRequestMiddleware`. Se algum tutorial ou documentação antiga mencionar o nome velho, ignorem — o `settings.py` já está com o nome certo para a versão travada no `requirements.txt`.

7. **Fuso horário do MySQL**: o `settings.py` fixa `SET time_zone = '+00:00'` na conexão (`TIME_ZONE_BANCO`, ajustável pelo `.env`). Sem isso, as colunas com `DEFAULT CURRENT_TIMESTAMP` do `banco.sql` saem com o fuso do servidor e as telas que filtram por período leem datas incoerentes. Se o seu MySQL tiver a tabela de fusos carregada, troque o offset por `America/Sao_Paulo` no `.env` (acompanha horário de verão). Detalhes na seção "Fuso horário" do `settings.py`.

8. **`Avaliacao` e `Favorito` não entram no Django Admin**: usam chave primária composta e o Admin recusa o registro (`ImproperlyConfigured`). A fila de avaliações do CU22 é uma tela própria em `/painel/avaliacoes/`, protegida por `admin_required`. Ver `moderacao/admin.py`.

---

## Estrutura de pastas

```
hub_fecc/
├── hub_fecc/          # configurações do projeto (settings, urls, wsgi, context_processors)
├── usuarios/          # Usuario (RF-001 a RF-004, RF-014, RF-016, RF-023, RF-026)
├── core/              # CategoriaInsumo, TermoUso, TermoAceite, LogAlteracao
│                      # + indicadores do painel (CU24) e telas de admin (CU21)
├── portfolio/         # Produto (RF-005 a RF-008, RF-010, RF-012, RF-013, RF-027)
├── demandas/          # Demanda (RF-009, RF-011, RF-012, RF-013, RF-027)
├── avaliacoes/        # Avaliacao, Favorito (RF-018, RF-028 a RF-030)
├── assinaturas/       # PlanoAssinatura, Assinatura (RF-020 a RF-022)
├── moderacao/         # Denuncia (RF-025, CU14, CU22)
├── suporte/           # Suporte (RF-019)
├── static/            # CSS, JS, logo e vídeo
├── media/             # uploads (evidências de denúncia/suporte)
├── templates/         # templates HTML (base, menus, componentes e um por app)
├── banco.sql          # SCHEMA: fonte da verdade. NÃO alterar.
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Mapa da documentação

Onde cada requisito e caso de uso da documentação está implementado.

### Requisitos funcionais

| RF | Onde |
|---|---|
| RF-001 / RF-002 Cadastrar fornecedor / comerciante | `usuarios/forms.py::CadastroForm`, `usuarios/views.py::cadastro_view` |
| RF-003 Autenticar usuários | `usuarios/views.py::login_view` |
| RF-004 Controle de acesso por perfil | `usuarios/decorators.py`, `usuarios/mixins.py`, `hub_fecc/context_processors.py` |
| RF-005 Cadastrar portfólio | `portfolio/views.py::cadastrar_produto` |
| RF-006 Editar produto | `portfolio/views.py::editar_produto` |
| RF-007 Atualizar disponibilidade | `portfolio/views.py::alternar_status_produto` |
| RF-008 Remover produto | `portfolio/views.py::remover_produto` |
| RF-009 Publicar demanda | `demandas/views.py::publicar_demanda_view` |
| RF-010 Visualizar portfólios | `portfolio/views.py::listar_fornecedores`, `detalhes_fornecedor` |
| RF-011 Visualizar demandas (por fornecedor) | `demandas/views.py::listar_demandas`, `detalhes_demanda` |
| RF-012 Canal de contato direto | `core/contato.py` (canais de telefone, WhatsApp e e-mail) |
| RF-013 Buscar e filtrar categorias | `portfolio/views.py`, `demandas/views.py` (parâmetros `?categoria=` e `?busca=`) |
| RF-014 Tutorial de onboarding | `usuarios/views.py::tutorial_view`, `usuarios/onboarding.py` |
| RF-015 FAQ | `core/views.py::faq_view` |
| RF-016 Excluir conta | `usuarios/views.py::excluir_conta_view`, `usuarios/services.py::anonimizar_usuario` |
| RF-017 Painel administrativo | `core/admin_views.py` (indicadores CU24) + Django Admin |
| RF-018 Avaliar fornecedores | `avaliacoes/views.py::avaliar_fornecedor` |
| RF-019 Canal de suporte interno | `suporte/views.py::suporte_view`, `meus_chamados_view` |
| RF-020 Visualizar planos | `assinaturas/views.py::planos_assinatura` |
| RF-021 Contratar plano | `assinaturas/views.py::contratar_plano` |
| RF-022 Gerenciar assinatura ativa | `assinaturas/views.py::meu_plano`, `cancelar_assinatura` |
| RF-023 Recuperar senha | `usuarios/password_reset.py`, `usuarios/views.py` |
| RF-024 Log de alterações | `django-simple-history` em `Produto`/`Demanda` + `core/services.py::registrar_log` |
| RF-025 Denúncia de conteúdo | `moderacao/views.py::denunciar_view`, `moderacao/services.py` |
| RF-026 Editar dados cadastrais | `usuarios/views.py::editar_perfil_view` |
| RF-027 Acesso público | `listar_fornecedores`, `detalhes_fornecedor`, `listar_demandas`, `detalhes_demanda` |
| RF-028 / RF-029 / RF-030 Favoritos | `avaliacoes/views.py::lista_favoritos`, `alternar_favorito`, `remover_favorito` |
| RF-031 a RF-034 Categorias de insumo | `core/admin.py::CategoriaInsumoAdmin` |

### Casos de uso

| CU | Onde |
|---|---|
| CU01 Cadastrar usuário | `usuarios/views.py::cadastro_view` (+ aceite gravado em `TermoAceite`) |
| CU02 / CU03 Login e recuperação de senha | `usuarios/views.py` + `usuarios/password_reset.py` |
| CU04 Visualizar publicamente | Telas públicas (sem decorator de perfil) |
| CU05 / CU06 Portfólio, busca e filtro | `portfolio/views.py` |
| CU07 Publicar / editar / encerrar / remover demanda | `demandas/views.py` |
| CU08 Favoritar fornecedor | `avaliacoes/views.py` |
| CU09 Avaliar fornecedor | `avaliacoes/views.py::avaliar_fornecedor` |
| CU10 Gerenciar portfólio | `portfolio/views.py` |
| CU11 Visualizar demandas do comerciante | `demandas/views.py` |
| CU12 / CU13 Planos e contratação | `assinaturas/views.py`, `assinaturas/services.py` |
| CU14 Denunciar conteúdo | `moderacao/views.py::denunciar_view` |
| CU15 Excluir conta | `usuarios/views.py::excluir_conta_view` |
| CU16 Editar dados cadastrais | `usuarios/views.py::editar_perfil_view` |
| CU17 Tutorial e onboarding | `usuarios/views.py::tutorial_view`, `pular_tutorial_view` |
| CU18 FAQ | `core/views.py::faq_view` |
| CU19 Suporte interno | `suporte/views.py` |
| CU20 Categorias (admin) | `core/admin.py::CategoriaInsumoAdmin` |
| CU21 Log de auditoria | `core/admin_views.py::log_auditoria_view` |
| CU22 Moderação de denúncias e avaliações | `moderacao/admin.py` + `core/admin_views.py::fila_avaliacoes_view` |
| CU23 Planos e assinaturas (admin) | `assinaturas/admin.py` |
| CU24 Indicadores do painel | `core/admin_views.py::painel_admin_view`, `core/indicadores.py` |

### Limites conhecidos (decididos pelo schema do `banco.sql`)

- **Tutorial (CU17)**: a pós-condição pede registrar que o usuário concluiu ou
  ignorou o tutorial. A tabela `usuario` não tem coluna livre e o `banco.sql` não
  pode ser alterado, então o estado é guardado **na sessão**. Se o usuário limpar
  o navegador ou trocar de aparelho, o tutorial aparece de novo. Se um dia o
  schema ganhar uma coluna, basta trocar as quatro funções de
  `usuarios/onboarding.py` — nenhuma view muda.
- **Denúncia e `tipo_conteudo`**: o `banco.sql` não tem CHECK amarrando
  `tipo_conteudo` ao `id_produto`/`id_demanda`. A coerência é validada na view
  (`moderacao/views.py::_resolver_alvo`).
- **Exclusão de conta (RF-016)**: soft delete por anonimização + `status_conta`,
  porque as FKs de produto/demanda/avaliação/assinatura impedem um DELETE real.
  Ver `usuarios/services.py`.
