# Contratos HTTP — Farol MVP v4.0

Base local: `http://127.0.0.1:8000`. Dados, contas e eventos desta demonstração são sintéticos. O serviço usa JSON, sessão por cookie e autorização no servidor. Não existe chave de API, login por papel escolhido no cliente nem endpoint público para obter dados de alunos.

## Sessão e respostas

| Operação | Corpo/resposta | Acesso |
|---|---|---|
| `POST /api/login` | `{"email":"...","password":"..."}` → `user`, `csrf_token`, `synthetic: true`; define cookie | Credenciais de conta criada pelo seed |
| `GET /api/session` | `user`, `csrf_token`, `synthetic` | Sessão válida |
| `POST /api/logout` | `{}` → `{"ok":true}`; revoga sessão e expira cookie | Sessão e CSRF |

O cookie `farol_session` é `HttpOnly`, `SameSite=Strict`, com validade de oito horas. `FAROL_SECURE_COOKIE=true` acrescenta `Secure` para uma implantação com HTTPS; o servidor local não fornece TLS. Todas as mutações, exceto login, exigem `X-CSRF-Token` com o valor retornado por login/sessão. As requisições mutáveis exigem `Content-Type: application/json` e objeto JSON de até 256 KiB, inclusive `{}` para operações sem campos. Origem informada e cabeçalho `Host` são verificados. Não há CORS para aplicações de outra origem; a futura integração deve operar na mesma origem ou estabelecer um mecanismo próprio revisado.

Toda operação bem-sucedida retorna HTTP 200. Falhas retornam `{"error":"mensagem","details":null}`; validações de regras podem retornar uma lista em `details`.

| HTTP | Significado |
|---|---|
| 400 | Entrada/configuração inválida |
| 401 | Sessão ausente/expirada ou credenciais inválidas |
| 403 | Papel, vínculo, destinatário, origem ou CSRF não autorizado |
| 404 | Rota/versão administrativa inexistente |
| 409 | Revisão desatualizada, transição inválida ou evento reutilizado com outro conteúdo |
| 413 / 415 | Tamanho de corpo / tipo de conteúdo não aceito |
| 429 | Dez tentativas inválidas de login no intervalo; aguardar 15 minutos |
| 503 | Nenhuma configuração ativa disponível |

IDs individuais sem permissão retornam 403, inclusive quando inexistentes, para não permitir enumeração da carteira alheia. Erros de uma mutação são revertidos transacionalmente; tentativas de login e rejeições administrativas relevantes preservam somente os registros necessários.

Exemplo executável com a biblioteca padrão, sem senha embutida. Inicie o servidor e informe uma conta sintética e a senha impressas pelo seed. A senha digitada não aparece no terminal.

```python
import getpass
import http.cookiejar
import json
import urllib.request

base = "http://127.0.0.1:8000"
jar = http.cookiejar.CookieJar()
http = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
csrf = None

def request(method, path, payload=None):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        if csrf:
            headers["X-CSRF-Token"] = csrf
    req = urllib.request.Request(base + path, data=body,
                                 headers=headers, method=method)
    with http.open(req) as response:
        return json.load(response)

login = request("POST", "/api/login", {
    "email": input("E-mail sintético: ").strip(),
    "password": getpass.getpass("Senha do seed: "),
})
csrf = login["csrf_token"]
try:
    role = request("GET", "/api/session")["user"]["role"]
    route = {"mentor": "/api/dashboard", "admin": "/api/rules",
             "student": "/api/student/home"}[role]
    print(json.dumps(request("GET", route), ensure_ascii=False, indent=2))
finally:
    request("POST", "/api/logout", {})
```

## Consultas do Mentor

| Operação | Conteúdo |
|---|---|
| `GET /api/dashboard` | `period`, `updated_at`, `students`, `summary`, `queue`, `observe`, `notifications`, `quality`, `evolution`, `synthetic` |
| `GET /api/students/:id` | Contexto do aluno, métricas, histórico, avaliação, alertas, notas do autor, planos, relatórios, intervenções, mensagens, tarefas, agenda, registros acadêmicos, presença e sessões de estudo |
| `POST /api/evaluate` | `{"reason":"motivo opcional"}` → quantidade processada, versão e instante; Mentor processa somente sua carteira, Admin processa o conjunto sintético |
| `GET /api/rules` | Versões ativas/arquivadas e `active_id`; Mentor não recebe rascunhos |

`summary` contém `prio`, `att`, `obs`, `ok`, `unknown`, `new_alerts`, `followed`, `interventions`. “Novos” conta alertas do período ainda sem triagem; “acompanhados” conta alunos com acompanhamento marcado no período. `queue` contém somente Atenção/Prioridade, ordenados por nível e nome. `observe` é o resumo separado. Pesquisa e filtros operam sobre essa carteira autorizada no cliente; a API não implementa paginação.

