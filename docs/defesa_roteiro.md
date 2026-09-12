# Roteiro de apresentação e defesa

Documento de trabalho, gerado a partir da versão corrente de `TCC.md`. Não é
parte da monografia e pode ser apagado depois da defesa.

**Fonte de tudo o que está aqui:** a monografia. Nenhum número, resultado ou
referência foi acrescentado. Onde a monografia declara uma limitação, o roteiro
a declara também.

---

## A contribuição que a apresentação precisa construir

Antes dos slides, o alvo. A banca precisa sair da sala capaz de repetir isto:

> O trabalho não avaliou um sistema pronto: **construiu um**, e foi essa
> condição que permitiu abrir, instrumentar e exercitar cada controle por
> dentro. A verificação empírica desses controles revelou dezenove defeitos que
> compartilham uma propriedade — **nenhum produz mensagem de erro**. Eles se
> agrupam em cinco mecanismos recorrentes, e cada mecanismo admite uma
> verificação que o torna detectável por medição, e não por atenção. As cinco
> verificações tornaram-se casos permanentes da suíte. A contribuição não é o
> prontuário, nem a lista de defeitos: é a demonstração de que **um controle de
> governança precisa vir acompanhado da verificação de que continua operando —
> e de que o próprio verificador é um controle, sujeito à mesma exigência.**

A frase mais afiada do trabalho, e que deve ser dita na defesa quase literalmente:

> Um controle de detecção produz duas informações: os achados, e a confiança de
> que não há mais nada. A primeira é verificável por inspeção; a segunda, não —
> e é sobre ela que se apoiam as decisões de aceitar risco residual.

**Arco narrativo em três atos:**

| Ato | Slides | Pergunta que responde |
|---|---|---|
| I — O artefato | 1 a 8 | O que foi construído, e com que controles |
| II — O método e o que ele achou | 9 a 13 | Como foi verificado, e o que apareceu |
| III — O significado | 14 a 18 | Por que isso é contribuição de governança |

**Sobre o tempo.** Os dezoito slides somam ~20 min. Se a banca sinalizar
aperto, os cortes seguros, nesta ordem: fundir 2 e 3, reduzir o 5 a trinta
segundos, cortar o 17. **Nunca corte 10, 11, 13 e 15** — são o trabalho.

---

# ATO I — O ARTEFATO

## Slide 1 — Capa

**Visual**
- Título e subtítulo da monografia
- Seu nome · Orientação · IF Baiano · ano
- Uma linha discreta no rodapé: *sistema desenvolvido integralmente nesta pesquisa*

**Fala (30s)**

> Bom dia. Meu nome é Iasmin Ribeiro de Souza e vou apresentar o trabalho
> "Construção de um prontuário eletrônico multi-tenant: avaliação empírica de
> controles de segurança, isolamento de dados e auditoria".
>
> Um esclarecimento antes de começar, porque ele condiciona tudo o que vem
> depois: o sistema não preexistia à pesquisa. Ele foi projetado e escrito ao
> longo dela. Isso não é detalhe biográfico — é o que tornou possível abrir os
> controles por dentro e submetê-los ao tipo de verificação que este trabalho
> relata, condição que raramente se tem ao avaliar sistema de terceiro.

**Objetivo do slide.** Estabelecer, na primeira frase, que o objeto é seu. Toda
a força do trabalho depende disso.

**Perguntas possíveis** — nenhuma, normalmente. Se vier: *"Desenvolveu sozinha?"*
→ responda com honestidade sobre orientação e ferramentas, sem diminuir a autoria
do projeto e das decisões.

---

## Slide 2 — Contexto e problema

**Visual**
- Um mapa mental simples: **cidadão** → atendido em **municípios distintos** →
  unidades administrativamente independentes
- Dois números: **8.930 → 26.091** unidades com prontuário eletrônico (2017→2022)
- Uma tensão desenhada em duas setas opostas: *ampliar acesso* × *restringir acesso*

**Fala (1 min)**

> O prontuário saiu do papel para sistemas que concentram, num único
> repositório, identificação civil, histórico clínico, prescrições, exames e
> internações. No SUS, essa concentração acontece em escala federativa: a mesma
> pessoa é atendida em municípios diferentes, por unidades administrativamente
> independentes.
>
> E a escala não é projeção. Celuppi e colaboradores, em 2024, na Revista de
> Saúde Pública, mediram a adesão ao Prontuário Eletrônico do Cidadão na
> atenção primária: passou de 8.930 unidades em 2017 para 26.091 em 2022.
>
> Esse arranjo produz uma tensão que é, antes de tudo, de gestão. De um lado, o
> prontuário longitudinal — recuperar o histórico completo do cidadão
> independentemente de onde ele foi atendido — é a principal promessa clínica da
> informatização. De outro, dado de saúde é dado pessoal sensível pela LGPD,
> artigo 5º, inciso II. Ampliar o acesso melhora o cuidado; restringi-lo protege
> o titular. **Onde essa fronteira é traçada é decisão de governança, e a
> arquitetura do sistema é o instrumento que a executa.**

**Objetivo.** Situar o problema como sendo de governança, não de programação —
o que justifica o trabalho estar num curso de Gestão da TI.

**Perguntas possíveis**
- *Por que esse problema é de gestão e não técnico?* → Porque a decisão de quem
  vê o quê é organizacional; a arquitetura só a implementa. E porque o erro aqui
  não se manifesta como falha, mas como funcionamento normal com dados a mais.

---

## Slide 3 — Justificativa

**Visual** — quatro blocos curtos, uma linha cada:
- Exposição entre unidades **não gera erro**
- Segregar sem impedir o cuidado longitudinal
- Rastreabilidade é obrigação legal (LGPD art. 37)
- Continuidade suposta ≠ continuidade verificada

**Fala (1 min)**

> Quatro razões sustentam o trabalho.
>
> A primeira é a que mais me interessou. Em arquitetura multi-tenant, o
> isolamento costuma ser implementado por filtros adicionados às consultas — e
> aí ele depende da disciplina de quem escreve cada consulta. **Uma consulta
> nova que esqueça o filtro expõe dados de outra unidade sem gerar erro, sem
> alerta e sem sinal perceptível ao usuário.** O incidente não se manifesta como
> falha: manifesta-se como funcionamento normal com dados a mais. Kabbedijk e
> colaboradores registram esse mesmo risco — dados serem acidentalmente
> consultados pelo inquilino errado.
>
> A segunda: a segregação não pode ser total, porque cadastro de paciente é
> nacional. Encontrar que o cidadão atendido hoje já foi atendido em outro
> município é a razão de existir do prontuário em rede.
>
> A terceira: o artigo 37 da LGPD exige registro das operações de tratamento, e
> em saúde isso tem contrapartida concreta — o titular tem direito de saber quem
> acessou o prontuário dele.
>
> A quarta: rotina de backup que nunca foi restaurada não é garantia de
> continuidade; é a suposição de uma garantia.

**Objetivo.** Plantar a expressão "não gera erro". Ela volta no slide 10 e é a
espinha do trabalho.

