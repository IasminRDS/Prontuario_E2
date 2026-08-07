<!--
ELEMENTOS PRÉ-TEXTUAIS

Conforme o Art. 14 do Regulamento de TCC do Curso Superior de Tecnologia em
Gestão da Tecnologia da Informação (IF Baiano — Campus Bom Jesus da Lapa), a
redação segue as regras da ABNT e as "Normas Gerais para Redação da Monografia"
definidas pelo COLEGIADO DO CURSO.

O regulamento NÃO especifica fonte, espaçamento nem margens — delega essa
definição ao colegiado. Solicite esse documento à coordenação antes da formatação
final. Na ausência dele, a referência usual é a ABNT NBR 14724: fonte tamanho 12,
espaçamento 1,5 no texto, margens de 3 cm (esquerda e superior) e 2 cm (direita e
inferior).

CAMPOS A COMPLETAR estão marcados com colchetes.
-->

# INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA BAIANO

## CAMPUS BOM JESUS DA LAPA

### CURSO SUPERIOR DE TECNOLOGIA EM GESTÃO DA TECNOLOGIA DA INFORMAÇÃO

{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}

**IASMIN RIBEIRO DE SOUZA**

{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}

# CONSTRUÇÃO DE UM PRONTUÁRIO ELETRÔNICO MULTI-TENANT

## avaliação empírica de controles de segurança, isolamento de dados e auditoria

{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}

BOM JESUS DA LAPA — BA

....

---

## FOLHA DE ROSTO

{{espaco}}
{{espaco}}
{{espaco}}

**IASMIN RIBEIRO DE SOUZA**

{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}

**CONSTRUÇÃO DE UM PRONTUÁRIO ELETRÔNICO MULTI-TENANT:**
avaliação empírica de controles de segurança, isolamento de dados e auditoria

{{espaco}}
{{espaco}}
{{espaco}}

> Trabalho de Conclusão de Curso apresentado ao Curso Superior de Tecnologia em
> Gestão da Tecnologia da Informação do Instituto Federal de Educação, Ciência e
> Tecnologia Baiano, Campus Bom Jesus da Lapa, como requisito parcial para
> obtenção do título de Tecnólogo em Gestão da Tecnologia da Informação.
>
> Orientador(a): ....

{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}
{{espaco}}

BOM JESUS DA LAPA — BA

....

---

## FOLHA DE APROVAÇÃO

**IASMIN RIBEIRO DE SOUZA**

**CONSTRUÇÃO DE UM PRONTUÁRIO ELETRÔNICO MULTI-TENANT:**
avaliação empírica de controles de segurança, isolamento de dados e auditoria

Trabalho de Conclusão de Curso apresentado como requisito parcial para obtenção do
título de Tecnólogo em Gestão da Tecnologia da Informação pelo Instituto Federal
de Educação, Ciência e Tecnologia Baiano, Campus Bom Jesus da Lapa.

Aprovado em ______ de ____________________ de __________.

**BANCA EXAMINADORA**

&nbsp;

_______________________________________________________________

.... — Presidente

Instituto Federal Baiano — Campus Bom Jesus da Lapa

&nbsp;

_______________________________________________________________

....

&nbsp;

_______________________________________________________________

....

---

## RESUMO

Sistemas de prontuário eletrônico concentram dados pessoais sensíveis e, em redes
públicas de saúde, precisam conciliar duas exigências opostas: permitir o cuidado
longitudinal, que atravessa unidades, e impedir o acesso indevido entre elas. Este
trabalho relata a construção, do início, de uma plataforma de prontuário
eletrônico multi-tenant — na qual múltiplas unidades compartilham a mesma
aplicação e a mesma instância de banco de dados com isolamento lógico dos dados —
e a verificação empírica dos controles de governança nela implementados. A
pesquisa é aplicada, de abordagem qualitativa, conduzida como estudo de caso com
construção de artefato. Adotou-se como premissa metodológica que a
inspeção de código é insuficiente para verificar controles de segurança,
recorrendo-se à instrumentação e ao exercício efetivo do sistema. Foram
implementados isolamento territorial por política de segurança em nível de linha
no banco de dados, controle de acesso por permissão nomeada combinado a escopo
territorial, trilha de auditoria encadeada por resumo criptográfico e rotina de
cópia de segurança com validação automatizada de restauração. A verificação
empírica identificou falhas nos controles projetados pela própria autora, entre elas a
ausência de cobertura da política de isolamento em cinco tabelas clínicas centrais
e um teste de segurança que reportava conformidade sem verificá-la. O desempenho
foi medido com volume sintético de 50 mil pacientes, observando-se redução de
185,9 ms para 0,96 ms na consulta de sugestão de pacientes e de 4.616 ms para
113 ms no relatório de pacientes. Conclui-se que a contribuição do mecanismo de
isolamento decorre de sua cobertura verificada, e não de sua existência, e que
controles de conformidade possuem custo operacional que exige medição —
evidenciado por uma regressão de desempenho introduzida pela própria correção que
passou a registrar as leituras de prontuário.

