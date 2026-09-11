# Análise de lacunas — Certificação SBIS/CFM

Confronto entre os requisitos de certificação de S-RES da SBIS e o que este
repositório efetivamente implementa.

**Fonte:** Planilha de Requisitos v5.2 (SBIS, novembro de 2021), obtida em
<https://sbis.org.br/certificacoes/certificacao-software/manuais-e-listas-de-requisitos/>.
Os requisitos foram extraídos da planilha, não transcritos à mão.

**Escopo.** O sistema é ambulatorial, com pronto-socorro e internação, então
valem três das nove modalidades: **Clínica/Ambulatório**, **Pronto Atendimento**
e **Internação**. Ficam de fora RIS (radiologia), as três de telessaúde,
Consultório Individual e Receita Digital. Filtrando por essas três modalidades
sobram **238 requisitos**: 148 ECF (funcionais), 71 NGS1 (segurança) e 19 NGS2
(certificação digital).

**Situação desta análise:** NGS1 e NGS2 estão avaliados requisito a requisito.
Os 148 do ECF ainda **não** foram — estão na seção final, com o motivo.

---

## Como ler

| Situação | Significado |
|---|---|
| **Atende** | Implementado, com o arquivo ou o teste que prova |
| **Parcial** | Existe, mas falta parte do que o requisito pede — o que falta está dito |
| **Não atende** | Não existe no código |
| **Fora do código** | Requisito de manual, de infraestrutura ou de operação |
| **Não se aplica** | A condição que dispara o requisito não ocorre aqui |

**Nenhum "Atende" está escrito sem evidência.** Requisito cuja verificação eu não
consegui fazer aparece como "a verificar", e não como atendido — o mesmo critério
que o repositório usa para números na monografia.

---

## Resumo

### NGS1 — Nível de Garantia de Segurança 1 (71 requisitos)

| Grupo | Total | Atende | Parcial | Não atende | Outro |
|---|---:|---:|---:|---:|---:|
| 01 Controle de versão do software | 1 | 0 | 1 | 0 | 0 |
| 02 Identificação e autenticação de pessoas | 15 | 4 | 7 | 4 | 0 |
| 03 Autorização e controle de acesso | 8 | 2 | 2 | 4 | 0 |
| 04 Disponibilidade do RES | 6 | 3 | 1 | 2 | 0 |
| 05 Comunicação entre componentes | 4 | 1 | 1 | 0 | 2 |
| 06 Segurança de dados | 3 | 2 | 1 | 0 | 0 |
| 07 Auditoria | 8 | 4 | 3 | 1 | 0 |
| 08 Documentação | 12 | 0 | 1 | 11 | 0 |
| 09 Tempo | 7 | 2 | 1 | 4 | 0 |
| 11 Privacidade | 5 | 1 | 1 | 3 | 0 |
| 12 Integridade | 2 | 0 | 1 | 1 | 0 |
| **Total** | **71** | **19** | **20** | **30** | **2** |

### NGS2 — Certificação digital (19 requisitos)

**16 não atendem, 3 parcialmente.** O bloqueio é único e vale para todos:
o sistema não faz **assinatura digital ICP-Brasil**. O que existe em
`models/lgpd.DocumentoAssinado` é integridade por SHA-256 mais um código de
verificação público — mecanismo legítimo, mas outro. NGS2 pede CAdES/XAdES/PAdES
sob política AD-RB, validação de cadeia de certificação e de revogação, e
exportação verificável no validador do ITI.

---

## NGS1.01 — Controle de versão do software

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 01.01 | Versão do software | **Parcial** | `app.py:128` define `APP_VERSAO = "v2.0.0-flask"`, injetado no contexto dos templates. Falta nome do fornecedor e identificação de build. |

