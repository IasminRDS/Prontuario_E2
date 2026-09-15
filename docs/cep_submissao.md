# Submissão ao CEP — rascunho

**O que é este documento.** É o rascunho do pacote a submeter ao Comitê de Ética
em Pesquisa (CEP) pela **Plataforma Brasil**, derivado do desenho em
`docs/avaliacao_usabilidade.md`. Reúne as duas peças que a pesquisadora redige — o
**Projeto de Pesquisa detalhado** e o **Termo de Consentimento Livre e Esclarecido
(TCLE)** — e a lista dos demais itens do pacote.

**Como usar.** Tudo entre colchetes `[...]` é um campo a preencher — dado que este
documento não tem como conhecer (orientador(a), datas, contatos, CNPJ, o CEP de
referência). Não invente nenhum: cada um vem de você, da coordenação de pesquisa
do campus ou do próprio CEP. **Nenhum número de resultado aparece aqui** — é uma
proposta; os números medidos só existem depois de o estudo rodar.

**Enquadramento (a confirmar com o CEP).** Avaliação de usabilidade com
profissionais como participantes costuma tramitar sob a **Resolução CNS 510/2016**
(ciências humanas e sociais), com a **466/2012** e a **CNS 580/2018** como
referência geral quando aplicável. Qual resolução rege é decisão do CEP a partir do
projeto; o texto abaixo atende às duas.

---

## Pacote da submissão (checklist)

Na Plataforma Brasil, a pesquisadora responsável **precisa ter vínculo e CV Lattes
cadastrado**; um(a) discente entra como **assistente/pesquisador**, e o(a)
orientador(a) costuma figurar como **pesquisador(a) responsável**. Confirme esse
arranjo com a coordenação de pesquisa do campus.

1. **Folha de Rosto** — gerada pela própria Plataforma Brasil ao final do
   cadastro; impressa, assinada pelo(a) pesquisador(a) responsável e pela
   autoridade da instituição proponente, e reenviada digitalizada.
2. **Projeto de Pesquisa detalhado** — a peça abaixo (§ Projeto de Pesquisa).
3. **TCLE** — a peça abaixo (§ TCLE), uma via por participante, duas cópias.
4. **Instrumentos de coleta** — questionário de caracterização, SUS, SEQ, roteiro
   do moderador e planilha (esboços no Anexo de `avaliacao_usabilidade.md`).
5. **Termo de Anuência / Autorização da instituição coparticipante** — se a coleta
   ocorrer em unidade de saúde ou usar profissionais de um serviço, aquele serviço
   é **coparticipante** e assina anuência. Se a coleta ocorrer inteiramente no
   campus, com a instância de demonstração do próprio trabalho, não há
   coparticipante — declare isso explicitamente.
6. **Cronograma** e **orçamento** (§ correspondentes abaixo).
7. **Currículo Lattes** dos pesquisadores (vinculado na plataforma).

---

## Projeto de Pesquisa

### 1. Identificação

- **Título:** Avaliação de usabilidade de um sistema de prontuário eletrônico
  hospitalar do SUS com profissionais de saúde.
- **Pesquisador(a) responsável:** [orientador(a) — nome, titulação, vínculo].
- **Pesquisador(a) assistente:** Iasmin Ribeiro de Souza, discente do curso
  [curso], Instituto Federal de Educação, Ciência e Tecnologia Baiano (IF Baiano),
  Campus Bom Jesus da Lapa.
- **Instituição proponente:** IF Baiano — Campus Bom Jesus da Lapa.
- **Instituição(ões) coparticipante(s):** [nome do serviço de saúde, se houver;
  senão, "não há — a coleta ocorre no campus, em instância de demonstração"].
- **Financiamento:** recursos próprios da pesquisadora; sem financiamento externo.

### 2. Introdução e justificativa