**Palavras-chave:** Governança de TI. Segurança da Informação. Multi-tenancy.
Row-Level Security. LGPD. Prontuário Eletrônico.

---

## ABSTRACT

Electronic health record systems concentrate sensitive personal data and, in
public health networks, must reconcile two opposing requirements: enabling
longitudinal care across facilities while preventing improper access between them.
This work reports the ground-up construction of a multi-tenant electronic health
record platform — in which multiple facilities share the same application and
database instance with logical data isolation — and the empirical verification of
the governance controls built into it. The research is
applied and qualitative, conducted as a case study with artifact construction. The
methodological premise adopted was that code inspection is insufficient to verify
security controls, resorting instead to instrumentation and effective exercise of
the system. Territorial isolation through row-level security policies in the
database, access control combining named permissions with territorial scope, a
hash-chained audit trail, and a backup routine with automated restore validation
were implemented. Empirical verification identified failures in the author's own
designed controls, including the absence of isolation policy coverage in five
core clinical tables and a security test that reported compliance without
verifying it. Performance was measured with a synthetic volume of 50,000 patients,
showing a reduction from 185.9 ms to 0.96 ms in the patient suggestion query and
from 4,616 ms to 113 ms in the patient report. It is concluded that the
contribution of the isolation mechanism derives from its verified coverage rather
than its existence, and that compliance controls carry an operational cost
requiring measurement — evidenced by a performance regression introduced by the
very correction that began recording record readings.

**Keywords:** IT Governance. Information Security. Multi-tenancy. Row-Level
Security. Data Protection. Electronic Health Record.

---

## LISTA DE ABREVIATURAS E SIGLAS

| Sigla | Significado |
|---|---|
| ABNT | Associação Brasileira de Normas Técnicas |
| AIH | Autorização de Internação Hospitalar |
| CID-10 | Classificação Estatística Internacional de Doenças, 10ª revisão |
| CNES | Cadastro Nacional de Estabelecimentos de Saúde |
| CNS | Cartão Nacional de Saúde |
| COBIT | *Control Objectives for Information and Related Technologies* |
| CSRF | *Cross-Site Request Forgery* |
| FHIR | *Fast Healthcare Interoperability Resources* |
| IBGE | Instituto Brasileiro de Geografia e Estatística |
| LGPD | Lei Geral de Proteção de Dados Pessoais |
| ORM | *Object-Relational Mapping* |
| RBAC | *Role-Based Access Control* |
| RLS | *Row-Level Security* |
| RNDS | Rede Nacional de Dados em Saúde |
| SUS | Sistema Único de Saúde |
| TI | Tecnologia da Informação |

---

## LISTA DE QUADROS

{{lista-de-quadros}}

---

## LISTA DE TABELAS

{{lista-de-tabelas}}

---

## LISTA DE FIGURAS

{{lista-de-figuras}}

---

## SUMÁRIO

{{sumario}}

<!--
O sumário e as três listas acima são CAMPOS do Word: preenchem-se sozinhos ao
abrir o .docx, com a página correta depois da diagramação final. Se o editor
não atualizar na abertura, selecione tudo (Ctrl+A) e tecle F9.

Sumário digitado à mão desatualiza na primeira quebra de página que mudar, e
o erro só aparece na versão impressa.
-->

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