## NGS1.02 — Identificação e autenticação de pessoas

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 02.01 | Método de autenticação | **Atende** | Usuário e senha, com TOTP e gov.br opcionais (`routes/auth.py`). `tests/test_auditoria_estatica.py` reprova rota nova sem `@login_required`. |
| 02.02 | Proteção dos parâmetros | **Atende** | `models/user.py:55` — `generate_password_hash` do Werkzeug (scrypt por padrão, com sal). Nenhuma senha em claro no banco. |
| 02.03 | Qualidade da senha | **Parcial** | Só o mínimo de 8 caracteres (`routes/conta.py:62`, `routes/admin.py:51`). Faltam as classes exigidas (alfabético, numérico, especial) e a parametrização delas. |
| 02.06 | Geração de senha pelo administrador | **Parcial** | O admin define a senha inicial. Falta senha temporária de uso único com troca obrigatória no primeiro acesso. |
| 02.08 | Troca pelo próprio usuário | **Atende** | `routes/conta.py:52`, exigindo a senha atual e confirmação. |
| 02.09 | Troca forçada de senha | **Não atende** | Não há indicador de "trocar no próximo acesso". |
| 02.10 | Periodicidade de troca | **Não atende** | Não há expiração de senha nem parametrização dela. |
| 02.11 | Igualdade de senhas | **Parcial** | `routes/conta.py:71` recusa senha igual à atual. Falta recusar a **imediatamente anterior** — não há histórico de senhas. |
| 02.12 | Obtenção de nova senha | **Não atende** | Não existe "esqueci a senha". Hoje, usuário sem senha depende do administrador. |
| 02.13 | Controle de tentativas | **Parcial** | `utils/seguranca_http.limitar` bloqueia por tentativas e janela, e `routes/auth.py:66` limpa o contador no acerto. O máximo é argumento do decorador, e o requisito pede que seja configurável. |
| 02.14 | Autenticação para operações críticas | **Parcial** | A troca de senha reexige a senha atual. As demais operações da lista (vínculo de certificado, alteração de permissões) não reexigem autenticação. |
| 02.16 | Informações em autenticação inválida | **Atende** | `routes/auth.py:137` — mensagem única, e `_consumir_tempo_de_hash` iguala o tempo de resposta para e-mail inexistente, fechando também o canal lateral de tempo. |
| 02.17 | Revelação de credenciais na interface | **Não atende** | `templates/auth/login.html:110` usa `autocomplete="current-password"`, que **habilita** a memorização pelo navegador. O requisito manda impedi-la. |
| 02.20 | Bloqueio por inatividade | **Parcial** | `config.py:53` — `PERMANENT_SESSION_LIFETIME` de 12 h com `SESSION_REFRESH_EACH_REQUEST`, o que é janela deslizante por inatividade, parametrizável por `SESSION_HOURS`. O requisito pede o parâmetro **no banco**, e 12 h é folgado para um posto de trabalho compartilhado. |
| 02.23 | Segurança contra roubo de sessão | **Parcial** | Cookie `HttpOnly`, `Secure` por padrão, `SameSite=Lax` (`config.py:65`), HSTS e CSP (`utils/seguranca_http.py:52`). Falta rotacionar o identificador de sessão no login. |

## NGS1.03 — Autorização e controle de acesso

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 03.01 | Impedir acesso não autorizado | **Atende** | `@requer_permissao` em toda rota (`utils/rbac.py`), com `tests/test_auditoria_estatica.py` garantindo que rota nova nasça protegida, e RLS no banco por baixo. |
| 03.03 | Gerenciamento de perfis | **Não atende** | Os perfis e suas permissões são constantes em `utils/rbac.py`. O requisito exige cadastrar, ativar/inativar e alterar perfis **pela aplicação**. |
| 03.06 | Papéis relacionados à TI | **Parcial** | Há administrador, e o backup é protegido por permissão. Faltam os papéis distintos de **operador de cópias de segurança** e de **auditor**, e o administrador hoje enxerga dado clínico real — o requisito quer o contrário. |
| 03.07 | Mais de um perfil por usuário | **Não atende** | `models/user.py:16` — `perfil` é coluna única de texto. |
| 03.08 | Gerenciamento de usuários | **Atende** | `routes/admin.py` — cadastro, ativação/inativação e alteração. |
| 03.09 | Identidade única e responsabilização | **Parcial** | Cada usuário é individual e `users.cpf` existe (`models/user.py:49`), mas é nulável e não é exigido no cadastro. |
| 03.10 | Usuário mínimo ativo | **Não atende** | Nada impede inativar o último administrador e deixar o sistema sem quem administre. |
| 03.11 | Restrição de autoconcessão | **Não atende** | Não há impedimento a um administrador alterar as próprias permissões. |