**Perguntas possíveis**
- *A LGPD se aplica ao SUS?* → Sim; e a obrigação de auditar o prontuário chega
  por duas vias independentes, porque a Resolução CFM 1.821/2007 já condicionava
  a substituição do papel a requisitos de autenticidade e rastreabilidade.

---

## Slide 4 — Objetivos

**Visual** — objetivo geral em destaque; os seis específicos como lista curta,
com o sexto realçado.

**Fala (45s)**

> O objetivo geral foi construir um sistema de prontuário multi-tenant e
> **verificar empiricamente seus controles**, analisando como isolamento,
> controle de acesso, auditoria e continuidade contribuem para a governança de
> TI numa organização de saúde.
>
> Os específicos foram seis: isolamento aplicado na camada de banco, e não só na
> aplicação; controle de acesso por menor privilégio; auditoria com detecção de
> adulteração; backup com validação automatizada de restauração; avaliação de
> usabilidade por inspeção heurística; e o sexto, que peço para destacar —
> **analisar criticamente os limites dos próprios controles, distinguindo o que
> a aplicação garante do que depende de infraestrutura.**
>
> O sexto objetivo não é uma ressalva de rodapé. A avaliação crítica é resultado
> do trabalho, e não apenas seu método.

**Objetivo.** Anunciar que a autocrítica é *entregável*, para que os defeitos do
slide 13 sejam lidos como resultado e não como confissão.

**Perguntas possíveis**
- *Um objetivo de "analisar limites" não é vago?* → Ele é operacionalizado: a
  seção 8.2 separa garantia da aplicação de dependência de infraestrutura, e um
  comando executável confronta o banco com cada pressuposto dessa separação.

---

## Slide 5 — Fundamentação essencial

**Visual** — quatro caixas, uma linha cada, com o autor abaixo:
- *Multi-tenancy* — Kabbedijk et al. (2015)
- Estratégias de isolamento — Chong, Carraro e Wolter (2006)
- Propriedades de segurança — ISO/IEC 27000:2018
- Falha fechada — Saltzer e Schroeder (1975)

**Fala (1 min)**

> Quatro âncoras conceituais, e menciono só o que muda a leitura do resto.
>
> *Multi-tenancy* não tem definição uniforme: Kabbedijk e colaboradores
> analisaram 761 artigos e encontraram 43 definições. Adotei a que eles
> consolidam — múltiplos clientes compartilhando de forma **transparente** os
> recursos do sistema. A palavra "transparente" importa: ela converte o
> isolamento de dado em requisito, não em característica desejável.
>
> A ISO/IEC 27000 define segurança da informação como preservação de
> confidencialidade, integridade e disponibilidade, e menciona em nota outras
> propriedades, entre elas autenticidade e não repúdio. **Eu trouxe essas duas
> para o primeiro plano deliberadamente**, e explico por quê: em prontuário, a
> autoria do registro clínico não é atributo acessório — quem prescreveu, quem
> classificou o risco, quem consultou. Isso é objeto de regulação profissional e
> de proteção de dados.
>
> E o princípio de *fail-safe defaults*, de Saltzer e Schroeder: a decisão padrão
> de um mecanismo de proteção deve ser a negação. Isso reaparece concretamente no
> slide 7.

**Objetivo.** Mostrar domínio da literatura sem virar aula. Prepara o argumento
de não repúdio, que fecha no slide 8 e no 14.

**Perguntas possíveis**
- *Por que elevou autenticidade e não repúdio, se a norma as põe em nota?* →
  Porque o domínio exige. E declarei a escolha em vez de apresentá-la como se
  fosse da norma.

---

## Slide 6 — Arquitetura e tecnologias

**Visual**
- A figura de camadas da monografia (usuário → aplicação → ORM → PostgreSQL),
  com o ponto de aplicação de cada controle marcado
- Números do quadro de dimensão, em rodapé discreto: **45 módulos · 214 rotas ·
  42 tabelas · 117 telas · 15 migrações**

**Fala (1 min 15)**

> A aplicação é Flask com Jinja2 e SQLAlchemy, sobre PostgreSQL. Organiza-se em
> módulos por domínio funcional, agrupados como o código os registra:
> assistencial; apoio diagnóstico e medicação; vigilância, regulação e
> interoperabilidade, que inclui o envio à Rede Nacional de Dados em Saúde;
> cidadão e conformidade; e gestão e plataforma.
>
> A dimensão está registrada porque condiciona a leitura dos resultados: 45
> módulos, 214 rotas, 42 tabelas, 117 telas, 15 migrações versionadas. **A
> cobertura de um controle sobre 42 tabelas e 214 rotas é afirmação de natureza
> diferente da mesma cobertura sobre meia dúzia de telas de demonstração.**
>
> Todos esses valores foram obtidos por contagem automatizada sobre o
> código-fonte e sobre o metadata do mapeador objeto-relacional. Nenhum é
> estimativa.
>
> E a figura mostra o que importa para o resto da apresentação: **cada controle
> tem uma camada onde é aplicado**, e a escolha da camada é a decisão de projeto.

**Objetivo.** Dar escala sem dar detalhe. E introduzir "camada onde o controle é
aplicado", que é o argumento do slide 7.

**Perguntas possíveis**
- *Por que Flask e não um framework maior?* → Decisão de projeto; o que o
  trabalho avalia são os controles, e eles estão em RLS, RBAC e auditoria, não no
  framework web.
- *214 rotas é muito para um TCC?* → A contagem é automatizada e verificável; e
  a escala é o que dá sentido à afirmação de cobertura.

---

## Slide 7 — Multi-tenancy e isolamento por RLS

**Visual**
- O quadro das três estratégias (banco por inquilino · schema por inquilino ·
  **coluna discriminadora**), com a adotada em destaque
- Ao lado, as quatro condições do RLS como *checklist*: `FORCE` · falha fechada ·
  escopo por transação · **cobertura efetiva**
- Um número: **23 tabelas sob política**

**Fala (1 min 30)**

> Chong, Carraro e Wolter descrevem três estratégias de isolamento, num contínuo
> entre isolamento e compartilhamento: bancos separados; banco compartilhado com
> esquemas separados; e banco e esquema compartilhados, com uma coluna que
> identifica o inquilino.
>
> Adotei a terceira, e adotei **contra uma expectativa documentada do setor** —
> os mesmos autores observam que clientes de gestão de registros médicos
> costumam exigir isolamento forte, e podem sequer considerar aplicação que não
> dê a cada um o seu próprio banco. Registro isso porque a decisão foi tomada
> com conhecimento do argumento contrário. A razão é o cuidado longitudinal:
> bancos separados transformariam a consulta entre unidades numa operação de
> integração entre sistemas, que é exatamente o obstáculo que o prontuário em
> rede existe para remover.
>
> A fragilidade reconhecida dessa escolha é depender da aplicação para aplicar o
> filtro. É por isso que existe a segunda camada: **Row-Level Security**, que
> coloca a mesma regra dentro do banco. Hoje são 23 tabelas sob política.
>
> E quatro condições decidem se isso é proteção ou teatro. `FORCE`, porque o
> dono da tabela ignora políticas por padrão e a aplicação é a dona. **Falha
> fechada**: sem escopo definido, nada é liberado — aplicação vazia é defeito
> óbvio, aplicação mostrando o país inteiro é incidente que ninguém percebe.
> Escopo reposto a cada transação, e não a cada conexão, porque conexões são
> reaproveitadas por *pool*. E a quarta, que parece trivial: **cobertura
> efetiva** — a política protege as tabelas às quais foi aplicada. Guardem essa
> quarta condição; foi ela que falhou.

