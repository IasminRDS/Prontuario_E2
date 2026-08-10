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
ausência de cobertura da política de isolamento em cinco tabelas clínicas centrais,
um teste de segurança que reportava conformidade sem verificá-la e um verificador
afetado pelo mesmo defeito que se destinava a detectar, cuja correção mais que
dobrou o número de achados. O desempenho
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
core clinical tables, a security test that reported compliance without
verifying it, and a detector affected by the very defect it was built to find,
whose correction more than doubled the number of findings.
Performance was measured with a synthetic volume of 50,000 patients,
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
pessoal sensível** pela Lei nº 13.709/2018 (BRASIL, 2018, art. 5º, II), exigindo
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
usuário. O risco é reconhecido na literatura da área: Kabbedijk *et al.* (2015)
registram que o compartilhamento de uma mesma instância por organizações
distintas eleva a possibilidade de dados serem **acidentalmente consultados pelo
inquilino errado**. O incidente não se manifesta como falha — manifesta-se como
funcionamento normal com dados a mais. É a classe de risco mais difícil de
detectar por observação operacional.

**Necessidade de segregação sem impedir o cuidado longitudinal.** A segregação
não pode ser total. O cadastro de pacientes é nacional por definição: identificar
que o cidadão atendido hoje já foi atendido em outro município é a razão de
existir do prontuário eletrônico em rede. A governança precisa distinguir o que é
**cadastro** (nacional) do que é **registro clínico** (territorial) — decisão
organizacional que a arquitetura precisa refletir.

**Rastreabilidade como obrigação legal e gerencial.** O art. 37 da LGPD
(BRASIL, 2018) determina
que o controlador mantenha registro das operações de tratamento. Em saúde, essa
exigência tem contrapartida concreta: o titular tem direito de saber quem acessou
seu prontuário. Um registro de auditoria incompleto não é apenas uma lacuna
técnica — é a impossibilidade de responder a um pedido de titular e de apurar
acesso indevido por usuário legítimo, que é o vetor de abuso mais comum em
sistemas de saúde.

A exigência não é recente nem exclusiva da proteção de dados pessoais. A
Resolução CFM nº 1.821/2007 (CONSELHO FEDERAL DE MEDICINA, 2007), ao aprovar as
normas técnicas para guarda e manuseio de documento eletrônico em saúde, já
condicionava a substituição do prontuário em papel a requisitos de autenticidade
e rastreabilidade do registro. A convergência é relevante para o argumento deste
trabalho: a obrigação de auditar o acesso ao prontuário precede a LGPD e chega
por duas vias normativas independentes — a regulação profissional e a proteção
de dados —, o que a torna requisito de projeto e não decisão de conveniência.

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

<!--
ANCORAGEM BIBLIOGRÁFICA — ESTADO ATUAL

A NBR 10520 exige a citação no texto, e a NBR 6023 pressupõe que a lista
corresponda ao que foi citado. Lista sem chamada no texto sugere bibliografia
montada e não usada; é das primeiras coisas que uma banca confere.

ANCORADO E VERIFICADO NA FONTE:
  1, 2.2, 4.5  artigos da LGPD ...................... (BRASIL, 2018)
  2.2   consulta acidental de outro inquilino ....... Kabbedijk et al. (2015, p. 20)
  2.2   auditoria anterior à LGPD .................. (CFM, 2007)
  4.1   distinção governança x gestão .............. (ISACA, 2018)
  4.1   estruturas/processos/mecanismos relacionais  Van Grembergen et al. (2004)
  4.2   propriedades da segurança .................. ISO/IEC 27000:2018, itens 3.6-3.48
  4.3   definição de multi-tenancy ................. Kabbedijk et al. (2015, p. 17)
  4.3   as três estratégias de isolamento .......... Chong, Carraro e Wolter (2006)
  4.3   expectativa do setor de saúde .............. Chong et al. (2006, p. 4)
  4.3   testes de isolamento como agenda ........... Kabbedijk et al. (2015, p. 20)
  4.4   falha fechada / fail-safe defaults ......... Saltzer e Schroeder (1975)
  4.5   finalidades e integridade dos registros .... Kent e Souppaya (2006)
  7.2   nome social ................................ (BRASIL, 2016)
  10.1  dez heurísticas ............................ Nielsen (1994)

CUIDADOS QUE NÃO PODEM SE PERDER NUMA REVISÃO FUTURA:
  - 4.1: "estruturas, processos e mecanismos relacionais" é o modelo de
    IMPLANTAÇÃO da governança, NÃO a definição dela. Foi assim que a atribuição
    saiu errada da primeira vez. Não funda as duas frases numa só.
  - 4.3: a frase sobre gestão de registros médicos é sobre o que CLIENTES
    exigem, não sobre exigência técnica. Não a cite como recomendação.
  - 4.3: a chamada por testes de isolamento (p. 20) vem da perspectiva
    INDUSTRIAL do estudo, não do corpus acadêmico. Não escreva "a literatura
    acadêmica aponta".
  - 4.5: a afirmação de que a consulta indevida seria "o vetor mais frequente"
    FOI REMOVIDA. Os dados do setor oscilam demais entre anos para sustentá-la,
    e o argumento é lógico e não estatístico. Não reintroduza o superlativo.

AINDA SEM FONTE:
  1  O contexto do prontuário eletrônico no SUS não cita literatura nacional.
     É onde a banca espera SciELO ou repositório da CAPES.

ACESSO:
  ISO/IEC 27000 é gratuita (iso.org/standard/73906.html); 27001 e 27002 são
  pagas e NÃO são citadas. NIST SP 800-92 é gratuita. Não cite tradução ABNT
  das normas ISO sem tê-la aberto.

REFERÊNCIAS ÓRFÃS — resolvidas: Decreto 8.727/2016 foi ancorado em 7.2 e a
Resolução CFM 1.821/2007 em 2.2. Permanecem as NBR 6023/6028/14724, que são
normas de formatação DESTE documento e não fontes do argumento; o usual é não
listá-las como referência.
-->

### 4.1 Governança de Tecnologia da Informação

Governança de tecnologia da informação trata de assegurar que a tecnologia
sustente os objetivos organizacionais, com gestão adequada de riscos e uso
responsável de recursos. Distingue-se da **gestão** de TI por ocupar-se de
decisão e responsabilização — quem decide, sob quais critérios, e como se
comprova que a decisão foi cumprida —, enquanto a gestão se ocupa de planejar,
construir, executar e monitorar as atividades que realizam a decisão tomada. O
modelo COBIT organiza esses elementos em domínios de avaliação, direcionamento,
monitoramento e execução (ISACA, 2018).

Definida a distinção, cabe perguntar por quais meios a governança se materializa.
Van Grembergen, De Haes e Guldentops (2004) propõem que ela seja **implantada**
por meio da combinação de três tipos de mecanismo: **estruturas** (órgãos e
papéis de decisão), **processos** (formalização das decisões e do monitoramento)
e **mecanismos relacionais** (participação e colaboração entre as áreas de
negócio e de tecnologia). A distinção entre definir governança e enumerar seus
mecanismos de implantação não é retórica: o presente trabalho atua sobre o
segundo tipo, os processos, ao converter decisões de controle em verificações
executáveis.

Dois princípios orientaram este trabalho:

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

A norma ISO/IEC 27000:2018 define segurança da informação como a **preservação da
confidencialidade, da integridade e da disponibilidade** da informação, e
acrescenta, em nota, que outras propriedades — entre elas autenticidade,
responsabilização (*accountability*) e não repúdio — podem também estar
envolvidas (item 3.28). A hierarquia é deliberada na norma e é preservada aqui,
com uma escolha que convém explicitar: neste trabalho, autenticidade e não
repúdio foram tratadas no mesmo nível das três primeiras, porque em prontuário
eletrônico a **autoria do registro clínico** não é atributo acessório. Quem
prescreveu, quem classificou o risco, quem consultou o prontuário de um cidadão
— essas perguntas constituem o objeto da regulação profissional e da proteção de
dados, e não uma qualidade desejável do sistema.

As definições abaixo são as da norma; a terceira coluna registra por qual
mecanismo cada propriedade se realiza neste sistema.

Quadro — Propriedades da segurança da informação e sua materialização no sistema

| Propriedade | Definição (ISO/IEC 27000:2018) | Materialização no sistema |
|---|---|---|
| **Confidencialidade** (3.10) | informação não disponibilizada nem revelada a indivíduos, entidades ou processos não autorizados | RLS no banco, RBAC por permissão nomeada, escopo territorial |
| **Integridade** (3.36) | propriedade de exatidão e completude | Restrições de integridade referencial, encadeamento por hash da auditoria, validação anterior à persistência |
| **Disponibilidade** (3.7) | propriedade de ser acessível e utilizável sob demanda por entidade autorizada | Backup em formato *custom* com validação automatizada de restauração |
| **Autenticidade** (3.6) | propriedade de que uma entidade é o que afirma ser | Autenticação com hash de senha (*scrypt*), sessão com atributos de segurança, verificação em duas etapas |
| **Responsabilização** | propriedade adicional prevista na nota ao item 3.28 | Registro de autoria, ação, endereço de origem e instante em cada mutação clínica |
| **Não repúdio** (3.48) | capacidade de **provar** a ocorrência de um evento ou ação e suas entidades de origem | Trilha de auditoria encadeada por hash, com ancoragem externa dos retratos |

A definição normativa de não repúdio impõe um critério mais exigente do que a
formulação corrente de "impossibilidade de negar autoria": a norma requer a
capacidade de **provar**. É contra esse critério, e não contra uma noção
intuitiva, que a trilha implementada neste trabalho é avaliada — e a avaliação
resulta em atendimento parcial, analisado ao final desta seção e retomado na
seção 12.

A propriedade de **não repúdio** merece qualificação em dois níveis. O
encadeamento por resumo criptográfico torna a trilha *tamper-evident*:
adulteração se torna detectável, porque alterar um registro invalida a cadeia
subsequente. Isso não a tornaria *tamper-proof* enquanto o papel de banco
utilizado pela aplicação fosse proprietário da tabela — condição corrigida neste
trabalho, com a transferência da propriedade e a revogação das permissões de
alteração e exclusão, verificadas por comando.

Resta um limite do mecanismo, e não da configuração: o encadeamento detecta
alteração e remoção intermediária, mas **não detecta a remoção dos registros
finais**, que deixa a cadeia remanescente internamente consistente. A distinção
importa porque o truncamento do fim é justamente o que serve a quem pretende
ocultar a própria ação recente. A mitigação — ancoragem externa do resumo do
último elo — foi implementada e é discutida na seção 12, onde se argumenta que o
que resta de limitação é a custódia da âncora, não o mecanismo.