## NGS1.04 — Disponibilidade do RES

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 04.01 | Geração de cópia de segurança | **Atende** | `routes/backup.py`, via `pg_dump` com `PGOPTIONS=-c app.nivel=SISTEMA` e `--enable-row-security`, o que evita dump silenciosamente parcial. |
| 04.02 | Restrição de geração e restauração | **Parcial** | Protegido por permissão RBAC, mas não pelo papel dedicado que o requisito nomeia (ver 03.06). |
| 04.03 | Sigilo da cópia de segurança | **Não atende** | O dump não é cifrado. |
| 04.04 | Restauração | **Atende** | `flask backup-validar` restaura o dump em schema temporário. |
| 04.05 | Integridade na restauração | **Atende** | `backup-validar` confere as contagens da origem contra as do restaurado — backup que nunca foi restaurado é arquivo, não backup. |
| 04.06 | Alerta de limiar de ocupação | **Não atende** | Não há monitoração de espaço nem notificação ao administrador. |

## NGS1.05 — Comunicação entre componentes

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 05.01 | Segurança da comunicação com o cliente | **Parcial** | HSTS, CSP e cookies seguros em `utils/seguranca_http.py`. O TLS em si é do servidor de implantação, não da aplicação. |
| 05.02 | Processamento no lado servidor | **Atende** | Toda mutação passa por rota Flask; os templates renderizam no servidor. |
| 05.03 | Segurança entre componentes | **Fora do código** | Depende de `sslmode` na `DATABASE_URL` e da rede. Cabe no manual de instalação, que não existe (08.05). |
| 05.04 | Integridade de componentes dinâmicos | **Não se aplica** | Não há componente baixado para executar no cliente. |

## NGS1.06 — Segurança de dados

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 06.01 | Utilização de SGBD | **Atende** | PostgreSQL via SQLAlchemy; os PDFs emitidos ficam na própria base (`models/lgpd.DocumentoAssinado`). |
| 06.03 | Validação de dados de entrada | **Parcial** | Não há injeção de SQL — tudo passa por consulta parametrizada do SQLAlchemy — e há CSRF em todo formulário. A validação de conteúdo por campo é irregular; `tests/test_contrato_formularios.py` cobre o descarte de campo, não o formato. |
| 06.04 | Segregação por organização | **Atende** | É o ponto mais forte do sistema: RLS em 23 tabelas com `FORCE`, falha fechada sem escopo definido, e `tests/test_rls_negacao.py` medindo a **negação** direto no banco, sem passar pelo filtro em Python. |