Níveis: `prio` = Prioridade, `att` = Atenção, `obs` = Observar, `ok` = Em dia, `unknown` = Sem dados. Cada avaliação expõe evidências, indicadores ausentes, versão, snapshot da configuração e instante. Alertas preservam a primeira ocorrência do mesmo aluno/período/nível; novas avaliações ficam registradas separadamente e não reescrevem alertas históricos.

O detalhe informa `source`, `sync_status` (`synced` ou `no_data`) e `student.last_sync`. A ausência de referência oficial é explícita: `reference_data` contém `{"tri":"unavailable","sisu":"unavailable"}`. Histórico e métricas faltantes não devem ser completados com zero pelo cliente. `quality` inclui definição, utilidade humana e métricas de eventos rotulados; valores indisponíveis são `null`. `evolution` contém pares factuais antes/depois com unidade e períodos, sem julgamento de sucesso.

## Autoria e triagem do Mentor

Todas as operações desta seção exigem papel `mentor` e vínculo atual com o aluno. O ator, autor e timestamps são determinados pelo servidor. Corpos são texto simples, com limite padrão de 10.000 caracteres; HTML enviado não é executado pela interface.

| Operação | Corpo |
|---|---|
| `POST /api/alerts/:id/triage` | `interpretation` (texto, pode ser vazio), `useful` (`true`, `false` ou `null`), `following` e `acted` (booleanos) |
| `POST /api/students/:id/notes` | `body` não vazio |
| `PUT /api/notes/:id` | `body`, `revision` atual |
| `POST /api/students/:id/interventions` | `body`, `alert_id` opcional pertencente ao mesmo aluno |
| `POST /api/students/:id/messages` | `body` |
| `POST /api/students/:id/plans` | Documento conforme abaixo |
| `POST /api/students/:id/reports` | Documento conforme abaixo |
| `GET /api/plans/:id` / `GET /api/reports/:id` | Documento autorizado; alunos recebem apenas a última revisão publicada |
| `PUT /api/plans/:id` / `PUT /api/reports/:id` | Documento completo e `revision` atual |

Cada triagem é um registro histórico; repetir a operação cria nova decisão. Notas são privadas do mentor autor, inclusive quando outro mentor passa a acompanhar o aluno. Edição da nota preserva revisões. Intervenção captura o período e as métricas atuais como referência factual. Mensagens têm disponibilização interna; `read_at` e `response_at` permanecem nulos até evento explícito do aluno. O serviço não gera texto de orientação nem rascunhos.

Campos de documento:

| Campo | Contrato |
|---|---|
| `title` | Texto não vazio, até 180 caracteres |
| `body` | Texto escrito pelo mentor, não vazio, até 10.000 caracteres |
| `period` | Segunda-feira em `AAAA-MM-DD`; padrão: semana atual de `America/Sao_Paulo` |
| `status` | Plano: `draft` ou `published`; relatório: `draft`, `reviewed` ou `published` |
| `revision` | Obrigatório ao editar; inteiro recebido na consulta anterior |
| `activities` | Somente planos; até 50 objetos com `id`, `title`, `priority` (`high`, `normal`, `low`) e `due_at` (`AAAA-MM-DD`) |

Na criação, `id` de atividade pode ser omitido; o servidor o atribui. Nas edições, conserve o ID retornado, mesmo ao reordenar atividades. Sem ID, uma correspondência exata de título, prioridade e prazo reutiliza a atividade anterior; outros conteúdos recebem nova identidade. Publicar novamente a mesma atividade preserva a identidade da tarefa e sua execução; título, prioridade e prazo atualizados geram histórico. Retirar uma atividade ao publicar uma revisão arquiva a tarefa (`archived_at`), preserva seu histórico e a remove das pendências e do denominador das tarefas ativas. Um rascunho não retira atividades publicadas. Não há exclusão destrutiva de tarefas nesta entrega.

Relatório exige três gravações explícitas: criar `draft`, editar para `reviewed` usando a revisão retornada e publicar `published` com nova revisão. A publicação precisa conservar título, corpo e período da versão revisada; mudanças exigem nova revisão humana. Um rascunho posterior não remove a revisão já publicada do acesso do aluno. Respostas incluem autoria, revisão, estado, `published_revision`, revisor quando aplicável e `external_status: "not_sent"`.

## Consulta do Aluno e responsáveis autorizados