Este trabalho relata a construção de uma plataforma de prontuário eletrônico
**multi-tenant**, na qual múltiplas unidades de saúde compartilham a mesma
aplicação e a mesma instância de banco de dados, mantendo isolamento lógico de
seus dados. A plataforma não preexistia à pesquisa: foi projetada e escrita ao
longo dela, e é esse o motivo pelo qual seus controles puderam ser abertos,
instrumentados e postos à prova em profundidade — condição raramente disponível
quando se avalia sistema de terceiro.

O objeto de análise, porém, não é o software em si, mas o conjunto de controles
de governança nele materializados — e, de forma igualmente relevante, as falhas
desses controles identificadas durante a verificação e o que elas revelam sobre
a diferença entre implementar um mecanismo de segurança e efetivamente cobrir
uma superfície com ele. Que essas falhas estivessem em controles projetados pela
própria autora não é circunstância a atenuar: é o que dá ao relato a franqueza
que uma avaliação externa dificilmente obteria.

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

Construir um sistema de prontuário eletrônico multi-tenant e verificar
empiricamente seus controles, analisando de que modo mecanismos de isolamento de
dados, controle de acesso, auditoria e continuidade contribuem para a governança
de TI de uma organização de saúde.

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
constitui contribuição relevante, conforme discutido na seção 11.4.

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

Quadro — Propriedades da segurança da informação e sua materialização no sistema

| Propriedade | Definição operacional | Materialização no sistema |
|---|---|---|
| **Confidencialidade** | Acesso restrito a quem é autorizado | RLS no banco, RBAC por perfil, escopo territorial |
| **Integridade** | Dado não alterado indevidamente | Restrições de integridade referencial, encadeamento por hash da auditoria, validação anterior à persistência |
| **Disponibilidade** | Informação acessível quando necessária | Backup em formato *custom* com validação automatizada de restauração |
| **Autenticidade** | Certeza sobre a origem da ação | Autenticação com hash de senha (*scrypt*), sessão com atributos de segurança, registro de autoria em cada mutação |
| **Não repúdio** | Impossibilidade de negar autoria | Trilha de auditoria com usuário, ação, IP e encadeamento por hash |

Fonte: elaborado pela autora (2026).

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

Quadro — Estratégias de isolamento em arquitetura multi-tenant

| Estratégia | Isolamento | Custo operacional | Consulta entre inquilinos | Adequação ao caso |
|---|---|---|---|---|
| Banco por inquilino | Máximo | Alto — *n* bancos, *n* migrações, *n* backups | Muito custosa | Inadequada: inviabiliza o prontuário longitudinal |
| *Schema* por inquilino | Alto | Médio-alto — *n* schemas por migração | Custosa | Inadequada: mesma limitação, com complexidade adicional |
| **Coluna discriminadora** | Médio, dependente de aplicação | Baixo — um banco, uma migração | Natural | **Adotada** |

Fonte: elaborado pela autora (2026).

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

Figura — Camadas da arquitetura e ponto de aplicação de cada controle

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

Fonte: elaborado pela autora (2026).

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

A dimensão do artefato é registrada abaixo porque condiciona a leitura dos
resultados: a cobertura de um controle sobre 42 tabelas e 211 rotas é uma
afirmação de natureza diferente da mesma cobertura sobre meia dúzia de telas de
demonstração. Os valores foram obtidos por contagem automatizada sobre o
código-fonte e sobre o *metadata* do mapeador objeto-relacional, e não por
estimativa.

Quadro — Dimensão do artefato construído

| Elemento | Quantidade |
|---|---|
| Módulos funcionais (*blueprints*) | 44 |
| Rotas expostas | 211 — 152 aceitam GET; 103, método de mutação |
| Tabelas no modelo de dados | 42, com 504 colunas e 106 chaves estrangeiras |
| Tabelas sob política de RLS | 15 |
| Migrações de esquema versionadas | 10 |
| Telas (*templates*) | 129 |
| Permissões nomeadas · perfis | 26 · 7 |
| Casos de teste automatizados | 290, em 27 arquivos |

Fonte: elaborado pela autora (2026), por contagem automatizada sobre o repositório.

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