O sistema avaliado é um prontuário eletrônico hospitalar de código próprio,
desenvolvido como trabalho de conclusão de curso, com aderência ao vocabulário e
aos fluxos do Sistema Único de Saúde (triagem com classificação de risco de
Manchester, prontuário longitudinal, prescrição e assinatura, integração com a
Rede Nacional de Dados em Saúde). Sua qualidade de uso foi verificada até aqui por
**inspeção heurística conduzida pela própria autora** — método que indica
conformidade com princípios de projeto, mas não substitui a avaliação por
**usuários finais**, cuja ausência o próprio trabalho registra como limitação.

Sistemas de informação em saúde mal usados não falham de modo visível: produzem
lentidão, erro de registro e contorno de fluxo no momento do atendimento, sem gerar
mensagem de erro. Avaliar a usabilidade com quem de fato exerce as funções —
recepção, enfermagem, medicina, farmácia e gestão — é o que distingue um sistema
que parece usável de um que é usável. Esta pesquisa produz essa evidência.

### 3. Objetivos

**Geral.** Avaliar a usabilidade do sistema com profissionais dos perfis reais que
ele atende, nas dimensões de eficácia, eficiência e satisfação (ISO 9241‑11).

**Específicos.**
- Medir a taxa de conclusão das tarefas clínicas centrais, com e sem assistência.
- Medir o tempo e os erros por tarefa e por perfil.
- Medir a satisfação percebida (System Usability Scale — SUS).
- Identificar e priorizar, por severidade, os pontos de fricção de uso.
- Verificar se as negações deliberadas do sistema — recorte territorial de acesso,
  recusa de sinal vital implausível, aviso de envio em modo simulado — são
  **compreendidas** pelo participante, e não lidas como defeito.

### 4. Metodologia

**Desenho.** Estudo **formativo** de usabilidade, com **teste moderado** e
**pensar-alto** (*think-aloud*), intra-sujeito, presencial ou remoto por
compartilhamento de tela. Formativo porque o objetivo é encontrar problemas a
corrigir, não certificar; moderado porque o valor está no *porquê* de cada
travamento.

**Participantes.** Profissionais (ou, na indisponibilidade, discentes concluintes
com estágio em serviço, hipótese registrada como redução de validade ecológica)
dos perfis Recepção, Enfermagem, Medicina, Farmácia e Gestão. **Tamanho amostral:**
3 a 5 por perfil, alvo de 15 a 20 participantes, conforme prática consolidada em
estudos formativos de usabilidade (Nielsen; Virzi), em que ~5 participantes por
grupo revelam a maior parte dos problemas. A amostra é de conveniência e propósito,
não dimensionada para inferência estatística — o que a análise respeita.

- **Inclusão:** exercer (ou estar em formação avançada para) a função do perfil;
  concordar com o TCLE.
- **Exclusão:** ter participado do desenvolvimento do sistema ou da inspeção
  heurística anterior.

**Recrutamento.** Convite pelos canais institucionais do campus e, quando houver
coparticipante, do serviço de saúde. Participação voluntária, sem remuneração.

**Local.** [Sala do Campus Bom Jesus da Lapa / dependência do serviço
coparticipante], em **instância de demonstração isolada** do sistema — nunca
ambiente de produção. A instância usa **pacientes e dados clínicos sintéticos**; a
rede de estabelecimentos é pública (CNES/IBGE). O banco é reposto ao estado inicial
antes de cada sessão.

**Procedimento (sessão de ~60–75 min).** Acolhimento e assinatura do TCLE →
questionário de caracterização → tarefa de aquecimento (não pontuada) → tarefas do
perfil, com pensar-alto e SEQ por tarefa → SUS e entrevista de encerramento. As
tarefas espelham fluxos reais: cadastro e busca de paciente; triagem com sinais
vitais; prontuário, prescrição e assinatura; dispensação; relatório e exportação.
Um **piloto** com 1–2 participantes precede a coleta, para calibrar enunciados e
tempo.

**Instrumentos.** Questionário de caracterização; System Usability Scale (SUS) em
versão validada em português; Single Ease Question (SEQ); roteiro do moderador;
planilha de coleta (sucesso, tempo, erros, assistências, incidentes). Gravação de
tela e de áudio **mediante consentimento específico** no TCLE.