## NGS1.07 — Auditoria

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 07.01 | Auditoria contínua | **Atende** | `utils/audit.registrar` grava na mesma transação da mutação, e não há chave para desligar. |
| 07.02 | Proteção dos registros | **Atende** | Encadeamento por hash (`utils/audit.py`), âncoras em journal só de acréscimo (`flask auditoria-ancora`) e `flask hardening-check` conferindo que a tabela não pertence ao papel da aplicação. |
| 07.03 | Eventos do RES | **Parcial** | Criação, consulta, alteração e inativação são registradas. Faltam **impressão** de registro, importação/exportação e solicitação de acesso de emergência (que não existe — ver 11.07). |
| 07.04 | Eventos avançados | **Não atende** | Não se registra encerramento nem bloqueio de sessão, nem o aceite do termo de uso. |
| 07.05 | Informações do registro | **Atende** | `models/audit_log.py` guarda id, data/hora, ação, usuário, IP (com `X-Forwarded-For`), tabela e registro afetado. |
| 07.06 | Privacidade do paciente na trilha | **Atende** | Corrigido: dezesseis chamadas gravavam nome do paciente ou conteúdo clínico na descrição — a de `routes/ps.py` gravava nome **e** queixa. Hoje a trilha registra que o evento ocorreu, e o par (`tabela`, `registro_id`) aponta o registro. `tests/test_auditoria_privacidade.py` trava a regressão em duas camadas: varredura estática do AST de toda chamada a `registrar()` contra as tabelas que o metadata diz terem `paciente_id`, e leitura da trilha gravada depois de abrir telas de paciente. |
| 07.07 | Visualização dos registros | **Parcial** | `routes/auditoria.py:26` lista em ordem cronológica e filtra por período, ação, tabela e texto livre. A alínea (c) pede também filtro pelo **identificador único do usuário** e pelo **identificador do registro**, que a tela não oferece. |
| 07.08 | Exportação em formato aberto | **Parcial** | `routes/exportacao.py:125` exporta a trilha em CSV com filtragem. Falta incluir no arquivo a identificação do software exigida pela alínea (c). |

## NGS1.08 — Documentação

Onze dos doze não atendem, e o motivo é o mesmo: **não existem manuais**. O que
há é `README.md` e `AGENTS.md`, que documentam o desenvolvimento, não a operação.

| ID | Requisito | Situação |
|---|---|---|
| 08.01 | Tópicos dos manuais (uso, instalação, administração) | **Não atende** |
| 08.02 | Referência à versão do software na documentação | **Não atende** |
| 08.03 | Operações de backup no manual de instalação | **Não atende** |
| 08.04 | Restrição de acesso a entidades não autorizadas | **Não atende** |
| 08.05 | Configuração de segurança entre componentes | **Não atende** |
| 08.06 | Sincronização de relógio (UTC/NTP) | **Não atende** |
| 08.07 | Guarda da cópia de segurança | **Não atende** |
| 08.08 | Segregação dos componentes | **Não atende** |
| 08.09 | Importação de dispositivos externos | **Não se aplica** (contado como não atende por conservadorismo) |
| 08.10 | Idioma português | **Não atende** (não há manual para estar em português) |
| 08.11 | Recomendações de configuração de segurança | **Não atende** |
| 08.12 | Histórico de alterações (*release notes*) | **Parcial** — o histórico do Git é descritivo e datado, mas não é documento com impacto e restrições de compatibilidade |

Vale registrar o contraste: parte substancial do conteúdo desses manuais **já
está escrita** em `AGENTS.md` — o procedimento de implantação com `chattr +a`, os
cron de emissão e verificação de âncora, a custódia externa do hash, o que o
`hardening-check` confere. Falta reorganizar por destinatário, não descobrir.

## NGS1.09 — Tempo

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 09.01 | Fonte temporal | **Parcial** | Todo carimbo vem de `datetime.utcnow()` no servidor, nunca do cliente. A sincronização por NTP é do ambiente. |
| 09.02 | RFC 3339 na exportação | **Não atende** | Os recursos FHIR passaram a sair conformes (`_instante` em `routes/rnds.py`), mas a exportação CSV de `routes/exportacao.py` não segue o formato. |
| 09.03 | Registro de tempo no banco com fuso | **Não atende** | As colunas são `db.DateTime` sem `timezone=True`, gravando UTC ingênuo. **É a raiz do defeito que o validador FHIR encontrou**: sem fuso na origem, o `isoformat()` saía sem fuso e produzia `dateTime` inválido. Hoje o fuso é acrescentado na borda; o requisito quer na coluna. |
| 09.04 | Entrada de data dd/mm/aaaa | **Atende** | Campos `type="date"` e conversão em `utils/datas.py`. |
| 09.05 | Exibição de data dd/mm/aaaa | **Atende** | Formatação centralizada em `utils/datas.py`. |
| 09.06 | Time zone e local da instituição | **Não atende** | Não há parametrização de fuso por unidade — relevante num sistema que se propõe nacional. |
| 09.07 | Ajuste automático de horário de verão | **Não atende** | Sem tratamento, ainda que o Brasil não adote horário de verão desde 2019. |

