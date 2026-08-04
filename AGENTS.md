# Prontuário Eletrônico Hospitalar — Flask

Sistema de prontuário eletrônico hospitalar estilo SUS, em **Flask + Jinja2 + SQLAlchemy**.
Este repositório tem **paridade funcional e visual** com o monorepo
[prontuario-eletronico-hospitalar](https://github.com/IasminRDS/prontuario-eletronico-hospitalar)
(NestJS + Next.js), mas implementado inteiramente em Flask.

## Convenções

- **Rotas**: um blueprint por domínio em `routes/`, registrado em `app.py`. Use
  `@bp.get(...)` / `@bp.post(...)`, não `@bp.route(..., methods=[...])`.
- **Models**: um arquivo por agregado em `models/`, `db.Model` do `extensions.py`.
  Ao criar um model novo, adicione-o ao `_MODEL_IMPORTS` em `models/__init__.py`.
- **Templates**: herdam de `base.html`. Não escreva CSS inline — use as classes do
  design system em `static/css/dsgov.css`.
- **RBAC**: proteja toda rota com `@requer_permissao("recurso:acao")` de
  `utils/rbac.py`. No template, esconda o controle com `{% if pode('recurso:acao') %}`.
  O backend é a autoridade; o template só espelha.
- **Auditoria**: toda mutação clínica chama `utils/audit.registrar(...)` na mesma
  transação da escrita.

## Design system (DSGov / gov.br)

Tokens em `static/css/dsgov.css`. Azul institucional `#1351B4`, amarelo `#FFCD07`.
Tema claro/escuro via `data-theme` no `<html>`, aplicado antes da pintura para não
piscar. Cores semânticas de estado clínico (`--status-*`) e de classificação de
risco Manchester (`--risk-*`) são o ponto único de re-skin — não hardcode cor de
estado clínico em template.

Acessibilidade é requisito (eMAG/WCAG): skip-link, `:focus-visible` visível em todo
controle, VLibras.

## Como rodar

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
# .env na raiz com SECRET_KEY e DATABASE_URL
flask db upgrade
python app.py
```

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

A suíte **não toca o banco de desenvolvimento**: em PostgreSQL cria um schema
próprio (`teste_automatizado`) e o destrói ao final, com o `search_path` preso a
ele; em SQLite usa um arquivo temporário. Para apontar outro banco, use
`TEST_DATABASE_URL`.

Dois testes seguram a maior parte dos regressos deste projeto:
`test_integridade_rotas.py` renderiza **toda** rota GET com dado semeado — é o
que pega template lendo atributo inexistente, formulário sem CSRF e link para
endpoint que não existe; e `test_auditoria_estatica.py` garante que rota nova
nasce com `@login_required` e, se escreve, com RBAC. Rota de autosserviço é
exceção e precisa entrar explicitamente na lista `AUTOSSERVICO`.

O CI (`.github/workflows/ci.yml`) roda a suíte nos **dois** bancos e aplica as
migrations num banco vazio — o `pytest` monta o schema com `create_all`, então
sem esse passo a migration não seria exercitada.

## Território e isolamento por unidade

`cidade`/`uf` em texto livre não agregam — "Feira de Santana" digitado de três
jeitos vira três municípios em qualquer relatório. A chave é o **código IBGE**
(`models/municipio.py`), que também é o que o SUS usa em CNES, SIA/SIH e SINAN.
Os dois primeiros dígitos do código são a UF, e a carga confere isso: linha
divergente é recusada em vez de contaminar a tabela territorial.

```bash
flask municipios-importar municipios.csv   # colunas: codigo_ibge, nome, uf
```

As 27 capitais são semeadas por padrão; a relação completa (5.570) vem do IBGE.

### Row-Level Security

A aplicação já filtra por unidade em Python. O RLS coloca a mesma regra **dentro
do banco**, para que uma consulta nova que esqueça o filtro não enxergue registro
de outro município. As políticas cobrem toda tabela com `unidade_id`, e a lista
sai do metadata (`utils/rls.tabelas_protegidas`) — tabela clínica nova nasce
protegida.

Quatro detalhes que decidem se isto é proteção ou teatro:

- **`FORCE ROW LEVEL SECURITY`** é obrigatório: o dono da tabela ignora RLS por
  padrão, e a aplicação É a dona.
- **Falha fechada**: sem escopo definido, nada é liberado. Aplicação vazia é bug
  óbvio; aplicação mostrando o país inteiro é incidente que ninguém percebe.
- **`set_config(..., is_local => true)` no `after_begin`**, não no checkout da
  conexão: as rotas dão commit no meio da requisição, e o escopo precisa ser
  reposto a cada transação. `SET` sem `LOCAL` vazaria pelo pool.
- **O hook nunca lê `current_user`** — isso dispara o carregador do Flask-Login,
  que consulta o banco, que abre transação, que chama o hook. O escopo é
  resolvido uma vez por requisição em `definir_escopo_da_requisicao`.

`users`, `medicos`, `leitos` e `mov_estoque` ficam fora (`FORA_DO_ESCOPO`):
proteger `users` quebraria o login. `pacientes` não entra porque cadastro de
paciente é nacional — encontrar quem foi atendido em outro município é o ponto
do prontuário longitudinal.

**Operação:** ferramentas que conectam direto ao banco precisam do escopo. O
backup já passa `PGOPTIONS=-c app.nivel=SISTEMA` e `--enable-row-security`; sem
isso o `pg_dump` se recusa a rodar, e com razão — ele não quer produzir dump
silenciosamente parcial. Em produção, o certo é um papel dedicado com `BYPASSRLS`
fazendo o dump, para que a completude não dependa de uma variável de ambiente.

## Índice mestre de pacientes

Em escala nacional, a mesma pessoa é cadastrada em municípios diferentes — às
vezes só com CPF, às vezes só com CNS. Sem reconciliar isso, o prontuário
longitudinal não existe.

```bash
flask pacientes-deduplicar    # varre e enfileira candidatos; não unifica nada
```

A varredura agrupa por **chave de bloqueio** (`utils/identidade.py`): data de
nascimento + código fonético do primeiro nome. Comparar todos contra todos seria
O(N²) e inviável. Dentro do bloco, `pontuar()` combina documento, nome, nome da
mãe e sexo. Documento oficial coincidente é prova (score 1.0); documento
**divergente** zera o par, por mais parecido que seja o nome.

**Nada é unificado automaticamente**, nem com score 1.0: unificar dois pacientes
errados mistura o histórico clínico de duas pessoas, e isso não tem desfazer bom.
A decisão acontece em `/pacientes/duplicatas/`, que mostra os dois cadastros lado
a lado com o volume clínico de cada um.

A unificação move todo registro que aponte para o paciente. As colunas são
descobertas pelo **metadata**, nunca listadas à mão — hoje são 21, e a que
alguém esquecesse deixaria registro clínico órfão. O absorvido **não é apagado**:
fica inativo apontando para o sobrevivente. Ao herdar `cpf`/`cns`, o valor sai do
absorvido e é gravado antes de entrar no sobrevivente: os dois não podem carregar
o mesmo documento nem no flush intermediário, ou o `UNIQUE` dispara.

## RNDS

A tela **enfileira**; quem envia é o drenador. Sem isso, uma indisponibilidade
momentânea da RNDS viraria registro clínico perdido.

```bash
flask rnds-processar          # drena a fila; feito para rodar em cron
```

A fila vive na tabela `envios_rnds`, com recuo exponencial e no máximo
`MAX_TENTATIVAS` intentos. Erro **transitório** (timeout, 5xx, 429, 401)
reagenda; erro de **validação** (4xx) encerra o envio, porque retentar o mesmo
conteúdo daria o mesmo resultado. Rodar dois drenadores em paralelo é seguro: em
PostgreSQL o lote é travado com `SKIP LOCKED`.

Cada envio carrega uma `chave_idempotencia` — o hash do conteúdo. Ela impede o
mesmo documento de entrar duas vezes na fila e viaja no cabeçalho para a RNDS
descartar reenvio quando a resposta anterior se perdeu.

Sem `RNDS_AUTH_URL`, `RNDS_EHR_URL` e `RNDS_CERTIFICADO`, o sistema usa um
cliente **simulado**: nada sai da máquina, os protocolos vêm prefixados com
`SIM-` e a tela avisa. Os testes cobrem a máquina de estados da fila com o
transporte mockado; o envio real só pode ser verificado com certificado
ICP-Brasil contra o ambiente de homologação.
