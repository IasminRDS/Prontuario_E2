# Prontuário Eletrônico Hospitalar — Flask

![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)
![DSGov](https://img.shields.io/badge/design-gov.br%20%2F%20DSGov-1351B4)
![Licença](https://img.shields.io/badge/licença-MIT-green)

Sistema web de **prontuário eletrônico hospitalar** estilo SUS, cobrindo o fluxo
assistencial completo: chegada → triagem → atendimento → exames → prescrição →
internação → evolução → alta.

Esta versão tem **paridade funcional e visual** com o monorepo
[prontuario-eletronico-hospitalar](https://github.com/IasminRDS/prontuario-eletronico-hospitalar)
(NestJS + Next.js), implementada inteiramente em Flask + Jinja2.

**Problema que resolve:** unidades de saúde pequenas costumam operar com registros
em papel ou planilhas soltas, o que dificulta encontrar o histórico do paciente e
gerar relatórios. O sistema centraliza esse histórico num único lugar, com rastro
de auditoria de quem alterou o quê.

---

## Sumário

- [Stack](#stack)
- [Módulos](#módulos)
- [Design system](#design-system)
- [Segurança e conformidade](#segurança-e-conformidade)
- [Como rodar](#como-rodar)
- [Estrutura](#estrutura)
- [Números](#números)

---

## Stack

**Backend** — Python 3.11+ · Flask 3 · Flask-SQLAlchemy · Flask-Migrate (Alembic) ·
Flask-Login · Flask-WTF (CSRF) · pyotp (TOTP) · ReportLab (PDF) · pikepdf.

**Banco** — SQLite em desenvolvimento, PostgreSQL em produção.

**Frontend** — Jinja2 + CSS puro com design tokens, sem build step e sem
dependência de CDN: a aplicação precisa funcionar em rede restrita de unidade de
saúde.

**Deploy** — Gunicorn (`Procfile`).

---

## Módulos

| Área | Módulos |
|---|---|
| **Atendimento** | Pacientes, Prontuário (SOAP), Triagem (Manchester), Atendimentos, Pronto-Socorro, Portal do Cidadão, Prescrição |
| **Assistência hospitalar** | Internação, Leitos e setores, Centro cirúrgico, Encaminhamentos, Agenda, Agendamentos |
| **Apoio diagnóstico** | Exames, Catálogo de exames, Vacinas, Catálogo de vacinas, Farmácia, Estoque |
| **Vigilância e regulação** | Vigilância (SINAN), Regulação de vagas, Epidemiologia, Integrações RNDS |
| **Gestão** | Relatórios, Relatórios hospitalares, Faturamento (AIH/APAC), Importação CSV, Exportação, Tabelas oficiais |
| **Plataforma** | Autenticação com MFA, login gov.br, Auditoria com hash-chain, Unidades, Usuários, Configurações, Backup, Ferramentas PDF |

### Destaques

**Notificação compulsória automática.** Ao lançar um CID-10 de notificação
obrigatória no prontuário, o sistema gera a ficha SINAN sozinho e a coloca na fila
de vigilância. O profissional não precisa saber de cor quais agravos são
notificáveis.

**Classificação de risco Manchester.** Cinco níveis com as cores oficiais e
tempo-alvo de atendimento. A fila do pronto-socorro ordena por gravidade e, dentro
dela, por tempo de espera.

**Terminologias oficiais.** Consulta a CID-10, RENAME, CBO, SIGTAP e CNES, com
busca por código (prefixo) ou descrição (sem acento). Alimenta os autocompletes
dos formulários.

**Interoperabilidade FHIR R4.** Envio de `Patient`, `Encounter` e `Observation` à
Rede Nacional de Dados em Saúde. O despacho é simulado neste ambiente — o envio
real exige certificado ICP-Brasil e credenciais do DATASUS, e está isolado numa
única função para a troca ser trivial.

---

## Design system

Padrão Digital de Governo (**DSGov / gov.br**): barra institucional gov.br, azul
`#1351B4`, amarelo `#FFCD07`, sidebar clara com grupos colapsáveis e ícones SVG.

Os tokens em `static/css/dsgov.css` são o **ponto único de re-skin** — nenhum
componente hardcoda cor. Isso inclui as cores semânticas de estado clínico
(`--status-*`) e de risco Manchester (`--risk-*`).

**Tema claro e escuro**, aplicado antes da primeira pintura para não piscar na
navegação. Os tons médios e fortes não mudam entre temas: as cores oficiais
Manchester e os botões de perigo continuam idênticos.

**Acessibilidade (eMAG / WCAG 2.1 AA)**: skip-link, foco visível em todo controle,
contraste verificado nos dois temas e VLibras.

---

## Segurança e conformidade

- **Isolamento multi-tenant no banco (Row-Level Security)** — o filtro por
  unidade não vive só na aplicação: 15 tabelas carregam política do PostgreSQL
  com `FORCE`, derivada do metadata do ORM. Uma consulta nova que esqueça o
  filtro não enxerga registro de outro município. Falha fechada: sem escopo
  definido, nada é liberado. Dez tabelas ainda não têm a coluna de escopo e
  dependem só do filtro em Python — a lista está no `AGENTS.md`, e
  `flask hardening-check` a confronta com o banco.
- **RBAC granular por permissão** (`recurso:ação`) — 26 permissões e 7 perfis,
  ortogonais ao escopo territorial: a permissão diz *o que* se pode fazer, o
  escopo diz *sobre quais registros*. O backend é a autoridade; o template
  apenas espelha para esconder controles.
- **Verificação em duas etapas (TOTP)** — o segredo só é gravado depois que o
  usuário prova um código válido, então ninguém se tranca fora da própria conta.
- **Login federado gov.br** (OIDC), com simulador explícito quando não há
  credenciais de produção configuradas.
- **Auditoria encadeada por hash** — cada evento carrega o hash do anterior.
  Alterar ou remover uma linha rompe a cadeia, e a verificação aponta onde. Não
  depende de permissão do banco.
- **LGPD** — registro de consentimento, trilha de "quem acessou meu prontuário"
  exposta ao titular no Portal do Cidadão, e exportação de dados auditada.
- **Backup verificado, não presumido** — `flask backup-validar` restaura a cópia
  num schema temporário e compara as contagens com a origem, saindo com erro se
  divergir. Backup que nunca foi restaurado é um arquivo, não um backup.
- **Documentos verificáveis** — cada PDF emitido recebe um código e a impressão
  digital SHA-256 do arquivo, conferíveis publicamente em `/verificar/<código>`
  sem precisar de conta.

---

## Como rodar

```bash
# 1. Clonar
git clone https://github.com/IasminRDS/Prontuario_E2.git
cd Prontuario_E2

# 2. Ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate

# 3. Dependências
pip install -r requirements.txt

# 4. Variáveis de ambiente
copy .env.example .env          # Linux/macOS: cp .env.example .env
#    edite o .env e defina SECRET_KEY

# 5. Banco de dados
flask db upgrade

# 6. Dados de demonstração (opcional)
flask seed

# 7. Subir
python app.py
```

Acesse `http://localhost:5000`.

> `SECRET_KEY` é obrigatória e não tem valor padrão — a aplicação não sobe sem
> ela, de propósito.

---

## Estrutura

```
.
├── app.py                  → fábrica da aplicação e registro dos blueprints
├── config.py               → configuração por ambiente
├── extensions.py           → instâncias únicas das extensões Flask
├── models/                 → um arquivo por agregado (SQLAlchemy)
├── routes/                 → um blueprint por domínio
├── services/               → geração de PDF (prontuário, receituário, atestado,
│                             encaminhamento, sumário de alta)
├── utils/
│   ├── rbac.py             → permissões, perfis e decorators de autorização
│   ├── audit.py            → trilha de auditoria e verificação de integridade
│   ├── nav.py              → navegação lateral, filtrada por permissão
│   └── terminologias.py    → CID-10, RENAME, CBO, SIGTAP, CNES
├── templates/              → Jinja2, todos herdando de base.html
├── static/css/dsgov.css    → design system (tokens + componentes)
└── migrations/             → migrations versionadas (Alembic)
```

---

## Números

| | |
|---|---|
| Módulos (blueprints) | 44 |
| Rotas | 211 |
| Models | 29 arquivos, 42 tabelas |
| Templates | 129 |
| Migrations | 10, exercitadas do zero e em reversa no CI |
| Testes | 186 funções → 279 casos, em 26 arquivos, nos dois bancos |
| Tabelas sob RLS | 15 |
| Permissões RBAC | 26, em 7 perfis |
| Terminologias | 151 CID-10 · 92 RENAME · 17 CBO · 15 SIGTAP · 6 CNES |

Os valores acima saem de contagem sobre o repositório, não de estimativa. Estão
detalhados, com a análise de segurança e o que a verificação empírica achou de
defeito, em [docs/TCC.md](docs/TCC.md) — a monografia que documenta o sistema.
O `.docx` correspondente é gerado por `python scripts/gerar_tcc_docx.py`, e não
editado à mão: monografia editada nos dois lugares diverge nos dois.

---

## Aprendizados

- **Modelagem de domínio complexo:** traduzir um fluxo clínico real em agregados
  que não se contradizem — internar precisa ocupar o leito na mesma transação, e
  dar alta precisa mandar o leito para higienização, nunca direto para livre.
- **Autorização não é decoração:** esconder um botão no template não protege
  nada. A permissão é verificada na rota; o template só espelha a mesma decisão.
- **Auditoria só vale se for atômica:** o evento tem que cair na mesma transação
  da mutação que o originou, senão sobra escrita sem rastro quando algo falha no
  meio.
- **Design system é sobre tokens, não sobre CSS:** com as cores num único lugar,
  o tema escuro saiu como consequência, e não como uma segunda folha de estilo
  para manter em paralelo.

---

## Licença

[MIT](LICENSE) — Iasmin Ribeiro de Souza, 2026.