Confrontado o resultado com o item 3.48 da norma, o atendimento é **parcial** e
convém dizê-lo com precisão: o sistema torna a adulteração *detectável* por quem
examine a trilha, mas não produz *prova* oponível ao próprio operador, para o que
seriam necessários assinatura sob custódia externa, carimbo de tempo de
autoridade credenciada ou réplica em sistema independente. A distância entre
detectar e provar é a distância entre este trabalho e o critério normativo, e é
declarada como limitação em vez de dissolvida na redação.

### 4.3 Multi-Tenancy

O termo *multi-tenancy* carece de definição uniforme, e a divergência não é
apenas terminológica: Kabbedijk *et al.* (2015), em estudo de mapeamento
sistemático que analisou 761 artigos acadêmicos e 371 publicações do meio
profissional, identificaram 43 definições distintas, a maioria delas aplicável a
apenas uma camada da arquitetura. Da consolidação dessas definições os autores
propõem a seguinte, adotada neste trabalho:

> *Multi-tenancy* é uma propriedade de um sistema em que múltiplos clientes,
> denominados inquilinos, compartilham de forma transparente os recursos do
> sistema — serviços, aplicações, bancos de dados ou equipamentos —, com o
> objetivo de reduzir custos, mantendo-se a possibilidade de configurar o
> sistema exclusivamente conforme as necessidades de cada inquilino
> (KABBEDIJK *et al.*, 2015, p. 17, tradução nossa).

Dois elementos dessa definição orientam o restante da seção. O primeiro é
*transparente*: o compartilhamento não deve ser perceptível ao inquilino, o que
converte o isolamento de dado em requisito e não em característica. O segundo é
que a propriedade se aplica a **camadas distintas** — pode-se ser multi-inquilino
no equipamento, no banco de dados ou na aplicação —, de modo que afirmar que um
sistema é multi-inquilino, sem dizer em que camada, não informa nada sobre o
isolamento que ele oferece.

#### Alternativas arquiteturais

A referência usual para as estratégias de isolamento de dados é o trabalho de
Chong, Carraro e Wolter (2006), que as dispõe num contínuo entre isolamento e
compartilhamento, e não como escolha binária. São três:

- **Bancos separados** (*separate databases*) — cada inquilino possui o próprio
  banco; a aplicação e os recursos computacionais são compartilhados. É descrita
  pelos autores como a abordagem mais simples do ponto de vista do isolamento.
- **Banco compartilhado, esquemas separados** (*shared database, separate
  schemas*) — inquilinos convivem no mesmo banco, cada um com seu conjunto de
  tabelas agrupadas num esquema próprio.
- **Banco compartilhado, esquema compartilhado** (*shared database, shared
  schema*) — as mesmas tabelas hospedam os dados de todos os inquilinos, e uma
  **coluna identificadora do inquilino** associa cada registro ao seu titular.

#### Critérios de comparação

A escolha entre as três foi avaliada segundo quatro critérios, sendo o último
específico do domínio deste trabalho: grau de isolamento obtido; custo
operacional de manutenção, migração e cópia de segurança; viabilidade de consulta
que atravesse inquilinos; e adequação ao cuidado longitudinal em rede pública de
saúde.

Quadro — Estratégias de isolamento em arquitetura multi-tenant

| Estratégia | Isolamento | Custo operacional | Consulta entre inquilinos | Adequação ao caso |
|---|---|---|---|---|
| Banco por inquilino | Máximo | Alto — *n* bancos, *n* migrações, *n* backups | Muito custosa | Inadequada: inviabiliza o prontuário longitudinal |
| *Schema* por inquilino | Alto | Médio-alto — *n* schemas por migração | Custosa | Inadequada: mesma limitação, com complexidade adicional |
| **Coluna discriminadora** | Médio, dependente de aplicação | Baixo — um banco, uma migração | Natural | **Adotada** |

#### Decisão adotada, e o argumento contrário

A escolha pela coluna discriminadora (`unidade_id`) decorre de um requisito
organizacional, não de conveniência de implementação: o cuidado longitudinal
exige consulta que atravesse unidades de forma controlada. Bancos separados
tornariam essa consulta uma operação de integração entre sistemas — precisamente
o obstáculo que o prontuário em rede existe para remover.

A decisão foi tomada **contra uma expectativa documentada do próprio setor**, e
registrá-la é mais honesto que omiti-la. Chong, Carraro e Wolter (2006, p. 4)
observam que clientes de áreas como serviços bancários e **gestão de registros
médicos** costumam ter exigências de isolamento particularmente fortes, e podem
sequer considerar uma aplicação que não forneça a cada inquilino o seu próprio
banco de dados. A observação diz respeito ao que tais clientes **exigem**, não ao
que é tecnicamente necessário; ainda assim, contraria a estratégia aqui adotada e
transfere a este trabalho o ônus de demonstrar que o isolamento obtido é
suficiente — ônus que a seção 4.4 e o capítulo 9 assumem.

#### Fragilidade e mitigação

A fragilidade reconhecida da estratégia é a **dependência da aplicação** para
aplicar o filtro: o isolamento passa a repousar sobre a disciplina de quem
escreve cada consulta. Não é risco hipotético — Kabbedijk *et al.* (2015, p. 20)
registram, entre as preocupações levantadas em sua revisão, que o
compartilhamento de instância eleva o risco de dados serem **acidentalmente
consultados pelo inquilino errado**. É precisamente essa fragilidade que o
mecanismo descrito em 4.4 se propõe a mitigar, deslocando a regra de isolamento
da camada onde o erro é provável para a camada onde ela é declarada uma vez.

#### Verificar o isolamento como contribuição

Resta uma pergunta que a adoção do mecanismo não responde: **como se sabe que o
isolamento funciona?** Os mesmos autores, ao enunciarem a agenda de pesquisa
derivada de seu mapeamento, apontam o isolamento de dados como preocupação
central e acrescentam que *"desenvolver testes que assegurem que o isolamento de
dados está funcionando corretamente é também um caminho interessante para
trabalhos futuros"* (KABBEDIJK *et al.*, 2015, p. 20, tradução nossa). Registre-se
que essa chamada foi identificada pelos autores a partir da perspectiva
**profissional** examinada no estudo, e não do consenso da literatura acadêmica.

É nesse ponto que se situa a contribuição deste trabalho. O sistema não apenas
implementa isolamento multi-inquilino: submete-o a verificação empírica
permanente, por meio de casos de teste que tentam violar o isolamento e reprovam
caso obtenham êxito — descritos em 9.3 e cujos achados são analisados em 9.4.

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
   nada. É a aplicação do princípio dos *fail-safe defaults* de Saltzer e
   Schroeder (1975), segundo o qual a decisão padrão de um mecanismo de proteção
   deve ser a negação, e o acesso deve decorrer de permissão explícita.
   Aplicação que não exibe dado algum é defeito imediatamente perceptível;
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

O registro de auditoria é o mecanismo pelo qual as propriedades de
responsabilização e não repúdio, enunciadas em 4.2, deixam de ser declarações e
passam a ter suporte material. Kent e Souppaya (2006) situam entre as
finalidades da gestão de registros a identificação de incidentes de segurança,
de violações de política e de atividade fraudulenta, além do apoio a análises
forenses e a investigações internas. Em sistema de saúde, a essas finalidades
soma-se uma de natureza jurídica: o atendimento ao direito do titular de saber
quem acessou seus dados (BRASIL, 2018, art. 9º).

Duas propriedades condicionam a utilidade da trilha, e ambas são condições
necessárias — uma trilha íntegra porém incompleta e uma trilha completa porém
alterável falham por razões diferentes e com igual gravidade.

**Completude.** Trilha que registra escritas e omite leituras é estruturalmente
incapaz de detectar a consulta indevida por profissional autorizado. O argumento
é de construção, e não de frequência: a consulta não altera estado, não viola
restrição de integridade, não difere de uma consulta legítima em nenhum atributo
observável pelo sistema — de modo que, se não for registrada, **não deixa
vestígio algum**. Ausência de registro e ausência de acesso tornam-se
indistinguíveis. É por essa razão, e não por estimativa de incidência, que este
trabalho registra leituras além de escritas.

**Integridade.** Trilha que o sistema auditado pode alterar tem valor probatório
reduzido, pela razão evidente de que o interessado em suprimir o registro de um
acesso é frequentemente quem detém o controle do sistema que o produziu. Kent e
Souppaya (2006) tratam a proteção da confidencialidade e da integridade dos
registros como requisito próprio da gestão de logs, distinto da sua geração. As
condições concretas que essa exigência impõe — propriedade da tabela por papel
distinto do utilizado pela aplicação, revogação dos privilégios de alteração e
exclusão, encadeamento por resumo criptográfico e ancoragem externa — são
analisadas em 8.2 e verificadas por comando executável, e o que delas permanece
fora do alcance da aplicação está declarado na seção 12.

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
- geram os arquivos em formato CSV de cada exportação e examinam codificação,
  separador de campos, cabeçalho e alinhamento entre colunas e linhas;
- conciliam telas e rotas nos dois sentidos: nenhum modelo de tela sem rota que
  o renderize, nenhuma rota sem caminho que a alcance na interface;
- verificam que o registro de auditoria acompanha a transação da escrita que o
  originou, e não uma transação posterior;
- verificam, no catálogo do PostgreSQL, se as políticas de RLS estão
  efetivamente ativas nas tabelas esperadas.

Acrescentou-se a esses verificadores a **medição de cobertura de execução**,
empregada não como meta percentual a atingir, mas como mapa: a relação dos
trechos que nenhum teste percorre indica onde nenhuma evidência foi produzida, e
foi ali que se procurou. O critério mostrou-se produtivo — defeitos localizados
por essa via estão relatados em 9.4.12 e 9.4.14.

A adoção desse método é justificada pelos resultados: **defeitos com impacto
direto sobre a proteção de dados foram identificados por essa via e não haviam
sido percebidos por revisão de código**, conforme detalhado na seção 9.4.

Registra-se uma qualificação que a própria execução do método impôs. Um
verificador é um artefato de software e está sujeito aos defeitos que se propõe
a detectar; quando falha, sua falha se apresenta como ausência de achados, que é
indistinguível de conformidade. Ocorreu neste trabalho, e está relatado em
9.4.9. Disso decorre a prática adotada na sequência: **todo verificador foi
confrontado com pelo menos um defeito descoberto por outro caminho**, e a
divergência entre o que ele relatava e o que se sabia existir foi tratada como
evidência sobre o instrumento, não sobre o sistema.

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
resultados: a cobertura de um controle sobre 42 tabelas e 210 rotas é uma
afirmação de natureza diferente da mesma cobertura sobre meia dúzia de telas de
demonstração. Os valores foram obtidos por contagem automatizada sobre o
código-fonte e sobre o *metadata* do mapeador objeto-relacional, e não por
estimativa.