**Objetivo.** Mostrar profundidade técnica e plantar o gancho do slide 13.

**Perguntas possíveis** — muitas; veja o banco de perguntas 1, 2, 3, 5, 6, 7.

---

## Slide 8 — Segurança, RBAC, auditoria e LGPD

**Visual** — três colunas, sem texto corrido:
- **RBAC** — 27 permissões · 7 perfis · `recurso:ação`
- **Auditoria** — encadeada por hash · tabela de papel próprio · âncora externa
- **LGPD** — art. 5º II · art. 9º · art. 11 II "f" · art. 37

**Fala (1 min 30)**

> Três controles, e uma distinção que a banca pode querer explorar.
>
> O RBAC é por **permissão nomeada**, no formato recurso e ação — 27 permissões
> distribuídas em 7 perfis. E ele é **ortogonal ao escopo territorial**: a
> permissão diz *o que* se pode fazer, o escopo diz *sobre quais registros*.
> Confundir os dois foi um dos defeitos encontrados.
>
> A auditoria registra leituras e escritas, com encadeamento por hash: cada
> evento carrega o resumo do anterior, então alterar um registro invalida a
> cadeia seguinte. A tabela pertence a um papel de banco distinto do usado pela
> aplicação, e os privilégios de alteração e exclusão foram revogados.
>
> Sobre LGPD, uma decisão que quero explicitar. O sistema registra base legal
> **por finalidade**, e não trata tudo como consentimento — porque não é. O
> tratamento para **tutela da saúde** tem base própria no artigo 11, inciso II,
> alínea "f". Condicioná-lo a consentimento seria juridicamente incorreto e
> clinicamente perigoso, porque implicaria que a recusa do titular impede o
> atendimento. Consentimento é a base de finalidades acessórias: pesquisa,
> compartilhamento, contato. E só o que se apoia em consentimento é revogável.

**Objetivo.** Demonstrar que a LGPD foi lida, não citada. Este é o slide que
mais impressiona banca de gestão.

**Perguntas possíveis** — 4, 8, 9 do banco de perguntas.

---

# ATO II — O MÉTODO E O QUE ELE ACHOU

## Slide 9 — Metodologia de verificação

**Visual**
- Uma frase grande e sozinha: **"A inspeção de código é insuficiente para
  verificar controles de segurança."**
- Abaixo, quatro ícones/linhas: instrumentar · exercitar · confrontar nos dois
  sentidos · medir cobertura como mapa
- Números: **574 casos · 364 funções · 44 arquivos · dois bancos**

**Fala (1 min 15)**

> A etapa de verificação adotou uma premissa que determinou os resultados: **a
> inspeção de código é insuficiente para verificar controles de segurança.** Em
> lugar dela, instrumentação e exercício efetivo do sistema.
>
> Concretamente: verificadores que instrumentam o motor de templates para
> registrar acesso a variável inexistente e depois renderizam todas as telas com
> dados reais; que confrontam cada chamada assíncrona da interface com o mapa de
> rotas efetivo; que confrontam os campos que o formulário envia com os que a
> rota realmente lê; que geram os PDFs e extraem o texto para conferir; que
> conciliam telas e rotas **nos dois sentidos**; e que consultam o catálogo do
> PostgreSQL para ver se as políticas estão de fato ativas.
>
> São 574 casos de teste, provenientes de 364 funções em 44 arquivos, executados
> integralmente sobre os dois bancos usados no projeto.
>
> E acrescentei a medição de cobertura de execução — **não como meta percentual,
> mas como mapa**. Percentual de cobertura não mede qualidade; mas a lista de
> trechos que nenhum teste percorreu diz com precisão onde nenhuma evidência foi
> produzida.

**Objetivo.** Estabelecer o método antes dos achados, para que os achados sejam
lidos como produto do método.

**Perguntas possíveis** — 11, 13 do banco.

---

## Slide 10 — A taxonomia dos achados

**Visual** — o quadro das cinco classes, sem a coluna de verificação ainda
(ela é o slide 11). No topo, uma linha destacada:
**"Dezenove achados. Nenhum produz mensagem de erro."**

**Fala (2 min)** — *slide central, não corra*

> São dezenove achados. E eles compartilham uma propriedade que define o objeto
> deste capítulo: **nenhum produz mensagem de erro.** O sistema não interrompe,
> não registra exceção, não se comporta de modo anômalo para o operador. Uma
> consulta retorna menos linhas do que deveria; um campo preenchido é
> descartado; uma trilha deixa de crescer.
>
> Isso não é uma categoria entre outras. É **a categoria que os testes
> convencionais não alcançam** — porque teste convencional verifica que o
> esperado aconteceu, e aqui o que falta é justamente a expectativa.
>
> Enumerados um a um, dezenove defeitos diriam apenas que o sistema tinha erros,
> o que é verdadeiro e pouco informativo. Examinados em conjunto, agrupam-se em
> cinco mecanismos:
>
> **Classe I — a declaração que deixou de ser verdadeira.** O sistema evoluiu, a
> afirmação escrita sobre ele permaneceu. E ela resiste à leitura crítica, porque
> continua *literalmente* correta sobre o subconjunto que descreve.
>
> **Classe II — a regra escrita mais de uma vez.** Duas cópias que divergem sem
> que nada acuse, porque cada uma é internamente consistente. É a causa isolada
> mais frequente deste trabalho.
>
> **Classe III — o caminho que não existe.** Código correto, testável e
> inacessível. Não falha porque não executa.
>
> **Classe IV — o efeito que não ocorre.** A chamada acontece e o efeito não. A
> leitura do código confirma a intenção, não o resultado.
>
> **Classe V — o próprio controle como origem do defeito.** O teste que verifica
> o objeto errado, o detector cego para o próprio defeito, o endurecimento que
> interrompe o controle que protegia.
>
> Uma observação de método: **essa classificação foi obtida depois**, pelo exame
> dos achados já registrados, e não estabelecida antes deles.

**Objetivo.** Transformar "achei bugs" em "identifiquei mecanismos". É o pivô da
apresentação inteira.

**Perguntas possíveis** — 12 do banco.

---

## Slide 11 — De cada mecanismo, um instrumento

**Visual** — o mesmo quadro do slide 10, agora **com a coluna direita revelada**
(a verificação correspondente a cada classe). Visualmente: a tabela "completa-se".

**Fala (1 min 30)**

