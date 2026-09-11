# LEVANTAMENTO DAS BASES DE DADOS DO DATASUS

**Documento de trabalho** — resposta às duas tarefas propostas pela orientação:
(1) explorar os dados do DATASUS e (2) verificar se já existe programa que baixa
os dados do SUS e gera relatórios.

Data do levantamento: 10 de setembro de 2026. **Revisão 2** — os quatro itens que
haviam ficado como indicação de busca foram conferidos nas fontes oficiais; o
resultado está na seção 6.

Vale aqui a mesma régua do resto do projeto: **nada é afirmado sem a fonte que
prova**. Cada item traz a coluna *Verificação*, que diz se a informação foi lida
na fonte primária ou se é apenas indicação de busca. Referência copiada de
agregador entra no trabalho com data errada — e isso já quase aconteceu neste
projeto, com o Decreto 12.560/2025.

---

## 1. Antes das bases: o DATASUS tem três portas, não uma

A confusão mais comum ao "explorar o DATASUS" é tratá-lo como um repositório
único. Não é. São três canais distintos, com formatos, granularidades e
possibilidades de automação diferentes — e a escolha entre eles decide todo o
resto do trabalho.

| Porta | O que entrega | Formato | Granularidade | Automatizável |
|---|---|---|---|---|
| **TABNET** | Tabulação pronta, feita no navegador | HTML, CSV da tela | **Agregado** (já somado) | Difícil — formulário web |
| **Transferência de Arquivos (FTP)** | Microdado bruto, registro a registro | **`.DBC`** | **Microdado** | Sim, com descompressor |
| **OpenDataSUS / dados.gov.br** | Conjuntos publicados como dado aberto | CSV, JSON | Varia | **Sim — API HTTP (CKAN)** |

A diferença que mais importa para um sistema:

- **Agregado** já vem somado. "Quantas internações em Bom Jesus da Lapa em 2024"
  o TABNET responde. Mas não dá para cruzar por uma variável que a tabulação não
  ofereceu.
- **Microdado** é uma linha por internação. Permite qualquer cruzamento — e
  cobra o preço do volume e do formato proprietário.

Para quem quer **gerar relatório automaticamente**, o caminho é o microdado ou o
dado aberto. O TABNET é para exploração humana.

---

## 2. As bases, uma a uma

A lista abaixo **não é resumo de leitura**: foi extraída do próprio portal de
Transferência de Arquivos, cujo formulário é alimentado pelo arquivo
`datasus.saude.gov.br/wp-content/transferencia.js`. São **18 fontes**, e não as
seis ou sete que costumam ser citadas.

| Sigla | Sistema | Relatório que permite | Verificação |
|---|---|---|---|
| **SIHSUS** | Informações Hospitalares do SUS | Internações, CID, permanência, óbito hospitalar, valor pago | Fonte primária |
| **SIASUS** | Informações Ambulatoriais do SUS | Produção ambulatorial, APAC por especialidade, valor | Fonte primária |
| **CNES** | Cadastro Nacional de Estabelecimentos de Saúde | Rede instalada, leitos, profissionais, equipamentos, habilitações | Fonte primária |
| **SIM** | Informações de Mortalidade | Mortalidade por causa, faixa etária, sexo, município | Fonte primária |
| **SINASC** | Informação de Nascidos Vivos | Natalidade, peso ao nascer, pré-natal, tipo de parto | Fonte primária |
| **SINAN** | Agravos de Notificação | Incidência por agravo, curva epidêmica — **58 agravos em arquivos separados** | Fonte primária |
| **CIH** | Comunicação de Informação Hospitalar | Internação fora do financiamento SUS | Fonte primária |
| **CIHA** | Comunicação de Informação Hospitalar e Ambulatorial | Complemento do SIH/SIA para a rede não-SUS | Fonte primária |
| **SISCOLO** | Cânceres de Colo de Útero | Rastreamento e exames citopatológicos | Fonte primária |
| **SISMAMA** | Cânceres de Mama | Rastreamento e exames mamográficos | Fonte primária |
| **SISPRENATAL** | Pré-Natal, Parto, Puerpério e Criança | Acompanhamento de gestante | Fonte primária |
| **PO** | Painel de Oncologia — desde 2013 | Tratamento oncológico | Fonte primária |
| **PCE** | Programa de Controle da Esquistossomose | Inquérito e tratamento | Fonte primária |
| **RESP** | Notificações de casos suspeitos de SCZ — desde 2015 | Síndrome congênita associada ao Zika | Fonte primária |
| **ESUSNOTIFICA** | e-SUS Notifica (Doença de Chagas Crônica) | Notificação de DCC | Fonte primária |
| **IBGE** | **Base Populacional** | **Denominador** — indispensável para taxa por 100 mil | Fonte primária |
| **DATASUS** | Aplicativos — TabWin/TabNet | A própria ferramenta de tabulação | Fonte primária |
| **Base Territorial** | Mapas e conversões para tabulação | Cartografia para os mapas do TabWin | Fonte primária |

