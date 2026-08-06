# Governança de Tecnologia da Informação Aplicada à Proteção de Dados em Saúde: Implementação e Avaliação de um Prontuário Eletrônico Multi-Tenant com Isolamento em Banco de Dados, Controle de Acesso e Auditoria Encadeada

**Curso:** Gestão da Tecnologia da Informação
**Natureza:** Trabalho de Conclusão de Curso — estudo de caso aplicado

> **Nota de elaboração.** Este documento descreve exclusivamente mecanismos
> implementados e verificados no artefato produzido. Recursos planejados e não
> implementados estão declarados nas seções 11 (Limitações) e 12 (Trabalhos
> Futuros), nunca apresentados como resultados. Não são apresentadas métricas de
> desempenho sob carga, por não terem sido medidas.

---

## 1. INTRODUÇÃO

A transformação digital no setor de saúde deslocou o prontuário do papel para
sistemas de informação que concentram, em um único repositório, dados de
identificação civil, histórico clínico, prescrições, resultados de exames e
registros de internação. No Sistema Único de Saúde (SUS), essa concentração
ocorre em escala federativa: uma mesma pessoa é atendida em municípios distintos,
por unidades administrativamente independentes, sob gestão estadual e federal
compartilhada.

Esse arranjo produz uma tensão que é, antes de tudo, um problema de gestão. De um
lado, o prontuário longitudinal — a capacidade de recuperar o histórico completo
de um cidadão independentemente de onde foi atendido — é a principal promessa
clínica da informatização. De outro, dado de saúde é classificado como **dado
pessoal sensível** pela Lei nº 13.709/2018 (LGPD, art. 5º, II), exigindo
tratamento restrito, finalidade determinada e rastreabilidade. Ampliar o acesso
melhora o cuidado; restringi-lo protege o titular. A arquitetura do sistema é o
instrumento pelo qual a organização decide onde essa fronteira é traçada — e essa
decisão é de governança, não de programação.

Sob a ótica da Gestão da Tecnologia da Informação, um sistema de prontuário não
se avalia apenas por funcionar. Avalia-se por oferecer **garantias verificáveis**:
que um usuário não alcance dado fora de sua competência, que toda leitura de
informação sensível deixe rastro, que a informação sobreviva a uma falha de
infraestrutura, e que essas propriedades permaneçam válidas após alterações
futuras no código. Sistemas críticos não se sustentam pela intenção de quem os
escreveu, mas por controles que continuem operando quando a equipe mudar.

Este trabalho apresenta a implementação e a avaliação de uma plataforma de
prontuário eletrônico **multi-tenant**, na qual múltiplas unidades de saúde
compartilham a mesma aplicação e a mesma instância de banco de dados, mantendo
isolamento lógico de seus dados. O objeto de análise não é o software em si, mas
o conjunto de controles de governança nele materializados — e, de forma
igualmente relevante, as falhas desses controles identificadas durante a
avaliação e o que elas revelam sobre a diferença entre implementar um mecanismo
de segurança e efetivamente cobrir uma superfície com ele.

---

## 2. PROBLEMA E JUSTIFICATIVA

### 2.1 Problema de pesquisa

> **Como uma arquitetura multi-tenant associada a mecanismos de segurança
> aplicados na camada de dados pode contribuir para aumentar a confiabilidade, a
> proteção e a governança dos dados em sistemas de prontuário eletrônico?**

### 2.2 Justificativa

**Risco de exposição indevida entre unidades.** Em arquitetura multi-tenant, o
isolamento entre inquilinos costuma ser implementado na camada de aplicação, por
meio de filtros adicionados às consultas. O controle depende, então, da
disciplina do desenvolvedor: uma consulta nova que esqueça o filtro expõe dados
de outra unidade sem gerar erro, sem alerta e sem qualquer sinal perceptível ao
usuário. O incidente não se manifesta como falha — manifesta-se como
funcionamento normal com dados a mais. É a classe de risco mais difícil de
detectar por observação operacional.

**Necessidade de segregação sem impedir o cuidado longitudinal.** A segregação
não pode ser total. O cadastro de pacientes é nacional por definição: identificar
que o cidadão atendido hoje já foi atendido em outro município é a razão de
existir do prontuário eletrônico em rede. A governança precisa distinguir o que é
**cadastro** (nacional) do que é **registro clínico** (territorial) — decisão
organizacional que a arquitetura precisa refletir.

**Rastreabilidade como obrigação legal e gerencial.** O art. 37 da LGPD determina
que o controlador mantenha registro das operações de tratamento. Em saúde, essa
exigência tem contrapartida concreta: o titular tem direito de saber quem acessou
seu prontuário. Um registro de auditoria incompleto não é apenas uma lacuna
técnica — é a impossibilidade de responder a um pedido de titular e de apurar
acesso indevido por usuário legítimo, que é o vetor de abuso mais comum em
sistemas de saúde.

**Continuidade operacional.** A indisponibilidade de um prontuário eletrônico tem
efeito clínico direto. Rotina de backup que nunca foi restaurada não constitui
garantia de continuidade: constitui a suposição de uma garantia.

### 2.3 Aderência às áreas de conhecimento

O trabalho articula **Governança de TI** (controles internos, alinhamento entre
TI e objetivos organizacionais, gestão de riscos), **Segurança da Informação**
(confidencialidade, integridade, disponibilidade, autenticidade e não repúdio),
**Gestão de Riscos** (identificação, tratamento e risco residual) e
**Regulamentação e Ética Aplicada** (LGPD e sigilo profissional em saúde).

---

## 3. OBJETIVOS

### 3.1 Objetivo geral

Implementar e avaliar criticamente um sistema de prontuário eletrônico
multi-tenant, analisando de que modo mecanismos de isolamento de dados, controle
de acesso, auditoria e continuidade contribuem para a governança de TI de uma
organização de saúde.

### 3.2 Objetivos específicos

1. Implementar isolamento lógico entre unidades organizacionais aplicado na
   camada de banco de dados, e não exclusivamente na aplicação.
2. Aplicar controle de acesso baseado em perfis, orientado pelo princípio do
   menor privilégio.
3. Desenvolver mecanismo de auditoria com propriedades de detecção de adulteração.
4. Implementar estratégia de backup com **validação automatizada de restauração**.
5. Avaliar a usabilidade da solução por inspeção heurística.
6. Analisar criticamente os limites dos controles implementados, distinguindo
   garantias oferecidas pela aplicação de dependências de infraestrutura.

O objetivo 6 merece registro: a avaliação crítica é resultado do trabalho, não
apenas seu método. A identificação de falhas nos próprios controles projetados
constitui contribuição relevante, conforme discutido na seção 10.3.

---

