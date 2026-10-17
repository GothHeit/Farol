# Rastreabilidade — visão do Mentor, v4.0

Referência: `Farol_Documento_de_Requisitos_v4.pdf`, versão 4.0, 17/10/2026, 12 páginas, lido no workspace. O arquivo DOCX não estava disponível. Os identificadores abaixo seguem o PDF, inclusive RFs cuja entrega integral pertence ao futuro aplicativo do Aluno ou à gestão administrativa completa.

**Implementado** significa fluxo disponível no recorte desta tarefa com persistência/serviço aplicável; **Parcial** indica limite expresso; **Pendente** indica ausência de entrega funcional. Dados sintéticos não representam uma integração externa, teste com pessoas ou validação de eficácia pedagógica. A cobertura de RF/CA não constitui homologação de produção.

## Requisitos funcionais

| ID | Requisito resumido | Estado | Evidência e limite |
|---|---|---|---|
| RF-01 | Consolidar sinais acadêmicos e de execução | Implementado | Registros persistentes, períodos, presença, avaliações, estudo, questões, mensagens e tarefas; carteira/detalhe usam a API. |
| RF-02 | Histórico temporal individual | Implementado | Períodos semanais, comparação própria, avaliações e revisões preservados. |
| RF-03 | Curso, disponibilidade e plantões | Parcial | Contexto sintético persistente e consultável pelo mentor; cadastro completo pelo aluno fica para integração futura. |
| RF-04 | Causas de erros informadas pelo aluno | Parcial | Contrato de sessões/questões aceita conteúdo, leitura, descuido e tempo; interface móvel de registro pendente. |
| RF-05 | Relacionar causa, tempo e tema da questão | Implementado | Questões persistem contexto, tema, tempo e causa registrada; consulta no detalhe. |
| RF-06 | Distinguir estudo de simulado | Implementado | Contexto obrigatório; somente questões de estudo entram no sinal de questões difíceis puladas. |
| RF-07 | Consulta TRI e pesos de curso quando existentes | Parcial | Estado explícito “dados indisponíveis”; nenhuma fonte oficial foi inventada ou importada. |
| RF-08 | Comparar histórico com parâmetros ativos | Implementado | Motor puro; janelas e mínimo de histórico configuráveis; ausência/zero de referência não fabrica queda. |
| RF-09 | Detectar alterações acadêmicas/operacionais | Implementado | Regras de presença, cronograma, acesso, questões, horário, avaliações e tarefas. Mensagens sem resposta ficam desabilitadas até aprovação de quantidade/prazo. |
| RF-10 | Classificação configurável | Implementado | Níveis calculados por configuração validada; estado “sem dados” separado. |
| RF-11 | Padrões objetivos, sem perfis psicológicos | Implementado | Evidências numéricas e descrições neutras; interpretação é campo de autoria do mentor. |
| RF-12 | Explicação com evidências, parâmetros e versão | Implementado | Snapshot de configuração, regras e valores em cada avaliação/alerta. |
| RF-13 | Interpretação e decisão do mentor | Implementado | Triagem manual e campos vazios; sem recomendações automáticas. |
| RF-14 | Observar no resumo, Atenção na fila, Prioridade no dia | Implementado | Resumo separado e aviso in-app persistente com timestamp da detecção. Não há envio externo. |
| RF-15 | Resumo semanal e evolução após ação | Implementado | Totais persistentes e comparação factual; “melhora” não é julgamento automático de eficácia. |
| RF-16 | Painel limitado à carteira | Implementado | Autorização por vínculo no servidor, pesquisa, filtros e evidências. |
| RF-17 | Revisão humana e decisão independente | Implementado | Consulta do alerta e registro manual de interpretação/acompanhamento/ação. |
| RF-18 | Registrar intervenção com autoria e vínculo | Implementado | Intervenção persistente com autor, data, conteúdo e alerta opcional. |
| RF-19 | Histórico do alerta, ação e resultados | Implementado | Detalhe relaciona alertas, triagens, intervenções e períodos seguintes. |
| RF-20 | Comparação factual na semana seguinte | Implementado | Valores antes/depois e dados ausentes explícitos; nenhum veredito sobre eficácia. |
| RF-21 | Avaliação útil/não útil | Implementado | Triagem persistida por autor; não altera pesos automaticamente. |
| RF-22 | Redigir e publicar relatório semanal | Implementado | Editor humano, período, revisões e publicação autenticada. |
| RF-23 | Validação explícita antes de disponibilizar | Implementado | Estados rascunho/revisado/publicado e registro do revisor; publicação exige revisão. |
| RF-24 | Mesmo relatório para menor e responsáveis | Implementado | Acesso autenticado por concessão explícita; mesmo snapshot publicado; nenhum canal externo configurado. |
| RF-25 | Adulto é destinatário do próprio relatório | Implementado | Concessões de responsáveis não se aplicam a adultos. |
| RF-26 | Linguagem não estigmatizante | Implementado | Textos da plataforma neutros; texto livre continua de autoria e responsabilidade do mentor. |
| RF-27 | Falsos alarmes, não detectados e antecedência | Parcial | Modelo de eventos rotulados e cálculo quando há rótulos; sem rótulos, informa insuficiência. Definições locais são provisórias, não validadas em piloto. |
| RF-28 | Análise sintética e piloto posterior | Parcial | Seed reproduzível e testes sintéticos; piloto com mentores não realizado. |
| RF-29 | Utilidade apoia revisão manual de regras | Implementado | Avaliações disponíveis para análise; só Admin modifica/ativa configurações. |
| RF-30 | Autenticação distinta do Administrador | Implementado | Papel admin com sessão e interface de regras segregada; não implica gestão integral. |
| RF-31 | Gestão de contas e desativação | Pendente | Contas de demonstração pelo seed; não há fluxo integral de cadastro/edição/desativação. |
| RF-32 | Criar/consultar/atualizar vínculos e isolar carteira | Implementado | Interface e contrato administrativo substituem o vínculo do aluno com justificativa; RBAC aplicado a cada recurso. Não inclui cadastro completo de contas. |
| RF-33 | Indicadores de operação da mentoria | Parcial | Dados de qualidade e regras; painel de gestão e métricas de negócio não entregues. |
| RF-34 | Interface de parametrização e versões | Implementado | Consultar, alterar rascunho, validar, simular, ativar e restaurar sem redeploy. |
| RF-35 | Qualidade operacional das fontes | Parcial | Origem, atualização e ausência de sinais no detalhe; painel operacional integral pendente. |
| RF-36 | Consulta à auditoria crítica | Implementado | Histórico administrativo com ator, instante, justificativa e antes/depois minimizado. |
| RF-37 | Aplicativo móvel autenticado do aluno | Parcial | Sessão e contratos próprios, interface web mínima; aplicativo completo não entregue. |
| RF-38 | Início com agenda, pendências e orientações | Parcial | Contrato e consulta mínima; jornada móvel completa pendente. |
| RF-39 | Quadro Kanban | Pendente | Modelo e estados de tarefas existem; quadro interativo completo não entregue. |
| RF-40 | Criar/editar/priorizar/mover cartões | Parcial | Contrato do aluno altera estado/prazo com histórico; criação manual de cartões, edição de título/prioridade pelo aluno e quadro completo pendentes. |
| RF-41 | Checklists associados a tarefas | Pendente | Checklist completo não implementado. |
| RF-42 | Agenda diária e semanal | Parcial | Modelo, contrato e consulta de eventos; organização móvel completa pendente. |
| RF-43 | Reagendar e preservar execução | Parcial | API altera prazo da tarefa e início/fim da agenda com revisão, autoria e evento idempotente; fluxo móvel completo pendente. |
| RF-44 | Incorporar publicações sem duplicação | Parcial | Atividades publicadas preservam autoria e identidade; integração visual ao Kanban/agenda pendente. |
| RF-45 | Notificações conforme preferências | Parcial | Central interna efetiva; preferências completas e lembretes agendados do aluno pendentes. |
| RF-46 | Consultar regras e versão ativa | Implementado | Interface administrativa e API com sinais, condições, pesos e janelas. |
| RF-47 | Criar/editar/habilitar regras em rascunho | Implementado | Editor administrativo da configuração; nenhuma alteração de código necessária. |
| RF-48 | Limiares, quantidade, duração, janela e agregação | Implementado | Parâmetros validados e documentados; política de precedência explícita. |
| RF-49 | Rejeitar configurações inválidas/conflitantes | Implementado | Validação estruturada antes da ativação; faixas, IDs, métricas e conflitos verificados. |
| RF-50 | Simular e comparar sem alterar produção | Implementado | Mesmos dados autorizados comparados em versões; sem criar alertas de produção. |
| RF-51 | Versionar com autoria e antes/depois | Implementado | Versões e auditoria persistentes com justificativa obrigatória. |
| RF-52 | Ativar/restaurar para avaliações futuras | Implementado | Transação de ativação, cópia identificada na restauração e histórico preservado. |
| RF-53 | Snapshot imutável aplicado ao alerta | Implementado | ID e configuração preservados por avaliação/alerta; alterações não reescrevem fatos antigos. |
| RF-54 | Apenas Admin edita/ativa/restaura | Implementado | Autorização no servidor; Mentor consulta explicação; tentativa de escrita retorna 403. |
| RF-55 | Sincronizar tarefas/agenda com mentor | Implementado | Entrega por contrato: APIs autenticadas de tarefas, agenda e estudo, com identidade de evento e revisões aplicáveis; indicadores e consulta do mentor atualizados. Aplicativo completo e sincronização offline não entregues. |
| RF-56 | Mentor cria/revisa/publica planos e metas | Implementado | Editor manual com períodos, atividades, prioridades, autoria, revisão e publicação. |
| RF-57 | Admin sem acesso irrestrito a registros individuais | Implementado | Administração restrita a parâmetros, vínculos e auditoria; notas privadas não são gestão geral. |
| RF-58 | Consulta do relatório no aplicativo do aluno | Parcial | Contrato e consulta autenticada mínima; aplicativo completo pendente. |
| RF-59 | Estado/origem/atualização e autoria dos dados | Implementado | Metadados persistentes e interface distinguem aluno, mentor, seed e última sincronização. |
| RF-60 | Autorização em toda consulta/alteração | Implementado | Sessão, RBAC, vínculo, concessão de relatório e validação dos IDs no servidor. |