> E aqui está a razão de a taxonomia existir. **Cada mecanismo admite uma
> verificação específica que o torna detectável por medição, e não por atenção.**
>
> Para a classe I, confrontar a declaração com o estado real — e não com outra
> declaração. A lista de tabelas protegidas é derivada do metadata do ORM, e um
> comando interroga o servidor de banco.
>
> Para a classe II, comparar as cópias entre si, **no nível de abstração certo**:
> não os nomes das permissões, mas o conjunto de perfis que cada caminho admite.
>
> Para a classe III, alcançabilidade nos dois sentidos — tela sem rota e rota sem
> tela —, porque cada direção encontra um conjunto diferente.
>
> Para a classe IV, medir o efeito e nunca a chamada: contar linhas na tabela
> depois da requisição, em vez de conferir que a função foi invocada.
>
> E para a classe V, a única de segunda ordem: verificar o verificador,
> introduzindo deliberadamente o defeito que ele deve encontrar e confirmando que
> ele reprova.
>
> As cinco existem como casos permanentes da suíte. **Um defeito de qualquer
> dessas classes que reapareça reprova a execução.** É a diferença entre haver
> corrigido dezenove defeitos e haver instalado cinco instrumentos que encontram
> a próxima ocorrência de cada um.

**Objetivo.** Este slide é a contribuição em forma operacional. Diga a última
frase devagar.

**Perguntas possíveis** — 11, 13, 21 do banco.

---

## Slide 12 — Resultados

**Visual** — três blocos numéricos, sem prosa:
- **Isolamento:** 10 → 15 → **23** tabelas sob política
- **Desempenho:** 185,9 ms → **0,96 ms** *(ordem de grandeza; ver limitações)*
- **Continuidade:** restauração conferida em **13 tabelas**, correspondência exata
- **Configuração:** `hardening-check` — **10 verificações: 9 aprovadas, 1 reprovada**

**Fala (1 min 30)**

> Quatro resultados.
>
> O isolamento percorreu três estados, e a sequência é o resultado mais
> instrutivo do trabalho. No primeiro, dez tabelas estavam sob política e a
> documentação afirmava cobertura total. No segundo, a documentação passou a
> declarar honestamente que dez permaneciam fora, nomeando-as — a lacuna deixou
> de ser negada e continuou existindo. No terceiro, oito dessas dez foram
> cobertas e as duas restantes passaram a exigir **justificativa escrita e
> verificada**. Hoje são 23 tabelas sob política.
>
> Quero marcar a diferença entre o segundo e o terceiro estado, porque é fácil
> confundi-los: **declarar honestamente uma lacuna é melhor que ocultá-la, e não
> é o mesmo que corrigi-la.** Durante o segundo estado, o registro de
> consentimento, a aplicação de imunobiológicos e a fila de envio à rede nacional
> permaneceram legíveis a partir de qualquer município. A documentação estava
> certa, e o dado, exposto.
>
> Em desempenho, com volume sintético de 50 mil pacientes, a consulta de sugestão
> de paciente caiu de 185,9 para 0,96 milissegundos. Faço uma ressalva já aqui, e
> volto a ela: **isso demonstra ordem de grandeza, não é referência de
> capacidade.**
>
> A restauração do backup foi conferida em treze tabelas, com correspondência
> exata de contagens. E o comando de verificação de configuração roda dez
> verificações: nove passam e **uma reprova** — a que pergunta se o registro de
> âncoras é de acréscimo no sistema de arquivos. Ela reprova porque o atributo
> não foi aplicado, e o comando informa a linha exata que o aplica.
>
> Faço questão de mostrar isso reprovando, e não de esconder: um verificador que
> nunca acusa nada é indistinguível de um que parou de verificar. E ao lado dela
> existe uma décima, de sinal contrário, que pergunta se a aplicação **ainda
> consegue** escrever no registro — porque o endurecimento que a nona prescreve
> pode, se excessivo, interromper aquilo que ela protege.

**Objetivo.** Entregar resultados com as ressalvas já embutidas — tira a munição
da banca e demonstra maturidade metodológica.

**Perguntas possíveis** — 14, 20 do banco.

---

## Slide 13 — Três defeitos, três lições

**Visual** — três cartões, um por defeito. Sem texto longo: um título e um número.
1. **RLS correto, cinco tabelas fora**
2. **A auditoria de leitura que não persistia**
3. **O detector cego para o próprio defeito** — 19 → 46

**Fala (2 min)** — *o slide mais memorável; conte como história*

> Escolhi três, um de cada camada do argumento.
>
> **O primeiro.** A documentação escrita durante a própria construção afirmava
> que as políticas cobriam toda tabela com escopo territorial. A verificação
> mostrou que cinco tabelas clínicas centrais — cirurgias, encaminhamentos,
> atendimentos de pronto-socorro, evoluções de internação e itens de prescrição
> — não tinham a coluna e estavam integralmente fora de qualquer política. O
> mecanismo estava correto; o alcance é que não era o anunciado. E a afirmação
> era **literalmente verdadeira**: cobria as tabelas que tinham a coluna. Só que
> essas eram minoria.
>
> **O segundo.** As rotas de leitura chamavam o registro de auditoria com o
> comportamento padrão, que não confirma a transação. Isso é correto para
> escritas, onde o evento acompanha a transação da mutação. Mas em rota de
> leitura não há transação de escrita para carregá-lo, e o evento era descartado
> ao final da requisição. **O sistema aparentava auditar leituras e não as
> auditava** — e o módulo de transparência informaria ao titular, com base na
> mesma tabela, que ninguém havia consultado o prontuário dele.
>
> **O terceiro é o que eu mais aprendi.** Construí um detector que substitui o
> objeto que o Jinja usa para variável ausente por um que registra cada acesso.
> Ele reimplementava conversão para texto, iteração, teste lógico e contagem. Os
> dois primeiros registravam; os dois últimos devolviam falso e zero em silêncio.
> Consequência: nome ausente usado em condicional ficava invisível — e como a
> condicional dava falso, o bloco inteiro deixava de renderizar, inclusive a
> iteração, que era o que o detector conseguia ver. **O defeito escondia a si
> mesmo:** quanto mais a tela dependia da variável ausente, menos o verificador a
> via. Corrigidos os dois métodos, os achados passaram de dezenove para quarenta
> e seis, em doze telas. Mais da metade do que ele existia para encontrar estava
> fora do seu alcance — e a lista que ele produzia vinha sendo apresentada,
> inclusive neste documento, como o inventário do problema conhecido.

**Objetivo.** Provar que a autocrítica é real e produtiva. O terceiro caso é o
que sustenta a contribuição do slide 15.

**Perguntas possíveis** — 16, 17 do banco.

---

# ATO III — O SIGNIFICADO

## Slide 14 — Limitações

**Visual** — cinco linhas curtas, com um selo neutro do tipo *"declarado e
verificável"*:
- Não repúdio: **detectável, não irrefutável**
- Âncora de auditoria: **custódia é externa**
- Desempenho: **protocolo implementado; ambiente ainda sintético**
- Usabilidade: **inspeção pela equipe, sem usuários finais**
- RBAC: **não configurável por organização**