Quadro — Dimensão do artefato construído

| Elemento | Quantidade |
|---|---|
| Módulos funcionais (*blueprints*) | 45 |
| Rotas expostas | 213 — 152 aceitam GET; 105, método de mutação |
| Tabelas no modelo de dados | 42, com 532 colunas e 114 chaves estrangeiras |
| Tabelas sob política de RLS | 23 |
| Migrações de esquema versionadas | 14 |
| Telas (*templates*) | 118 |
| Permissões nomeadas · perfis | 27 · 7 |
| Casos de teste automatizados | 417, em 35 arquivos |

Os valores acima resultam de contagem automatizada sobre o repositório.

### 7.2 Banco de dados

O modelo relacional organiza-se em torno das seguintes entidades centrais:

- **Paciente** — cadastro civil e de contato, com CPF e CNS sob restrição de
  unicidade. **Deliberadamente fora do escopo territorial**, pela razão exposta
  em 2.2: cadastro é nacional. A entidade registra **nome social** em campo
  próprio, distinto do nome civil, e toda apresentação ao usuário deriva de um
  atributo único que privilegia o primeiro quando preenchido — de modo que a
  escolha do tratamento não depende de a tela lembrar de fazê-la. O registro
  atende ao Decreto nº 8.727/2016 (BRASIL, 2016), que dispõe sobre o uso do nome
  social por pessoas travestis e transexuais no âmbito da administração pública
  federal.
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
ambiente deste trabalho, o comando confirma **oito pressupostos** — incluindo os
dois que dependem de privilégio administrativo do banco e que permaneceram
pendentes durante a maior parte do desenvolvimento — e declara um nono como
**não verificável** naquele sistema operacional.

Essa terceira resposta merece justificação, porque a alternativa era mais
simples. A nona verificação pergunta se o registro sequencial de âncoras é de
acréscimo no sistema de arquivos, atributo que o ambiente de desenvolvimento
utilizado não expõe de forma legível. Tratá-la como reprovação produziria um
comando que falha permanentemente naquele ambiente — e conviver com um controle
que sempre reprova ensina quem o executa a ignorá-lo, de modo que a reprovação
verdadeira, quando ocorresse, não seria percebida. Distinguir "não verificável"
de "reprovado" preserva o significado da reprovação, e a saída do comando afirma
explicitamente que ausência de reprovação não constitui aprovação.

A oitava verificação merece registro próprio, porque nasceu de um erro cometido
ao aplicar a correção que as outras prescreviam. A instrução para retirar a
tabela de auditoria da propriedade do papel da aplicação transferia a tabela e
concedia inserção, mas omitia a permissão de uso sobre a **sequência**, que muda
de proprietário junto no mesmo comando. Aplicada a instrução, a aplicação passou
a receber erro de permissão ao tentar registrar qualquer evento — e as sete
verificações continuaram passando, porque nenhuma delas perguntava se a
aplicação ainda conseguia auditar.

O modo de falha resultante é o pior possível para um controle de rastreabilidade:
**a trilha para de crescer e nada acusa**, porque a ausência de eventos é
indistinguível da ausência de acessos. Um endurecimento que impede o registro é
mais danoso que a lacuna que ele fecha. Acrescentou-se, por isso, a verificação
de que a aplicação **ainda consegue escrever** na trilha — e a instrução de
correção passou a incluir a sequência.

---

## 9. TESTES E VALIDAÇÃO

### 9.1 Estratégia

A suíte automatizada compreende **417 casos de teste**, provenientes de 264
funções distribuídas em 35 arquivos — a diferença corresponde às funções
parametrizadas, executadas uma vez por conjunto de entradas. A suíte é executada
integralmente sobre os dois sistemas gerenciadores de banco de dados
utilizados no projeto: sobre PostgreSQL, com um caso não aplicável; sobre
SQLite, com 27 casos não aplicáveis, correspondentes às verificações de RLS e de
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

Os dezenove achados relatados a seguir não constituem uma lista de defeitos
independentes. Enumerados isoladamente, sugeririam apenas que o sistema continha
erros — afirmação verdadeira, pouco informativa e válida para qualquer software.
Examinados em conjunto, revelam algo mais útil: **agrupam-se em um número
pequeno de mecanismos recorrentes**, e cada mecanismo admite uma forma
específica de verificação que o torna detectável antes de causar dano.

Todos compartilham uma característica, e é ela que define o objeto deste
capítulo: **nenhum produz mensagem de erro.** O sistema não interrompe, não
registra exceção, não apresenta comportamento anômalo ao operador. Uma consulta
retorna menos linhas do que deveria; um campo preenchido é descartado; uma trilha
deixa de crescer. O defeito silencioso não é uma categoria entre outras — é a
categoria que os testes convencionais não alcançam, porque testes convencionais
verificam que o esperado aconteceu, e aqui o que falta é justamente a expectativa.

A classificação abaixo foi obtida **a posteriori**, pelo exame dos achados já
registrados, e não estabelecida antes deles. As classes se sobrepõem em três
casos, o que é informativo e não defeito da classificação: sobreposição marca os
achados em que dois mecanismos se somaram, e são precisamente os mais graves.

**Classe I — A declaração que deixou de ser verdadeira.** O sistema evoluiu; a
afirmação escrita sobre ele permaneceu. Não é documentação desatualizada no
sentido trivial: a afirmação continua *literalmente* correta sobre o subconjunto
que descreve, e por isso resiste à leitura crítica. *Instâncias: 9.4.1, 9.4.5,
9.4.19.* **Verificação correspondente:** confrontar a declaração com o estado
real, e não com outra declaração — a lista de tabelas protegidas derivada do
*metadata*, o comando que interroga o servidor de banco de dados.

**Classe II — A regra escrita mais de uma vez.** A mesma decisão registrada em
dois ou mais lugares, que divergem sem que nada acuse, porque cada cópia é
internamente consistente. É a causa isolada mais frequente deste trabalho.
*Instâncias: 9.4.3, 9.4.14, 9.4.17, 9.4.18, 9.4.19.* **Verificação
correspondente:** comparar as cópias entre si, e no nível de abstração certo —
não os nomes das permissões, mas o conjunto de perfis que cada caminho admite.

**Classe III — O caminho que não existe.** Código correto, testável e inacessível:
nenhuma tela conduz até ele, ou a entidade não é construída por nenhuma rota. Não
falha porque não executa. *Instâncias: 9.4.10, 9.4.11, 9.4.12, 9.4.16.*
**Verificação correspondente:** alcançabilidade nos dois sentidos — tela sem rota
e rota sem tela —, porque cada direção encontra um conjunto distinto.

**Classe IV — O efeito que não ocorre.** A chamada acontece, e o efeito não: o
registro de auditoria é criado e não persistido, o campo é lido e não gravado. A
leitura do código confirma a intenção e não o resultado. *Instâncias: 9.4.4,
9.4.8, 9.4.13.* **Verificação correspondente:** medir o efeito, nunca a chamada —
contar linhas na tabela depois da requisição, não conferir que a função foi
invocada.

**Classe V — O próprio controle como origem do defeito.** O instrumento de
garantia produzindo aquilo que deveria impedir: o teste que verifica o objeto
errado, o detector cego para o próprio defeito, a correção de conformidade que
degrada o desempenho, o endurecimento que interrompe o controle que protegia.
*Instâncias: 9.4.2, 9.4.7, 9.4.9, 9.4.15.* **Verificação correspondente:** a
única de segunda ordem — verificar o verificador, introduzindo deliberadamente o
defeito que ele deve encontrar e confirmando que ele reprova.

Quadro — Mecanismos recorrentes e achados correspondentes

| Classe | Mecanismo | Achados | Verificação que a torna detectável |
|---|---|---|---|
| I | Declaração que deixou de valer | 9.4.1, 9.4.5, 9.4.19 | confronto com o estado real, não com outra declaração |
| II | Regra escrita mais de uma vez | 9.4.3, 9.4.14, 9.4.17, 9.4.18, 9.4.19 | comparação entre as cópias, no nível de abstração do efeito |
| III | Caminho inexistente | 9.4.10, 9.4.11, 9.4.12, 9.4.16 | alcançabilidade nos dois sentidos |
| IV | Efeito que não ocorre | 9.4.4, 9.4.8, 9.4.13 | medição do efeito, não da chamada |
| V | Controle como origem do defeito | 9.4.2, 9.4.7, 9.4.9, 9.4.15 | verificação de segunda ordem sobre o próprio controle |

O achado 9.4.6 reúne observações pontuais
de interesse gerencial e não corresponde a mecanismo único. As sobreposições —
9.4.15 nas classes IV e V, 9.4.17 nas classes II e IV, 9.4.19 nas classes I e
II — são registradas por serem informativas: correspondem aos casos em que dois
mecanismos se somaram.

A numeração original dos achados foi preservada. Renumerá-los para acompanhar as
classes tornaria inválidas as remissões cruzadas do texto, e a rastreabilidade
entre o relato e o registro de correção no repositório importa mais que a ordem
de apresentação.

**Consequência metodológica.** A coluna direita do quadro é o resultado que
transcende este sistema. Cada mecanismo admite uma verificação que o torna
detectável por medição e não por atenção, e as cinco foram implementadas como
casos permanentes da suíte, cada uma descrita no achado que a originou:

Quadro — Instrumentos permanentes derivados de cada mecanismo

| Classe | Instrumento no repositório |
|---|---|
| I | `hardening_check`, que interroga o servidor de banco; lista de tabelas protegidas derivada do *metadata*; conferência do vocabulário de permissões nos dois sentidos |
| II | conferência de que rotas que gravam a mesma entidade admitem os mesmos perfis; contrato entre formulário e rota |
| III | conferência recíproca entre telas e rotas: nenhuma tela sem rota, nenhuma rota sem porta de entrada |
| IV | renderização de toda rota de leitura com dados semeados; conferência de que rota de escrita registra auditoria na mesma transação; medição do que ficou persistido |
| V | listas de exceção que reprovam **nos dois sentidos** — achado novo falha, e achado já corrigido que continue listado também; conferência de que o endurecimento não impediu a função protegida |

O instrumento da classe V merece nota, por ser o único de segunda ordem. As
listas de exceção existem porque toda verificação automatizada acumula casos
tolerados, e casos tolerados envelhecem: o que era exceção justificada torna-se
defeito esquecido, e a lista passa a documentar uma decisão que ninguém mais
sustenta. Reprovar nos dois sentidos obriga a lista a permanecer verdadeira —
remover a justificativa de um caso já corrigido é tão obrigatório quanto
justificar um caso novo. Sem isso, a lista de exceções vira decoração, e a
verificação que ela acompanha deixa de medir sem deixar de passar.