## 4. FUNDAMENTAÇÃO TEÓRICA

### 4.1 Governança de Tecnologia da Informação

Governança de TI designa o conjunto de estruturas, processos e mecanismos
relacionais que asseguram que a tecnologia sustente os objetivos organizacionais,
com gestão adequada de riscos e uso responsável de recursos. Distingue-se da
gestão de TI por tratar de **decisão e responsabilização** — quem decide, sob
quais critérios, e como se comprova que a decisão foi cumprida.

O modelo COBIT organiza esses elementos em domínios de avaliação, direcionamento,
monitoramento e execução. Dois princípios orientaram este trabalho:

**Controle interno preferencialmente automatizado.** Controle dependente de
conduta humana degrada com rotatividade e pressão operacional. Um controle
implementado como restrição técnica — que impede em vez de recomendar — permanece
ativo independentemente de quem opera o sistema.

**Verificabilidade.** Governança exige evidência. Um controle cuja eficácia não
pode ser demonstrada é indistinguível de sua ausência do ponto de vista de
auditoria. Este princípio motivou a decisão metodológica central do trabalho:
cada controle implementado foi acompanhado de teste automatizado que falha caso o
controle deixe de operar, convertendo a verificação pontual em verificação
contínua.

### 4.2 Segurança da Informação

| Propriedade | Definição operacional | Materialização no sistema |
|---|---|---|
| **Confidencialidade** | Acesso restrito a quem é autorizado | RLS no banco, RBAC por perfil, escopo territorial |
| **Integridade** | Dado não alterado indevidamente | Restrições de integridade referencial, encadeamento por hash da auditoria, validação anterior à persistência |
| **Disponibilidade** | Informação acessível quando necessária | Backup em formato *custom* com validação automatizada de restauração |
| **Autenticidade** | Certeza sobre a origem da ação | Autenticação com hash de senha (*scrypt*), sessão com atributos de segurança, registro de autoria em cada mutação |
| **Não repúdio** | Impossibilidade de negar autoria | Trilha de auditoria com usuário, ação, IP e encadeamento por hash |

A propriedade de **não repúdio** merece qualificação. O encadeamento por hash
torna a trilha *tamper-evident* — adulteração se torna detectável, porque alterar
um registro invalida a cadeia subsequente. Não a torna *tamper-proof*: enquanto o
papel de banco utilizado pela aplicação for proprietário da tabela, ele mantém
capacidade técnica de alterá-la. A distinção é relevante para a análise de risco
residual (seção 11).

### 4.3 Multi-Tenancy

Multi-tenancy designa a arquitetura em que uma única instância de aplicação serve
múltiplos inquilinos com isolamento entre seus dados. As estratégias usuais
apresentam o seguinte quadro comparativo:

| Estratégia | Isolamento | Custo operacional | Consulta entre inquilinos | Adequação ao caso |
|---|---|---|---|---|
| Banco por inquilino | Máximo | Alto — *n* bancos, *n* migrações, *n* backups | Muito custosa | Inadequada: inviabiliza o prontuário longitudinal |
| *Schema* por inquilino | Alto | Médio-alto — *n* schemas por migração | Custosa | Inadequada: mesma limitação, com complexidade adicional |
| **Coluna discriminadora** | Médio, dependente de aplicação | Baixo — um banco, uma migração | Natural | **Adotada** |

A escolha pela coluna discriminadora (`unidade_id`) decorre de um requisito
organizacional, não de conveniência de implementação: o cuidado longitudinal
exige consulta que atravesse unidades de forma controlada. Bancos separados
tornariam essa consulta uma operação de integração entre sistemas.

A fragilidade reconhecida dessa estratégia é a dependência da aplicação para
aplicar o filtro. É precisamente essa fragilidade que o mecanismo descrito em 4.4
se propõe a mitigar.

### 4.4 Row-Level Security (RLS)

O RLS do PostgreSQL permite definir políticas que restringem, por linha, quais
registros uma sessão pode enxergar. A política é avaliada pelo servidor de banco
de dados em toda consulta, independentemente de sua origem.

Do ponto de vista de governança, o RLS transfere o controle de isolamento da
camada onde o erro é provável (aplicação, com dezenas de consultas escritas por
pessoas diferentes ao longo do tempo) para a camada onde a regra é declarada uma
vez e aplicada uniformemente. Trata-se de defesa em profundidade: o filtro da
aplicação permanece, e a política do banco cobre a hipótese de sua ausência.

Quatro condições determinam se o mecanismo constitui proteção efetiva:

1. **`FORCE ROW LEVEL SECURITY`** — o proprietário da tabela ignora políticas por
   padrão. Como a aplicação é proprietária das tabelas, sem `FORCE` as políticas
   existiriam sem efeito.
2. **Falha fechada** — na ausência de escopo definido, a política não libera
   nada. Aplicação que não exibe dado algum é defeito imediatamente perceptível;
   aplicação que exibe dado de todo o território é incidente que pode permanecer
   despercebido indefinidamente.
3. **Escopo reposto por transação** — o escopo é definido com
   `set_config(..., is_local => true)` no início de cada transação, e não no
   estabelecimento da conexão, pois conexões são reutilizadas por *pool* e
   requisições efetuam múltiplas transações.
4. **Cobertura efetiva** — a política protege as tabelas às quais foi aplicada.
   Esta condição, aparentemente trivial, foi a que falhou neste trabalho e é
   analisada na seção 10.3.

### 4.5 Auditoria e rastreabilidade

Trilha de auditoria em sistema de saúde cumpre três funções distintas:
responsabilização individual, atendimento a direito do titular (LGPD, art. 9º) e
apuração de incidentes.

Duas propriedades condicionam sua utilidade. **Completude:** trilha que registra
escritas mas omite leituras não detecta o vetor de abuso mais frequente em saúde
— consulta indevida por profissional autorizado, que não altera nada.
**Integridade:** trilha alterável pelo próprio sistema auditado tem valor
probatório reduzido.

---

## 5. METODOLOGIA

**Natureza:** pesquisa aplicada.
**Objetivos:** exploratória e descritiva.
**Abordagem:** qualitativa.
**Procedimento técnico:** estudo de caso aplicado, com construção de artefato.

### 5.1 Etapas

1. **Levantamento do problema** — análise do contexto federativo do SUS e das
   exigências da LGPD para dados sensíveis.
2. **Análise de requisitos** — identificação dos requisitos funcionais e,
   sobretudo, dos requisitos não funcionais de segurança, rastreabilidade e
   continuidade.
3. **Definição da arquitetura** — escolha da estratégia de multi-tenancy e dos
   mecanismos de controle.
4. **Implementação** — construção incremental com versionamento de esquema por
   migrações.