## NGS1.11 — Privacidade

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 11.01 | Concordância com termos de uso | **Não atende** | Não há termo apresentado no primeiro acesso do **usuário do sistema**. O que existe é consentimento do **paciente**, que é outra coisa. |
| 11.05 | Consentimento do paciente | **Parcial** | `routes/consentimentos.py` registra finalidade, status e versão do termo. Falta o *upload* de consentimento assinado e digitalizado. |
| 11.06 | Revogação de consentimento | **Atende** | `routes/consentimentos.py:127` — revoga com carimbo de tempo, responsável e registro em auditoria, e recusa revogar o que não é revogável, explicando por quê. |
| 11.07 | Acesso de emergência | **Não atende** | **Não existe** *break-glass*. Hoje, profissional sem permissão simplesmente não acessa — o que é seguro e clinicamente errado numa emergência. |
| 11.09 | Setores autorizados a ver o prontuário | **Não atende** | O escopo é territorial e por unidade, não por setor. Não há como restringir o prontuário da UTI aos setores que precisam dele. |

## NGS1.12 — Integridade

| ID | Requisito | Situação | Evidência / o que falta |
|---|---|---|---|
| 12.01 | Correção de dados finalizados | **Parcial** | `prontuarios.assinado` marca o fechamento. Faltam as três exigências: só o autor corrige, a correção gera **nova versão** e exige justificativa. |
| 12.03 | Inativação de registros finalizados | **Não atende** | Não há inativação com justificativa para prescrições, sinais vitais, diagnósticos e documentos. |

---

## NGS2 — Certificação digital (19 requisitos)

| ID | Requisito | Situação |
|---|---|---|
| 01.01 | Certificado ICP-Brasil para assinatura | **Não atende** |
| 01.02 | Validação do CPF do usuário contra o certificado | **Não atende** |
| 01.03 | Validação do certificado e da cadeia antes do uso | **Não atende** |
| 01.05 | Compatibilidade com duas ACs de 1º nível | **Não atende** |
| 02.01 | Formato CAdES/XAdES/PAdES, política AD-RB | **Não atende** |
| 02.02 | Verificação do propósito do certificado | **Não atende** |
| 02.03 | Instante da assinatura | **Não atende** |
| 02.04 | Visualização do que será assinado | **Não atende** |
| 02.06 | Aviso de registro pendente de assinatura | **Não atende** |
| 02.09 | Informações sobre a assinatura | **Parcial** — há status de assinado e página pública de verificação (`routes/documentos.py`), mas a informação exibida é de hash, não de assinatura |
| 03.01 | Validação da assinatura | **Não atende** |
| 03.02 | Referência temporal para revogação | **Não atende** |
| 03.04 | Resultado da validação | **Não atende** |
| 06.01 | Validação de assinatura em documentos importados | **Não atende** |
| 06.03 | Exportação verificável externamente (ITI) | **Não atende** |
| 06.05 | Impressão de registros assinados | **Parcial** — o PDF sai com código de verificação impresso |
| 06.06 | Mensagem de rodapé na impressão | **Parcial** — há rodapé, com texto diferente do exigido |
| 06.07 | Relatório de assinaturas | **Não atende** |
| 07.01 | Certificado digital para autenticação | **Não atende** |