Na consulta do Mentor, cada alerta contém `raw_inputs` com fatos e histórico preservados na avaliação. O detalhe do aluno também fornece `observations` e `metric_metadata`, com fonte, identificador e atualização de cada indicador. Atualizar uma tarefa registra sua nova origem sem atribuir ao aluno os registros acadêmicos independentes do seed.

`GET /api/student/home` exige papel `student` e retorna `student`, `plans`, `reports`, `tasks`, `messages`, `agenda`, `notifications`, `reports_only` e `synthetic`. Não inclui notas privadas, triagens, rascunhos, intervenções ou a carteira de outro usuário.

O domínio de autenticação mantém três papéis. Uma conta de responsável usa acesso restrito de `student`, sem perfil próprio de aluno: `reports_only: true`. Ela consulta somente relatórios publicados do menor com concessão ativa em `report_grants`. `GET /api/reports/:id` retorna a mesma revisão publicada disponível ao menor. Concessões revogadas ou aluno com 18 anos ou mais não autorizam esse acesso. As concessões da demonstração são criadas pelo seed; não há interface/API de gestão de consentimento ou convites. Essa decisão provisória não substitui política operacional para dados reais.

## Sincronização de execução

As rotas abaixo exigem conta do próprio aluno. Mentor, Admin e conta restrita de responsável não podem se passar pelo executor. IDs de tarefa/agenda são obtidos em `GET /api/student/home`. As consultas do Mentor refletem as alterações persistidas na próxima atualização; não há WebSocket nem sincronização offline automática.

### Eventos e revisão

Envie `event_id` único por ator, com 8–100 caracteres alfanuméricos, hífen ou sublinhado, em todas as integrações. Reutilize exatamente o mesmo corpo/ID ao repetir uma requisição após falha de rede. O servidor retorna a resposta original com `replayed: true`, sem duplicar execução. Reutilizar o evento com outro corpo ou outro destino gera 409. O espaço de IDs é compartilhado entre operações do mesmo ator; use um identificador novo para cada intenção.

Tarefas e agenda exigem `revision` atual. Uma intenção nova com revisão antiga recebe 409; recarregue, apresente o conflito ao usuário e envie novo evento com a revisão correta. A repetição idempotente de um evento já aceito continua válida mesmo se a entidade avançar depois. Não marque sincronização concluída antes da resposta bem-sucedida.

### Tarefas

`PATCH /api/tasks/:id` aceita `event_id`, `revision`, `status` (`todo`, `doing`, `done`) e `due_at` (`AAAA-MM-DD`). Estado/prazo omitidos são conservados. Retorna a tarefa com nova revisão, `author_id`, `updated_by`, timestamps, atraso calculado e histórico. Preserva a autoria do mentor, registra o aluno como executor e recalcula cumprimento de tarefas nas semanas afetadas, avaliando os indicadores atuais.

```json
{
  "event_id": "evento-tarefa-0001",
  "revision": 1,
  "status": "done"
}
```

### Agenda

`PATCH /api/agenda/:id` aceita `event_id`, `revision`, `starts_at`, `ends_at` e `title` opcional (até 180 caracteres, não vazio). Use timestamps ISO 8601 com fuso explícito; fim deve ser posterior ao início e a duração máxima é de 24 horas. Campos não alterados podem ser omitidos. Retorna o evento atualizado, revisão, autor original, ator da atualização e timestamp. O replanejamento preserva o ID e fica consultável pelo Mentor; mover um evento de agenda não significa concluir uma tarefa.

```json
{
  "event_id": "evento-agenda-0001",
  "revision": 1,
  "starts_at": "2026-10-20T18:00:00-03:00",
  "ends_at": "2026-10-20T19:00:00-03:00"
}
```

### Estudo e questões

`POST /api/integration/study` aceita somente os campos abaixo. Retorna `id`, `student_id`, `period`, `source: "student"` e `synced_at`.

| Campo | Contrato |
|---|---|
| `event_id` | Identidade do evento conforme acima |
| `student_id` | Opcional; se informado, precisa ser o próprio aluno |
| `context` | `study` ou `exam` |
| `subject` | Texto não vazio, até 100 caracteres |
| `started_at` | ISO 8601 com fuso explícito, não futuro |
| `duration_minutes` | Inteiro entre 1 e 720 |
| `questions` | Entre 1 e 180 objetos de questão |

Cada questão exige `theme` (texto, até 100), `difficulty` (`easy`, `medium`, `hard`, `unknown`), `seconds` (número finito de 0 a 7200), `skipped` (booleano), `correct` (booleano ou `null`). `error_cause` é opcional: `conteudo`, `leitura`, `descuido`, `tempo` ou `null`. Questão pulada não pode ser marcada correta.