**Desfechos.** *Primário:* satisfação (escore SUS por perfil e agregado).
*Secundários:* taxa de conclusão por tarefa; tempo (mediana e amplitude
interquartil); número de erros e de assistências; lista priorizada de problemas por
severidade.

**Análise.** Quantitativa descritiva — taxas de conclusão, tempos em **mediana e
amplitude interquartil**, contagens de erro —, sem inferência estatística sobre
amostra formativa. SUS interpretado por referência consolidada e por perfil.
Qualitativa por análise temática dos incidentes, com severidade na escala 0–4 de
Nielsen, triangulando comportamento observado, percepção (SUS/SEQ) e pensar-alto.

### 5. Riscos e benefícios

**Riscos (mínimos, e ainda assim nomeados).** Toda pesquisa com pessoas tem risco.
Aqui, os previsíveis são: **desconforto, fadiga ou constrangimento** por executar
tarefas sendo observado e gravado, e eventual frustração diante de uma tarefa
difícil. **Mitigação:** o participante é informado de que quem está sendo avaliado
é o **sistema, não ele**; pode interromper qualquer tarefa ou a sessão a qualquer
momento, sem justificativa e sem prejuízo; as pausas são livres. Há ainda o risco
de **quebra de sigilo dos dados do participante** (gravações, questionários),
mitigado por anonimização (identificador P01…P20), guarda em meio restrito e
descarte no prazo declarado. **Não há risco de exposição de dado de saúde de
terceiros:** os pacientes do ambiente são **sintéticos**, por decisão de projeto.

**Benefícios.** Não há benefício direto ao participante. O benefício é **indireto e
coletivo:** contribuir para que sistemas de informação do SUS sejam mais usáveis e
seguros, reduzindo erro e retrabalho no atendimento. O participante recebe, se
desejar, a devolutiva dos resultados.

**Ressarcimento e indenização.** A participação não gera custo previsto; havendo
qualquer despesa decorrente exclusivamente da participação (por exemplo,
deslocamento), ela será **ressarcida**. Fica assegurado o direito a **indenização**
por eventuais danos comprovadamente decorrentes da participação, nos termos da
Resolução CNS 466/2012.

### 6. Confidencialidade e proteção de dados (LGPD)

Os dados dos participantes são tratados sob a Lei Geral de Proteção de Dados (Lei
13.709/2018), com finalidade específica (esta pesquisa), **anonimização** na
análise e na divulgação, acesso restrito à equipe de pesquisa, e **guarda por [5]
anos** seguida de descarte definitivo. Nenhum participante é identificado em
publicação. As gravações servem apenas à análise e não são divulgadas.

### 7. Critérios de suspensão e encerramento

A participação encerra-se a pedido do participante, a qualquer momento. A pesquisa
encerra-se ao atingir o número previsto de participantes ou a saturação dos
achados. Suspende-se se surgir risco não previsto aos participantes.

### 8. Cronograma

Planejado de trás para frente a partir da defesa (junho de 2027), com folga no
caminho crítico (aprovação ética). Datas a preencher.

| Etapa | Período estimado |
|---|---|
| Submissão e aprovação no CEP (Plataforma Brasil) | [início] — [+2 a 3 meses] |
| Preparação de instrumentos e ambiente + piloto | [ ] |
| Coleta (15–20 sessões) | [ ] |
| Análise e redação dos resultados | [ ] |
| Correções de usabilidade decorrentes | [ ] |

**Nenhuma coleta se inicia antes da aprovação do CEP.**

### 9. Orçamento

Recursos próprios. Itens previstos: [material de consumo, se houver],
[deslocamento], [ressarcimento a participantes]. Sem financiamento externo.

### 10. Bibliografia (referência)

ISO 9241‑11; NIELSEN, J. *Usability Engineering*; BROOKE, J. *SUS: A quick and
dirty usability scale*; SAURO, J.; LEWIS, J. R. *Quantifying the User Experience*;
BRASIL. Resolução CNS 466/2012; Resolução CNS 510/2016; Lei 13.709/2018 (LGPD).
[Completar no formato ABNT e alinhar com a `docs/LEITURAS.pdf`.]