Um defeito de qualquer dessas classes que reapareça em versão futura reprova a
suíte. É a diferença entre haver corrigido dezenove defeitos e haver instalado
cinco instrumentos que encontram a próxima ocorrência de cada um.

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

#### 9.4.9 O verificador afetado pelo defeito que verificava

**Achado.** O detector de acessos indefinidos descrito em 5.2 substitui o objeto
que o motor de modelos usa para representar variável ausente por um objeto que
registra cada acesso. Esse objeto reimplementava os métodos de conversão para
texto, de iteração, de teste lógico e de contagem. Os dois primeiros
registravam; os dois últimos não — devolviam falso e zero em silêncio.

A consequência é específica e severa: nome ausente usado apenas em condicional
(`{% if x %}`) ou em contagem (`{{ x|length }}`) ficava invisível para o
detector. E como a condicional resultava falsa, o bloco inteiro deixava de
renderizar — inclusive a iteração interna, que era justamente o que o detector
conseguia enxergar. **O defeito escondia a si mesmo:** quanto mais o template
dependia da variável ausente, menos o verificador a via.

**Análise.** Corrigidos os dois métodos, o detector passou de dezenove para
quarenta e seis acessos indefinidos, distribuídos por doze telas. Mais da metade
do que ele existia para encontrar estava fora do seu alcance, e a lista de
pendências que o acompanhava — apresentada como o inventário do problema
conhecido — descrevia menos da metade dele.

Este é o segundo achado desta natureza no trabalho. O primeiro, relatado em
9.4.2, foi um teste de segurança que reportava conformidade sem verificá-la. A
diferença é que aquele consultava o objeto errado, enquanto este verificava o
objeto certo de forma incompleta. **O instrumento de verificação é um artefato
como outro qualquer e está sujeito aos mesmos defeitos que se propõe a
detectar** — com o agravante de que sua falha se apresenta como ausência de
falhas.

**Correção.** Os quatro métodos passaram a registrar. Os defeitos revelados
estão nas seções seguintes.

**Lição de governança.** Um controle automatizado produz duas informações: o que
encontra e a confiança de que não há mais nada. A segunda não é verificada por
ele próprio. Neste trabalho ela foi verificada por confronto: um achado obtido
por outro caminho — a leitura de um par de telas que exibiam o título de módulo
alheio — não constava do relatório do detector, e foi essa discrepância que
levou ao exame do instrumento.

#### 9.4.10 Telas trocadas entre si, em pares

**Achado.** A seção 9.4.6 registra quatro telas que apresentavam o formulário de
outra funcionalidade, copiado durante a construção e não reescrito. A
verificação posterior encontrou uma variante mais difícil de perceber: pares de
telas cujos arquivos estavam **trocados entre si**.

O catálogo de exames continha o catálogo de medicamentos, e o de medicamentos
continha o de exames. A listagem de encaminhamentos por paciente continha a
listagem de exames, e a de exames continha a de encaminhamentos. Em ambos os
casos, cada rota fornecia à tela exatamente o conjunto de dados que a **outra**
esperava.

**Análise.** A troca em par é mais difícil de detectar que a cópia simples por
duas razões. A primeira é que nenhuma das duas telas produz erro: cada uma lê
nomes que não recebe, e o motor de modelos os renderiza como vazio. A segunda é
o efeito observado: as duas telas exibem uma tabela vazia sob o título do módulo
alheio, e tabela vazia é uma condição plausível — atribui-se à ausência de
dados, não a um defeito de montagem.

Encontrou-se ainda uma terceira ocorrência, não em par: a listagem de
prescrições de um paciente era mais uma cópia da listagem de exames. A tela
correspondente às prescrições nunca chegou a existir.

**Correção.** Troca do conteúdo dos arquivos, ajuste das rotas para fornecerem a
separação que cada tela apresenta — regra de domínio, e não de apresentação — e
redação da tela de prescrições a partir do que o modelo de dados armazena.

**Lição de governança.** O sintoma diagnóstico é barato e foi confirmado quatro
vezes: **o título declarado pela tela não corresponde à pasta em que o arquivo
está.** Um verificador que compare o módulo declarado com o módulo em que o
arquivo reside encontra essa família inteira sem executar nada.

#### 9.4.11 Funcionalidade implementada e inalcançável pela interface

**Achado.** Aplicou-se o raciocínio inverso ao da seção anterior: em vez de
procurar telas sem rota, procuraram-se rotas sem tela. Confrontou-se cada rota
registrada com toda referência a ela existente nos modelos de tela, no
JavaScript e na navegação lateral.

Vinte rotas não eram alcançáveis por nenhum caminho da interface. A mais grave
é o **cadastro de usuário**: a rota existia, funcionava e estava corretamente
autorizada, e a tela de administração listava, editava, ativava e desativava
contas — apenas não oferecia como criar uma. Também inalcançáveis: a criação de
setor com seus leitos, o cancelamento de cirurgia — que além de cancelar libera
a sala, mantida ocupada indefinidamente sem ele —, a suspensão de prescrição, o
registro de comparecimento em agendamento, e a tela de alertas de estoque, que
reúne o que está crítico e o que está vencendo.

**Análise.** Rota inalcançável é aprovada por todos os demais verificadores:
responde corretamente, está autorizada, não quebra nada. O que falta não é
correção — é caminho. Trata-se do defeito simétrico ao da tela órfã, e a
simetria é instrutiva: um conjunto de telas sem rota e um conjunto de rotas sem
tela indicam a mesma causa, que é a ausência de um inventário conciliando os
dois.

**Correção.** As rotas foram ligadas às telas correspondentes. Uma delas não
foi: um comutador de estado de conta que havia sido substituído por duas rotas
explícitas — ativar e desativar — permanecia registrado, acessível por método de
leitura e sem nenhuma referência. Rota de mutação alcançável por requisição de
leitura e não referenciada por nada é superfície de ataque sem proprietário; foi
removida.

**Verificação permanente.** Dois verificadores passaram a exigir a conciliação:
todo modelo de tela precisa ser renderizado por alguma rota ou herdado por outro
modelo, e toda rota precisa ser alcançável por vínculo, formulário, menu ou
chamada assíncrona. As exceções legítimas — interface programável, endereços
antigos que redirecionam — são declaradas em lista explícita, com a razão de
cada uma.

Registre-se um erro cometido na primeira versão desse verificador, por ser
instrutivo: ele comparava nomes de rota e acusou como inalcançáveis telas que
funcionavam, porque o sistema registra apelidos — nomes distintos para a mesma
função. Comparar por nome, e não por função, produziria a inclusão de vínculos
duplicados para telas que já os tinham. **Verificador recém-escrito é hipótese,
não autoridade:** seus primeiros achados exigem confirmação como quaisquer
outros.

#### 9.4.12 Exportações de dados que nunca funcionaram

**Achado.** Os arquivos em formato CSV constituíam a última camada de saída não
verificada. Aplicou-se a ela o mesmo procedimento da seção 9.4 dedicada aos
documentos em PDF: gerar o arquivo e examinar o conteúdo produzido.

Nenhuma das exportações funcionava. Os seis vínculos de exportação montavam o
endereço concatenando um separador de parâmetros ao endereço corrente; aberta a
tela sem filtro — que é como se chega a ela pelo índice de relatórios —, não há
parâmetro anterior, e o separador passa a integrar o caminho. Os seis
resultavam em erro de recurso não encontrado.

Duas exportações, alcançadas diretamente, encerravam com erro interno do
servidor: uma lia atributo inexistente no registro de atendimento e a outra lia
o modo de chegada ao pronto-socorro, campo que o formulário envia, a rota
descarta e o modelo nunca possuiu.

Constatou-se ainda que o caractere de marcação de codificação estava presente em
todos os arquivos, mas o separador de campos divergia: as exportações do módulo
de dados usavam ponto e vírgula, e as dos relatórios, vírgula. Em configuração
regional brasileira o separador de listas é o ponto e vírgula, de modo que os
arquivos de relatório eram abertos com todas as colunas reunidas numa só. **O
sistema não era capaz de reimportar aquilo que ele próprio exportava**, pois a
rotina de importação lê ponto e vírgula.

**Análise.** O defeito do atendimento é o mesmo já catalogado nas telas, onde se
manifestava como campo vazio. Na geração do arquivo, a mesma leitura interrompe
a exportação inteira. **O custo de um defeito não é propriedade dele, e sim da
camada em que se manifesta** — o que recomenda exercitar cada camada de saída em
vez de inferir seu comportamento a partir das demais.

Quanto à razão de nenhum verificador haver detectado: a varredura de rotas
visita o endereço sem parâmetros, e é o parâmetro de exportação que seleciona o
ramo de geração do arquivo. O ramo nunca havia sido executado.

**Correção.** Vínculos construídos pela função de montagem de endereços, que
trata corretamente a ausência de parâmetros anteriores e preserva os filtros já
aplicados; remoção das leituras a campos inexistentes; e padronização do
separador. Vinte e cinco verificações passaram a cobrir cada endereço que produz
arquivo — presença da marcação de codificação, separador, cabeçalho, alinhamento
entre colunas e linhas, e presença efetiva do conteúdo — além do exercício de
cada vínculo com a tela aberta sem filtro.

#### 9.4.13 Registro operatório descartado na conclusão da cirurgia

**Achado.** A seção 9.4.6 relata que o agendamento de cirurgia nunca criou
registro algum. A rota de **conclusão** do mesmo fluxo apresentava o defeito
complementar: atribuía cinco campos — descrição do ato operatório, achados,
intercorrências, materiais empregados e diagnóstico pós-operatório — a atributos
que não correspondem a colunas do modelo.

Na linguagem utilizada, atribuir atributo não mapeado a um objeto persistente é
operação válida que simplesmente não persiste. A rota, portanto, respondia com
sucesso, alterava a situação da cirurgia para realizada, encaminhava a sala para
higienização e exibia confirmação ao usuário — enquanto o documento clínico
integral era descartado.

**Análise.** As duas extremidades do mesmo fluxo assistencial falhavam pela
mesma causa: atributos não conferidos contra o modelo de dados. A diferença
entre elas é relevante para o método. No agendamento, o primeiro atributo
inválido provocava exceção, capturada por tratamento genérico e apresentada como
advertência — havia, ao menos, um sinal. Na conclusão **não há sinal algum**,
porque não há erro: a operação é legítima e silenciosa.

Verificou-se disparando a rota e recarregando o registro: os cinco atributos não
existiam no objeto lido do banco de dados.

