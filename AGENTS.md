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
flask seed          # catálogos, municípios, leitos e um médico de demonstração
flask criar-admin   # pergunta nome, e-mail e senha
python app.py
```

### Comandos operacionais

```bash
flask backup-validar backups/<arquivo>.dump   # restaura num schema e confere
flask backup-validar --apenas-restore <arq>   # para arquivo antigo
flask hardening-check                         # confere o banco, sai 1 se falhar
flask seed-volume --pacientes 50000           # carga para medir; --limpar remove
flask medir-desempenho --repeticoes 15        # mediana e dispersao, com protocolo
flask auditoria-ancora                        # acrescenta uma âncora ao journal
flask auditoria-ancora --conferir             # confere o journal e a trilha
flask auditoria-ancora --retida <hash>        # valida o prefixo até a âncora guardada fora
flask auditoria-ancora --contra T:ID:HASH     # confere sem ler arquivo desta máquina
flask auditoria-ancora --destino stdout       # imprime a linha, para canalizar a um coletor
flask auditoria-ancora --conferir --idade-maxima 7   # emissão que parou também é falha
```

`backup-validar` restaura o dump num schema temporário e compara as contagens com
a origem — backup que nunca foi restaurado é um arquivo, não um backup. Restaura
em *schema* e não em banco novo porque `CREATE DATABASE` exige `CREATEDB`, que o
papel da aplicação não tem e não deve ter.

`hardening-check` verifica o que a aplicação **não** garante sozinha: `FORCE`
ativo, papel sem `BYPASSRLS`, ausência de escopo pré-definido no ambiente e
propriedade da tabela de auditoria. É a fronteira entre garantia da aplicação e
dependência de infraestrutura, em forma executável.

A oitava verificação é de sinal contrário às outras sete: elas confirmam que
algo está **impedido**, ela confirma que a aplicação **ainda consegue** inserir
na trilha. Existe porque o endurecimento prescrito pelas outras já quebrou o
registro de auditoria — transferir a tabela leva a sequência junto, e `GRANT
INSERT` sem `GRANT USAGE ON SEQUENCE` deixa a trilha parar de crescer sem que
nada acuse. Trilha vazia e sistema sem uso produzem o mesmo relatório.

`auditoria-ancora` fecha o único buraco que o encadeamento por hash não fecha:
**truncar o FIM da trilha é indetectável** — os elos que sobram continuam
consistentes entre si e nada na tabela diz que ela já foi maior. A âncora grava
total, último id e hash final; `--conferir` acusa contagem que encolheu ou hash
divergente. As âncoras vivem num **journal encadeado e só de acréscimo**
(`backups/ancora_auditoria.jsonl`): cada linha referencia o hash da anterior.

Seja preciso sobre o que isso compra, porque é fácil prometer demais:

- **Não** fecha truncar o fim do journal — é a mesma recursão do problema
  original. `tests/test_ancora_journal.py` exercita essa limitação de propósito,
  para que ela continue verdadeira por medição e não por memória.
- **Fecha** reescrever ou remover uma âncora do meio: o elo quebra.
- **Barateia a custódia**, que é o ganho principal. Guardada UMA linha qualquer
  fora do servidor, `--retida <hash>` valida todo o prefixo até ela. A obrigação
  operacional passa de "guarde sempre a última" para "guarde qualquer uma, uma
  vez" — a diferença entre um procedimento que ninguém cumpre e um que sobrevive.
- **Testemunha contra si mesmo** sem nada externo: `--conferir` compara âncoras
  CONSECUTIVAS e acusa trilha que encolheu entre dois checkpoints, ainda que
  hoje ela esteja internamente consistente.

`--destino stdout` imprime só a linha JSON, para canalizar a um coletor que a
aplicação não controle. É a única forma de a regra "quem escreve o log não
guarda a âncora" ser verdade — e o que sobra de limitação é exatamente essa
custódia, que é decisão de governança e que nenhum código deste repositório
resolve. O modo `"a"` na escrita é convenção, não garantia: append-only de
verdade é do sistema de arquivos, e a nona verificação do `hardening-check`
confere isso em vez de supor.

`--idade-maxima DIAS` reprova quando a âncora mais recente envelheceu: um
verificador que parou produz o mesmo silêncio que um sistema íntegro, e sem
checkpoint novo não há o que comparar. Falha de verificação também imprime
**uma linha JSON em stderr**, para um coletor apanhar sem ler a saída humana —
e ela não vai para a trilha de auditoria de propósito, porque registrar ali o
alerta de que a trilha foi adulterada é circular.

### Procedimento de implantação (a metade que não é código)

Três coisas ficam fora do alcance da aplicação por definição — se ela pudesse
aplicá-las, poderia desfazê-las, e então não seriam garantia:

```bash
# 1. Acréscimo de verdade, aplicado por quem administra a máquina.
sudo chattr +a /var/lib/prontuario/backups/ancora_auditoria.jsonl