**Retenção e descarte de cópia inválida.** A rotina mantém um número configurável
de cópias, removendo as mais antigas: gerar sem expurgar esgota o armazenamento e,
por consequência, indisponibiliza o próprio banco que se pretendia proteger. Além
disso, arquivo de tamanho implausível é descartado na origem — situação observada
neste trabalho, em que uma falha de autenticação ocorreu **após** a criação do
arquivo, deixando no diretório de cópias um arquivo vazio com nome inteiramente
plausível. Cópia aparente é mais perigosa que cópia ausente, porque só se revela
no momento da recuperação.

A restauração ocorre em *schema* e não em banco separado por decisão de segurança:
criar banco exige privilégio `CREATEDB`, que o papel da aplicação não possui e
não deve possuir, enquanto criar *schema* exige apenas privilégio sobre o próprio
banco. O procedimento respeita o princípio do menor privilégio em vez de
requerer sua flexibilização.

---

## 8. SEGURANÇA DA INFORMAÇÃO — ANÁLISE

### 8.1 Matriz de riscos e controles

Quadro — Matriz de riscos, controles aplicados e benefício gerencial

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

Fonte: elaborado pela autora (2026).

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

Mais relevante que documentá-la é **torná-la verificável**. O comando
`flask hardening-check` confronta o estado real do servidor de banco de dados com
cada pressuposto da coluna direita, e encerra com código de erro quando algum não
se sustenta. A fronteira deixa de ser uma afirmação da documentação e passa a ser
uma verificação executável, apta a integrar rotina periódica. Executado sobre o
ambiente deste trabalho, o comando confirma cinco dos sete pressupostos e acusa os
dois que dependem de privilégio administrativo do banco — resultado que a seção 12
registra como limitação, e que o próprio sistema passa a denunciar em vez de
depender da memória de quem o implantou.

---

## 9. TESTES E VALIDAÇÃO

### 9.1 Estratégia

A suíte automatizada compreende **290 casos de teste**, provenientes de 194
funções distribuídas em 27 arquivos — a diferença corresponde às funções
parametrizadas, executadas uma vez por conjunto de entradas. A suíte é executada
integralmente sobre os dois sistemas gerenciadores de banco de dados
utilizados no projeto: sobre PostgreSQL, com um caso não aplicável; sobre
SQLite, com 33 casos não aplicáveis, correspondentes às verificações de RLS e de
dialeto, que não possuem equivalente naquele sistema.

Dois testes estruturais sustentam a maior parte da proteção contra
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

**Testes de negação.** Um conjunto específico verifica a propriedade inversa: não
que a política exista, mas que ela **recuse**. Cada caso grava um registro
pertencente a uma unidade e tenta alcançá-lo com o escopo de outra, consultando o
banco diretamente, sem passar pelo filtro da aplicação. A escolha é deliberada —
o que se mede é a defesa que resta quando o filtro da aplicação falha; um teste
que passasse pela aplicação provaria os dois controles juntos e não distinguiria
qual deles operou. O conjunto cobre: leitura cruzada entre unidades; a unidade
proprietária enxergando o próprio registro (negar em excesso é falha de
disponibilidade, não sucesso); escopo ausente; nível de acesso inválido; e a
não persistência do escopo entre transações da mesma conexão.

**Verificação da configuração do banco.** Um comando específico
(`flask hardening-check`) confronta o estado do servidor com os pressupostos do
modelo de segurança: políticas ativas, modo `FORCE`, ausência de `BYPASSRLS` e de
privilégio de superusuário no papel da aplicação, ausência de escopo
pré-definido na sessão, e propriedade da tabela de auditoria. O comando encerra
com código de erro quando alguma verificação falha, permitindo execução
periódica.

### 9.4 Defeitos identificados e correções aplicadas

Esta seção apresenta os achados da avaliação. Sua inclusão é deliberada: em
governança, a capacidade de detectar falhas nos próprios controles é evidência de
maturidade mais significativa que a ausência de relato de falhas.

#### 9.4.1 Cobertura incompleta do isolamento no banco de dados

**Achado.** A documentação escrita durante a própria construção do sistema
afirmava que as políticas de RLS cobriam toda tabela com escopo territorial e que
toda tabela clínica nova nasceria protegida. A verificação demonstrou que
**cinco tabelas clínicas centrais** —
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

#### 9.4.7 Regressão de desempenho introduzida por uma correção de conformidade