**Correção.** Migração acrescentando as cinco colunas; validação do diagnóstico
pós-operatório pela rotina que o sistema já aplica no prontuário, uma vez que o
registro operatório alimenta o faturamento e a auditoria; e recusa que **não**
conclui a cirurgia — preservando-a em andamento em lugar de encerrá-la sem
documento. O tratamento genérico de exceções passou a registrar em diário antes
de degradar, precisamente por ter sido um tratamento assim que ocultou o defeito
descrito em 9.4.6.

#### 9.4.14 Regra replicada como causa recorrente

**Achado.** A mesma regra escrita em mais de um lugar, com conteúdos
divergentes, é a causa isolada mais frequente entre os defeitos deste trabalho.
Manifestou-se em duas famílias.

**Vocabulário de estado.** A prioridade de encaminhamento existia em cinco
lugares com três conteúdos: a rota gravava um valor que o modelo não sabia
rotular — exibido em texto bruto e na cor de menor gravidade — e o documento em
PDF conhecia um valor que a rota nunca grava, imprimindo o caso mais grave sem
acentuação e na cor mais branda. A situação de agendamento oferecia na tela um
valor inexistente no modelo e ocultava dois que existiam.

**Conversão de valor numérico clínico.** A leitura de sinais vitais vindos de
formulário — temperatura, saturação, peso, altura, glicemia, frequências —
estava implementada **quatro vezes**, em quatro rotas, com quatro
comportamentos. O registro de prontuário substituía a vírgula decimal por ponto
antes de converter; a triagem chamava a conversão diretamente; a evolução de
internação substituía a vírgula e em seguida convertia para inteiro; o cadastro
de item de estoque convertia diretamente, enquanto a edição do **mesmo** item,
no mesmo arquivo, substituía a vírgula.

O efeito é regional e não hipotético: a vírgula é o separador decimal em
português. O mesmo valor "38,4" era aceito pelo prontuário e recusado pela
triagem — e recusado da pior forma, porque a conversão ocorria dentro da
construção do objeto, sob tratamento genérico de exceções: **um único campo
ilegível descartava o registro inteiro**, exibindo a mensagem de exceção da
linguagem e sem identificar o campo.

**Análise.** Nenhuma dessas divergências produz erro no sentido corrente. Todas
produzem exibição incorreta ou descarte silencioso: o valor é rejeitado pela
validação, ou perdido na conversão, sem que nada informe qual.

Três observações merecem registro.

A primeira é que **a implementação parcialmente correta foi a que falhou de modo
menos previsível**. A evolução de internação efetuava a substituição da vírgula
— o cuidado que faltava à triagem — e em seguida convertia para inteiro; o
resultado é que "102,0", que é um valor inteiro legítimo, tornava-se "102.0" e
era recusado. Meia correção produziu um modo de falha que nenhuma das
implementações ingênuas apresentava.

A segunda é que a **coexistência das variantes no mesmo arquivo** — cadastro
intolerante e edição tolerante em rotas vizinhas — descarta a explicação por
desconhecimento e indica a causa real: a regra é pequena o bastante para que
reescrevê-la pareça mais barato que localizá-la, e cada reescrita é plausível
quando lida isoladamente.

A terceira é metodológica. O caso do agendamento: a rota não lia o campo de
situação; ao corrigi-la, acrescentou-se validação contra o vocabulário do
modelo, e **foi o teste escrito para comprovar a correção que revelou a
divergência** — ele falhou porque o valor oferecido pela tela não existia. Sem a
validação, a correção teria gravado valor desconhecido e aparentado êxito.
Correção sem verificação é hipótese.

**Como as réplicas foram encontradas.** As duas últimas não vieram de inspeção,
e sim de **medição de cobertura de execução**. Constatou-se que os trechos de
conversão de sinais vitais jamais haviam sido executados pela suíte — em rota
alguma. Exercitá-los revelou a divergência. O critério "trecho de código que
nenhum teste executa" mostrou-se um bom preditor de onde procurar: é onde a
verificação empírica ainda não chegou, e portanto onde a discrepância entre o
comportamento pretendido e o real pode persistir indefinidamente.

**Correção.** Vocabulário declarado uma única vez, no modelo, com a ordem de
gravidade junto; conversão numérica declarada uma única vez, em módulo próprio.
As telas, as rotas e os documentos derivam de ambos. A conversão distingue campo
vazio — ausência legítima de medida — de texto ilegível, que é erro e precisa
alcançar o usuário nomeando o campo. Onde há duas convenções de nomenclatura
visual, traduz-se o tom da cor e nunca o vocabulário.

**Lição de governança.** Regra replicada não é questão de estilo de código: é um
gerador de divergência com prazo. Enquanto as cópias concordam, o sistema
funciona e nada as denuncia; a partir da primeira alteração em uma delas, passam
a produzir resultados diferentes para a mesma entrada, e o defeito aparece longe
de onde foi introduzido. A propriedade útil para auditoria é que **a replicação
é contável** — quantas vezes a mesma decisão está escrita —, o que a torna
verificável antes de causar dano, ao contrário do dano em si.

#### 9.4.15 O endurecimento que impediu o controle que protegia

**Achado.** A verificação de configuração descrita em 8.2 acusava, desde o
início, que a tabela de auditoria pertencia ao papel utilizado pela aplicação —
e prescrevia a correção: transferir a propriedade a papel dedicado, revogar os
privilégios e conceder de volta apenas inserção e leitura.

Executada a instrução, as verificações passaram a confirmar todos os
pressupostos. **E a aplicação parou de conseguir registrar auditoria.**

A causa é uma consequência do próprio comando de transferência: em PostgreSQL, a
sequência que gera o identificador da tabela muda de proprietário junto com ela.
Conceder inserção sobre a tabela não basta — a inserção também exige permissão de
uso sobre a sequência, que a instrução omitia. Toda tentativa de registrar evento
passou a falhar com erro de permissão.

**Análise.** O modo de falha é o pior possível para um controle de
rastreabilidade, e por uma razão específica: **a trilha para de crescer e nada
acusa**, porque a ausência de eventos é indistinguível da ausência de acessos.
Um sistema que ninguém usou e um sistema que parou de auditar produzem
exatamente o mesmo relatório. Um endurecimento que impede o registro é mais
danoso que a lacuna que ele fecha, porque a lacuna era detectável e a
interrupção não é.

O ponto de governança, porém, não é o comando incompleto. É que **as sete
verificações continuaram passando**. Elas conferiam a propriedade da tabela e a
ausência de privilégio de exclusão — isto é, confirmavam que o controle fora
endurecido — e nenhuma perguntava se a aplicação ainda conseguia auditar. O
instrumento certificou como correto um estado em que a função protegida havia
sido eliminada.

É a terceira ocorrência da mesma natureza neste trabalho, e a mais aguda. Em
9.4.2, um teste verificava o objeto errado. Em 9.4.9, um detector verificava o
objeto certo de modo incompleto. Aqui, o verificador **prescreveu** a alteração
que quebrou o sistema e em seguida a atestou. A progressão sugere uma
formulação mais forte que a da seção 5.2: um controle de verificação não apenas
pode falhar como qualquer artefato — ele pode ser a causa do dano que deveria
detectar.

**Correção.** A instrução passou a incluir a permissão sobre a sequência. E
acrescentou-se uma oitava verificação, que confere se a aplicação **ainda
consegue escrever** na trilha, examinando tanto o privilégio sobre a tabela
quanto o uso da sequência. A assimetria é deliberada: as demais verificações
confirmam que algo está impedido; esta confirma que algo continua possível.

**Lição transferível.** Todo controle que restringe deve ser acompanhado da
verificação de que a função legítima permanece disponível. Verificar apenas a
restrição mede metade do resultado — e é a metade que não dói quando está
errada. Formulado como pergunta de auditoria: *"o que este endurecimento pode
ter impedido, e como saberíamos?"*

#### 9.4.16 A base legal implementada e nunca exercida

**Achado.** O modelo de dados previa o registro de consentimento do titular
desde o início: tabela criada, migração aplicada, campos de finalidade,
identificação da versão do termo, data de concessão e data de revogação. A
entidade constava do diagrama, da documentação e do inventário de tratamento de
dados exigido pelo art. 37 da LGPD.

**Nenhuma linha de código a instanciava.** Nenhuma rota a escrevia, nenhuma tela
a exibia, nenhum caso de teste a exercitava. A varredura descrita em 9.4.11 —
que procura rota sem porta de entrada — não a alcançava, porque não havia rota:
o defeito estava um nível abaixo, numa entidade sem qualquer código que a
tocasse.

**Análise.** A distinção que este achado impõe é entre **conformidade
documentada** e **conformidade operante**. O inventário de tratamento afirmava
que o sistema registrava consentimento, e a afirmação era verificável contra o
modelo de dados — a tabela existia. Não era verificável contra o comportamento,
e é o comportamento que a norma exige. Uma auditoria de conformidade conduzida
sobre a documentação e o *schema* teria aprovado o sistema.

O achado é agravado por um erro conceitual que a implementação revelou: o
registro de consentimento fora modelado como se toda finalidade dependesse de
consentimento. Não depende. O tratamento de dados de saúde para a **tutela da
saúde** tem base legal própria no art. 11, II, "f" da LGPD, e não é
consentimento — condicioná-lo a consentimento seria juridicamente incorreto e
clinicamente perigoso, porque implicaria que a recusa do titular impede o
atendimento. Consentimento é a base legal de finalidades **acessórias**:
pesquisa, compartilhamento com a rede nacional, contato.

**Correção.** Cada finalidade passou a declarar sua base legal e, derivada
dela, a própria revogabilidade: apenas o que se fundamenta em consentimento pode
ser revogado. A assistência à saúde aparece na tela do titular como tratamento
informado, não como pedido de autorização — o que atende ao art. 9º, que
assegura o direito de **saber**, sem converter em opcional o que a lei não fez
opcional. Foram acrescentadas as rotas de registro e revogação, a tela
correspondente, o bloco no portal do cidadão e casos de teste que exercitam o
ciclo completo.

**Lição transferível.** Existência de estrutura de dados não é evidência de
funcionamento. A pergunta que separa uma coisa da outra é operacional e não
documental: *"que caminho da interface escreve nesta tabela, e que teste percorre
esse caminho?"* Tabela sem escritor é, para efeito de conformidade, tabela
inexistente — com o agravante de aparentar o contrário.

#### 9.4.17 Dois campos descartados, duas correções diferentes

**Achado.** O detector de contrato de formulário descrito em 9.4.12 acusava, na
tela de entrada do pronto-socorro, dois campos preenchidos pelo usuário e nunca
lidos pela rota: a **classificação de risco na chegada** e o **modo de chegada**
— se o paciente veio por demanda espontânea, por serviço móvel de urgência, por
transferência.

**Análise.** O interesse do caso está em os dois campos exigirem correções
opostas, e a razão ser a mesma que a seção 9.4.14 desenvolve.