Três achados desta lista que mudam o desenho de qualquer módulo:

- **A base populacional do IBGE é servida pelo mesmo portal.** Sem denominador
  não existe taxa: "487 óbitos" é contagem, "óbitos por 100 mil habitantes" é
  indicador. Quem for gerar relatório epidemiológico precisa dessa fonte tanto
  quanto da clínica, e é comum descobrir isso tarde.
- **SISAB e SIOPS não estão aqui**, confirmando que atenção primária e orçamento
  seguem por portal próprio (seção 2.2).
- **SI-PNI/Imunizações também não está no portal de transferência.** Vacinação se
  obtém pelo TABNET ou pelo OpenDataSUS, não por microdado em `.DBC`.

### 2.1 O arquivo não é a base: são 167 tipos

Escolher "SIHSUS" não basta — cada fonte se divide em **tipos de arquivo**, e o
portal oferece **167** deles, com séries que começam em 1979. Os que interessam
a este projeto:

| Fonte | Tipo | Conteúdo | Início |
|---|---|---|---|
| SIHSUS | **RD** | **AIH Reduzida** — é o que se quer dizer com "dados do SIH" | — |
| SIHSUS | RJ / ER | AIH rejeitadas, e rejeitadas com código de erro | — |
| SIHSUS | SP | Serviços Profissionais | — |
| SIASUS | **PA** | **Produção Ambulatorial** | Jul/1994 |
| SIASUS | AQ / AR / AM | APAC de quimioterapia, radioterapia e medicamentos | Jan/2008 |
| CNES | **LT** | **Leitos** | Out/2005 |
| CNES | **ST** | **Estabelecimentos** | Ago/2005 |
| CNES | PF / EQ / EP | Profissionais, equipamentos, equipes | Ago/2005 |

O CNES sozinho tem 13 tipos; o SINAN, 58 — um por agravo. Um módulo que prometa
"importar o CNES" precisa dizer **qual** CNES.

### 2.2 As bases que ficam fora do DATASUS

| Sistema | Onde vive | O que é | Automatizável | Verificação |
|---|---|---|---|---|
| **SISAB / e-SUS APS** | `sisab.saude.gov.br` | Atenção primária. Criado pela Portaria GM/MS nº 1.412/2013, substituiu o SIAB; gerido pela SAPS/MS | Relatórios pela interface; **sem download ou API documentados** | Fonte primária |
| **SIOPS** | `siops.datasus.gov.br` e gov.br/saude | Receitas e despesas públicas em saúde de todos os entes federados. Preenchimento **bimestral e obrigatório** (Lei Complementar nº 141/2012) | O portal oferece "downloads dos **sistemas** do SIOPS" — o programa, não a base | Fonte primária |

O SIOPS merece nota: é descrito pelo Ministério da Saúde como o **único** sistema
do país com informação orçamentária pública de saúde, e é o que permite
monitorar a aplicação mínima em ações e serviços públicos de saúde. Para um
trabalho de **Gestão da TI**, é a base mais diretamente gerencial de todas — e é
justamente a que não sai por microdado.

### 2.3 Como o TABNET organiza tudo isso

O TABNET agrupa as bases em *Indicadores de Saúde e Pactuações*, *Assistência à
Saúde*, *Epidemiológicas e Morbidade*, *Rede Assistencial*, *Estatísticas
Vitais*, *Demográficas e Socioeconômicas* e *Informações Financeiras*.

Uma observação que só aparece olhando de perto: **o SIH aparece duas vezes**,
como *Produção Hospitalar* e como *Morbidade Hospitalar*. É a mesma origem lida
com finalidades diferentes — uma conta dinheiro, a outra conta doença. Citar
"dados do SIH" sem dizer qual é fonte de ambiguidade em qualquer relatório.

---

## 3. O obstáculo técnico: o formato `.DBC`

Este é o ponto que separa "baixar os dados" de uma linha de código de um projeto
de verdade, e é o que costuma ficar de fora das descrições otimistas.