**Achado.** Após a correção descrita em 9.4.4 — que passou a persistir a
auditoria de leitura —, a listagem de pacientes passou a emitir uma consulta por
registro exibido: vinte consultas para uma página de vinte linhas.

**Análise.** A confirmação da transação expira os objetos carregados na sessão do
mapeador objeto-relacional, comportamento padrão da ferramenta. Como o registro
de auditoria era gravado **depois** de carregar as linhas, a camada de
apresentação encontrava objetos expirados e recarregava cada um individualmente.

O caso é relevante para a discussão de governança por três razões. Primeiro,
demonstra que **controle de conformidade tem custo operacional**, e que esse
custo precisa ser medido — não é suficiente implementar o controle e declarar o
requisito atendido. Segundo, o defeito é invisível sem instrumentação: a página
respondia corretamente, apenas mais devagar, e o volume de consultas só aparece
ao contá-las. Terceiro, a correção adequada **não foi remover o controle**, mas
reordená-lo.

**Correção.** Registrar a leitura antes de materializar as linhas. O evento de
auditoria é idêntico, a exigência legal permanece atendida, e a sessão do mapeador
não é invalidada.

**Generalização.** Toda rota de leitura que confirme a transação de auditoria
após carregar entidades apresenta a mesma latência. O padrão foi documentado no
código para que a correção não seja desfeita por desconhecimento.

#### 9.4.8 Auditoria de escrita ausente ou não atômica na interface programável

**Achado.** A correção descrita em 9.4.4 tratou as rotas de **leitura**. A
verificação posterior das rotas de **escrita** da interface programável (API
JSON) revelou dois defeitos distintos e de sinais opostos, em sete rotas.

Em três rotas de paciente — criação, alteração e desativação — a confirmação da
transação ocorria **antes** do registro de auditoria, que por omissão apenas
anexa o evento à sessão. A transação da escrita já estava encerrada, e o evento
era anexado a uma sessão nova que nada confirmava. O disparo efetivo da rota de
criação retornou código 201, com o paciente persistido e **nenhum** evento de
auditoria gravado.

Em quatro rotas de prontuário — criação, alteração, assinatura e exclusão — o
registro era efetuado por um decorador executado **antes** da função da rota, em
transação própria. Havia rastro, mas ele registrava a *intenção* e não o *fato*:
uma mutação que falhasse depois deixaria na trilha a afirmação de que o
prontuário fora assinado. Adicionalmente, a chamada de auditoria posicionada
após a confirmação constituía código morto — um segundo evento nunca persistido,
cuja presença no código sugeria cobertura.

**Análise.** O primeiro caso é omissão de registro; o segundo é registro sem
atomicidade. Ambos contradizem a garantia declarada nas seções 7.4 e 8.2 deste
trabalho — "o evento é gravado na mesma transação da mutação" —, e a
contradição não era perceptível por leitura do código, pois em ambos os casos
havia uma chamada de auditoria visível na rota.

A gravidade não é uniforme: entre as ações sem rastro atômico estavam a
assinatura e a exclusão de prontuário, que são precisamente as que a trilha
existe para documentar.

**Correção.** O registro passou a ocorrer dentro da transação da mutação, antes
da confirmação, com `flush` intermediário nas criações para que o identificador
do registro criado conste do evento — sem ele, a trilha registrava que algo fora
criado sem dizer o quê. Os decoradores de auditoria anteriores à execução foram
removidos.

**Lição de governança.** É o mesmo achado de 9.4.1 em outro controle: o
mecanismo estava implementado e a documentação afirmava cobertura, mas o alcance
efetivo era menor que o declarado. A recorrência sugere que a verificação de
cobertura não deve ser um exame pontual, e sim um teste permanente — foi o que
se adotou, com um verificador que reprova qualquer rota que registre auditoria
após encerrar a transação.