**Fala (1 min)** — *tom firme, não defensivo*

> As limitações são limites de método, e estão declaradas.
>
> A mais importante é conceitual. A ISO define não repúdio como a capacidade de
> **provar** a ocorrência de um evento. O encadeamento por hash, somado à
> ancoragem externa, torna a adulteração **detectável** — mas não constitui prova
> oponível ao próprio operador do sistema, para o que seriam necessários
> assinatura sob custódia externa, carimbo de tempo credenciado ou réplica em
> sistema independente. Então o atendimento ao critério normativo é parcial, e
> digo isso explicitamente em vez de dissolvê-lo na redação.
>
> Sobre a âncora: o mecanismo existe e um caso de teste exercita **o que ele não
> fecha** — truncar o fim do próprio registro de âncoras. O que resta de
> limitação é a custódia, que é decisão organizacional, não de software.
>
> Em desempenho, a limitação mudou de natureza durante o trabalho. Os tempos
> vinham de observação, sem repetições nem dispersão. Isso foi fechado: há um
> comando que descarta aquecimento, repete, e reporta mediana com amplitude
> interquartil — e que acusa quando a dispersão passa de um quarto da mediana,
> caso em que o número não deve ser citado como estável. **O que permanece é de
> ambiente, e não de método:** a medição continua em máquina de desenvolvimento e
> sobre volume sintético, e protocolo não converte dado sintético em dado real.
>
> A usabilidade foi avaliada por inspeção heurística conduzida pela própria
> equipe, sem avaliadores independentes e sem usuários finais. Os resultados
> indicam conformidade com princípios de projeto, **não satisfação de usuários
> reais**.
>
> E a matriz de permissões é estrutura de código, idêntica em toda instalação —
> uma rede que queira decidir diferente não tem onde fazê-lo.

**Objetivo.** Apresentar limitações como rigor. Bancas punem limitação
escondida, não limitação declarada.

**Perguntas possíveis** — 9, 10, 14, 18, 19 do banco.

---

## Slide 15 — A contribuição

**Visual** — quase vazio. Só isto, em duas linhas grandes:

> **Um controle de detecção produz duas informações:
> os achados, e a confiança de que não há mais nada.
> A primeira é verificável por inspeção. A segunda, não.**

**Fala (1 min 30)** — *o clímax; fale devagar e pare depois*

> Chego à contribuição, e ela não é "desenvolvi um prontuário eletrônico".
>
> Construir o sistema foi a **condição**, não o resultado: foi o que permitiu
> abrir cada controle, instrumentá-lo e exercitá-lo por dentro — o que não se
> consegue avaliando sistema de terceiro.
>
> O resultado é este. Há diferença substantiva entre **implementar um controle** e
> **haver verificado que ele opera sobre a superfície que se pretende cobrir**. O
> sistema tinha Row-Level Security corretamente implementado — com `FORCE`, falha
> fechada e escopo reposto por transação — e ainda assim mantinha cinco tabelas
> clínicas centrais integralmente fora de proteção. O mecanismo estava certo; o
> alcance, não.
>
> E há um segundo nível, que considero a contribuição propriamente dita. **O
> instrumento de verificação é ele próprio um controle, e falha como tal.** Um
> controle de detecção produz duas informações: os achados, e a confiança de que
> não há mais nada. A primeira é verificável por inspeção; a segunda, não — e é
> exatamente sobre ela que se apoiam as decisões de aceitar risco residual. Um
> relatório vazio significa "não há defeito" ou "o detector parou de detectar", e
> nada no próprio relatório distingue as duas leituras.
>
> A prática que se mostrou eficaz foi confrontar cada verificador com um defeito
> conhecido por outra via, tratando a divergência como evidência sobre o
> instrumento. É isso que eu levo deste trabalho para a gestão da TI.

**Objetivo.** A frase que a banca vai repetir na ata. Silêncio de dois segundos
depois dela.

**Perguntas possíveis** — 17, 21 do banco.

---

## Slide 16 — Conclusão

**Visual** — o problema de pesquisa reescrito como resposta, em uma linha:
**"A contribuição decorre da cobertura verificada do mecanismo, não da sua
existência."**

**Fala (1 min)**

> Quanto ao problema de pesquisa — como arquitetura multi-tenant associada a
> mecanismos na camada de dados contribui para confiabilidade e proteção —, a
> resposta é afirmativa, sob uma condição que a experiência tornou explícita: **a
> contribuição decorre da cobertura verificada do mecanismo, não da sua
> existência.**
>
> Os objetivos específicos foram atendidos, com as ressalvas registradas: o
> isolamento foi implementado e sua cobertura ampliada e quantificada, ainda que
> não integral; o controle de acesso distingue permissão de escopo; a auditoria
> tem encadeamento por hash e passou a registrar leituras, permanecendo a
> imutabilidade efetiva dependente de configuração de infraestrutura; a
> continuidade tem validação automatizada de restauração; e a usabilidade foi
> avaliada por inspeção heurística, sem participação de usuários finais.

**Objetivo.** Fechar o círculo com o slide 4. Mostrar que cada objetivo tem
resposta e ressalva.

---

## Slide 17 — Trabalhos futuros

**Visual** — seis itens curtos, agrupados por natureza (segurança ·
desempenho · arquitetura · funcionalidade).

**Fala (45s)**

> Os desdobramentos que considero mais relevantes: matriz de permissões
> persistida e configurável por organização, com auditoria das próprias
> alterações de permissão; avaliação de usabilidade com usuários dos perfis
> reais; medição sob distribuição real de dados, e não sintética; camada de
> serviço explícita, centralizando a decisão de autorização em ponto único; e
> ampliação da conformidade com FHIR para interoperabilidade.
>
> E o que fecharia a limitação de não repúdio: custódia externa da âncora, com
> emissão e verificação em papéis distintos — que é decisão de governança, e
> nenhum código a resolve.

---

## Slide 18 — Encerramento

**Visual** — agradecimento e contato. Nada mais.

**Fala (15s)**

> É isso. Agradeço à banca pelo tempo e fico à disposição para as perguntas.

---

# Perguntas prováveis da banca

Cada uma tem **resposta curta** (para falar) e **aprofundamento** (se pedirem
detalhe). Não decore: entenda a estrutura de cada uma.

### 1. Por que usar PostgreSQL RLS?

**Curta.** Porque ele coloca a regra de isolamento na camada onde ela é
declarada uma vez e aplicada uniformemente, em vez da camada onde o erro é
provável — a aplicação, com dezenas de consultas escritas por pessoas diferentes
ao longo do tempo. É defesa em profundidade: o filtro da aplicação permanece, e a
política do banco cobre a hipótese de ele faltar.

**Aprofundamento.** A política é avaliada pelo servidor em toda consulta,
independentemente da origem — inclusive de uma consulta escrita amanhã por outra
pessoa, ou de uma ferramenta que conecte direto ao banco. Foi decisão de escolha
do SGBD: o suporte a políticas por linha foi um dos critérios. E a escolha só
vale sob quatro condições, que verifico: `FORCE`, falha fechada, escopo reposto
por transação e cobertura efetiva.