Os arquivos de microdado do FTP do DATASUS vêm em **`.DBC`**. Não é um formato
de banco: é um arquivo **DBF (dBase) comprimido** com o algoritmo *implode* da
**PKWare Data Compression Library** — compressão legada, anterior ao ZIP como se
conhece hoje, que nenhuma biblioteca padrão de Python, R ou Java descomprime.

A estrutura do arquivo, conforme a especificação publicada junto ao pacote
`read.dbc`:

| Deslocamento | Conteúdo |
|---|---|
| 0 | Assinatura — 8 bytes |
| 8 | Tamanho `H` do cabeçalho DBF — 2 bytes, *little-endian* |
| 10 | **Cabeçalho DBF, não comprimido** — `H` bytes |
| 10 + `H` | Preenchimento / soma de verificação — 4 bytes |
| **14 + `H`** | Fluxo comprimido com **PKWare DCL Implode** (LZ77 + Shannon-Fano) |

Um `.dbc` é, portanto, um contêiner para **um único** `.dbf`.

Há aqui um detalhe de valor prático para quem for construir importador: **o
cabeçalho fica fora da compressão**. Dá para ler o esquema — nomes, tipos e
tamanhos dos campos — sem descomprimir o arquivo inteiro. Um validador que
recuse arquivo com esquema inesperado custa a leitura de alguns bytes, não o
processamento de centenas de megabytes.

A confirmação de autoria fecha o argumento: tanto o `read.dbc` quanto o
`microdatasus` creditam **Mark Adler** — autor do `blast.c`, implementação de
referência do *implode* da PKWare — e o `read.dbc` credita também Pablo Fonseca,
do `blast-dbf`. Ambos precisaram embutir o descompressor porque não havia outro
caminho.

Existem descompressores em três linguagens:

| Ferramenta | Linguagem | Papel |
|---|---|---|
| `read.dbc` | R | Lê `.DBC` direto para *data frame* |
| `dbc-to-dbf` | Python | Converte `.DBC` em `.DBF` |
| `datasus-dbc` | Rust | Converte `.DBC` em `.DBF` |

**Consequência de projeto:** qualquer módulo que baixe microdado do DATASUS
carrega uma dependência de descompressão — em geral código C ou Rust compilado.
Isso não inviabiliza nada, mas muda a conversa: deixa de ser "um `requests.get` e
um `pandas.read_csv`" e passa a ser uma dependência binária a instalar,
versionar e manter no servidor.

O caminho que **não** tem esse custo é o **OpenDataSUS**, que serve CSV por HTTP
com API CKAN. Em compensação, cobre menos bases.

---

## 4. Tarefa 2 — sim, os programas existem, e são mais de um

A resposta curta à segunda tarefa é **sim**. Existe ferramenta oficial do próprio
DATASUS e existem bibliotecas acadêmicas maduras. Nenhuma delas precisa ser
reescrita.

| Ferramenta | Origem | Faz o quê | Verificação |
|---|---|---|---|
| **TabWin** | **Oficial do DATASUS** | Programa Windows. Importa tabulação gerada pelo TABNET, faz operações aritméticas e estatísticas sobre a tabela, gera gráficos e **mapas** | Fonte primária |
| **TABNET** | **Oficial do DATASUS** | Tabulação pelo navegador, sem instalar nada | Fonte primária |
| **microdatasus** | R — Raphael Saldanha | Download, descompressão e **pré-processamento** dos microdados: rotula campos categóricos de mortalidade, nascimentos, internação, ambulatorial, estabelecimentos e notificação | Fonte primária |
| **PySUS** | Python — AlertaDengue | Baixa, converte e analisa a partir de **quatro** fontes (FTP, dados.gov.br, OpenDataSUS e espelho S3), com API orientada a *DataFrame* e interface web em Streamlit | Fonte primária |
| **datasus-fetcher** | Python | Ferramenta de linha de comando: baixa os `.dbc` brutos do FTP | Indicação de busca |
| **datasus** | R | Consulta ao TABNET a partir do R | Indicação de busca |

### 4.1 O que o DATASUS diz do próprio TabWin

Vale citar a página oficial, porque ela é mais explícita do que qualquer resumo.
O TabWin permite que você:

- *"importe as tabulações efetuadas na Internet (geradas pelo aplicativo
  TABNET)"*;
- *"realize operações aritméticas e estatísticas nos dados da tabela gerada ou
  importada"*;
- *"elabore gráficos de vários tipos, inclusive mapas, a partir dos dados dessa
  tabela"*;
- *"efetue outras operações na tabela, ajustando-a às suas necessidades"*.

E declara que o programa facilita a construção de índices e indicadores de
produção de serviços, de características epidemiológicas e de aspectos
demográficos **por estado e município**, o planejamento e a programação de
serviços, a avaliação de decisões relativas à alocação de recursos e a avaliação
do impacto de intervenções.