A classificação de risco **já tinha dono**: é atributo da triagem, entidade
existente, com vocabulário Manchester próprio e relacionamento estabelecido com
o atendimento. Acrescentar uma coluna de classificação ao atendimento resolveria
o sintoma e criaria a nona ocorrência da replicação de regra — dois lugares
guardando a mesma informação clínica, livres para divergir. A rota passou,
portanto, a **criar uma triagem** a partir da classificação informada na chegada,
e o atendimento a apontar para ela. O dado deixou de ser descartado sem que
nenhuma informação passasse a existir em duplicidade.

O modo de chegada não tinha dono em lugar nenhum do modelo. Não era replicação;
era ausência. Recebeu coluna própria, com vocabulário fechado no modelo — não no
gabarito da tela, pela razão exposta em 9.4.14 — e migração versionada.

**Lição transferível.** Diante de um campo descartado, a correção não é
automaticamente "criar a coluna". A pergunta anterior é se o dado já existe em
algum lugar do modelo. Se existe, criar coluna é introduzir divergência futura
sob aparência de correção; se não existe, deixar de criá-la é perder a
informação. As duas respostas erradas são simétricas, e distingui-las exige
consultar o modelo, não o formulário.

#### 9.4.18 Autorização incoerente entre portas da mesma entidade

**Achado.** A correção descrita em 9.4.17 — fazer a entrada do pronto-socorro
criar uma triagem — produziu, ela própria, uma reincidência do defeito 9.4.3.
Passaram a existir duas rotas que gravam a mesma entidade sob exigências
diferentes: a triagem propriamente dita, sob `triage:write`, e a entrada de
urgência, sob `emergency:write`. Como o perfil Médico detinha a segunda e não a
primeira, o resultado era um sistema em que **o médico não podia classificar
risco pela tela de triagem e podia pela tela do pronto-socorro**. A restrição
não estava sendo aplicada; estava apenas mal sinalizada.

Convertido o achado em verificação — e é essa a parte que interessa —, o mesmo
instrumento revelou outras três ocorrências que nenhuma leitura dirigida havia
encontrado:

- **Movimentação de estoque** gravada sob `clinical:read` em um módulo e
  `med-admin:write` em outro. O efeito era invertido em relação à competência:
  o Gestor, perfil de leitura e relatório, movimentava estoque; o Farmacêutico,
  de quem é a função, não conseguia.
- **Catálogo de vacinas** criado sob `clinical:read`, enquanto o catálogo de
  exames — rota irmã, escrita no mesmo padrão — já exigia `exam:write`.
- **Envio à Rede Nacional de Dados em Saúde** sob `reports:read`, o que
  permitia ao perfil de gestão **publicar documento clínico de paciente na rede
  nacional** por deter uma permissão de relatório.

**Análise.** Os quatro casos compartilham a causa de 9.4.14 — a mesma regra
escrita em mais de um lugar —, mas numa variante que os detectores anteriores
não alcançavam, porque aqui a regra não está replicada em dados e sim
distribuída entre um decorador de rota e uma matriz de perfis. A conferência
exige cruzar as duas, e nenhuma leitura de arquivo isolado a faz.

A formulação do verificador foi a decisão de projeto relevante. Comparar os
**nomes** das permissões produziria falso positivo legítimo: a entrada de
urgência é primariamente admissão, e exigir `emergency:write` ali está correto.
O que não pode divergir é o **conjunto de perfis que atravessa cada porta** —
porque é isso que o usuário experimenta. O teste, portanto, resolve cada
permissão contra a matriz, inclusive o coringa administrativo, e compara
conjuntos de perfis. Nomes diferentes são tolerados enquanto forem
coextensivos, e a reprovação ocorre no instante em que a matriz deixa de
torná-los coextensivos — que é exatamente o momento em que o defeito nasce.

Acrescentou-se um segundo verificador, mais simples e de alcance distinto:
permissão terminada em `:read` guardando rota de mutação. Foi ele que localizou
os casos do estoque, do catálogo e da RNDS.

**Correção.** As três incoerências de competência foram corrigidas pela
permissão, não pela matriz: estoque e catálogo de vacinas passaram às permissões
de escrita já usadas por suas rotas irmãs, e o envio à RNDS passou a exigir
`clinical:write` — quem publica o registro precisa poder tê-lo escrito. A
consulta à fila e a pré-visualização permaneceram em `reports:read`, porque
acompanhar o andamento é função legítima da gestão.

A quarta foi decidida no sentido oposto, pela matriz: **concedeu-se
`triage:write` ao perfil Médico**. É a única das quatro que constitui escolha de
produto, e não correção de defeito, e por isso o argumento fica registrado.

A decisão foi tomada, em primeira análise, contra o que se supunha ser uma
restrição normativa: a de que a classificação de risco constituiria atividade
privativa do enfermeiro. **A verificação da fonte desfez a suposição em dois
níveis, e o registro do episódio interessa mais que a decisão em si.**

A resolução consultada — Resolução Cofen nº 423/2012 — encontrava-se
**revogada** pela Resolução Cofen nº 661/2021 (CONSELHO FEDERAL DE ENFERMAGEM,
2021). E o dispositivo vigente, lido na íntegra, delimita expressamente o próprio
alcance: *"No âmbito da Equipe de Enfermagem, a classificação de Risco e
priorização da assistência é privativa do Enfermeiro"*. A norma não menciona
profissionais médicos, e não poderia fazê-lo — o conselho de enfermagem não
detém competência regulatória sobre outra profissão. O que ela estabelece é a
distinção **interna à enfermagem**, entre o enfermeiro e o técnico de
enfermagem.

Segue-se que a restrição que se imaginava opor-se à concessão não existe nos
termos supostos, e a decisão de conceder `triage:write` ao perfil Médico não
enfrenta objeção normativa. Permanecem válidos, e agora como fundamentação
principal, os três argumentos de projeto. Primeiro, o de disponibilidade
clínica: o sistema destina-se a rede municipal, e na unidade pequena sem
enfermeiro de plantão negar a permissão produz paciente na fila **sem
classificação de risco** — e é a classificação que ordena o painel de
atendimento. Segundo, o de que a segregação de funções protege pouco neste caso,
porque a trilha registra a autoria da classificação e o controle contra
classificação inadequada é revisão clínica, não controle de acesso. Terceiro, e
o mais decisivo: negar não impede o ato, apenas o empurra para o registro por
terceiro — e então a trilha passa a **atribuir a classificação a quem não a
decidiu**, que é perda de rastreabilidade em nome de uma restrição que não
restringiu.

**A norma vigente impõe, porém, uma restrição diferente — e esta o sistema não
atende.** Ao reservar a classificação ao enfermeiro *dentro da equipe de
enfermagem*, ela pressupõe que enfermeiro e técnico de enfermagem sejam perfis
distintos. O modelo de perfis implementado possui um único perfil de enfermagem,
de modo que a distinção que a norma exige não tem onde existir. Enquanto não
houver perfil de técnico, a conformidade depende de a organização simplesmente
não atribuir o perfil de enfermagem a técnicos — controle administrativo, não
técnico, e portanto exatamente o tipo de garantia que este trabalho se propôs a
tornar verificável. Registra-se como lacuna identificada e não corrigida.

O episódio ilustra a classe I da taxonomia desta seção — *a declaração que
deixou de ser verdadeira* — aplicada ao próprio texto: uma resolução revogada
havia nove anos sustentava um argumento, e a leitura parcial de um dispositivo
sustentava outro. A verificação que o trabalho aplica ao software teve de ser
aplicada à sua própria fundamentação, com o mesmo resultado: a afirmação
parecia verdadeira porque estava escrita.

O lugar próprio de decisões desse tipo seria uma matriz de permissões
configurável por organização, em que cada rede ajustasse a concessão às normas
que observa e ao quadro de pessoal que possui. O sistema não a possui — a matriz
é estrutura de código — e a limitação está registrada na seção 12.

**Lição transferível.** Autorização não se audita rota a rota. A pergunta
correta é por entidade e por perfil: *"quem consegue gravar isto, por todos os
caminhos que existem?"* — e ela só se responde cruzando decoradores com matriz,
o que nenhuma revisão de código faz de forma confiável e um verificador faz a
cada execução.

#### 9.4.19 A matriz de permissões que descrevia outro sistema

**Achado.** Convertida em verificação a pergunta "toda permissão exigida existe
na matriz?", perguntou-se também a inversa — "toda permissão da matriz é exigida
por alguma rota?" — e a resposta reprovou. **Quatro dos vinte e seis nomes não
guardavam coisa alguma:** `triage:read`, `prescription:read`,
`prescription:write` e `encounter:write`.

O efeito não era ausência de controle em toda parte, e sim controle **diferente
do declarado**. A matriz atribuía `triage:read` a três perfis, e quem a lesse
concluiria que Recepção e Farmacêutico não alcançavam a fila de triagem. Na
verdade **qualquer sessão autenticada** a alcançava, porque nenhuma rota exigia
o nome — as telas de leitura de triagem e de prescrição estavam protegidas
apenas por autenticação.

A causa dos outros dois era distinta e mais interessante: as rotas de prescrição
usavam `@medico_requerido`, um decorador de **perfil**, enquanto a matriz
declarava `prescription:write`, uma **permissão**. Duas linguagens de
autorização coexistiam, e a documentada não era a que operava.

**Análise.** A investigação do decorador de perfil revelou defeito latente
adicional. Ele comparava a string do banco contra literais em minúsculo, ao
passo que o módulo de RBAC normaliza por apelido. Um usuário gravado com a forma
canônica do perfil atravessava a permissão e era barrado pelo perfil; gravado com
o apelido, o inverso. As instalações existentes usavam o apelido, e por isso o
defeito não se manifestara — mas a tela de cadastro de usuário é que decidia,
sozinha e por lista escrita à mão, qual das duas formas seria gravada.

Essa mesma lista escrita à mão continha um terceiro achado. Oferecia **quatro
dos sete perfis**: Farmacêutico e Gestor existiam na matriz, tinham permissões
próprias e **não havia como criar usuário com eles**. O Farmacêutico é
precisamente o perfil a quem a correção descrita em 9.4.18 devolveu a gestão de
estoque — de modo que a correção teria permanecido inalcançável.

Os três achados compartilham a estrutura de 9.4.14: a mesma regra escrita em
três lugares — matriz, decorador e formulário — com três conteúdos. O que os
tornou visíveis foi perguntar pelo vocabulário em vez de perguntar pelas rotas.