### 2. Por que multi-tenancy?

**Curta.** Porque o SUS é federativo: uma única aplicação serve múltiplas
unidades administrativamente independentes, e o cuidado longitudinal exige que
o cadastro do cidadão atravesse essas fronteiras de forma controlada.

**Aprofundamento.** Adotei a definição de Kabbedijk e colaboradores, que enfatiza
o compartilhamento *transparente* — o inquilino não deve perceber que divide
recursos. Isso transforma o isolamento em requisito. E a propriedade se aplica a
camadas distintas; dizer que um sistema é multi-inquilino sem dizer em que camada
não informa nada sobre o isolamento que ele oferece.

### 3. Por que não separar cada unidade em um banco?

**Curta.** Porque destruiria a função principal do sistema. Cadastro de paciente
é nacional, e encontrar que o cidadão atendido hoje já foi atendido em outro
município é a razão de existir do prontuário em rede. Com bancos separados, essa
consulta vira uma operação de integração entre sistemas.

**Aprofundamento.** E registro que decidi **contra** um argumento documentado:
Chong, Carraro e Wolter observam que clientes de gestão de registros médicos
frequentemente exigem banco próprio por inquilino. A observação é sobre o que
clientes exigem, não sobre necessidade técnica — mas ela transfere a mim o ônus
de demonstrar que o isolamento obtido é suficiente, e é esse ônus que o capítulo
de verificação assume. O custo operacional também pesa: *n* bancos significam *n*
migrações e *n* backups.

### 4. Qual a diferença entre RBAC e RLS?

**Curta.** São ortogonais. O RBAC responde *o que* o usuário pode fazer — criar
prescrição, ler prontuário. O RLS responde *sobre quais registros* ele pode fazê-lo.
Um médico com permissão de escrita clínica continua limitado aos pacientes do seu
escopo territorial.

**Aprofundamento.** Confundir os dois foi um dos defeitos encontrados: um perfil
administrativo estava sendo tratado como se implicasse alcance territorial amplo,
quando o alcance deveria vir do nível de acesso do cadastro. Corrigido, o perfil
passou a dizer só o que a pessoa faz, e o escopo, sobre o que ela faz.

### 5. O RLS sozinho garante isolamento?

**Curta.** Não, e o trabalho demonstra isso empiricamente. O RLS estava
corretamente implementado e cinco tabelas clínicas centrais estavam integralmente
fora dele, porque não tinham a coluna de escopo. A política protege as tabelas às
quais foi aplicada — e essa condição, aparentemente trivial, foi a que falhou.

**Aprofundamento.** Por isso a lista de tabelas protegidas passou a ser derivada
do metadata do ORM, e não escrita à mão, e um comando confronta o banco com essa
lista. E as tabelas que ficam de fora precisam de **justificativa escrita**, que
um teste confere nos dois sentidos: tabela sem escopo e sem justificativa
reprova, e justificativa para tabela que já ganhou escopo também.

### 6. Como você comprovou que o isolamento funciona?

**Curta.** Com testes de **negação**, que fazem a pergunta inversa. Não que a
política exista, mas que ela recuse. Cada caso grava um registro de uma unidade e
tenta alcançá-lo com o escopo de outra, consultando o banco diretamente, sem
passar pelo filtro da aplicação.

**Aprofundamento.** A escolha de ir direto ao banco é deliberada: o que se mede é
a defesa que resta quando o filtro da aplicação falha. Um teste que passasse pela
aplicação provaria os dois controles juntos e não distinguiria qual operou. E os
casos cobrem também o sentido oposto — a unidade proprietária enxergando o
próprio registro —, porque negar em excesso é falha de disponibilidade, não
sucesso.

### 7. O que acontece se alguém esquecer o filtro `unidade_id`?

**Curta.** A política do banco nega assim mesmo. É exatamente o cenário para o
qual a segunda camada existe: o filtro em Python é a primeira linha, e a política
é a que sobra quando a disciplina falha.

**Aprofundamento.** Com uma condição que precisa ser dita: isso vale para as
tabelas sob política. Para as que não estivessem cobertas, esquecer o filtro
expunha o dado — e foi precisamente o que aconteceu com as cinco tabelas do
achado 9.4.1.

### 8. Como a auditoria se relaciona com a LGPD?

**Curta.** Por duas vias. O artigo 37 exige que o controlador mantenha registro
das operações de tratamento. E o artigo 9º assegura ao titular o direito de saber
como seus dados são tratados — o que, em prontuário, significa saber quem o
acessou.

**Aprofundamento.** E a obrigação não nasce com a LGPD: a Resolução CFM
1.821/2007 já condicionava a substituição do prontuário em papel a requisitos de
autenticidade e rastreabilidade. A convergência por duas vias normativas
independentes é o que torna a auditoria requisito de projeto, e não conveniência.
Foi também por isso que registrar **leituras** importou: a consulta indevida por
profissional autorizado não altera estado e, se não for registrada, não deixa
vestígio algum.

### 9. Por que a trilha de auditoria não garante não repúdio?

**Curta.** Porque a ISO/IEC 27000 define não repúdio como a capacidade de
**provar** a ocorrência de um evento, e o que o sistema oferece é **detecção**.
Adulteração se torna detectável para quem examine a trilha; isso não é o mesmo
que prova oponível ao próprio operador do sistema.

**Aprofundamento.** Faltam três elementos, e todos dependem de algo externo:
assinatura com chave sob custódia separada, carimbo de tempo de autoridade
credenciada e réplica em sistema independente. Implementar assinatura com a chave
no mesmo servidor seria pior que não implementar — daria aparência de não repúdio
sem a substância, já que quem reescreve a tabela detém a chave. Preferi declarar
o atendimento como parcial.

### 10. Quais são as limitações do sistema?

**Curta.** Cinco declaradas: não repúdio parcial; custódia da âncora de auditoria
é externa ao software; medição de desempenho limitada a ambiente sintético;
usabilidade avaliada sem usuários finais; e matriz de permissões não configurável
por organização.

**Aprofundamento.** Acrescento duas que são de alcance, não de mecanismo: o
modelo de perfis não distingue enfermeiro de técnico de enfermagem, distinção que
a Resolução Cofen 661/2021 pressupõe; e a medição foi feita com volume sintético,
não com a distribuição real de uma rede.

### 11. Por que os testes são uma contribuição e não apenas testes de software?

**Curta.** Porque não verificam funcionalidade, verificam **propriedades de
governança** — e verificam o tipo de defeito que não gera erro. Um teste
convencional confirma que o esperado aconteceu; estes procuram o que deixou de
acontecer em silêncio.

**Aprofundamento.** E são derivados de uma classificação: cada uma das cinco
classes de mecanismo tem um verificador correspondente, que a torna detectável por
medição. Além disso, vários carregam listas de exceção que **reprovam nos dois
sentidos** — achado novo falha, e achado já corrigido que continue na lista também
falha. Sem isso, a lista de exceções envelhece e a verificação deixa de medir sem
deixar de passar.