Duas leituras disso, e ambas importam para o projeto:

- **É exatamente a lista de funções que se imaginaria construir.** Qualquer
  proposta de "sistema que gera indicadores a partir do DATASUS" precisa dizer o
  que faz **além** disto.
- **A ferramenta é de outra era.** A página oficial anuncia "Versão 3" e traz
  aviso de direitos autorais de 2008; é executável para Windows, de instalação
  manual, sem interface web. Aí está a lacuna real — não na função, mas na
  forma de entrega.

### 4.2 Dois dados verificados sobre as bibliotecas

Respondem à dúvida sobre se são projetos vivos:

- **`microdatasus` versão 3.0.0, publicada no CRAN em 29 de julho de 2026**,
  licença MIT. Verificado na página do CRAN. O pacote tem artigo publicado nos
  *Cadernos de Saúde Pública* (2019), o que o torna citável em trabalho
  acadêmico.
- **`PySUS`** instala com `pip install pysus` e busca dados com uma chamada:
  `pysus.ftp.sinan(disease="deng", year=2024, as_dataframe=True)`. Licença GPL —
  o que **importa**, porque GPL contamina a licença de quem incorpora.

O ponto de licença merece registro: o `microdatasus` é MIT (permissiva), o
`PySUS` é GPL. Incorporar GPL a um sistema exige publicar o sistema sob GPL. Para
um TCC não é problema; para um sistema que se pretenda distribuir a uma
secretaria de saúde, é decisão a tomar com consciência, não por acidente.

---

## 5. O que este levantamento significa para o Prontuário_E2

### 5.1 O sistema já está do outro lado do balcão

O achado que muda a conversa: **o Prontuário_E2 não é consumidor do SIH e do
SIA — ele é, conceitualmente, um dos emissores.** O módulo `routes/faturamento.py`
emite **AIH** e **APAC**, com competência, CID principal, procedimento e valores.
Esses são exatamente os documentos cuja consolidação nacional **forma** o SIH e o
SIA — a ponto de o arquivo central do SIHSUS se chamar literalmente **RD, AIH
Reduzida**, e o do SIASUS, **PA, Produção Ambulatorial**. Some-se a isso o módulo
RNDS, que já envia registro clínico a sistema nacional, com fila, idempotência e
recuo exponencial.

Importar o SIH para dentro do sistema é, portanto, importar de volta um dado que
o próprio sistema é desenhado para produzir. Isso pode ser útil — mas é uma
escolha, e não a continuação natural do que já existe.

### 5.2 O que a arquitetura atual cobraria

Uma tabela de dados do DATASUS **não tem `unidade_id`**, porque o dado é público,
agregado e nacional. Pela regra vigente em `tests/test_rls_negacao.py`, toda
tabela sem essa coluna precisa de justificativa escrita em `FORA_POR_DECISAO`, e
o teste reprova nos dois sentidos. A justificativa aqui é fácil de sustentar —
dado público, sem paciente identificável, cujo escopo territorial destruiria a
função de comparação —, mas **precisa ser escrita**, e não esquecida.

### 5.3 Aderência aos objetivos declarados do trabalho

O objetivo geral da monografia é construir um prontuário multi-tenant e
**verificar empiricamente seus controles** de isolamento, acesso, auditoria e
continuidade. Os seis objetivos específicos são todos dessa natureza. Um módulo
de análise de dados abertos não responde a nenhum deles — e *"painéis gerenciais
de indicadores assistenciais"* já consta da seção **13. Trabalhos Futuros**, isto
é, já foi declarado fora do escopo pelo próprio texto.

### 5.4 Três caminhos, com custo honesto

| Caminho | O que é | Custo | Efeito sobre a monografia |
|---|---|---|---|
| **A. Levantamento** | Este documento, eventualmente ampliado, como seção de trabalhos futuros | Baixo — dias | Nenhum. Enriquece sem abrir frente |
| **B. Prova de conceito estreita** | Uma base só (CNES ou SIH), um município, importação manual de CSV, uma tela comparando o indicador interno com o municipal | Médio — semanas | Exige parágrafo novo em Trabalhos Futuros e uma seção de implementação |
| **C. Módulo completo** | Downloader, descompressor, processamento, indicadores, dashboard, PDF e Excel para seis bases | Alto — meses | Exige **reescrever título, objetivos, resumo, abstract e conclusão** |