**Achado colateral.** O exercício da rota de criação em ambos os bancos de dados
revelou que a data de nascimento era repassada ao mapeador como texto, sem
conversão. O driver do PostgreSQL efetua a coerção silenciosamente; o do SQLite
a recusa. A funcionalidade operava em um dos dois sistemas suportados e falhava
no outro, e em nenhum deles a data era validada. É argumento empírico a favor da
decisão metodológica de executar a suíte sobre os dois bancos: um defeito de
portabilidade não se manifesta onde se desenvolve.

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
em 9.4.1, quinze tabelas estão sob política, com verificação automatizada de sua
efetividade. **A cobertura não é total, e essa constatação é resultado.** Dez
tabelas permanecem sem a coluna de escopo e, portanto, fora de qualquer política
— entre elas o registro de consentimento LGPD, a aplicação de imunobiológicos e a
administração de medicamentos. Para essas, o isolamento continua dependendo
apenas do filtro da aplicação. Diferentemente do estado inicial, porém, a lacuna
está identificada, quantificada e detectável por comando, em vez de afirmada como
inexistente pela documentação.

O controle de acesso combina permissão nomeada e escopo territorial como
dimensões independentes, com decisão no servidor.

A trilha de auditoria registra leituras e escritas, com encadeamento por hash e
verificação automatizada de que os eventos são efetivamente persistidos.

A estratégia de continuidade compreende backup completo sob RLS e validação
automatizada de restauração, executável de forma agendada.

A suíte de 290 casos de teste executa sem falhas em ambos os sistemas de banco de
dados. A sequência de dez migrações foi exercitada a partir de banco vazio e
também no sentido inverso, com reversão completa até o estado inicial e
reaplicação.

A coluna de escopo territorial tornou-se obrigatória nas cinco tabelas clínicas
corrigidas, após o preenchimento retroativo ser exercitado com 9.565 registros:
zerada a coluna e reprocessado o preenchimento, nenhuma linha permaneceu sem
unidade resolvida. A migração que aplica a obrigatoriedade não executa a alteração
diretamente — conta os registros irresolúveis e, havendo algum, interrompe com o
diagnóstico da tabela e da quantidade, em vez de falhar com a mensagem genérica do
servidor. A decisão de **não atribuir** unidade arbitrária a registro irresolúvel é
deliberada: registro clínico associado ao município errado é mais danoso que
registro invisível, pois o invisível é notado e o incorreto integra relatórios sem
ser percebido.

### 11.2 Resultados de desempenho

O desempenho foi medido com volume sintético de 50 mil pacientes e cerca de 20 mil
internações, distribuídos de forma desbalanceada entre unidades — a distribuição
uniforme produziria seletividade artificialmente favorável e ocultaria o pior caso,
que é o da unidade de maior movimento.

**Consultas de busca**, sob escopo de unidade, antes e depois da criação de índices
escolhidos a partir dos planos de execução observados:

Tabela — Tempo de execução das consultas de busca antes e depois da indexação

| Consulta | Antes | Depois | Plano após |
|---|---|---|---|
| Listagem paginada de pacientes | 40,1 ms | 0,19 ms | varredura sequencial e ordenação → varredura por índice |
| Contagem para paginação | 16,0 ms | 6,7 ms | varredura sequencial → varredura apenas de índice |
| Sugestão de paciente (`ILIKE`) | 185,9 ms | 0,96 ms | varredura sequencial e ordenação → varredura por índice |

Fonte: dados da pesquisa (2026), medidos com 50 mil pacientes sintéticos.

A sugestão de paciente é o caso determinante: a consulta é disparada a cada
caractere digitado, e executava varredura completa da tabela. Com volume de
demonstração o problema é indetectável — o otimizador do PostgreSQL sequer
considera índice em tabela pequena, pois a varredura integral é menos custosa.
**Sem volume representativo, a decisão de indexação não é informada; é arbitrária.**

**Rotas de relatório**, medidas por número de consultas emitidas e tempo total:

Tabela — Consultas emitidas e tempo total das rotas de relatório

| Rota | Antes | Depois |
|---|---|---|
| Relatório de pacientes | 4.616 ms | 113 ms |
| Ocupação de leitos | 106 consultas · 190 ms | 17 consultas · 78 ms |
| Listagem de pacientes | 44 consultas · 123 ms | 24 consultas · 67 ms |

Fonte: dados da pesquisa (2026), medidos com 50 mil pacientes sintéticos.