**Correção.** As permissões sem uso foram aplicadas onde deveriam valer, e não
removidas: leitura de triagem e de prescrição passaram a exigi-las, o que
efetivamente restringiu telas antes abertas a qualquer sessão. As rotas de
prescrição migraram do decorador de perfil para a permissão, unificando a
linguagem. O decorador de perfil, que permanece em uso na cirurgia, passou a
normalizar. A lista de perfis do formulário passou a derivar da matriz, com uma
única exceção codificada: o operador de plataforma só é atribuível por outro
operador de plataforma, porque um administrador de hospital que pudesse
concedê-lo escaparia do próprio escopo territorial pela porta da gestão de
contas.

Acrescentou-se ainda `schedule:write`, ausente do vocabulário: agenda e
agendamento gravavam sob `patient:read` — permissão de leitura — por não haver
nome para a função.

**Verificação.** Aqui a lição de 9.4.9 voltou a aplicar-se ao próprio trabalho.
Após o aperto, a suíte completa executou sem falhas nos dois bancos, e isso
**não significava nada**: a varredura que renderiza todas as rotas autentica-se
como administrador, perfil que detém o coringa `admin:full`. Ela mede
renderização, não discriminação. Um controle recém-restringido não tinha um
único caso que o exercitasse pelo lado restringido.

Criou-se então um arquivo de casos que pergunta, por perfil e por resposta HTTP,
o que cada um alcança — e que verifica **os dois sentidos**, porque restrição
que barra quem deveria passar é indisponibilidade clínica, não segurança. Foi
preciso, antes, acrescentar Enfermeiro e Farmacêutico ao conjunto de usuários de
teste: faltavam, e são exatamente os perfis de quem são a triagem e o estoque.

**Lição transferível.** Uma matriz de permissões é documento de governança, e
documento de governança que não corresponde ao sistema é pior que documento
ausente, porque produz confiança. A verificação que a mantém honesta é barata e
tem dois sentidos: nome exigido que não existe na matriz nega todo mundo em
silêncio; nome na matriz que rota alguma exige promete um controle que não
existe. As duas ocorreram neste trabalho.

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

Aplicou-se **inspeção heurística** segundo as dez heurísticas de Nielsen (1994).
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
em 9.4.1, e após a ampliação descrita adiante, **vinte e três tabelas** estão sob
política, com verificação automatizada de sua efetividade.

A trajetória dessa cobertura é, ela própria, o resultado mais instrutivo desta
seção. O mecanismo sempre esteve correto; o alcance percorreu três estados. No
primeiro, dez tabelas estavam sob política e a documentação afirmava cobertura
total — cinco tabelas clínicas centrais estavam fora, e é o achado de 9.4.1. No
segundo, quinze tabelas estavam sob política e a documentação passou a declarar
que dez permaneciam fora, nomeando-as: a lacuna deixou de ser negada, mas
continuou existindo. No terceiro, oito dessas dez foram cobertas, e as duas
restantes passaram a exigir **justificativa escrita e verificada**.

A diferença entre o segundo e o terceiro estado merece registro porque é fácil
confundi-los. Declarar honestamente uma lacuna é melhor que ocultá-la, e não é o
mesmo que corrigi-la: durante o segundo estado, o registro de consentimento
previsto na LGPD, a aplicação de imunobiológicos que alimenta o cartão do
cidadão e a fila de envio à rede nacional — que transporta o conteúdo clínico
serializado — permaneceram legíveis a partir de qualquer município. A
documentação estava certa, e o dado, exposto.

Das duas tabelas que permanecem fora, nenhuma o está por omissão. O cadastro de
candidatos a duplicata existe para reconciliar a mesma pessoa registrada em
municípios distintos, e o escopo territorial destruiria sua função — é o mesmo
motivo pelo qual o cadastro de pacientes está fora. A tabela de eventos de
agenda não possui vínculo com paciente nem qualquer chave estrangeira, de modo
que não há de onde derivar unidade nem dado pessoal a proteger; sua ausência de
relações é questão de modelagem, anterior e independente do isolamento.

**A ausência passou a custar justificativa.** Um verificador exige que toda
tabela sem escopo territorial conste de uma lista com a razão declarada, e
reprova nos dois sentidos: tabela sem coluna e sem justificativa falha, e
justificativa remanescente para tabela que já ganhou a coluna também. É a
resposta direta à causa de 9.4.1 — lá, a ausência não custava nada a ninguém, e
por isso passou despercebida.

O controle de acesso combina permissão nomeada e escopo territorial como
dimensões independentes, com decisão no servidor.

A trilha de auditoria registra leituras e escritas, com encadeamento por hash e
verificação automatizada de que os eventos são efetivamente persistidos.

A estratégia de continuidade compreende backup completo sob RLS e validação
automatizada de restauração, executável de forma agendada.

A suíte de 417 casos de teste executa sem falhas em ambos os sistemas de banco de
dados. A sequência de treze migrações foi exercitada a partir de banco vazio e
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

**O instrumento de verificação é ele próprio um controle, e falha como tal.**
Duas ocorrências o demonstram: um teste que consultava o objeto errado (9.4.2) e
um detector que examinava o objeto certo de modo incompleto (9.4.9). No segundo
caso, metade dos defeitos que ele existia para encontrar estava fora do seu
alcance, e o relatório que produzia era apresentado — inclusive neste documento
— como o inventário do problema conhecido.

A consequência de governança é específica e transferível. Um controle de
detecção produz duas informações: os achados e a **confiança de que não há mais
nada**. A primeira é verificável por inspeção; a segunda, não — e é justamente
sobre ela que se apoiam as decisões de aceitar risco residual. Um relatório
vazio significa "não há defeito" ou "o detector parou de detectar", e nada no
próprio relatório distingue as duas leituras. A prática que se mostrou eficaz
foi confrontar cada verificador com um defeito conhecido por outra via, tratando
a divergência como evidência sobre o instrumento.

Esta constatação qualifica, sem contradizer, a recomendação da seção 14:
controles devem ser acompanhados de verificação automatizada de sua efetividade
— e essa verificação, por sua vez, precisa de evidência independente de que
permanece capaz de detectar.

**A recorrência dos padrões é achado autônomo.** Vários defeitos não são
independentes: são a mesma causa em pontos diferentes. Telas montadas com o
conteúdo de outro módulo aparecem sete vezes; regra replicada em mais de um
lugar, oito — quatro vocabulários de estado e quatro implementações da conversão
de sinais vitais; leitura de campo inexistente no modelo de dados,
sistematicamente. Isso desloca a recomendação do caso para a classe — corrigir
uma ocorrência tem valor local, ao passo que um verificador da classe encontra
as demais, inclusive as ainda não escritas. Foi essa a razão de cada achado
relatado nesta seção ter sido convertido em verificação permanente, e não apenas
em correção.

Da replicação decorre uma observação de método com valor prático. Duas das
quatro implementações divergentes da conversão numérica não foram localizadas
por inspeção, e sim por **medição de cobertura de execução**: os trechos jamais
haviam sido executados pela suíte. Trecho que nenhum teste percorre é onde a
verificação empírica ainda não chegou — e, portanto, onde a diferença entre o
comportamento pretendido e o real pode subsistir sem limite de prazo. A
cobertura, aqui, não foi usada como meta a atingir, e sim como **mapa de onde
procurar**, que é um uso mais defensável: percentual de cobertura não mede
qualidade, mas a lista de trechos não executados diz com precisão onde nenhuma
evidência foi produzida.

---

## 12. LIMITAÇÕES

**A trilha de auditoria não detecta truncamento.** A propriedade da tabela foi
transferida a papel distinto do utilizado pela aplicação, e as permissões de
alteração e exclusão foram revogadas — o que remove a limitação registrada
durante a maior parte deste trabalho. Permanece, contudo, um limite do próprio
encadeamento por resumo criptográfico, e ele é mais específico do que a
literatura costuma enunciar.

A verificação percorre a cadeia desde o início e confere cada elo. Detecta,
portanto, a **alteração** de um registro e a **remoção intermediária**, que
rompem a correspondência entre um elo e o seguinte. Não detecta a **remoção dos
registros finais**: suprimidos os últimos eventos, a cadeia remanescente
permanece internamente consistente, e nada na tabela indica que ela já foi
maior. E é precisamente a supressão do fim que interessa a quem pretende ocultar
o que acabou de fazer.

A mitigação conhecida é ancorar externamente o resumo do último elo — registrá-lo
em meio que a aplicação não possa reescrever, com periodicidade definida, de
modo que a divergência entre o valor registrado e o valor corrente revele o
truncamento. O mecanismo foi implementado ao final deste trabalho: um comando
emite a âncora — total de registros, identificador do último e resumo do elo
final — e um segundo modo a confronta com o estado corrente, acusando redução da
contagem ou divergência do resumo. Um caso de teste apaga o último registro e
verifica os dois lados da afirmação: que a verificação da cadeia **não** acusa
nada, e que a âncora acusa.

As âncoras não são um valor único reescrito a cada emissão, e sim um **registro
sequencial encadeado**: cada linha referencia o resumo da anterior, de modo que
a série de retratos é ela própria uma cadeia. Convém enunciar com precisão o que
essa construção obtém, porque é fácil atribuir-lhe mais do que entrega.

Ela **não** resolve a supressão das últimas linhas do próprio registro
sequencial — é a mesma recursão do problema original, e nenhuma quantidade de
encadeamento a encerra. A limitação é exercitada por caso de teste específico,
para que permaneça verdadeira por medição e não por memória: se algum dia esse
caso passar a falhar, é porque alguém acrescentou defesa, e a documentação
precisará acompanhar.

Ela **resolve** a reescrita de um retrato passado, manobra que a âncora isolada
não detecta — com um único valor, quem suprime o fim da trilha reescreve o valor
e o par volta a corresponder.

Ela **reduz o custo da custódia externa**, que é o ganho principal e o menos
evidente. Retida uma linha qualquer fora do servidor — por mensagem, em ata, em
cofre de senhas —, a verificação confirma que ela pertence ao registro e que
todo o trecho anterior a ela corresponde. A obrigação operacional deixa de ser
"guardar sempre o último valor" e passa a ser "guardar um valor qualquer, uma
vez". A diferença é entre um procedimento que a rotina abandona e um que
sobrevive a ela.

Ela **produz, por fim, uma verificação que não depende de nada externo**: a
comparação entre retratos consecutivos acusa que a trilha diminuiu **entre dois
momentos de conferência**, ainda que hoje esteja internamente consistente. O
registro testemunha contra o sistema que o mantém.

O conjunto dessas propriedades foi organizado como matriz explícita, e a
organização não é editorial. Cada linha corresponde a um caso de teste que
aplica a manipulação e afere o resultado, e a matriz é a **fonte** desses casos,
não um resumo posterior — de modo que a única forma de alterar o que ela promete
é alterar o que se mede. Documento paralelo ao teste envelhece em silêncio, e o
efeito é o que a seção 9.4.19 descreve a propósito da matriz de permissões: um
artefato de governança que descreve um sistema que já não existe.

