# Avaliação de usabilidade com usuários reais — desenho do estudo

**O que é este documento.** É o **protocolo** da avaliação de usabilidade com
usuários dos perfis reais, hoje ausente do trabalho: a seção 10 da monografia
aplicou inspeção heurística conduzida pela própria autora, e registra como
limitação a falta de avaliadores independentes e de usuários finais (§10.1); a
seção 12 a nomeia como limitação e a seção 13 como trabalho futuro. Este é o
desenho que, uma vez **executado**, produz a seção 10.3 (resultados com usuários),
retira aquela limitação e entrega à banca um número de satisfação medido, não
inspecionado.

**Status e disciplina de números.** Este é um plano, não um resultado. **Nenhum
número aqui é medição** — tamanhos de amostra, tempos-alvo e limiar de SUS são
parâmetros do desenho, revisáveis, e assim rotulados. Vale a mesma regra da
monografia: quando a avaliação rodar, os números que entrarem na seção 10.3 serão
os medidos, e a análise reportará **mediana e amplitude interquartil**, como o
`medir-desempenho` já faz para o desempenho técnico — média esconde a dispersão, e
dispersão é o que diz se o próximo participante repete o resultado.

---

## 1. Objetivo e perguntas de pesquisa

O objetivo é **formativo**, não somativo: encontrar problemas de uso a corrigir
antes da defesa, e não certificar o sistema. A distinção importa porque decide o
tamanho da amostra e o tipo de análise — um estudo formativo procura problemas,
não estima parâmetros populacionais.

A usabilidade é operacionalizada segundo a ISO 9241‑11 em três dimensões —
**eficácia, eficiência e satisfação** —, e as perguntas de pesquisa são:

- **PP1 (eficácia).** Os profissionais completam as tarefas clínicas centrais —
  cadastro, triagem, prontuário, prescrição, assinatura, dispensação e relatório —
  **sem assistência**?
- **PP2 (eficiência).** Em que tempo, com quantos erros e quantos desvios do
  caminho esperado?
- **PP3 (satisfação).** Qual a satisfação percebida, medida por SUS, e como ela
  varia entre os perfis?
- **PP4 (qualitativa).** Onde estão os pontos de fricção, e qual a sua causa
  provável, segundo o pensar-alto e a entrevista?

Uma quinta pergunta é específica deste sistema e cruza usabilidade com segurança:

- **PP5 (limite compreensível).** Quando o sistema **nega** — escopo territorial
  que esconde registro de outra unidade, sinal vital implausível recusado, envio à
  RNDS em modo simulado —, o usuário **entende** a negação, ou a lê como defeito?
  É a heurística 9 (auxílio no diagnóstico de erros) posta à prova por quem não
  escreveu o código, e toca controles centrais do trabalho.

## 2. Desenho do estudo

**Teste de usabilidade moderado, com pensar-alto (*think-aloud*)**, intra-sujeito
(cada participante executa as tarefas do próprio perfil), presencial ou remoto por
compartilhamento de tela. A escolha é deliberada:

- **Moderado e não automático**, porque o valor formativo está no *porquê* de cada
  travamento, que só o pensar-alto e a observação revelam.
- **Por perfil**, porque o sistema atribui a cada perfil um conjunto distinto de
  telas e permissões (RBAC): medir "o usuário" em abstrato mediria uma pessoa que
  não existe. Recepção, enfermagem, medicina, farmácia e gestão têm tarefas,
  vocabulário e pressões diferentes.
- **Formativo**, porque a defesa é em junho de 2027 e há tempo de corrigir o que o
  estudo achar — o desenho existe para gerar backlog de correção, não só um selo.

## 3. Participantes

**Perfis, espelhando os do sistema** (`utils/rbac.PERFIS`): Recepção, Enfermagem
(triagem), Medicina, Farmácia e Gestão. O perfil de operador da plataforma
(SuperAdmin) e o de administrador de hospital são de configuração, não de uso
clínico contínuo, e ficam fora do teste de tarefas — sua avaliação, se houver, é
separada e centrada em administração de contas e escopo.

**Tamanho da amostra (parâmetro de desenho).** Para estudo formativo, a literatura
(Nielsen; Virzi) indica que ~5 participantes por grupo homogêneo revelam a maior
parte dos problemas de usabilidade; retornos marginais caem rápido depois disso.
Plano: **3 a 5 por perfil**, alvo de **15 a 20 participantes** ao todo. É amostra
de conveniência e propósito, **não** dimensionada para inferência estatística — e
a seção 11 (ameaças) declara isso, em vez de deixar o número sugerir poder que ele
não tem.