Entre B e C, a diferença não é de esforço apenas: é de identidade do trabalho. O
caminho C transforma um TCC sobre controles de segurança em um TCC sobre
inteligência em saúde, e a banca avalia o que o texto prometeu.

---

## 6. O que foi verificado e o que não foi

Registro explícito, para que ninguém cite daqui um dado que não foi conferido.
A primeira versão deste levantamento deixou **quatro itens** como indicação de
busca. Os quatro foram conferidos na origem, e um deles mudou o conteúdo do
documento.

| Item | Como estava | Resultado da conferência |
|---|---|---|
| Recursos do TabWin | Indicação de busca | **Confirmado.** Página oficial do DATASUS, com as quatro funções transcritas na seção 4.1. Ganho extra: "Versão 3", aviso de copyright de 2008 |
| Lista de sistemas do portal de transferência | Indicação de busca | **Confirmado e corrigido.** São **18 fontes** e 167 tipos de arquivo, não as 7 antes listadas. Oito sistemas faltavam |
| CIHA, SISAB e SIOPS | Indicação de busca | **Confirmado.** CIHA **está** no portal; SISAB e SIOPS têm portal próprio, com base legal e periodicidade identificadas |
| Especificação do `.DBC` | Indicação de busca | **Confirmado.** Estrutura byte a byte na seção 3, com o achado do cabeçalho não comprimido |

**Lido na fonte primária:**

- Portal de Transferência de Arquivos do DATASUS — lista de fontes e tipos de
  arquivo extraída de `transferencia.js`, que alimenta o próprio formulário.
- Página do TabWin em `siab.datasus.gov.br` — texto transcrito na seção 4.1.
- Página do TABNET no portal do DATASUS — agrupamento das bases por categoria.
- `DBC_FORMAT.md` do `read.dbc` — estrutura do arquivo e algoritmo.
- Página do `microdatasus` no CRAN — versão 3.0.0, data 2026-07-29, licença MIT,
  atribuição a Mark Adler.
- README do PySUS no repositório oficial — fontes, licença GPL, instalação e uso.
- Portal do SISAB e página do SIOPS no gov.br — natureza, base legal e forma de
  acesso.

**O que continua sem confirmação:**

- **Se o portal de transferência publica por HTTP ou apenas por FTP.** O
  formulário aponta para um `ftp.php`, mas o caminho efetivo do arquivo não foi
  percorrido até o fim. Isso decide se um importador precisa de cliente FTP.
- **Cobertura por município de cada base.** Os arquivos do SIH, SIA e CNES são
  por **UF**; os do SINAN, por **Brasil**. Filtrar por município é trabalho de
  quem processa, não da origem — mas o volume disso não foi medido.

Nenhum dos dois é obstáculo para as conclusões deste documento; ambos precisam
ser resolvidos antes de escrever um importador.

---

## 7. Referências consultadas

- **TABNET — Informações de Saúde.** DATASUS.
  https://datasus.saude.gov.br/informacoes-de-saude-tabnet/
- **Transferência de Arquivos.** DATASUS.
  https://datasus.saude.gov.br/transferencia-de-arquivos/
- **Fontes e tipos de arquivo do portal de transferência** (origem da lista da
  seção 2). https://datasus.saude.gov.br/wp-content/transferencia.js
- **TabWin — Apresentação.** DATASUS.
  http://siab.datasus.gov.br/DATASUS/index.php?area=060805&item=1
- **SISAB — Sistema de Informação em Saúde para a Atenção Básica.** SAPS/MS.
  https://sisab.saude.gov.br/
- **SIOPS — Sistema de Informações sobre Orçamentos Públicos em Saúde.**
  Ministério da Saúde.
  https://www.gov.br/saude/pt-br/acesso-a-informacao/siops
- **Especificação do formato DBC.**
  https://github.com/danicat/read.dbc/blob/master/DBC_FORMAT.md
- **microdatasus.** CRAN. https://cran.r-project.org/package=microdatasus
- **microdatasus — documentação.** https://rfsaldanha.github.io/microdatasus/
- SALDANHA, R. F. *et al.* Microdatasus: pacote para download e pré-processamento
  de microdados do DATASUS. **Cadernos de Saúde Pública**, v. 35, n. 9, 2019.
  https://www.scielo.br/j/csp/a/gdJXqcrW5PPDHX8rwPDYL7F/
- **PySUS.** AlertaDengue. https://github.com/AlertaDengue/PySUS
- **PySUS — documentação.** https://pysus.readthedocs.io/en/latest/
- **read.dbc.** https://github.com/danicat/read.dbc
- **OpenDataSUS.** Ministério da Saúde. https://opendatasus.saude.gov.br/dataset/