Quadro — Manipulações do registro de âncoras e o que é detectado

| Manipulação | Detectada | Por quê |
|---|---|---|
| Reordenar duas linhas | Sim | a ordem faz parte da prova; o elo da linha deslocada deixa de corresponder |
| Duplicar uma linha | Sim | a cópia ocupa o lugar da precedente e a seguinte deixa de apontar corretamente |
| Inserir linha forjada no meio | Sim | encadeia-se na anterior, mas a seguinte não fecha |
| Remover linha do meio | Sim | o elo da seguinte aponta para linha ausente |
| Reescrever uma linha passada | Sim | é a manobra que o retrato único não detecta, e a razão de haver registro sequencial |
| Acrescentar campo não previsto | Sim | com validação estrita de forma; sem ela, conteúdo forjado viaja dentro de linha que fecha |
| **Truncar o fim do registro** | **Não** | as linhas restantes seguem encadeadas e nada no arquivo indica que já foi maior |
| **Recomputar o registro inteiro** | **Não** | quem controla o arquivo produz sequência internamente coerente; só o valor retido fora a desmascara |

Cada linha da tabela corresponde a um caso executado em
`tests/test_ancora_journal.py`.

A penúltima linha da tabela merece nota, porque foi acrescentada tarde e por
medição, não por previsão. O resumo criptográfico cobria apenas os campos
declarados, de modo que uma chave adicional inserida em uma linha legítima —
por exemplo, uma anotação afirmando conferência por auditoria externa —
permanecia dentro do arquivo verificado **sem estar coberta por nada**, e a
verificação continuava aprovando. O conteúdo forjado adquiria, aos olhos de quem
lesse o arquivo, a mesma autoridade da parte protegida. A correção foi tornar a
validação de forma estrita: o que não é exatamente válido é inválido. Registra-se
o achado porque ele ilustra uma regra geral — em artefato de auditoria, tolerância
sintática não é conveniência, é superfície.

Duas verificações complementares protegem a própria capacidade de verificar. A
primeira confronta o código atual com um registro **congelado no repositório**,
escrito em versão anterior e declarado não regenerável: se ele deixar de
conferir, é porque toda âncora já retida fora de um servidor também deixou, e o
fato só seria descoberto no momento de usá-la. A segunda confere que duas
execuções sobre a mesma entrada produzem o mesmo veredito — verificador cujo
resultado oscila desloca a dúvida do sistema verificado para o instrumento.

Registra-se, por fim, uma decisão sobre a redação dos diagnósticos. A mensagem
de elo rompido enumerava duas causas possíveis; a matriz demonstrou que cinco
manipulações distintas produzem o mesmo sintoma. A mensagem passou a descrever
o que foi observado, sem nomear causa — diagnóstico que afirma mais do que o
dado sustenta orienta a investigação na direção errada, e num incidente de
auditoria o custo é o tempo que mais importa.

O que permanece limitação não é o mecanismo, e sim o depositário. Registro
guardado no mesmo servidor que a aplicação pode ser reescrito por quem reescreva
a tabela — o próprio comando o adverte ao emitir. Para que a advertência não
fosse apenas retórica, a conferência aceita o valor **na própria linha de
comando**, sem ler arquivo algum da máquina verificada, e a emissão admite
destino em saída padrão, para que o retrato seja encaminhado a um coletor que a
aplicação não controle. Quem anotou o valor em cofre de senhas, em ata de
reunião ou em mensagem assinada o informa, e a verificação deixa de depender de
um arquivo local. É a diferença entre conferir contra uma cópia e conferir
contra uma testemunha.

Registre-se ainda o que a escrita em modo de acréscimo **não** é. Abrir o
arquivo em modo de anexação é convenção da aplicação, não garantia: o mesmo
processo poderia abri-lo em modo de escrita. Acréscimo efetivo é propriedade do
sistema de arquivos — `chattr +a` em sistemas Linux, lista de controle de acesso
sem permissão de escrita direta em Windows — e pertence, portanto, à mesma
fronteira entre garantia da aplicação e dependência de infraestrutura que a
seção 8.2 torna executável. O comando faz o que lhe cabe: recusa acrescentar
sobre um registro que não corresponda, porque anexar um retrato válido a uma
sequência rompida produziria um arquivo que **aparenta crescer** e cujo trecho
anterior já não vale — o pior dos dois estados.

O que o software não pode fornecer é a testemunha. Onde guardar o valor, com que
periodicidade e sob custódia de quem são decisões organizacionais, e é nesse
ponto que a garantia deixa de ser de software e passa a ser de governança.

**A trilha é detectável, não irrefutável.** Distinção que convém enunciar com
precisão, porque a literatura frequentemente as confunde. O encadeamento por
resumo criptográfico, somado à âncora externa, torna a adulteração *detectável*
— alguém que a examine percebe que houve. Não a torna *irrefutável* perante
terceiro: não há assinatura digital de chave sob custódia externa, nem carimbo
de tempo de autoridade credenciada, nem réplica da trilha em sistema
independente. Consequentemente, a trilha sustenta apuração interna e não constitui,
por si, prova oponível ao próprio operador do sistema. Fechar essa distância
exigiria elementos que este trabalho não implementa por dependerem de
infraestrutura externa — e implementá-los sem essa infraestrutura produziria
código não exercitável afirmando propriedade de segurança que não teria, que é
falha pior que a ausência.

**A matriz de permissões não é configurável por organização.** A associação
entre perfis e permissões é estrutura de código, idêntica em toda instalação.
A consequência aparece com nitidez na decisão registrada em 9.4.18: a concessão
de `triage:write` ao perfil Médico foi tomada por análise de disponibilidade
clínica, e uma rede que prefira reservar a classificação de risco à enfermagem
não tem como revogá-la sem alterar o código. A decisão é global porque o sistema
não oferece o lugar onde ela deveria ser local.

Do mesmo achado decorre uma segunda limitação, de natureza distinta: **o modelo
de perfis não distingue enfermeiro de técnico de enfermagem**. A Resolução Cofen
nº 661/2021 reserva a classificação de risco ao enfermeiro no âmbito da equipe
de enfermagem, distinção que o sistema não consegue expressar por possuir perfil
único. A conformidade passa a depender de a organização não atribuir o perfil de
enfermagem a técnicos — controle administrativo, e portanto precisamente o tipo
de garantia que este trabalho se propôs a substituir por verificação.

O que a limitação **não** significa: não se trata de ausência de granularidade.
As 27 permissões nomeadas são suficientemente finas, e a autorização é validada
no servidor em todas as rotas de escrita. Trata-se de ausência de um ponto de
configuração por inquilino — o mesmo isolamento territorial que o trabalho
implementa para os dados não existe para as regras de autorização. Fechar essa
lacuna exigiria persistir a matriz por unidade ou por rede, com precedência
definida e com auditoria das próprias alterações de permissão, o que constitui
trabalho autônomo e está indicado entre as continuações possíveis.

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
- Matriz de permissões persistida e configurável por organização, com auditoria
  das próprias alterações de permissão — de modo que decisões como a registrada
  em 9.4.18 sejam locais à rede que as toma, e não globais ao software.
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

Um terceiro achado incide sobre o próprio método e o delimita. O verificador
construído para detectar dados que as telas leem sem receber apresentava, ele
mesmo, uma variante do defeito que procurava: deixava de registrar os acessos
feitos em teste lógico e em contagem, justamente aqueles que suprimiam o bloco
inteiro da tela. Corrigido o instrumento, o número de achados mais que dobrou. A
consequência para a governança não é abandonar a verificação automatizada, e sim
reconhecer o que ela informa: **um relatório vazio significa "não há defeito" ou
"o detector parou de detectar", e nada no relatório distingue as duas leituras.**
Como o risco residual é aceito com base exatamente nessa segunda informação, ela
precisa de evidência própria — obtida, neste trabalho, confrontando cada
verificador com defeito conhecido por outra via.

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

CONSELHO FEDERAL DE ENFERMAGEM. **Resolução Cofen nº 661, de 9 de março de
2021**. Atualiza e normatiza, no âmbito do Sistema Cofen/Conselhos Regionais de
Enfermagem, a participação do Enfermeiro na atividade de Classificação de Risco.
Brasília, DF: Cofen, 2021. Disponível em:
https://www.cofen.gov.br/resolucao-cofen-no-661-2021/. Acesso em: ....

CONSELHO FEDERAL DE MEDICINA. **Resolução CFM nº 1.821/2007**. Aprova as normas
técnicas concernentes à digitalização e uso dos sistemas informatizados para a
guarda e manuseio dos documentos dos prontuários dos pacientes. Brasília, DF:
CFM, 2007.

### Governança e segurança da informação

INTERNATIONAL ORGANIZATION FOR STANDARDIZATION; INTERNATIONAL ELECTROTECHNICAL
COMMISSION. **ISO/IEC 27000:2018**: information technology — security techniques
— information security management systems — overview and vocabulary. 5. ed.
Genebra: ISO, 2018.

ISACA. **COBIT 2019 framework**: governance and management objectives. Schaumburg:
ISACA, 2018.

KENT, Karen; SOUPPAYA, Murugiah. **Guide to computer security log management**.
Gaithersburg: National Institute of Standards and Technology, set. 2006. (NIST
Special Publication, 800-92). Disponível em:
https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-92.pdf.
Acesso em: ....

SALTZER, Jerome H.; SCHROEDER, Michael D. The protection of information in
computer systems. **Proceedings of the IEEE**, v. 63, n. 9, p. 1278-1308, 1975.

VAN GREMBERGEN, Wim; DE HAES, Steven; GULDENTOPS, Erik. Structures, processes and
relational mechanisms for IT governance. In: VAN GREMBERGEN, Wim (org.).
**Strategies for information technology governance**. Hershey: Idea Group
Publishing, 2004. p. 1-36.

<!--
Saltzer e Schroeder é a origem do princípio de "fail-safe defaults" (padrões que
falham fechado), citado nas seções 4.4 e 8.1. É referência clássica e ainda
usada; vale a leitura da seção "Design Principles", que é curta.
-->

### Arquitetura de software

CHONG, Frederick; CARRARO, Gianpaolo; WOLTER, Roger. **Multi-tenant data
architecture**. [S. l.]: Microsoft Corporation, jun. 2006. Disponível em:
https://docs.citusdata.com/en/v13.0/_static/mt-data-arch.pdf. Acesso em: ....

KABBEDIJK, Jaap; BEZEMER, Cor-Paul; JANSEN, Slinger; ZAIDMAN, Andy. Defining
multi-tenancy: a systematic mapping study on the academic and the industrial
perspective. **Journal of Systems and Software**, v. 100, p. 139-148, 2015. DOI:
10.1016/j.jss.2014.10.034.

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
