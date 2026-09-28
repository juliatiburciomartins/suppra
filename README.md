# Hub FECC — Projeto Django (Escopo Base v2)

Este é o **novo escopo base** do projeto, já com:

- Os 8 apps do Django criados: `usuarios`, `core`, `portfolio`, `demandas`, `avaliacoes`, `assinaturas`, `moderacao`, `suporte`.
- **`models.py` de todos os apps já escritos**, espelhando fielmente as tabelas do `banco.sql` do TCC (mesmos nomes de tabela e de coluna).
- **Migrations do Django já geradas e testadas**, sincronizadas com o `banco.sql` via `--fake-initial` (ver seção "Como isso funciona" abaixo).
- `django-simple-history` ativo em `Produto` e `Demanda`, atendendo ao **RF-024** (log de alterações).
- `django-widget-tweaks` e `Pillow` instalados e prontos.
- Painel `/admin/` já com todos os models registrados (exceto `Avaliacao`/`Favorito`, que usam chave composta — ver observação no final).
- Versões de biblioteca **travadas** no `requirements.txt` (testadas e validadas de ponta a ponta nesta máquina).

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

5. **Testes**: `python manage.py test usuarios` (precisa do MySQL configurado; o Django cria um banco `test_hub_fecc_of` à parte).

6. **`django-simple-history==3.13.0`**: essa versão renomeou a middleware de `HistoricalRecordsMiddleware` para `HistoryRequestMiddleware`. Se algum tutorial ou documentação antiga mencionar o nome velho, ignorem — o `settings.py` já está com o nome certo para a versão travada no `requirements.txt`.

---

## Estrutura de pastas

```
hub_fecc/
├── hub_fecc/          # configurações do projeto (settings, urls, wsgi)
├── usuarios/          # Usuario (RF-001 a RF-004, RF-014, RF-023, RF-026)
├── core/              # CategoriaInsumo, TermoUso, TermoAceite, LogAlteracao
├── portfolio/         # Produto (RF-005 a RF-008, RF-010, RF-013)
├── demandas/          # Demanda (RF-009, RF-011)
├── avaliacoes/        # Avaliacao, Favorito (RF-018, RF-028 a RF-030)
├── assinaturas/       # PlanoAssinatura, Assinatura (RF-020 a RF-022)
├── moderacao/         # Denuncia (RF-025)
├── suporte/           # Suporte (RF-019)
├── static/            # arquivos estáticos (CSS, JS, imagens do site) — vazio, aguardando RNF-001/010
├── media/             # uploads (evidências de denúncia/suporte, fotos)
├── templates/          # templates HTML globais — AINDA VAZIO, próxima tarefa
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```