As três causas foram distintas e ilustrativas. O relatório de pacientes
materializava a base inteira para renderizar uma tabela — corrigido com paginação,
preservando o carregamento completo apenas na exportação, onde o arquivo é o
produto. A ocupação de leitos invocava, dentro de um laço, propriedades do modelo
que emitiam uma contagem cada — substituídas por uma única consulta agregada. A
listagem de pacientes é o caso analisado em 9.4.7, em que a própria correção de
conformidade introduziu a regressão.

Registre-se que **não foi criado índice onde a medição não o justificou**: as
consultas sobre internações já resolviam por varredura de índice, e um índice sem
consulta que o utilize representa custo de escrita e armazenamento sem retorno.

### 11.3 Resultados gerenciais

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

### 11.4 A avaliação crítica como resultado

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
não executada, o controle é *tamper-evident*, não *tamper-proof*. A pendência é
detectada automaticamente pela verificação de configuração descrita em 8.2, de
modo que permanece visível em vez de esquecida.

**Medição limitada a volume sintético.** Os planos de execução foram analisados
com 50 mil pacientes gerados artificialmente. O comportamento sob a distribuição
real de uma rede de saúde — sazonalidade, concentração por especialidade,
crescimento da trilha de auditoria ao longo de anos — não foi observado.
Particionamento por unidade não foi avaliado, por ausência de evidência que o
justifique no volume medido.

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
- Ampliação dos testes de negação de acesso, hoje concentrados na camada de
  dados, para cobrir sistematicamente cada rota da aplicação.
- Extensão do controle de tentativas às rotas de dados, hoje limitado à
  autenticação.
- Evolução do modelo de autorização para incorporar atributos contextuais, além
  do perfil.

**Operação e continuidade**
- Custódia externa das cópias de segurança: a retenção e a rotação foram
  implementadas, mas as cópias permanecem no mesmo servidor que protegem.
- Agregação e alerta sobre as negações de autorização já registradas em log —
  o registro existe; o monitoramento que o consome é infraestrutura.

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

Este trabalho relatou a construção de um sistema de prontuário eletrônico
multi-tenant e a verificação empírica de seus controles, analisando como
mecanismos de isolamento de dados, controle de acesso, auditoria e continuidade
se articulam como instrumentos de governança de Tecnologia da Informação em uma
organização de saúde.

Quanto ao problema de pesquisa, verificou-se que a associação entre arquitetura
multi-tenant e controles aplicados na camada de dados contribui efetivamente para
a confiabilidade e a proteção da informação, sob uma condição que a experiência
tornou explícita: **a contribuição decorre da cobertura verificada do mecanismo,
não de sua existência.** O sistema construído nesta pesquisa possuía Row-Level
Security corretamente implementado — com `FORCE`, falha fechada e escopo reposto
por transação — e ainda assim mantinha cinco tabelas clínicas centrais
integralmente fora de proteção. O mecanismo estava certo; o alcance, não.

Um segundo achado, de natureza distinta, reforça a mesma tese por outro caminho.
A correção que passou a registrar as leituras de prontuário — exigência do art. 37
da LGPD — introduziu uma regressão de desempenho, por invalidar a sessão do
mapeador objeto-relacional no momento em que confirmava a transação. O controle
estava correto e a exigência legal, atendida; o custo operacional é que não havia
sido medido. A correção adequada não foi remover o controle, mas reordená-lo.
**Controle de conformidade tem custo, e o custo precisa ser medido com o mesmo
rigor com que se verifica a conformidade.**

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
registradas: o isolamento foi implementado e sua cobertura ampliada e
quantificada, ainda que não integral; o controle
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

## REFERÊNCIAS

<!--
ATENÇÃO — LEIA ANTES DE ENTREGAR.

Esta lista contém as obras e normas efetivamente MENCIONADAS no texto. Referência
é declaração de que a fonte foi CONSULTADA: cite apenas o que você leu, e remova
o que não leu, ajustando o texto que a mencionava.

Duas verificações obrigatórias:

1. CONFIRME A EDIÇÃO E O ANO de cada obra contra o exemplar que você consultou.
   Editora, edição e ano mudam entre tiragens, e referência com dado errado é
   apontada em banca.
2. AS NORMAS DA ABNT SÃO REVISADAS. Confirme na Biblioteca do campus se as
   versões listadas continuam vigentes.