## Critérios de aceite

| ID | Cenário | Estado | Verificação/limite |
|---|---|---|---|
| CA-01 | Um sinal → Observar só no resumo | Implementado | Teste do motor e separação resumo/fila. |
| CA-02 | Dois sinais → Atenção com evidências | Implementado | Teste do motor e resposta da API sem ação sugerida. |
| CA-03 | Sete dias sem acesso → Prioridade no mesmo dia | Implementado | Motor e notificação interna persistente com timestamp da avaliação. |
| CA-04 | Pular questão em simulado não equivale a estudo | Implementado | Teste da agregação de sessões e contexto de questões. |
| CA-05 | Mentor publica suas prioridades/atividades | Implementado | Criação, revisão/publicação e consulta autenticada; nenhum texto gerado. |
| CA-06 | Consultar plantões ao editar plano | Implementado | Contexto persistente acessível junto ao editor manual. |
| CA-07 | Ação + evolução factual da semana posterior | Implementado | Histórico e comparação, sem conclusão automática de eficácia. |
| CA-08 | Menor/responsável autorizado veem mesmo relatório | Implementado | Autorização por concessão e leitura da mesma revisão publicada. |
| CA-09 | Adulto sem relatório a pais | Implementado | Restrições de destinatários testadas na API. |
| CA-10 | Marcar alerta útil/não útil | Implementado | Triagem e histórico persistentes. |
| CA-11 | Qualidade com eventos rotulados | Parcial | Cálculo sintético e estado insuficiente; definições ainda não homologadas com operação. |
| CA-12 | Gestão de contas, vínculos e indicadores | Parcial | Vínculos/regras/auditoria; gestão de contas e operação integral pendentes. |
| CA-13 | Sem acesso a alunos de outro mentor | Implementado | Testes de leitura e alteração direta por ID. |
| CA-14 | Início completo do aluno no celular | Parcial | Consulta mínima e contratos; aplicativo completo não entregue. |
| CA-15 | Mover cartão sem duplicar atividade | Parcial | Identidade/histórico garantidos no contrato de tarefa; quadro Kanban pendente. |
| CA-16 | Marcar checklist atualiza progresso | Pendente | Checklist completo pendente. |
| CA-17 | Reagendar reflete no mentor | Parcial | API de agenda/tarefa persiste alterações consultáveis pelo mentor e evita eventos duplicados; jornada móvel completa pendente. |
| CA-18 | Incorporar atividade preserva autoria/identidade | Parcial | Publicação gera tarefas identificadas; integração visual no app pendente. |
| CA-19 | MVP independente de sono/tempo de tela | Parcial | Núcleo entregue funciona sem essas fontes; Kanban/checklist/app integral permanece pendente. |
| CA-20 | Novo limiar só após ativação | Implementado | Testes de rascunho/ativação e avaliações futuras. |
| CA-21 | Simulação compara sem modificar alertas | Implementado | Comparação lado a lado e teste da ausência de efeitos em produção. |
| CA-22 | Configuração inválida não ativa | Implementado | Erros legíveis de validação e rejeição transacional. |
| CA-23 | Alerta antigo conserva versão A | Implementado | Teste de snapshot após ativar B. |
| CA-24 | Auditoria antes/depois, autor e motivo | Implementado | Criação/edição/ativação/restauração registradas. |
| CA-25 | Mentor/Aluno não alteram regras | Implementado | Testes de autorização 403 na API. |
| CA-26 | Restauração preserva histórico | Implementado | Restauração identificada, efeito futuro e alerta original imutável. |

## Restrições não funcionais relevantes

- RNF-01/02/05/06/07/08/10/18/19/20: evidências, determinismo, autoria humana, auditoria, aviso interno, segregação e versionamento compõem a entrega.
- RNF-03/04/11: minimização, hashes de senha, sessões e acesso controlado implementados para demonstração local; bases legais, consentimento operacional, retenção e homologação de segurança continuam sujeitos à definição antes de usar dados reais.
- RNF-12/13/14: sinais acadêmicos usam namespace/contrato próprio e lista permitida de métricas. Fontes opcionais futuras exigirão outro módulo, autorização e política de dados; não existem coletores operacionais dessas métricas no MVP.
- RNF-09/15/16/17: metas de produção, aplicação móvel integral, sincronização offline com resolução de conflitos e observabilidade operacional completa permanecem fora da homologação desta entrega. Revisões e idempotência cobrem as atualizações conectadas disponíveis.