### 12. O que significa a taxonomia dos 19 achados?

**Curta.** Significa que os defeitos não são independentes: são um número pequeno
de causas em pontos diferentes. Isso desloca a recomendação do caso para a classe
— corrigir uma ocorrência tem valor local; um verificador da classe encontra as
demais, inclusive as ainda não escritas.

**Aprofundamento.** A classificação foi obtida *a posteriori*, pelo exame dos
achados já registrados. As classes se sobrepõem em três casos, e mantive as
sobreposições registradas em vez de forçar exclusividade, porque elas marcam
exatamente os achados em que dois mecanismos se somaram — que são os mais graves.

### 13. Como você sabe que os 574 casos são suficientes?

**Curta.** Não sei, e o trabalho não afirma isso. Suficiência não é demonstrável.
O que os casos garantem é outra coisa: que um defeito de qualquer das cinco
classes que reapareça reprova a execução.

**Aprofundamento.** E o trabalho é explícito sobre o limite disso. Usei medição de
cobertura de execução não como meta, mas como mapa — a lista dos trechos que
nenhum teste percorre diz onde nenhuma evidência foi produzida. Foi assim que
localizei duas das quatro implementações divergentes da conversão de sinais
vitais: os trechos jamais haviam sido executados pela suíte. Há também um piso
que a verificação não alcança, e ele apareceu: uma entidade que nenhuma linha de
código instancia não aparece em varredura alguma.

### 14. Por que 0,96 ms não deve ser tratado como benchmark?

**Curta.** Porque foi feita em ambiente de desenvolvimento e sobre volume
sintético. Ela demonstra **ordem de grandeza** — de 185,9 para 0,96
milissegundos —, magnitude em que a variação entre execuções não altera a
conclusão.

**Aprofundamento.** Esse número específico veio de observação, sem repetições
nem dispersão. Reconhecida a falha de método, ela foi corrigida: há um comando
que executa cada consulta sob protocolo — descarta aquecimento, porque a
primeira execução mede a partida e não o regime; repete; e reporta **mediana**
com **amplitude interquartil**, assinalando quando a dispersão passa de um
quarto da mediana. Mas protocolo não converte dado sintético em dado real: o
que a medição continua **não** sustentando é comparação fina entre alternativas
de implementação ou referência de capacidade, e isso segue declarado nas
limitações.

### 15. O que a Resolução Cofen revelou sobre o próprio processo de pesquisa?

**Curta.** Que o método precisava ser aplicado também ao texto. Eu sustentava uma
decisão de permissão numa resolução que estava **revogada havia nove anos**, e
cuja leitura eu tinha feito parcialmente: o dispositivo diz "no âmbito da equipe
de enfermagem", e não menciona médicos.

**Aprofundamento.** É a classe I da minha própria taxonomia — a declaração que
deixou de ser verdadeira — aplicada à fundamentação do trabalho. A verificação da
fonte mudou o argumento em dois sentidos: a concessão de permissão de triagem ao
perfil médico não enfrenta a objeção normativa que eu supunha, e a norma vigente
impõe **outra** restrição, que o sistema não atende — ela pressupõe que enfermeiro
e técnico de enfermagem sejam perfis distintos, e o meu modelo tem perfil único de
enfermagem. Registrei isso como lacuna identificada e não corrigida.

### 16. Qual foi o principal erro encontrado no sistema?

**Curta.** A cobertura incompleta do isolamento: cinco tabelas clínicas centrais
fora de qualquer política, enquanto a documentação afirmava cobertura total. É o
mais grave porque combina exposição real de dado com uma afirmação que teria
sustentado decisões organizacionais equivocadas.

**Aprofundamento.** Se a pergunta for pelo mais *instrutivo*, é outro: o detector
cego para o próprio defeito, que passou de dezenove para quarenta e seis achados
depois de corrigido. Esse é mais importante metodologicamente, porque mostra que o
instrumento de verificação é ele próprio um controle e falha como tal.

### 17. Qual foi o principal resultado técnico?

**Curta.** A demonstração de que há diferença substantiva entre implementar um
controle e haver verificado que ele opera sobre a superfície pretendida — e a
conversão de cada classe de defeito encontrada num verificador permanente.

**Aprofundamento.** E o corolário de governança, que é o que levo do trabalho: um
controle de detecção produz duas informações, os achados e a confiança de que não
há mais nada, e apenas a primeira é verificável por inspeção. Como o risco
residual é aceito com base na segunda, ela precisa de evidência própria — obtida,
aqui, confrontando cada verificador com defeito conhecido por outra via.

### 18. O que seria necessário para colocar isso em produção real no SUS?

**Curta.** Três coisas que o trabalho identifica e não entrega: infraestrutura
configurada conforme a fronteira da seção 8.2; custódia externa da âncora de
auditoria, com emissão e verificação em papéis separados; e validação com usuários
reais dos perfis clínicos.

**Aprofundamento.** Acrescento a matriz de permissões configurável por
organização, porque decisões como a de quem classifica risco variam com o quadro
de pessoal de cada rede; a distinção entre enfermeiro e técnico; homologação do
envio à RNDS com certificado ICP-Brasil, que só pode ser verificada contra o
ambiente oficial; e medição sob distribuição real de dados. O trabalho não afirma
prontidão para produção.

### 19. O que ainda não está resolvido?

**Curta.** A custódia da âncora, que é decisão organizacional; o não repúdio no
sentido normativo; a configurabilidade da matriz de permissões; e a distinção
entre enfermeiro e técnico de enfermagem.

**Aprofundamento.** Também não está resolvido, e é honesto dizer: o sistema não
tem vínculo profissional–paciente nem mecanismo de quebra de sigilo com
justificativa. Hoje o escopo territorial é a única dimensão — dentro de um
município, o acesso não distingue se há relação de cuidado com aquele paciente.
Em termos de LGPD, isso é necessidade e finalidade, e considero a lacuna de maior
impacto clínico entre as que restam.

### 20. O que você faria diferente com mais tempo?

**Curta.** Teria começado pelos verificadores, e não pelas funcionalidades. Todos
os achados vieram de verificação empírica, e cada verificador construído revelou
uma classe inteira — construí-los depois significou que os defeitos existiram por
mais tempo do que precisavam.

**Aprofundamento.** E teria medido desempenho com protocolo desde o início:
repetições, dispersão, ambiente controlado. A medição que fiz serve ao propósito
que tinha, mas fecharia uma limitação que hoje preciso declarar.

### 21. Isso não é apenas boas práticas de teste?

**Curta.** A prática de testar é conhecida; o que o trabalho acrescenta é a
classificação dos defeitos **silenciosos** por mecanismo causal, e a demonstração
de que cada mecanismo admite um verificador específico. E acrescenta o nível de
segunda ordem: verificar o verificador, que não é prática difundida.

**Aprofundamento.** Há evidência de que o problema é reconhecido e não resolvido:
Kabbedijk e colaboradores, ao enunciarem a agenda de pesquisa derivada do
mapeamento de 761 artigos, apontam desenvolver testes que assegurem o
funcionamento do isolamento de dados como caminho para trabalhos futuros. Registro
que essa chamada foi identificada por eles a partir da perspectiva profissional
examinada no estudo.