---

## TCLE — Termo de Consentimento Livre e Esclarecido

> Documento em duas vias de igual teor, uma para o participante e uma para o
> pesquisador. Redija em fonte legível; substitua os `[...]`.

**Título da pesquisa:** Avaliação de usabilidade de um sistema de prontuário
eletrônico hospitalar do SUS com profissionais de saúde.

**Pesquisador(a) responsável:** [nome], [vínculo] — telefone [ ], e‑mail [ ].
**Pesquisadora assistente:** Iasmin Ribeiro de Souza — e‑mail
20241BJL04GT0005@alunos.ifbaiano.edu.br.
**Instituição:** IF Baiano — Campus Bom Jesus da Lapa.

Você está sendo convidado(a) a participar, de forma **voluntária**, desta pesquisa.
Leia este termo com calma e pergunte o que quiser antes de decidir.

**Por que esta pesquisa é feita.** Para avaliar se um sistema de prontuário
eletrônico é fácil e seguro de usar por profissionais como você, e para descobrir o
que nele precisa melhorar.

**O que você fará.** Em uma sessão de cerca de **60 a 75 minutos**, você usará o
sistema para realizar tarefas parecidas com as do seu trabalho (por exemplo,
registrar uma triagem ou consultar um prontuário) e responderá a dois breves
questionários sobre a facilidade de uso. Pediremos que **fale em voz alta** o que
pensa enquanto usa. **A tela e o áudio serão gravados** apenas para a análise.

**Importante:** quem está sendo avaliado é o **sistema, não você**. Não há resposta
certa ou errada, e os pacientes usados nas tarefas são **fictícios** — nenhum dado
real de paciente é acessado.

**Riscos.** Os riscos são mínimos: você pode sentir cansaço ou desconforto por
estar sendo observado(a). Pode **parar qualquer tarefa ou a sessão a qualquer
momento**, sem precisar explicar e sem qualquer prejuízo.

**Benefícios.** Você não terá benefício direto. Sua participação ajuda a tornar
sistemas de saúde pública mais fáceis e seguros de usar. Se quiser, receberá um
resumo dos resultados.

**Sigilo.** Seus dados serão tratados com **sigilo** e **anonimizados**: você não
será identificado(a) em nenhum documento ou publicação. As gravações servem só à
análise, serão guardadas em local restrito por [5] anos e depois **destruídas**,
conforme a Lei Geral de Proteção de Dados.

**Custos e ressarcimento.** Não há custo para participar. Qualquer despesa que você
tenha por causa da participação será **ressarcida**. Você tem direito a
**indenização** por eventuais danos comprovadamente decorrentes da pesquisa.

**Dúvidas.** Fale com a pesquisadora pelos contatos acima. Sobre questões éticas,
procure o **[Comitê de Ética em Pesquisa — nome, endereço, telefone, e‑mail e
horário de atendimento]**.

**Consentimento.** Declaro que li (ou me foi lido) este termo, que minhas dúvidas
foram esclarecidas e que concordo em participar voluntariamente. Recebi uma via
deste documento.

Autorizo a gravação de tela e áudio para fins de análise: ( ) Sim ( ) Não

______________________________   ______________________________   Data: __/__/____
Participante                     Pesquisador(a)

---

### Observações para a submissão

- **Não preencha resultado nenhum** neste pacote — CEP avalia o **projeto**, não
  achados.
- Confirme com a coordenação de pesquisa do campus **quem é o(a) pesquisador(a)
  responsável** na Plataforma Brasil (em geral o(a) orientador(a), não o(a)
  discente) e se o IF Baiano tem **CEP próprio ou de referência**.
- Se algum profissional de um serviço de saúde participar **na condição de
  profissional daquele serviço**, o serviço é **coparticipante** e assina **Termo
  de Anuência** — providencie antes da submissão.
- A **Folha de Rosto** sai da própria Plataforma Brasil ao final do cadastro do
  projeto; ela exige as assinaturas institucionais, que levam tempo — some esse
  prazo ao do parecer do CEP.