**Recrutamento.** Profissionais do SUS da rede de Bom Jesus da Lapa e região, pelos
canais institucionais do campus. Onde o acesso a profissionais em exercício for
inviável no prazo, admite-se **proxy** — discentes concluintes de Enfermagem e
Medicina com estágio em serviço —, registrando a substituição como redução de
validade ecológica (seção 11), nunca omitindo-a.

**Critérios.** Inclusão: exercer (ou estar em formação avançada para) a função do
perfil; consentir por escrito. Exclusão: ter participado do desenvolvimento ou da
inspeção heurística.

**Caracterização (antes das tarefas).** Questionário curto: função, tempo de
experiência, uso prévio de prontuário eletrônico (qual), autoavaliação de
letramento digital. Serve para ler os resultados à luz de quem os produziu — um
SUS baixo de quem nunca usou prontuário eletrônico diz algo diferente do mesmo SUS
vindo de quem usa outro sistema há anos.

## 4. Ética e proteção de dados — o item de maior prazo

**Este é o caminho crítico do cronograma.** Pesquisa com seres humanos no Brasil
exige apreciação por Comitê de Ética em Pesquisa (CEP), pela Plataforma Brasil,
sob as Resoluções CNS 466/2012 e 510/2016 (esta última específica de ciências
humanas e sociais). A aprovação leva semanas a meses, e **nenhuma coleta pode
começar antes dela**. Submeter cedo é a única mitigação.

O projeto de pesquisa submetido inclui: objetivo, método, **Termo de Consentimento
Livre e Esclarecido (TCLE)**, instrumentos, análise de **riscos** (mínimos:
desconforto ou fadiga durante as tarefas; direito de interromper a qualquer
momento sem prejuízo) e de **benefícios** (contribuição para um sistema público de
saúde mais usável).

**Proteção de dados (LGPD).** Um ponto a favor deste estudo: **os pacientes do
ambiente são sintéticos** — decisão de projeto documentada na monografia —, de modo
que **nenhum dado sensível de saúde de pessoa real é manipulado** durante as
tarefas. O dado pessoal em jogo é o **do participante**: gravação de tela e de voz,
questionários. Trata-se com consentimento específico, **anonimização** na análise
(identificador P01…P20, sem nome), guarda em meio restrito e **descarte** ao fim do
prazo declarado no TCLE.

## 5. Ambiente e materiais

**Ambiente.** A instância de demonstração já construída e corrigida no projeto:
rede de estabelecimentos **real**, importada do CNES do Ministério da Saúde
(`flask cnes-importar`), municípios do IBGE, e **pacientes e dados clínicos
sintéticos** semeados (`flask seed`, geradores de triagem/prontuário/agenda/exames).
Uma conta por perfil, com o escopo territorial adequado. **Instância isolada, nunca
produção.**

**Reprodutibilidade entre participantes.** O banco é reposto ao estado inicial
antes de cada sessão, de modo que todos encontrem o mesmo ponto de partida — a
semeadura é idempotente e a carga de volume tem `--limpar`. Sem isso, o segundo
participante mede um sistema de tamanho desconhecido, exatamente o que o protocolo
de `seed-volume` já evita para o desempenho.

**Materiais** (esboços no Anexo): TCLE; questionário de caracterização; roteiro do
moderador; **SUS** em versão validada em português; **SEQ** (pergunta única de
facilidade) por tarefa; planilha de coleta por tarefa (sucesso, tempo, erros,
assistências, incidentes). Dispositivo e navegador padronizados; gravação de tela
e de áudio mediante consentimento.

## 6. Tarefas

Cenários representativos, um conjunto por perfil, ordenados do simples ao complexo.
Cada tarefa declara **critério de sucesso observável** — não "o usuário achou
fácil", mas "o registro foi criado com os campos X e Y". Uma **tarefa de
aquecimento** (login e navegação até a própria área) abre a sessão e **não é
pontuada**, para separar a curva de primeiro contato do que se quer medir.

**Recepção**
1. Cadastrar um paciente novo com CPF e CNS válidos; critério: cadastro criado e
   localizável na busca.
2. Localizar um paciente existente pela busca com sugestão e abrir seu cadastro.
3. Agendar um atendimento para esse paciente.