A formatação abaixo segue a ABNT NBR 6023. Se as "Normas Gerais para Redação da
Monografia" do colegiado divergirem, elas prevalecem (Art. 14 do Regulamento).
-->

### Normas técnicas

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6023**: informação e
documentação: referências: elaboração. Rio de Janeiro: ABNT, 2018.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6028**: informação e
documentação: resumo, resenha e recensão: apresentação. Rio de Janeiro: ABNT,
2021.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 14724**: informação e
documentação: trabalhos acadêmicos: apresentação. Rio de Janeiro: ABNT, 2011.

### Legislação e normas oficiais

BRASIL. **Lei nº 13.709, de 14 de agosto de 2018**. Lei Geral de Proteção de
Dados Pessoais (LGPD). Brasília, DF: Presidência da República, 2018. Disponível
em: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm.
Acesso em: ....

BRASIL. **Decreto nº 8.727, de 28 de abril de 2016**. Dispõe sobre o uso do nome
social e o reconhecimento da identidade de gênero de pessoas travestis e
transexuais no âmbito da administração pública federal direta, autárquica e
fundacional. Brasília, DF: Presidência da República, 2016. Disponível em:
https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/decreto/d8727.htm.
Acesso em: ....

BRASIL. Ministério da Saúde. **Rede Nacional de Dados em Saúde (RNDS)**.
Brasília, DF: Ministério da Saúde, ..... Disponível em:
https://www.gov.br/saude/pt-br/composicao/seidigi/rnds. Acesso em: ....

CONSELHO FEDERAL DE MEDICINA. **Resolução CFM nº 1.821/2007**. Aprova as normas
técnicas concernentes à digitalização e uso dos sistemas informatizados para a
guarda e manuseio dos documentos dos prontuários dos pacientes. Brasília, DF:
CFM, 2007.

### Governança e segurança da informação

ISACA. **COBIT 2019 framework**: governance and management objectives. Schaumburg:
ISACA, 2018.

SALTZER, Jerome H.; SCHROEDER, Michael D. The protection of information in
computer systems. **Proceedings of the IEEE**, v. 63, n. 9, p. 1278-1308, 1975.

<!--
Saltzer e Schroeder é a origem do princípio de "fail-safe defaults" (padrões que
falham fechado), citado nas seções 4.4 e 8.1. É referência clássica e ainda
usada; vale a leitura da seção "Design Principles", que é curta.
-->

### Usabilidade

NIELSEN, Jakob. **Usability engineering**. San Francisco: Morgan Kaufmann, 1993.

NIELSEN, Jakob. **10 usability heuristics for user interface design**. Nielsen
Norman Group, 1994. Disponível em:
https://www.nngroup.com/articles/ten-usability-heuristics/. Acesso em: ....

### Documentação técnica

THE POSTGRESQL GLOBAL DEVELOPMENT GROUP. **PostgreSQL documentation**: row
security policies. [S. l.]: PostgreSQL, ..... Disponível em:
https://www.postgresql.org/docs/current/ddl-rowsecurity.html. Acesso em: ....

<!--
SUGESTÕES DE LEITURA COMPLEMENTAR — não incluídas na lista acima porque só devem
entrar se você efetivamente consultá-las:

- ABNT NBR ISO/IEC 27001 e 27002, para fundamentar a seção 4.2 (Segurança da
  Informação) em norma, e não apenas em definição operacional.
- ABNT NBR ISO/IEC 38500, sobre governança de TI, complementar ao COBIT.
- Literatura sobre multi-tenancy: procure artigos revisados por pares sobre
  "multi-tenant data architecture", que dão respaldo à comparação da seção 4.3.
- Trabalhos sobre prontuário eletrônico no SUS, para situar o contexto nacional
  da seção 1 — busque no repositório da CAPES ou na SciELO.

A seção 4 é a que mais se beneficia de referências: hoje ela apresenta conceitos
com definição própria, e uma banca costuma cobrar ancoragem bibliográfica.
-->

---

## APÊNDICE A — Relação com as disciplinas do curso

Quadro — Correspondência entre as disciplinas do curso e o trabalho

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

Fonte: elaborado pela autora (2026).

## APÊNDICE B — Glossário

Quadro — Glossário dos termos técnicos empregados

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

Fonte: elaborado pela autora (2026).