**Conclusão do bloco.** NGS2 não é alcançável por incremento: exige biblioteca de
assinatura ICP-Brasil, consulta a listas de revogação e mídia criptográfica
(token, cartão ou HSM) na mão do profissional. **NGS1 é o alvo realista**, e é
onde o trabalho já está concentrado.

---

## ECF — requisitos funcionais (148, pendentes)

Os 148 requisitos funcionais estão extraídos e disponíveis, mas ainda não
confrontados com o código. Os grupos, com o número de requisitos de cada um:

| Grupo | Nº | Grupo | Nº |
|---|---:|---|---:|
| Documentação Clínica | 37 | Gestão de Atendimentos | 7 |
| Estrutura e Qualidade de Registros | 16 | Cadastros de Substâncias e Exames | 4 |
| Identificação de Pacientes | 14 | Direitos do Paciente | 4 |
| Apoio à Decisão Clínica | 13 | Administração de Produtos | 4 |
| Pronto Atendimento | 13 | Identificação de Estabelecimentos | 4 |
| Prescrição Eletrônica | 10 | Uso Secundário de Dados | 4 |
| Solicitações e Resultados de Exames | 8 | Farmácia | 3 |
| | | Identificação de Profissionais | 3 |
| | | Notas e Comunicação | 2 |
| | | Agendamento | 1 |
| | | Ciclo de Vida de Registros Clínicos | 1 |

Não foram avaliados porque cada um exige percorrer o módulo correspondente, e
declará-los atendidos por semelhança de nome seria repetir exatamente o defeito
que este repositório passou a caçar: afirmar sobre o sistema o que não foi
medido.

---

## O que fazer com isto

**Barato e de efeito imediato**

1. ~~**07.06 — tirar o nome do paciente da trilha de auditoria.**~~ **Feito.**
   Eram dezesseis chamadas, não dez, e uma delas gravava também a queixa
   clínica. O detector previsto existe e reprova violação plantada.
2. **02.17 — `autocomplete="off"` na tela de login.** Uma linha.
3. **03.10 e 03.11 — último administrador e autoconcessão.** Duas verificações em
   `routes/admin.py`, ambas testáveis.
4. **07.08 — identificação do software no CSV exportado.** `APP_VERSAO` já existe.

**Médio, e cada um vira seção da monografia**

5. **02.03, 02.09 a 02.12 — política de senha completa**, com histórico,
   expiração, troca forçada e recuperação. Cinco requisitos de uma vez.
6. **11.07 — acesso de emergência.** É o requisito mais interessante do conjunto,
   porque é o contrário de tudo o que o sistema faz: exige **abrir** o que o RBAC
   fecha, registrando quem abriu, por quê, e avisando depois. Discutir a tensão
   entre falha fechada e emergência clínica é bom material de defesa.
7. **09.03 — `timezone=True` nas colunas de data.** É migração e ajuste de
   borda, e fecha na origem o defeito que o validador FHIR pegou.
8. **03.03 e 03.07 — perfis geridos pela aplicação e múltiplos por usuário.**
   Mexe no RBAC, que hoje é constante em código.

**Grande**

9. **NGS1.08 — os manuais.** Onze requisitos, e é escrita, não programação. Boa
   parte do conteúdo já está em `AGENTS.md`.
10. **12.01 e 12.03 — versionamento de registro clínico.** Correção que gera nova
    versão com justificativa é mudança de modelagem, não de tela.

**Fora de alcance**

11. **NGS2 inteiro.** Depende de certificado ICP-Brasil em mídia criptográfica.
    Cabe declarar como limitação, não como trabalho futuro vago.

---

*Levantamento de 28 de agosto de 2026, contra a versão do repositório desta data.
Os requisitos vieram da planilha oficial; as classificações são deste
levantamento e devem ser refeitas quando o código mudar.*