**Enfermagem (triagem)**
4. Realizar a triagem de um paciente pelo protocolo de Manchester, registrando os
   sinais vitais; critério: triagem salva com classificação de risco.
5. **Tarefa-sonda de PP5:** ao registrar os sinais, digitar deliberadamente uma
   altura implausível (ex.: 172 no campo em metros) e observar se a pessoa
   compreende a recusa e a corrige. Critério: o valor impossível não é gravado, e o
   participante entende por quê.

**Medicina**
6. Abrir o prontuário longitudinal de um paciente e registrar uma evolução.
7. Prescrever um medicamento (busca com apresentação e via) e **assinar** o
   documento; critério: documento assinado.
8. Observar o encaminhamento à RNDS e reconhecer que o envio foi **enfileirado em
   modo simulado** (a tela avisa) — sonda de PP5, heurística 10.

**Farmácia**
9. Dispensar um item prescrito e consultar o estoque resultante.

**Gestão**
10. Ler o relatório de produção (ou territorial) e **exportar em CSV**.
11. **Sonda de PP5 e do isolamento:** com um gestor de escopo de unidade, tentar
    alcançar registro de outra unidade e observar se a ausência do dado é lida como
    limite compreensível ou como defeito — a tela **declara o próprio recorte** de
    propósito, e este é o teste de que a declaração funciona com quem não a
    escreveu.

## 7. Métricas e coleta

**Eficácia (PP1).** Taxa de conclusão por tarefa, em três níveis: **sucesso**,
**sucesso com assistência** (o moderador precisou intervir) e **falha**. A
distinção do nível intermediário importa: tarefa "concluída" só porque o moderador
apontou o caminho não é a mesma coisa que tarefa concluída sozinho.

**Eficiência (PP2).** Tempo-na-tarefa, reportado como **mediana e IQR** por tarefa
e por perfil; número de **erros** (ação que afasta do objetivo); número de
**assistências**; **desvios** do caminho esperado.

**Satisfação (PP3).** **SUS** ao fim da sessão (dez itens, escore 0–100); **SEQ**
(1–7) logo após cada tarefa, enquanto a impressão está fresca. O SEQ localiza a
insatisfação na tarefa; o SUS resume a sessão.

**Qualitativo (PP4, PP5).** Transcrição do pensar-alto; **incidentes críticos**
(momentos de travamento, erro ou surpresa); entrevista semiestruturada de
encerramento. Instrumento **opcional**, a decidir no piloto: NASA‑TLX para carga
percebida, se o tempo de sessão comportar sem fadigar.

## 8. Procedimento da sessão

Duração-alvo ~60–75 min: acolhimento e TCLE (5) → caracterização (5) → aquecimento
não pontuado (5) → tarefas com pensar-alto e SEQ (30–40) → SUS e entrevista (10) →
encerramento (5). **Piloto com 1–2 participantes** antes da coleta, para calibrar
enunciados de tarefa, tempo e instrumentos; dados do piloto **não** entram na
análise principal, salvo se nada mudar após ele.

O moderador segue **roteiro fixo**, não intervém antes de um limite de tempo ou
pedido explícito de ajuda, e registra intervenções como assistências — para não
contaminar a própria medida de eficácia.

## 9. Análise

**Quantitativa, descritiva.** Taxas de conclusão por tarefa e perfil; tempos em
mediana e IQR; contagem de erros e assistências. **Sem inferência estatística
pesada** — a amostra é formativa, e um teste de hipótese sobre 4 participantes por
grupo prometeria o que não pode cumprir.

**SUS.** Escore 0–100 por participante e agregado; interpretação por referência
consolidada (faixa média em torno de 68; classificação adjetiva de Bangor);
leitura **por perfil**, porque um bom escore global pode esconder um perfil mal
atendido.

**Qualitativa.** Análise temática dos incidentes; cada problema recebe
**severidade** (escala 0–4 de Nielsen, combinando frequência, impacto e
persistência), e a lista priorizada vira backlog. **Triangulação:** cruzar o
problema observado (comportamento) com o SEQ/SUS (percepção) e o pensar-alto
(causa) — problema que aparece nas três fontes é o mais confiável.

## 10. Metas do estudo (declaradas, não medidas)

Alvos de referência para orientar a leitura, revisáveis à luz do piloto — **não são
resultados**:

- Conclusão **sem assistência ≥ 80%** nas tarefas centrais de cada perfil.
- **SUS ≥ 68** (média de referência) por perfil.
- Todo problema de **severidade 3–4** endereçado antes da defesa, ou justificado
  como fora de alcance na seção 12.

## 11. Ameaças à validade e limitações

Declaradas aqui para que a seção 10.3 as herde em vez de descobri-las na banca:

- **Amostra pequena e de conveniência:** resultados formativos, não
  generalizáveis. É o desenho, não um defeito dele — mas precisa ser dito.
- **Moderadora é a autora:** risco de viés de condução e de interpretação.
  Mitigação: roteiro fixo, pensar-alto do participante, não intervir antes do
  limite, e — quando possível — um segundo observador independente na análise
  qualitativa.
- **Dados sintéticos:** as tarefas são realistas, mas sem a pressão e a carga
  emocional do atendimento real; e o paciente sintético é decisão de projeto, não
  acidente. A validade é de interface, não de desempenho sob estresse clínico.
- **RNDS simulada:** a tarefa de envio observa o **enfileiramento** e o aviso de
  modo simulado, não o envio real, que exige certificado ICP‑Brasil contra
  homologação. É a mesma fronteira que a monografia já declara.
- **Efeito de aprendizagem e ordem:** contrabalancear a ordem das tarefas quando a
  independência entre elas permitir; onde houver dependência (cadastrar antes de
  triar), a ordem é fixa e declarada.
- **Proxy de participantes**, se usado: reduz a validade ecológica; registrar quais
  participantes eram profissionais em exercício e quais eram concluintes.

## 12. Cronograma (planejado de trás para frente, defesa em junho/2027)

O caminho crítico é a ética. Sugestão de folga generosa:

| Etapa | Duração estimada | Observação |
|---|---|---|
| Submissão e aprovação no CEP (Plataforma Brasil) | 2–3 meses | **começar cedo**; nada roda antes |
| Preparação de instrumentos e ambiente + piloto | 3–4 semanas | calibra tarefas e tempo |
| Coleta (15–20 sessões) | 2–4 semanas | agenda dos participantes é o gargalo |
| Análise e redação da seção 10.3 | 3–4 semanas | mediana/IQR, SUS, temática |
| Correções de usabilidade decorrentes | buffer | severidade 3–4 antes da defesa |

Para não depender de tudo dar certo na primeira tentativa, **iniciar o processo do
CEP com folga** — da ordem de seis a nove meses antes da defesa — é a decisão que
mais reduz risco de cronograma.

## 13. Produtos da execução

Quando este desenho rodar, ele entrega:

- a **seção 10.3** da monografia, com eficácia, eficiência e SUS **medidos** por
  perfil, substituindo a proposta que hoje mora nas seções 12 e 13;
- a **retirada** da limitação de "sem usuários finais" registrada em §10.1;
- um **backlog priorizado** de problemas por severidade, que alimenta a correção
  antes da banca;
- um **número de satisfação citável na defesa** que não é inspeção da autora, mas
  medida de quem usa — que é precisamente o que falta ao capítulo de validação hoje.

---

## Anexo — esboços dos instrumentos

**A. TCLE (estrutura).** Identificação da pesquisa e da instituição; objetivo em
linguagem leiga; procedimentos (tarefas, gravação); riscos e benefícios;
voluntariedade e direito de interromper; sigilo e anonimização; guarda e descarte
dos dados; contatos da pesquisadora e do CEP; duas vias assinadas.

**B. Caracterização.** Função; tempo de experiência na função; usa prontuário
eletrônico hoje? qual?; autoavaliação de letramento digital (escala 1–5).

**C. SEQ (por tarefa).** "No geral, esta tarefa foi:" — de 1 (*muito difícil*) a 7
(*muito fácil*).

**D. SUS (pós-teste).** Os dez itens padrão, alternados entre positivos e
negativos, em escala de 1 (*discordo totalmente*) a 5 (*concordo totalmente*), em
versão validada em português; escore calculado ao fim.

**E. Planilha de coleta (por participante × tarefa).** Colunas: resultado
(sucesso / com assistência / falha), tempo, nº de erros, nº de assistências, SEQ,
incidentes observados.

**F. Roteiro do moderador.** Fala de acolhimento; instrução de pensar-alto;
enunciado de cada tarefa em cartão separado; regra de intervenção (quando e como);
fala de encerramento e roteiro da entrevista semiestruturada.