5. **Testes e verificação empírica** — descrito em 5.2.
6. **Avaliação** — análise crítica dos resultados, com identificação de risco
   residual.

### 5.2 Verificação empírica como método

A etapa de testes adotou premissa metodológica que se mostrou determinante para
os resultados: **a inspeção de código é insuficiente para verificar controles de
segurança.** Adotou-se, em seu lugar, a instrumentação e o exercício efetivo do
sistema.

Concretamente, foram construídos verificadores automatizados que:

- instrumentam o mecanismo de renderização de páginas para registrar acessos a
  variáveis inexistentes, executando em seguida todas as telas do sistema com
  dados reais;
- confrontam cada chamada assíncrona da interface com o mapa de rotas efetivo da
  aplicação;
- confrontam os campos que cada formulário submete com os campos que a rota
  correspondente efetivamente lê;
- geram os documentos em PDF do sistema e extraem seu texto para conferir o
  conteúdo produzido;
- verificam, no catálogo do PostgreSQL, se as políticas de RLS estão
  efetivamente ativas nas tabelas esperadas.

A adoção desse método é justificada pelos resultados: **defeitos com impacto
direto sobre a proteção de dados foram identificados por essa via e não haviam
sido percebidos por revisão de código**, conforme detalhado na seção 9.4.

---

## 6. ARQUITETURA DO SISTEMA

### 6.1 Descrição textual do diagrama arquitetural

O sistema organiza-se em quatro camadas, com o fluxo de uma requisição
percorrendo-as na seguinte ordem:

```
┌──────────────────────────────────────────────────────────────┐
│ 1. USUÁRIO — navegador                                       │
│    Perfis: recepção, enfermagem, medicina, farmácia,         │
│    gestão, administração, operação da plataforma             │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTPS · cookie de sessão
                            │ (HttpOnly, Secure, SameSite=Lax)
┌───────────────────────────▼──────────────────────────────────┐
│ 2. APLICAÇÃO WEB — Flask + Jinja2                            │
│    · Autenticação          · Proteção contra CSRF            │
│    · Cabeçalhos de segurança (CSP, HSTS)                     │
│    · Limitação de tentativas de autenticação                 │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│ 3. CAMADA DE AUTORIZAÇÃO E DOMÍNIO                           │
│    · RBAC por permissão nomeada (recurso:ação)               │
│    · Escopo territorial do usuário                           │
│    · Registro de auditoria na mesma transação da escrita     │
│    · Resolução do escopo uma vez por requisição              │
└───────────────────────────┬──────────────────────────────────┘
                            │ SQLAlchemy · pool de conexões
                            │ set_config(app.nivel, app.unidade_id)
                            │ aplicado no início de CADA transação
┌───────────────────────────▼──────────────────────────────────┐
│ 4. POSTGRESQL                                                │
│    · Políticas de RLS com FORCE em toda tabela com           │
│      unidade_id, derivadas do metadata do ORM                │
│    · Integridade referencial e restrições de unicidade       │
│    · Trilha de auditoria encadeada por hash                  │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Fluxo de uma requisição

1. O navegador envia a requisição com o cookie de sessão.
2. A aplicação valida a sessão e identifica o usuário.
3. O escopo territorial do usuário é resolvido **uma única vez por requisição**,
   antes de qualquer acesso a dados.
4. O decorador de autorização verifica se o perfil possui a permissão nomeada
   exigida pela rota; caso não possua, a requisição é rejeitada.
5. Ao iniciar cada transação de banco, o escopo é publicado na sessão do
   PostgreSQL por meio de `set_config` com escopo local à transação.
6. As consultas são executadas. Além do filtro da aplicação, a política de RLS
   restringe as linhas retornadas.
7. Operações de mutação registram evento de auditoria **na mesma transação** da
   escrita: ou ambas persistem, ou nenhuma persiste.

O item 3 merece justificativa técnica. A resolução do escopo não pode ocorrer
dentro do gatilho de início de transação, pois ler a identidade do usuário
autenticado dispara consulta ao banco, que abre transação, que aciona novamente o
gatilho — recursão. A separação entre *resolver o escopo* (uma vez por
requisição) e *publicá-lo* (a cada transação) é consequência direta dessa
restrição.

### 6.3 Justificativa das escolhas tecnológicas

**PostgreSQL.** Escolhido pelo suporte nativo a Row-Level Security. A decisão é
de governança: o mecanismo permite que a regra de isolamento seja declarada como
política do banco, e não replicada em cada consulta da aplicação. Nenhum outro
componente da arquitetura oferece equivalente.

**Flask.** Adotado por não impor estrutura própria de autorização, o que permitiu
que o controle de acesso fosse projetado explicitamente e permanecesse legível —
requisito relevante em sistema cuja auditabilidade é objetivo declarado. O
contraponto está registrado na seção 11: a ausência de imposição estrutural
permitiu que regra de negócio se acumulasse nas rotas.

**SQLAlchemy.** Além do mapeamento objeto-relacional, o *metadata* do ORM é
utilizado como **fonte de verdade** para determinar quais tabelas devem receber
política de RLS. A lista não é mantida manualmente: deriva da presença da coluna
`unidade_id`. Trata-se de decisão de governança destinada a evitar divergência
entre o modelo de dados e os controles aplicados sobre ele.

---

## 7. IMPLEMENTAÇÃO

### 7.1 Estrutura do sistema

A aplicação organiza-se em módulos por domínio funcional (pacientes, prontuário,
triagem, internação, pronto-socorro, cirurgia, prescrição, exames, encaminhamento
e regulação, imunização, faturamento, vigilância epidemiológica, estoque e
farmácia, auditoria, administração), acompanhados de camadas transversais de
autorização, auditoria, escopo territorial e identidade de pacientes.

### 7.2 Banco de dados

O modelo relacional organiza-se em torno das seguintes entidades centrais:

- **Paciente** — cadastro civil e de contato, com CPF e CNS sob restrição de
  unicidade. **Deliberadamente fora do escopo territorial**, pela razão exposta
  em 2.2: cadastro é nacional.
- **Unidade de Saúde** — inquilino do modelo multi-tenant, vinculado a município
  (código IBGE) e regional de saúde.
- **Município** — hierarquia territorial pelo código IBGE, o mesmo identificador
  utilizado pelo SUS em CNES, SIA/SIH e SINAN.
- **Registros clínicos** — prontuário, atendimento, triagem, internação e
  evolução, atendimento de pronto-socorro, cirurgia, prescrição e seus itens,
  exame, encaminhamento, imunização.
- **Trilha de auditoria** — evento, autor, endereço de origem e encadeamento por
  hash.

**O papel de `unidade_id`.** A coluna identifica a unidade proprietária do
registro e é simultaneamente o critério do filtro da aplicação e o critério da
política de RLS. A hierarquia territorial permite que o escopo seja avaliado em
cinco níveis — unidade, município, regional, estado e sistema —, resolvendo-se os
níveis superiores por consulta à hierarquia de unidades.

**Chave territorial por código IBGE.** Campos de texto livre para município e
unidade federativa não agregam de forma confiável: uma mesma localidade grafada
de três formas produz três agrupamentos distintos em qualquer relatório. A
adoção do código IBGE como chave, com validação dos dois primeiros dígitos contra
a unidade federativa declarada, é decisão de **qualidade de dado** com efeito
direto sobre a confiabilidade da informação gerencial.

### 7.3 Controle de acesso

O modelo combina três dimensões independentes:

**Autenticação.** Senha armazenada como hash (*scrypt*), com limitação de
tentativas por janela temporal e suporte a segundo fator.

**Autorização por permissão nomeada.** Cada rota declara a permissão exigida no
formato `recurso:ação`. Perfis recebem conjuntos de permissões. A interface
oculta controles para os quais o usuário não possui permissão, mas **a decisão é
sempre do servidor** — a interface apenas reflete o que o servidor autoriza.

**Escopo territorial.** Ortogonal à permissão: define *sobre quais registros* a
permissão se aplica.

A distinção entre as duas últimas dimensões é essencial ao princípio do menor
privilégio. Um profissional de medicina possui permissão de leitura clínica em
todo o sistema; o escopo territorial determina de quais unidades. Confundir as
dimensões produz precisamente a falha analisada em 9.4.4.

**Perfis implementados:** operação da plataforma (único autorizado a atravessar o
isolamento entre hospitais), administração de hospital, medicina, enfermagem,
farmácia, recepção e gestão.

### 7.4 Auditoria

Cada evento registra tabela, identificador do registro, ação, descrição, autor,
endereço de origem e instante. O evento é gravado **na mesma transação** da
mutação que o originou, garantindo atomicidade entre o fato e seu registro.

**Encadeamento por hash.** Cada registro armazena o hash do registro anterior e o
hash de seu próprio conteúdo, formando cadeia. A alteração de um registro
invalida todos os subsequentes, tornando a adulteração detectável por verificação
da cadeia.

**Transparência ao titular.** Módulo específico apresenta, para um paciente, o
histórico de acessos ao seu prontuário — atendimento direto ao art. 9º da LGPD.

### 7.5 Backup e recuperação

O backup utiliza `pg_dump` em formato *custom*, que permite compressão e
restauração seletiva. Duas particularidades merecem registro:

**Interação com o RLS.** Com RLS ativo, o `pg_dump` recusa-se a executar sem a
opção `--enable-row-security`, e a recusa é apropriada: sem ela, produziria um
dump silenciosamente parcial. A rotina estabelece escopo de sistema para a
conexão de backup, garantindo completude.

**Validação automatizada da restauração.** Foi implementado o comando
`flask backup-validar`, que restaura o arquivo em *schema* temporário, compara as
contagens de registros com a origem, remove o *schema* e encerra com código de
erro em caso de divergência — permitindo execução automatizada e alarme
automático.

A restauração ocorre em *schema* e não em banco separado por decisão de segurança:
criar banco exige privilégio `CREATEDB`, que o papel da aplicação não possui e
não deve possuir, enquanto criar *schema* exige apenas privilégio sobre o próprio
banco. O procedimento respeita o princípio do menor privilégio em vez de
requerer sua flexibilização.

---

## 8. SEGURANÇA DA INFORMAÇÃO — ANÁLISE

### 8.1 Matriz de riscos e controles

| Risco | Controle aplicado | Benefício gerencial |
|---|---|---|
| Consulta que omite filtro expõe dados de outra unidade | Política de RLS com `FORCE` no banco, derivada do *metadata* | Reduz dependência da disciplina individual; o controle opera mesmo em código novo |
| Escopo vaza entre requisições por reuso de conexão | `set_config` com escopo local à transação | Elimina classe de falha de difícil reprodução e diagnóstico |
| Escopo não resolvido libera acesso amplo | Política de falha fechada | Erro de configuração torna-se visível imediatamente, em vez de silencioso |
| Usuário acessa funcionalidade além de sua competência | RBAC por permissão nomeada, validado no servidor | Menor privilégio auditável; matriz de permissões documentada |
| Acesso indevido por usuário legítimo | Auditoria de leitura e escrita | Viabiliza apuração e atende direito do titular |
| Adulteração da trilha de auditoria | Encadeamento por hash | Torna adulteração detectável (*tamper-evident*) |
| Perda de dados por falha de infraestrutura | Backup em formato *custom* com validação automatizada | Continuidade verificada, não presumida |
| Dump parcial sob RLS | Escopo de sistema explícito e `--enable-row-security` | Backup completo comprovado por conferência de contagens |
| Interceptação de sessão | Cookie `HttpOnly`, `Secure`, `SameSite`; sessão de duração limitada | Reduz superfície de sequestro de sessão |
| Ataque por força bruta na autenticação | Limitação de tentativas por janela | Mitiga acesso por tentativa exaustiva |
| Configuração de produção aplicada incorretamente | Ambiente exigido explicitamente, sem valor padrão | Configuração inválida impede a inicialização em vez de degradar silenciosamente |
| Divergência entre modelo de dados e controles | Lista de tabelas protegidas derivada do *metadata* | Reduz risco de tabela nova nascer desprotegida |

### 8.2 Fronteira entre garantias da aplicação e dependências de infraestrutura

Distinção metodologicamente relevante para a avaliação:

**Garantido pela aplicação e verificado por teste automatizado:** políticas de RLS
ativas com `FORCE`; escopo publicado a cada transação; autorização por permissão
nomeada em todas as rotas de escrita; auditoria gravada na transação da mutação;
validação de dados antes da persistência; completude e restaurabilidade do
backup.

**Dependente de configuração de infraestrutura, fora do alcance da aplicação:**
imutabilidade efetiva da trilha de auditoria (exige que a tabela pertença a papel
distinto do utilizado pela aplicação); uso de TLS no transporte; gestão de
segredos; política de retenção e custódia de cópias de segurança; segregação de
funções entre administração de banco e operação do sistema.

Esta separação constitui, por si, contribuição de governança: torna explícito
quais controles a organização recebe pronto e quais deve implementar e auditar
por conta própria — informação frequentemente ausente na documentação de sistemas
adquiridos.

---

## 9. TESTES E VALIDAÇÃO

### 9.1 Estratégia

A suíte automatizada compreende **269 testes**, executados sobre PostgreSQL e
sobre SQLite. Dois testes estruturais sustentam a maior parte da proteção contra
regressões: a renderização de todas as rotas de leitura com dados reais, e a
verificação estática de que toda rota nasce com autenticação e, quando efetua
escrita, com autorização declarada.

As migrações de esquema são exercitadas **a partir de banco vazio**, decisão
metodológica necessária: a suíte constrói o esquema diretamente a partir do
modelo, de modo que sua aprovação não demonstra que a sequência de migrações
executa corretamente em uma instalação nova.

### 9.2 Testes funcionais

Cobrem cadastro e consulta de pacientes, fluxos de triagem, internação, cirurgia,
prescrição e encaminhamento, geração de documentos, e as transições de estado dos
registros clínicos. Os testes verificam **os dados efetivamente persistidos**, e
não apenas o código de resposta HTTP — distinção que se revelou determinante
(seção 9.4.5).

### 9.3 Testes de segurança

- Tentativa de acesso a registro de unidade distinta, com expectativa de negação.
- Verificação, no catálogo do PostgreSQL, de que as políticas estão ativas e em
  modo `FORCE` nas tabelas esperadas.
- Verificação de que escopo não resolvido não libera acesso.
- Verificação de que o escopo não persiste entre transações.
- Matriz de perfis por rota.
- Verificação de que rotas de escrita declaram autorização.
- Verificação de ausência de construção dinâmica de SQL por interpolação.

### 9.4 Defeitos identificados e correções aplicadas

Esta seção apresenta os achados da avaliação. Sua inclusão é deliberada: em
governança, a capacidade de detectar falhas nos próprios controles é evidência de
maturidade mais significativa que a ausência de relato de falhas.

#### 9.4.1 Cobertura incompleta do isolamento no banco de dados

**Achado.** A documentação do sistema afirmava que as políticas de RLS cobriam
toda tabela com escopo territorial e que toda tabela clínica nova nasceria
protegida. A verificação demonstrou que **cinco tabelas clínicas centrais** —
cirurgias, encaminhamentos, atendimentos de pronto-socorro, evoluções de
internação e itens de prescrição — **não possuíam a coluna `unidade_id`** e,
portanto, estavam integralmente fora de qualquer política.

**Análise.** O mecanismo estava corretamente implementado; o alcance é que era
insuficiente. A afirmação da documentação era literalmente verdadeira e
praticamente enganosa: cobria as tabelas que possuíam a coluna, e essas eram
minoria entre as tabelas clínicas. Para as cinco tabelas, a promessa de que "uma
consulta que esqueça o filtro não enxerga registro de outro município" não se
aplicava — o isolamento dependia exclusivamente da aplicação.

**Correção.** Migração que adiciona `unidade_id` às cinco tabelas, com
preenchimento retroativo derivado da entidade-pai (internação, prescrição,
triagem ou unidade de origem, conforme o caso), seguida da aplicação das
políticas. As rotas de criação passaram a preencher a coluna.

**Lição de governança.** Documentação que afirma cobertura sem declarar o recorte
é mais prejudicial que a ausência de documentação, pois induz confiança
indevida. A verificação automatizada da cobertura efetiva, e não da existência do
mecanismo, é o controle apropriado.

#### 9.4.2 Teste de segurança que produzia confiança injustificada

**Achado.** O teste que verificava a ativação das políticas consultava o catálogo
do PostgreSQL **sem restringir o *schema*** inspecionado. O catálogo é global à
instância, de modo que a consulta avaliava as tabelas homônimas do banco de
desenvolvimento em vez das do *schema* de teste.

**Análise.** O teste era aprovado por coincidência. Este achado é, sob a ótica de
governança, mais grave que o anterior: um controle ausente é uma lacuna
conhecida; um controle que reporta conformidade sem verificá-la é uma lacuna que
se apresenta como conformidade.

**Correção.** Restrição explícita do *schema* nas consultas ao catálogo.

#### 9.4.3 Autorização ausente em módulo de transparência ao titular

**Achado.** O módulo de portal do cidadão recuperava o paciente por seu
identificador sem qualquer verificação de escopo, e sua busca percorria a base
nacional. As demais rotas que servem o mesmo dado realizam a verificação.

**Análise.** Autorização inconsistente entre rotas que servem a mesma entidade
constitui a vulnerabilidade em si: é suficiente utilizar a rota que não verifica.
A causa raiz é a replicação da regra de autorização por rota, em vez de sua
centralização.

**Achado adicional.** Durante a correção, identificou-se que a trilha de acessos
apresentada ao titular comparava o identificador do paciente com o identificador
do **registro auditado**, que pertence a outra tabela. O histórico do paciente de
identificador *n* listava acessos ao prontuário de identificador *n* — de outra
pessoa. Em funcionalidade cuja finalidade é a transparência prevista na LGPD, o
defeito produzia simultaneamente informação incorreta e exposição indevida.

**Correção.** Verificação de escopo antes da exibição, busca restrita ao escopo
territorial, e resolução dos identificadores de cada tabela a partir do vínculo
efetivo com o paciente.

#### 9.4.4 Auditoria de leitura não persistida

**Achado.** As rotas de leitura invocavam o registro de auditoria com o
comportamento padrão de não confirmar a transação. Esse comportamento é correto
para escritas — o evento acompanha a transação da mutação — mas em rota de
leitura não existe transação de escrita para carregá-lo, e o evento era
descartado ao final da requisição. Verificou-se a inexistência de qualquer
mecanismo global de confirmação.

**Análise.** O sistema aparentava auditar leituras de prontuário e não as
auditava. O impacto é duplo: descumprimento do art. 37 da LGPD e ausência de
detecção do vetor de abuso mais frequente em sistemas de saúde. Adicionalmente, o
módulo de transparência informaria ao titular, com base na mesma tabela, que não
houve acessos.

**Correção.** Confirmação explícita nas rotas de leitura, acompanhada de teste
que verifica o incremento efetivo de registros na tabela após a requisição.

#### 9.4.5 Confusão entre perfil administrativo e escopo territorial

**Achado.** A função de verificação de acesso autorizava incondicionalmente o
perfil administrativo, cuja definição no próprio sistema é "administrador dentro
do próprio hospital". Na prática, administradores de hospital acessavam registros
de qualquer unidade.

**Análise.** Manifestação concreta da confusão entre as dimensões descritas em
7.3. O código não implementava o modelo que a documentação declarava.

**Correção.** Apenas o perfil de operação da plataforma atravessa o isolamento
entre hospitais. O alcance ampliado, quando necessário, passa a ser concedido
pelo escopo territorial — atributo do cadastro do usuário, sujeito a decisão
administrativa explícita e auditável.

#### 9.4.6 Achados adicionais relevantes para a gestão

- **Funcionalidade clínica integralmente inoperante.** O agendamento de cirurgia
  nunca criou registro algum: a rota construía o objeto com atributos inexistentes
  no modelo, e o tratamento genérico de exceções convertia o erro em mensagem de
  advertência na interface. A resposta HTTP era bem-sucedida. Somente a
  verificação da persistência efetiva revelou o defeito — um teste de código de
  resposta o teria aprovado.
- **Telas apresentando formulário de outro domínio.** Quatro telas apresentavam o
  formulário de funcionalidade distinta, copiado durante a construção e não
  reescrito, resultando em descarte silencioso dos dados informados.
- **Rotina de backup inoperante por localização de dependência.** A rotina
  procurava o utilitário `pg_dump` exclusivamente no diretório padrão de
  instalação, falhando quando o servidor está instalado em outra unidade de
  disco. O defeito só se manifestaria no momento de necessidade do backup.

### 9.5 Testes de backup e restauração

A validação foi executada em duas modalidades: restauração de arquivo contendo
dados reais, aplicada sem qualquer erro; e ciclo completo de cópia e restauração,
com conferência de contagens em doze tabelas, apresentando correspondência exata.
O *schema* temporário foi removido ao final, e os arquivos intermediários — que
contêm o banco em texto legível — foram eliminados.

**Ressalva metodológica.** O ambiente de verificação continha volume reduzido de
dados clínicos. O procedimento está validado; o comportamento sob volume de
produção não foi medido e é declarado como limitação (seção 11).

---

## 10. VALIDAÇÃO DE USABILIDADE

### 10.1 Método

Aplicou-se **inspeção heurística** segundo as dez heurísticas de Nielsen.
Registra-se como limitação metodológica que a inspeção foi conduzida pela própria
equipe de desenvolvimento, sem participação de avaliadores independentes nem de
usuários finais. Os resultados indicam conformidade com princípios de projeto, não
satisfação de usuários reais, cuja verificação é proposta na seção 12.

### 10.2 Avaliação por heurística

**1. Visibilidade do status do sistema.** *Aplicação:* toda operação de mutação
retorna mensagem de confirmação ou de erro; estados clínicos são exibidos como
rótulos com cor semântica, derivados de mapeamento único no modelo, e não de
formatação replicada nas telas. *Avaliação:* verificação de que cada rota de
escrita produz retorno visível. *Exemplo:* o agendamento de cirurgia retorna
confirmação explícita e redireciona para o registro criado; a interface sinaliza
que o acesso foi auditado.

**2. Correspondência com o mundo real.** *Aplicação:* a terminologia reproduz o
vocabulário do SUS — prontuário, triagem com classificação de risco, CNS, CID-10,
AIH, encaminhamento, regulação. As cores de classificação de risco seguem o
protocolo de Manchester. *Avaliação:* conferência dos rótulos contra a
terminologia oficial. *Exemplo:* a tela de triagem apresenta as cores do
protocolo, e não uma escala numérica arbitrária.

**3. Controle e liberdade do usuário.** *Aplicação:* formulários oferecem
cancelamento e retorno; filtros oferecem limpeza; operações irreversíveis exigem
confirmação. *Avaliação:* inspeção da presença de saída em cada formulário.
*Exemplo:* a unificação de cadastros duplicados apresenta ambos lado a lado com o
volume clínico de cada um antes da decisão, e não é executada automaticamente
mesmo com indício máximo de correspondência.

**4. Consistência e padrões.** *Aplicação:* todas as telas herdam estrutura
comum e utilizam o sistema de design institucional (padrão gov.br), com tema
claro e escuro. Estados clínicos seguem convenção única de apresentação.
*Avaliação:* inspeção da aderência ao sistema de design. *Exemplo:* botões,
cartões e tabelas mantêm aparência e comportamento uniformes entre módulos.
*Ressalva:* remanesce formatação direta em parte dos modelos de tela, registrada
como dívida técnica (seção 11).

**5. Prevenção de erros.** *Aplicação:* validação de CPF e CNS; campos
obrigatórios sinalizados; validação no servidor antes da persistência; restrição
de unicidade impedindo duplicidade de documento. *Avaliação:* submissão de
formulários incompletos ou inválidos. *Exemplo:* o agendamento de cirurgia recusa
submissão sem paciente ou sem procedimento, com mensagem específica, em vez de
produzir erro de integridade do banco.

**6. Reconhecimento em vez de memorização.** *Aplicação:* campos de busca com
sugestão apresentam as opções conforme a digitação. *Avaliação:* verificação de
que as sugestões apresentam informação suficiente para desambiguação. *Exemplo:*
a busca de paciente exibe nome, CNS e idade; a de medicamento exibe apresentação
e via de administração, dispensando consulta a documento externo.

**7. Flexibilidade e eficiência.** *Aplicação:* busca disponível em todas as
telas; filtros preservados na URL, permitindo compartilhamento e retorno;
exportação em CSV nos relatórios. *Avaliação:* verificação da preservação dos
filtros. *Exemplo:* relatórios de produção e de pronto-socorro permitem
exportação para tratamento externo.

**8. Design minimalista.** *Aplicação:* indicadores consolidados apresentados em
cartões; listagens restritas às colunas necessárias; estados vazios explícitos.
*Avaliação:* inspeção da densidade informacional. *Exemplo:* a tela de alertas
distingue "nenhuma pendência" de falha de carregamento — condições que, sem
tratamento, produziriam a mesma página em branco.

**9. Auxílio no diagnóstico de erros.** *Aplicação:* mensagens indicam a ação
corretiva; páginas próprias para as condições de erro 403, 404 e 500.
*Avaliação:* verificação de que a mensagem identifica o campo ou a condição.
*Exemplo:* "Informe a especialidade de destino" em lugar de mensagem genérica de
falha.

**10. Ajuda e documentação.** *Aplicação:* textos de apoio nos campos; avisos
sobre o estado operacional de integrações; recursos de acessibilidade — atalho
para o conteúdo principal, indicação visível de foco e tradução para Libras.
*Avaliação:* inspeção da presença de orientação nos formulários complexos.
*Exemplo:* a tela de integração com a rede nacional informa explicitamente quando
opera em modo simulado, evitando a suposição de que documentos foram
efetivamente transmitidos.

---

## 11. RESULTADOS

### 11.1 Resultados técnicos

O isolamento territorial passou a ser aplicado em duas camadas independentes: o
filtro da aplicação e a política do banco de dados. Após as correções descritas
em 9.4.1, a cobertura abrange todas as tabelas clínicas com escopo territorial,
com verificação automatizada da efetividade das políticas.

O controle de acesso combina permissão nomeada e escopo territorial como
dimensões independentes, com decisão no servidor.

A trilha de auditoria registra leituras e escritas, com encadeamento por hash e
verificação automatizada de que os eventos são efetivamente persistidos.

A estratégia de continuidade compreende backup completo sob RLS e validação
automatizada de restauração, executável de forma agendada.

A suíte de 269 testes executa em ambos os sistemas de banco de dados, e a
sequência de migrações foi exercitada a partir de banco vazio.

### 11.2 Resultados gerenciais

**Redução de risco por transferência de camada.** Ao mover o isolamento para o
banco, o controle deixa de depender da disciplina individual em cada consulta
escrita. Trata-se de substituição de controle dependente de conduta por controle
técnico — princípio central de controles internos.

**Confiabilidade da informação gerencial.** A adoção do código IBGE como chave
territorial elimina a fragmentação de agrupamentos por variação de grafia,
condição necessária para que relatórios agregados sejam utilizáveis em decisão.

**Continuidade verificada.** A validação automatizada da restauração converte a
suposição de continuidade em verificação periódica com alarme automático.

**Explicitação do risco residual.** A separação entre garantias da aplicação e
dependências de infraestrutura (seção 8.2) fornece à organização a lista dos
controles que permanecem sob sua responsabilidade.

### 11.3 A avaliação crítica como resultado

Os defeitos relatados em 9.4 constituem resultado do trabalho, e não relato de
insucesso. Três considerações sustentam essa interpretação.

**Todos foram identificados por verificação empírica, e nenhum por inspeção de
código.** Isso valida a premissa metodológica adotada em 5.2 e recomenda-a para
contextos análogos.

**A natureza dos defeitos é instrutiva.** Predominam falhas de *cobertura* e de
*consistência*, não de implementação: mecanismo correto aplicado a conjunto
insuficiente de tabelas; regra de autorização correta ausente em uma rota; teste
correto avaliando o objeto errado. Sistemas de segurança falham menos por
mecanismos mal construídos e mais por lacunas na sua aplicação.

**A relação entre documentação e realidade constitui risco.** A afirmação de
cobertura integral do isolamento, correta apenas sob recorte não declarado, teria
sustentado decisões organizacionais equivocadas. Em governança, documentação é
artefato de controle e está sujeita a verificação como qualquer outro.

---

## 12. LIMITAÇÕES

**Imutabilidade da auditoria depende de configuração externa.** O encadeamento por
hash torna a adulteração detectável, não impossível. A imutabilidade efetiva exige
que a tabela pertença a papel distinto do utilizado pela aplicação, o que demanda
privilégio de superusuário e é ação de administração de banco de dados. Enquanto
não executada, o controle é *tamper-evident*, não *tamper-proof*.

**A coluna de escopo admite valor nulo.** Registros anteriores à migração cuja
unidade não pôde ser derivada permanecem sem escopo definido e, por consequência,
invisíveis a qualquer escopo territorial — comportamento de falha fechada,
deliberado. A restrição de obrigatoriedade da coluna depende da estabilização do
preenchimento retroativo em base de produção e não foi aplicada.

**Ausência de medição sob volume.** Não foram executados testes de carga nem
análise de planos de execução com RLS ativo. Índices compostos incluindo a coluna
de escopo e eventual particionamento não foram avaliados. Não se afirma nada sobre
o desempenho do sistema em escala de produção.

**Regra de negócio acoplada à camada de rotas.** Não há camada de serviço
explícita: parte da lógica de domínio reside nos manipuladores de requisição. A
consequência foi observada empiricamente — a replicação da regra de autorização
por rota produziu a falha descrita em 9.4.3.

**Dependência da correta administração do PostgreSQL.** A eficácia do RLS pressupõe
`FORCE` ativo, papel da aplicação sem `BYPASSRLS` e escopo corretamente publicado.
Erro de administração desativa o controle sem sinal perceptível na aplicação.

**Limitação de escopo do controle de tentativas.** A limitação de requisições está
aplicada apenas às rotas de autenticação. Rotas de dados não são limitadas, de
modo que a enumeração de identificadores permanece possível, ainda que sem
retorno de conteúdo após as correções de autorização.

**Ausência de auditoria externa.** Não foi realizado teste de intrusão nem
avaliação por terceiro independente. As conclusões de segurança limitam-se aos
controles verificados pelos meios descritos.

**Política de retenção de cópias não implementada.** O sistema gera e valida
backups, mas não implementa rotação, versionamento ou custódia externa.

**Validação de usabilidade sem usuários.** Conforme registrado em 10.1.

### 12.1 Trade-offs assumidos

**Desnormalização da coluna de escopo.** A alternativa seria política de RLS com
subconsulta à entidade-pai, evitando redundância. Optou-se pela replicação da
coluna: a política torna-se comparação direta, sem verificação de existência por
linha lida. O custo é a redundância e a necessidade de manter o valor coerente com
o pai. A decisão privilegia previsibilidade de desempenho e uniformidade das
políticas — todas as tabelas protegidas pelo mesmo critério — sobre normalização.
Em modelo com política heterogênea, a exceção tende a ser esquecida na manutenção.

**Cadastro de pacientes fora do escopo territorial.** Decisão que amplia
deliberadamente a superfície de exposição do cadastro civil em favor do cuidado
longitudinal. A mitigação adotada é que o *registro clínico* permanece sob escopo:
localizar que uma pessoa foi atendida em outro município não implica acesso ao que
foi registrado naquele atendimento.

**Isolamento por coluna em vez de banco por inquilino.** Isolamento inferior em
troca de viabilidade operacional e da consulta longitudinal, conforme 4.3.

**Restauração em *schema* em vez de banco separado.** Aproximação menos fiel ao
procedimento de recuperação real, adotada para não exigir a concessão de
privilégio `CREATEDB` ao papel da aplicação.

---

## 13. TRABALHOS FUTUROS

**Segurança e conformidade**
- Transferência da propriedade da tabela de auditoria para papel dedicado, com
  concessão restrita a inserção e leitura.
- Aplicação de obrigatoriedade à coluna de escopo, após estabilização do
  preenchimento retroativo.
- Ampliação dos testes de negação de acesso, cobrindo sistematicamente todas as
  rotas.
- Extensão do controle de tentativas às rotas de dados.
- Evolução do modelo de autorização para incorporar atributos contextuais, além
  do perfil.
- Roteiro automatizado de verificação de configuração do banco (papéis,
  concessões, estado das políticas).

**Operação e continuidade**
- Política de retenção, rotação e custódia externa de cópias de segurança.
- Integração da migração a partir de banco vazio e da validação de restauração ao
  processo de integração contínua.
- Teste automatizado das migrações reversas.
- Monitoramento com alerta sobre falhas de autorização, que constituem indicador
  precoce de tentativa de acesso indevido.

**Desempenho e escala**
- Construção de base de dados sintética em volume representativo.
- Análise de planos de execução com RLS ativo e avaliação de índices compostos.
- Avaliação de particionamento por unidade, se justificado pelo volume.

**Arquitetura**
- Introdução de camada de serviço explícita, com centralização da decisão de
  autorização em ponto único.
- Documentação formal do modelo multi-tenant como especificação versionada.

**Funcionalidade e integração**
- Ampliação da conformidade com o padrão FHIR para interoperabilidade.
- Painéis gerenciais de indicadores assistenciais.
- Avaliação de usabilidade com usuários dos perfis reais.

---

## 14. CONCLUSÃO

Este trabalho apresentou a implementação e a avaliação de um sistema de prontuário
eletrônico multi-tenant, analisando como mecanismos de isolamento de dados,
controle de acesso, auditoria e continuidade se articulam como instrumentos de
governança de Tecnologia da Informação em uma organização de saúde.

Quanto ao problema de pesquisa, verificou-se que a associação entre arquitetura
multi-tenant e controles aplicados na camada de dados contribui efetivamente para
a confiabilidade e a proteção da informação, sob uma condição que a experiência
tornou explícita: **a contribuição decorre da cobertura verificada do mecanismo,
não de sua existência.** O sistema possuía Row-Level Security corretamente
implementado — com `FORCE`, falha fechada e escopo reposto por transação — e ainda
assim mantinha cinco tabelas clínicas centrais integralmente fora de proteção. O
mecanismo estava certo; o alcance, não.

Essa constatação constitui a principal contribuição do trabalho para a Gestão da
Tecnologia da Informação. Há diferença substantiva entre **implementar um controle**
e **cobrir uma superfície com ele**, e essa diferença não é perceptível por
inspeção de código nem por leitura de documentação — ambas, no caso estudado,
indicavam conformidade. Foi necessário instrumentar o sistema, exercitá-lo e
consultar o catálogo do próprio banco de dados para constatar a lacuna.
Decorre daí uma recomendação transferível: controles de segurança devem ser
acompanhados de verificação automatizada de sua **efetividade**, e não apenas de
sua presença.

Os objetivos específicos foram atendidos, com as ressalvas explicitamente
registradas: o isolamento foi implementado e sua cobertura corrigida; o controle
de acesso foi implementado com distinção entre permissão e escopo, corrigindo-se
confusão identificada entre perfil administrativo e alcance territorial; a
auditoria foi implementada com encadeamento por hash e passou a registrar
leituras, permanecendo a imutabilidade efetiva dependente de configuração de
infraestrutura; a estratégia de continuidade foi implementada com validação
automatizada de restauração; e a usabilidade foi avaliada por inspeção
heurística, sem participação de usuários finais.

O trabalho demonstra que decisões tecnológicas — a escolha do sistema gerenciador
de banco de dados pelo suporte a políticas por linha, a adoção de identificador
oficial como chave territorial, a definição de falha fechada como padrão, a
derivação da lista de tabelas protegidas a partir do modelo de dados — não são
decisões meramente técnicas. São decisões de governança, pois determinam quais
garantias a organização pode oferecer sobre os dados sob sua custódia e quais
riscos permanecem sob sua responsabilidade.

Por fim, o trabalho documenta, com igual ênfase, os controles implementados e as
falhas identificadas nos controles projetados. Essa opção é deliberada. Em
sistemas que custodiam dados pessoais sensíveis, a maturidade de governança não
se evidencia pela ausência de relato de falhas, mas pela existência de mecanismos
capazes de detectá-las — e pela disposição institucional de registrá-las.

---

## APÊNDICE A — Relação com as disciplinas do curso

| Disciplina | Aplicação no trabalho |
|---|---|
| **Fundamentos da Tecnologia da Informação** | Compreensão do papel dos sistemas de informação como infraestrutura de processos organizacionais em saúde |
| **Banco de Dados I** | Modelagem relacional, integridade referencial, restrições de unicidade, normalização e sua flexibilização justificada |
| **Banco de Dados II** | Row-Level Security, políticas por linha, papéis e concessões, versionamento de esquema por migrações, backup e restauração |
| **Engenharia de Software I** | Levantamento de requisitos, com ênfase em requisitos não funcionais de segurança e rastreabilidade |
| **Engenharia de Software II** | Estratégia de testes automatizados, verificação empírica, prevenção de regressões, análise de dívida técnica |
| **Desenvolvimento Web I** | Arquitetura de aplicação web, ciclo requisição-resposta, gestão de sessão |
| **Desenvolvimento Web II** | Autenticação e autorização, proteção contra CSRF, cabeçalhos de segurança, acessibilidade digital |
| **Segurança da Informação** | Confidencialidade, integridade, disponibilidade, autenticidade, não repúdio; menor privilégio; defesa em profundidade; modelagem de ameaças |
| **Governança de TI** | Controles internos automatizados, verificabilidade, gestão de risco residual, separação entre garantias da aplicação e dependências de infraestrutura |
| **Gestão de Projetos de TI** | Priorização por impacto, gestão de escopo, decisão sobre dívida técnica |
| **Gestão Empresarial** | Alinhamento entre solução tecnológica e processos assistenciais e administrativos |
| **Regulamentação e Ética Aplicada** | LGPD (arts. 5º, 9º, 11 e 37), sigilo profissional, direito do titular à transparência de acessos |
| **Pesquisa Orientada ao TCC** | Classificação metodológica, estudo de caso aplicado, análise crítica de resultados |

## APÊNDICE B — Glossário

| Termo | Definição |
|---|---|
| **Multi-tenant** | Arquitetura em que uma instância de aplicação atende múltiplos inquilinos com isolamento de dados |
| **Row-Level Security (RLS)** | Mecanismo do PostgreSQL que restringe, por linha, os registros visíveis a uma sessão |
| **FORCE ROW LEVEL SECURITY** | Modalidade que submete também o proprietário da tabela às políticas |
| **Falha fechada** | Princípio segundo o qual a condição de erro resulta em negação de acesso |
| **Tamper-evident** | Propriedade que torna a adulteração detectável, sem necessariamente impedi-la |
| **RBAC** | Controle de acesso baseado em papéis |
| **Escopo territorial** | Abrangência geográfica dos registros acessíveis a um usuário |
| **CNS** | Cartão Nacional de Saúde, identificador do usuário do SUS |
| **CNES** | Cadastro Nacional de Estabelecimentos de Saúde |
| **AIH** | Autorização de Internação Hospitalar |
| **Preenchimento retroativo** | Atribuição de valor a coluna nova em registros preexistentes |