### 22. A avaliação não é enviesada, já que você avaliou o próprio sistema?

**Curta.** É, e o trabalho declara isso. O viés existe e foi mitigado de uma
forma específica: os achados não vieram de julgamento meu, vieram de verificadores
automatizados que reprovam ou passam. A autocrítica que um avaliador externo
dificilmente obteria é justamente o que a autoria do sistema tornou possível.

**Aprofundamento.** O mesmo vale para a usabilidade, e ali a limitação é maior
porque a inspeção heurística **é** julgamento: foi conduzida pela própria equipe,
sem avaliadores independentes nem usuários finais, e por isso os resultados são
apresentados como conformidade com princípios de projeto, e não como satisfação de
usuários. Avaliação com usuários dos perfis reais está entre os trabalhos futuros.

### 23. Por que a documentação do próprio sistema errou sobre a cobertura?

**Curta.** Porque a afirmação era literalmente verdadeira sobre o subconjunto que
descrevia — cobria as tabelas que tinham a coluna de escopo — e por isso resistia
à leitura crítica. É o mecanismo que classifiquei como classe I.

**Aprofundamento.** A correção não foi reescrever a frase: foi derivar a lista de
tabelas protegidas do metadata, de modo que a afirmação passe a ser calculada e
não redigida. Em governança, documentação é artefato de controle e está sujeita a
verificação como qualquer outro.

### 24. Como você garante que a auditoria não foi adulterada?

**Curta.** Não garanto — detecto. Cada evento carrega o resumo do anterior, então
alterar um registro ou remover um do meio quebra a cadeia. A tabela pertence a um
papel de banco distinto do usado pela aplicação, e os privilégios de alteração e
exclusão foram revogados, o que é conferido por comando.

**Aprofundamento.** E há um limite específico que o encadeamento não fecha:
**truncar o fim** da trilha não rompe elo nenhum — os que sobram continuam
consistentes e nada na tabela diz que ela já foi maior. Por isso existe a âncora
externa, que registra total, último identificador e resumo final. Guardado um
único valor fora do servidor, valida-se todo o prefixo. O que permanece limitação
é a custódia desse valor.

---

# Resumo de 2 minutos

*Para quando a banca pedir uma síntese.*

> Construí um sistema de prontuário eletrônico multi-tenant, em que múltiplas
> unidades de saúde compartilham a mesma aplicação e o mesmo banco mantendo
> isolamento lógico dos seus dados — e, principalmente, submeti os controles
> desse sistema a verificação empírica.
>
> O isolamento é aplicado em duas camadas: o filtro da aplicação e uma política
> de *Row-Level Security* dentro do PostgreSQL, hoje sobre 23 tabelas. O controle
> de acesso é por permissão nomeada, 27 permissões em 7 perfis, ortogonal ao
> escopo territorial. A auditoria registra leituras e escritas, encadeadas por
> hash. E o backup tem validação automatizada de restauração.
>
> A verificação — 574 casos de teste — revelou dezenove defeitos, e todos
> compartilham uma propriedade: **nenhum gera mensagem de erro**. Entre eles, o
> Row-Level Security estava corretamente implementado e cinco tabelas clínicas
> centrais estavam integralmente fora dele, enquanto a documentação afirmava
> cobertura total.
>
> Esses dezenove agrupam-se em cinco mecanismos recorrentes, e cada mecanismo
> admite uma verificação que o torna detectável por medição em vez de por
> atenção. As cinco viraram casos permanentes da suíte.
>
> A contribuição é essa: **há diferença substantiva entre implementar um controle
> e haver verificado que ele opera sobre a superfície que se pretende cobrir.** E
> como o próprio verificador é um controle e falha como tal, ele também precisa de
> evidência independente de que continua capaz de detectar.

---

# Frase central da defesa

> **Implementar um controle e verificar que ele cobre a superfície pretendida são
> coisas diferentes — e o instrumento que faz essa verificação é, ele próprio, um
> controle sujeito à mesma exigência.**

Variante mais curta, se precisar de uma linha:

> **A contribuição decorre da cobertura verificada do mecanismo, não da sua
> existência.**

---

# O que NÃO dizer

Cada item abaixo é uma afirmação que o trabalho **não** sustenta. Dizer qualquer
uma delas entrega à banca uma contradição contra o próprio documento.

**Sobre segurança**
- ❌ "O sistema é seguro." → *diga:* "os controles implementados foram
  verificados, e as limitações estão declaradas".
- ❌ "O RLS garante o isolamento." → o trabalho **demonstra o contrário**: o
  mecanismo estava correto e cinco tabelas estavam fora.
- ❌ "A trilha de auditoria é imutável." → é **detectável**, e a imutabilidade
  efetiva depende de configuração de infraestrutura.
- ❌ "O sistema garante não repúdio." → atendimento **parcial** ao critério da
  ISO/IEC 27000; falta prova oponível ao operador.

**Sobre os testes**
- ❌ "574 testes provam que não há mais defeitos." → provam que um defeito das
  classes conhecidas reprova a execução. Suficiência não é demonstrável.
- ❌ "A cobertura de testes é alta." → cobertura foi usada como **mapa**, não
  como meta; percentual não mede qualidade.
- ❌ "Todos os defeitos foram encontrados por verificação empírica." → há uma
  exceção declarada: a entidade que nenhum código instanciava.

**Sobre resultados**
- ❌ "O sistema é 200 vezes mais rápido." → a medição demonstra ordem de
  grandeza, sem repetições nem dispersão, com volume sintético.
- ❌ "A usabilidade foi validada." → foi avaliada por inspeção heurística da
  própria equipe, **sem usuários finais**.
- ❌ "O código IBGE elimina a fragmentação dos relatórios." → fornece um critério
  imune à grafia; os campos textuais continuam no esquema.
- ❌ "A cobertura de RLS é total." → 23 tabelas; as demais têm justificativa
  escrita, e duas foram deixadas de fora por decisão registrada.

**Sobre maturidade**
- ❌ "O sistema está pronto para produção." → o trabalho lista o que faltaria.
- ❌ "Está em conformidade com a LGPD." → *diga:* "implementa controles que
  atendem a exigências específicas — artigos 5º, 9º, 11 e 37 —, com limitações
  declaradas". Conformidade é juízo jurídico, não técnico.

**Sobre postura**
- ❌ Minimizar os defeitos ("eram poucos", "eram bobos"). Eles são **resultado**;
  minimizá-los desmonta a contribuição.
- ❌ Atribuir defeito a terceiros ou a pressa. O trabalho ganha força por
  assumi-los: *"que essas falhas estivessem em controles projetados pela própria
  autora não é circunstância a atenuar — é o que dá ao relato a franqueza que uma
  avaliação externa dificilmente obteria."*
- ❌ Responder "não sei" e parar. Prefira: "o trabalho não mediu isso; o que
  posso afirmar com base no que medi é…".