Somente `study` participa das agregações de questões de estudo. O padrão de questões difíceis puladas exige repetição entre sessões de estudo, além do limiar percentual configurado; questões puladas em `exam` não geram esse sinal. O indicador de horário conta início a partir das 23h em `America/Sao_Paulo`. Nenhum campo dessas rotas coleta sono ou tempo de tela. Registros acadêmicos de presença, simulados/redações e contexto cadastral são sintéticos no seed; não há endpoint geral de importação/cadastro desses domínios nesta entrega.

### Eventos de mensagem

`POST /api/messages/:id/read` e `POST /api/messages/:id/respond` recebem `{}` e registram, respectivamente, `read_at` e `response_at` para mensagem do próprio aluno. São marcadores explícitos da integração; não enviam resposta textual nem integram um canal externo. O cliente deve acioná-los apenas quando o evento correspondente tiver ocorrido. Não recebem `event_id` e não fazem parte da garantia de repetição idempotente das rotas anteriores.

## Notificações internas

`GET /api/notifications` retorna até 100 notificações da própria conta. `POST /api/notifications/:id/read`, com `{}`, registra a leitura daquela notificação. `read_at` da notificação não implica leitura de mensagem ou relatório. Avisos têm `channel: "in_app"`, `status: "available"`, `created_at` e destinatário; não há status fictício de envio externo. Prioridade gera aviso ao mentor no dia em que a avaliação detecta a condição.

## Administração de regras, vínculos e auditoria

Todas as mutações abaixo exigem Admin. Mentor pode consultar somente versões ativas/arquivadas em `GET /api/rules`; não pode validar, simular, editar, ativar ou restaurar.

| Operação | Corpo / resultado |
|---|---|
| `GET /api/rules` | Admin recebe todas as versões e `active_id` |
| `POST /api/rules` | `name` (até 120), `reason` (até 1000), `config` (objeto) → rascunho e erros de validação |
| `PUT /api/rules/:id` | Mesmos campos; somente versão `draft` |
| `POST /api/rules/:id/validate` | `{}` → `valid` e `errors` |
| `POST /api/rules/:id/simulate` | `compare_id` opcional, padrão versão ativa → níveis/pesos antes/depois por pseudônimo sintético e `production_changed: false` |
| `POST /api/rules/:id/activate` | `reason` obrigatório; exige rascunho válido |
| `POST /api/rules/:id/restore` | `reason` obrigatório; exige versão arquivada válida e cria uma nova versão ativa com origem preservada |
| `GET /api/assignments` | Mentores, identificação mínima dos alunos e vínculos |
| `PUT /api/assignments/:student_id` | `mentor_id`, `reason`; substitui vínculo atual e remove notificações nominativas do antigo mentor |
| `GET /api/audit` | Até 200 eventos recentes, com ator, instante, motivo e antes/depois minimizados |

Use a configuração retornada pela API como base do rascunho. Estrutura: `schema_version: 1`, `precedence: ["prio","att","obs","ok"]`, `aggregation` e `rules`. Cada regra define `id`, `label`, `metric`, `condition`, `threshold`, `weight`, `window_weeks`, `min_history`, `min_samples`, `enabled`, `priority` e `precedence`. A condição `unanswered` também usa `days_threshold`; seu prazo e quantidade precisam ser definidos explicitamente antes de habilitar. As faixas e a precedência estão documentadas em [IMPLEMENTACAO_MENTOR_V4.md](IMPLEMENTACAO_MENTOR_V4.md).

Salvar rascunho inválido é permitido para correção; validar devolve erros legíveis. Simular/ativar/restaurar configuração inválida falha. Uma versão ativa ou arquivada não aceita edição. Ativar/restaurar devolve `applies_to: "future_evaluations"`: avaliações antigas não são recalculadas; a próxima avaliação periódica/explicita usa a nova versão. Simulação compara versões usando os mesmos fatos atuais, sem criar avaliações ou alertas de produção. O Admin recebe resultados pseudonimizados na simulação, sem notas privadas ou corpos de documentos.

## Limites do contrato

As rotas são o contrato da demonstração local, sem promessa de estabilidade pública de uma API de produção. Não há cadastro/recuperação de contas, aplicativo móvel completo, Kanban/checklist integral, importação oficial TRI/SISU, serviço externo de mensagens, gestão de consentimento ou recuperação offline automática. O armazenamento persiste entre reinícios; uma futura implantação com dados reais exige definir operação, retenção e mecanismos de identidade adequados ao ambiente. Consulte a [matriz de rastreabilidade](RASTREABILIDADE_V4.md) para distinguir contrato implementado de jornada ainda pendente.