# 2. Emissão e verificação em papéis distintos, em cron separados.
#    O verificador não precisa de credencial de escrita.
0 2 * * *  flask auditoria-ancora --destino stdout | logger -t ancora -n coletor.interno
0 3 * * *  flask auditoria-ancora --conferir --idade-maxima 2

# 3. Custódia externa: guarde UM hash, uma vez, fora deste servidor.
flask auditoria-ancora --retida <o hash guardado>
```

Verificador rodando na mesma máquina, com as mesmas credenciais de quem emite,
não separou nada — duplicou a autoridade. A separação só significa alguma coisa
quando o destino do passo 2 é um coletor que a aplicação não controla, e é por
isso que `--destino stdout` existe.

`medir-desempenho` mede as consultas críticas **com protocolo**: descarta as
primeiras execuções, que medem a partida e não o regime; repete; e reporta
mediana com amplitude interquartil. Média esconderia uma pausa do coletor de
lixo; valor sem dispersão não diz se a próxima execução o repete. O relatório
acusa quando a dispersão passa de um quarto da mediana — ali o número não deve
ser citado como estável. Rode depois do `seed-volume`: com base pequena o
planejador nem considera índice.

`seed-volume` gera carga sintética marcada como `SINTETICO`. **Não use em
produção.** Existe porque com dezenas de linhas nenhuma decisão de índice é
informada — o planejador nem considera índice em tabela pequena.

## Documentação

`docs/TCC.md` é a monografia e é a **fonte**; `docs/TCC.docx` é gerado dela:

```bash
python scripts/gerar_tcc_docx.py
```

`docs/LEITURAS.pdf` é o levantamento de referências — norma, especificação da
RNDS, literatura, ferramenta e software comparável —, gerado por
`scripts/gerar_leituras_pdf.py`, com o conteúdo no próprio script. Cada item
diz se foi **lido na fonte primária ou se é indicação de busca**: referência
copiada de agregador entra na monografia com data errada, e foi o que quase
aconteceu com o Decreto 12.560/2025.

`docs/sbis_gap_analysis.md` confronta o sistema com os requisitos de certificação
S-RES da SBIS (planilha oficial v5.2), requisito a requisito. Vale a mesma regra
dos números da monografia: **nenhum "Atende" sem o arquivo ou o teste que prova**,
e requisito não verificado aparece como não verificado, nunca como atendido.
Refaça a classificação quando o código mudar — ela é um retrato datado.

`docs/defesa_roteiro.md` é o roteiro de apresentação e defesa — documento de
trabalho, não parte da monografia, e descartável depois da banca. Tem gerador
próprio, e não reaproveita o do TCC porque o destino é outro: ali é ABNT, aqui
é documento de ensaio, com uma página por slide, a fala em corpo maior com
barra lateral e o tempo no cabeçalho.

```bash
python scripts/gerar_defesa_docx.py   # o roteiro, para ensaiar
python scripts/gerar_defesa_pptx.py   # os slides, para projetar
```

Os slides saem do mesmo roteiro, e a divisão é a que importa: **o corpo do
slide é escrito no gerador** — a rubrica "Visual" do roteiro descreve o que
desenhar, e não é texto projetável —, enquanto **a fala vai para as notas do
apresentador**, que é onde ela serve. Nada da fala é projetado na parede.

O sumário e as três listas saem **preenchidos, com paginação medida**, e não
como campo vazio do Word. O motivo é prático: campo de sumário só se preenche
depois que alguém abre o arquivo no Word e aperta F9 — enviado a quem lê no
navegador, no LibreOffice ou já em PDF, ele aparece em branco, e um trabalho
sem sumário se apresenta como rascunho.

Por isso a geração é em **duas passagens**: a primeira reserva o espaço exato
que os índices vão ocupar e é renderizada em PDF pelo LibreOffice; lê-se em que
folha cada título e cada legenda caiu; a segunda escreve os índices como texto,
com os números. A reserva de espaço é o que faz as duas passagens terem a mesma
paginação — sem ela o índice empurraria o texto e invalidaria os números que
ele próprio anuncia. Sem LibreOffice instalado o comando avisa e deixa os
índices em branco, em vez de inventar número.

A numeração segue a NBR 14724: conta desde a folha de rosto (a capa não entra)
e só aparece a partir da introdução. Os índices descontam a capa pela mesma
razão — o número anunciado tem de ser o número impresso na folha.

Nunca edite o `.docx` — a próxima geração descarta a edição, e enquanto isso os
dois arquivos afirmam coisas diferentes. O conversor é próprio porque a ABNT
pede o que um conversor genérico não faz: capa e pré-textuais fora do sumário,
número de página que conta desde a folha de rosto mas só aparece na introdução,
e legenda acima do quadro com fonte abaixo. As convenções do markdown
(`{{sumario}}`, `Quadro — título`, `Fonte: ...`) estão na docstring do script.

**Todo número citado na monografia é medido, não estimado.** Antes de alterar
uma contagem, meça: `pytest` para os testes, `app.url_map` para as rotas,
`db.metadata` para tabelas e colunas. Número herdado de uma versão anterior é
como a afirmação de cobertura de RLS que estava errada — parece verdade porque
já esteve.

O `criar-admin` não é opcional: o `seed` cria apenas um médico, e sem ele
`/admin/`, `/configuracoes/`, `/unidades/` e `/backup/` ficam inalcançáveis. A
senha é pedida pelo terminal com confirmação — não vai por argumento, que
apareceria no histórico do shell e na lista de processos.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

A suíte **não toca o banco de desenvolvimento**: em PostgreSQL cria um schema
próprio (`teste_automatizado_<pid>`) e o destrói ao final, com o `search_path`
preso a ele; em SQLite usa um arquivo temporário, também com o PID no nome. O PID
não é capricho: com nome fixo, duas suítes rodando ao mesmo tempo se destroem, e
o sintoma é `UndefinedTable: não existe a relação "users"` em dezenas de testes
sem relação com a mudança. Para apontar outro banco, use `TEST_DATABASE_URL`.

Dois testes seguram a maior parte dos regressos deste projeto:
`test_integridade_rotas.py` renderiza **toda** rota GET com dado semeado — é o
que pega template lendo atributo inexistente, formulário sem CSRF e link para
endpoint que não existe; e `test_auditoria_estatica.py` garante que rota nova
nasce com `@login_required` e, se escreve, com RBAC. Rota de autosserviço é
exceção e precisa entrar explicitamente na lista `AUTOSSERVICO`.

### Os detectores

Quatro testes caçam a mesma classe de defeito em camadas diferentes: aquele que
**não gera erro**, só deixa de funcionar. Todos nasceram de defeito real.

| Teste | Pega |
|---|---|
| `test_templates_undefined.py` | variável que o template lê e a rota não fornece — o Jinja rende string vazia sem acusar |
| `test_contrato_front_api.py` | `fetch` para rota inexistente e chave que o JavaScript lê e o JSON não traz |
| `test_contrato_formularios.py` | campo que o formulário envia e a rota nunca lê: o usuário preenche e o dado é descartado |
| `test_pdf_conteudo.py` | dado ausente no PDF, mês em inglês e glifo fora da fonte |

Os três últimos carregam uma lista `PENDENCIAS` que **reprova nos dois sentidos**:
achado novo falha, e achado já corrigido que continue na lista também. Sem isso a
lista vira decoração.

`test_rls_negacao.py` faz a pergunta inversa da suíte de RLS: não que a política
exista, mas que ela **negue**. Vai direto ao banco, sem passar pelo filtro em
Python, porque o que se mede é a defesa que resta quando o filtro falha.

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
de outro município. A lista sai do metadata (`utils/rls.tabelas_protegidas`), e a
política alcança **toda tabela que tenha a coluna `unidade_id`** — hoje são 23.

**A frase acima já esteve errada, e o erro custou caro.** Ela dizia que "tabela
clínica nova nasce protegida", o que é falso: nasce protegida a tabela que
NASCER COM A COLUNA. Durante uma auditoria descobriu-se que cinco tabelas
clínicas centrais — cirurgias, encaminhamentos, atendimentos_ps,
evolucoes_internacao e itens_prescricao — não tinham `unidade_id` e estavam
inteiramente fora de qualquer política, enquanto a documentação afirmava
cobertura total. O mecanismo estava certo; o alcance é que não era o anunciado.

Dez tabelas continuaram sem a coluna por mais tempo. **Oito foram cobertas em
`c6b83f2a41d7`**: seis guardam dado identificável de paciente
(`consentimentos_lgpd`, `vacinas_aplicadas`, `envios_rnds`,
`documentos_assinados`, `faturamento_aih`, `faturamento_apac`) e duas eram
filhas de tabelas já protegidas (`itens_prescricao_hosp`, `administracoes_med`)
— depender do pai é exatamente o argumento que a auditoria acima derrubou.

**As que ficam de fora agora precisam de razão escrita.**
`tests/test_rls_negacao.py` mantém `FORA_POR_DECISAO`, que reprova nos dois
sentidos: tabela sem `unidade_id` e sem justificativa falha, e justificativa
para tabela que já ganhou a coluna também. As duas que sobraram desta leva:

- `candidatos_duplicata` — existe para reconciliar a mesma pessoa cadastrada em
  municípios diferentes; escopo territorial destruiria a função. Mesmo motivo
  de `pacientes`.
- `agenda_eventos` — não tem `paciente_id` nem uma única chave estrangeira. Não
  há de onde derivar unidade nem dado de paciente a proteger. A ausência total
  de relações é questão de modelagem, anterior e independente do isolamento.

**Antes de afirmar cobertura, rode `flask hardening-check`** — ele confronta o
banco com o metadata em vez de repetir o que está escrito aqui. Foi ele que
acusou, logo após esta migration, que o banco de desenvolvimento ainda não a
tinha aplicado.

**A coluna nasce NULLABLE e isso tem consequência:** com a política ativa, linha
com `unidade_id` nulo fica invisível para todo escopo, menos SISTEMA. É falha
fechada, que é correto — e significa que registro que o backfill não resolveu
some da tela até alguém resolver. A migration conta e informa quantos são.

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

### Concessão do escopo, e a porta que ela abre

O escopo territorial se edita em `/admin/usuarios/<id>/editar`, num cartão
separado do perfil. A separação é conceitual e não estética: o perfil diz **o
que** a pessoa pode fazer, o escopo diz **sobre quais registros**, e a
autorização é o par. A mesma tela distingue **lotação** (a unidade onde a pessoa
escreve) de **alcance** (o que ela enxerga) — eram a mesma coluna na listagem,
e gestor estadual ficava indistinguível do recepcionista da mesma unidade.

Abrir esse campo numa tela abre uma porta de escalação, e `utils/territorio.py`
é a fechadura: **o território concedido tem de caber dentro do território de
quem concede**. Sem isso, o administrador de uma unidade criaria um usuário com
`nivel_acesso = 'ESTADO'`, entraria com ele e leria o estado inteiro — saindo do
próprio isolamento pela porta de gestão de contas.

A regra é uma só, e **não há tabela de precedência entre os níveis**: um escopo
estadual não cabe numa regional porque um estado não tem regional a comparar, e
a comparação falha sozinha. Escrever a ordem à mão seria uma segunda fonte de
verdade, que envelheceria em silêncio ao surgir um nível novo. O escopo de quem
concede vem de `utils.rls.escopo_do_usuario` — a **mesma** função que o RLS usa,
para que a tela não autorize o que o banco depois trataria de outro jeito.

Três coisas que a mesma porta expunha e que ficaram fechadas junto:

- **o perfil que chegava no POST nunca era conferido.** `perfis_atribuiveis` não
  oferece `SuperAdmin` a quem não é SuperAdmin, e a docstring diz por quê — mas
  a restrição vivia só no `{% for %}` da tela, e um POST montado à mão criava o
  operador da plataforma, que atravessa todo o isolamento pelo perfil;
- **não se edita quem não se poderia criar.** Sem isso a defesa acima era
  contornável sem conceder perfil nenhum: abrir o SuperAdmin existente, definir
  uma senha nova, entrar como ele;
- **`minlength="6"` no campo de senha** contradizia a rota, que exige 8.

`SISTEMA` não é oferecido: `escopo_do_usuario` o rebaixa para `UNIDADE` quando
vem do cadastro, porque é escopo de processo (CLI, migration, backup) e não de
gente. Oferecê-lo seria prometer na tela um valor que o banco ignora.

A tela **declara o próprio recorte** em vez de só mostrar uma lista curta:
política que nega em silêncio é indistinguível de defeito na interface, e quem
vê uma lista vazia pede mais privilégio em vez de entender o limite. Pela mesma
razão, só aparecem municípios, regionais e UFs **com unidade cadastrada** —
escopo sobre território onde a rede não tem unidade não alcança registro nenhum,
e concedê-lo faria quem concedeu acreditar que abriu um acesso que não abre
nada. A lista fica limitada pela pegada da rede, não pelos 5.570 municípios.

**Há uma divergência conhecida e ainda aberta:** `utils/security.py`
(`pode_acessar_paciente`) honra `nivel_acesso == "SISTEMA"` vindo do cadastro, e
`utils/rls.py` o recusa. Em PostgreSQL o RLS decide e o efeito é nulo; em SQLite,
que não tem RLS, o valor liberaria acesso nacional. A tela não concede `SISTEMA`,
então nada novo entra por aqui — mas quem for reconciliar os dois módulos comece
por `tests/conftest.py`, que semeia o admin da suíte com `SISTEMA` de propósito.

## Sinais vitais: número válido e medida impossível

`utils/numeros.py` responde se o que foi digitado **é um número**.
`utils/sinais_vitais.py` responde se o número **pode ser aquela medida**. São
perguntas diferentes, e por muito tempo só a primeira tinha resposta: uma altura
de 172 — metros, que é o que o rótulo do campo pede — convertia sem erro,
gravava, aparecia na tela, entrava no cálculo de IMC e saía num recurso FHIR
`8302-2` bem formado. Documento válido e impossível, aceito pelo transporte e
guardado pelo registro nacional.

**Recusa apenas o impossível, nunca o improvável.** A distinção é clínica: 41,8
°C é raro e verdadeiro, e um sistema que o recusasse obrigaria quem tria a
contornar o prontuário no momento em que ele mais importa. Os limites são
deliberadamente generosos, ancorados em extremos registrados na literatura e não
em faixas de normalidade — e **cada um carrega a justificativa na própria
tabela**, porque limite sem origem é limite que alguém aperta "por segurança" no
ano seguinte, e o aperto só aparece quando recusa a medida de um paciente real.

**O que ele não pega, e não tem como pegar:** peso 7,0 no lugar de 70,0. Sete
quilos é o peso de um lactente, e nenhuma faixa distingue isso sem saber a idade.
`tests/test_plausibilidade_vitais.py` fixa essa limitação por medição, para que a
documentação não passe a prometer uma conferência que não existe.

A tabela é **fonte única**: `min`/`max` do formulário saem dela pelo global Jinja
`limites_vitais`, e o servidor decide por ela. Escrita duas vezes, a metade que
envelheceria seria a do HTML, que nenhum teste lê. A validação do navegador é
conveniência, nunca controle — ela não existe para quem posta sem passar pela
tela. No formulário de prontuário não há `min`/`max` de propósito: os campos são
`text` com `inputmode`, porque `type="number"` devolve vazio quando o valor traz
vírgula decimal, e `min`/`max` em campo de texto é atributo morto que passa a
impressão de validar.

Campo sem faixa precisa de **razão escrita** em `SEM_LIMITE`, e o teste reprova
nos dois sentidos — como `FORA_POR_DECISAO` no RLS. Hoje só `balanco_hidrico`:
é diferença com sinal, legitimamente negativa, e o campo não guarda o período a
que se refere.

A conferência vale nas **quatro portas** que escrevem sinal vital: triagem,
prontuário (formulário), evolução de internação e a interface JSON de
prontuários. A última é a que mais importa e foi a última a ser lembrada — é a
estrutura de 9.4.18 com outro assunto: regra que mora perto de UMA rota é regra
que a próxima rota esquece. E na emissão FHIR (`routes/rnds.py`) a guarda é para
o que **já está gravado**: registro anterior a esta conferência não vira
`Observation`, pelo mesmo motivo que uma pressão ilegível nunca virou.

A expressão que lê "120/80" mora em `utils/sinais_vitais.PRESSAO` e é importada
pelo mapeador FHIR. Escrita nos dois lugares, as duas divergiam no número de
dígitos aceito — um par recusado na entrada seria lido na emissão, ou o
contrário. A **inversão** (80/120) é o único erro que nenhum intervalo isolado
pega: as duas metades estão na faixa e mesmo assim não existe.

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
