# Implementação da visão do Mentor — MVP v4.0

## Fonte, recorte e auditoria inicial

A versão 4.0 local estava disponível como `Farol_Documento_de_Requisitos_v4.pdf`, datada de 17/10/2026, com 12 páginas. Seu texto foi extraído e lido; o DOCX não estava no workspace. O PDF permanece preservado e ignorado pela política preexistente do `.gitignore`. O prompt delimita esta entrega no Mentor, nos serviços necessários e na configuração mínima de regras pelo Administrador. Os requisitos do aplicativo móvel completo e da gestão administrativa integral são rastreados separadamente em [RASTREABILIDADE_V4.md](RASTREABILIDADE_V4.md).

A inspeção inicial encontrou checkout limpo, branch `main`, commit `efcbe35`, coincidente com a referência local `origin/main`. A consulta ao GitHub não ficou disponível; não se afirma igualdade com o estado remoto ao vivo. O checkout local foi a base técnica. `index.html` continha HTML/CSS/JavaScript com dados fixos, login visual, ações simuladas e conteúdo automático incompatível com v4.0. README e PRODUCT descreviam a proposta anterior. Não existiam servidor, migrações, dependências de runtime ou testes.

Foram preservados a identidade náutica, luz âmbar, farol, legibilidade e estrutura web sem framework. Conteúdos de ações sugeridas, feedbacks gerados, perfis interpretativos e a visão antiga de Coordenação foram substituídos por evidências e autoria humana. `proposta.html` continua sendo uma apresentação; os fluxos funcionais estão em `/` e usam a API.

## Arquitetura mínima

| Camada | Implementação | Responsabilidade |
|---|---|---|
| Interface | HTML, CSS e JavaScript em `index.html`/`assets/` | Renderizar dados recebidos, estados, formulários humanos e navegação por papel. |
| HTTP | `server.py`, biblioteca padrão Python | Servir arquivos explicitamente permitidos e API local autenticada. |
| Serviços | `farol/` | Vínculos, sessões, documentos, sincronização, avaliação, notificações e auditoria. |
| Motor | `farol/rules.py` | Função determinística, sem UI, efeitos externos ou texto pedagógico gerado. |
| Persistência | SQLite e `migrations/` | Transações, chaves, revisões, snapshots e histórico. |
| Verificação | `tests/`, `unittest` | Casos de regras, APIs, permissões e smoke dos fluxos persistentes. |

Python com biblioteca padrão foi escolhido por estar disponível no ambiente e dispensar instalação de dependências. A mudança é necessária para cumprir autorização no servidor e persistência entre reinícios; um `localStorage` isolado ou login apenas visual não atenderia esses fluxos. Não há requisito de serviço pago, conta externa, Node.js, build ou Docker.

O servidor inicia em `127.0.0.1:8000`. A demonstração deve ser acessada por HTTP local; abrir `index.html` diretamente ou hospedá-lo isoladamente no GitHub Pages não executa as APIs. Não foi feito deploy público.

## Execução e banco

```bash
python3 server.py --seed
python3 server.py
python3 -m unittest discover -s tests -v
```

A senha sintética é gerada no seed e exibida uma vez no terminal. `FAROL_DEMO_PASSWORD`, se informado, deve conter pelo menos 12 caracteres; nenhuma senha real é necessária. O formulário de login fica vazio. O servidor lê automaticamente `.env`, se existir, somente para as variáveis listadas em `.env.example`; variáveis exportadas no ambiente prevalecem. O seed não apaga dados existentes nem redefine senhas. Use outro caminho com `--db` para iniciar uma demonstração independente.

O banco padrão é `data/farol.sqlite3`; a migração é aplicada por versão. SQLite usa chaves estrangeiras, WAL e timeout para escrita. O arquivo do banco é criado com permissões restritas. Dados não são apagados ao reiniciar o servidor. Testes usam diretórios temporários.

Timestamps persistidos usam ISO 8601 com offset explícito. Semanas acadêmicas começam na segunda-feira segundo `America/Sao_Paulo`, representadas por data ISO; elas não são timestamps sem fuso. IDs de entidades são estáveis; revisões de documentos, tarefas e agenda distinguem mudanças sobre a mesma entidade. As migrações são incrementais: a segunda adiciona revisões à agenda; a terceira permite arquivar tarefas retiradas de planos publicados, preservando execução e histórico.

## Modelo persistente

| Domínio | Tabelas | Históricos e restrições |
|---|---|---|
| Identidade/acesso | `users`, `students`, `mentor_students`, `sessions`, `login_attempts`, `report_grants` | Três papéis; vínculo explícito; sessões expirantes; concessões de relatório com consentimento/revogação. |
| Fatos | `periods`, `signal_observations`, `academic_records`, `attendance`, `study_sessions` | Origem, período, timestamp, contexto estudo/simulado e causas de erro. |
| Execução | `tasks`, `task_events`, `agenda`, `agenda_events`, `integration_events` | Autor e executor distintos; revisão; deduplicação de evento; estado e histórico. |
| Classificação | `rule_versions`, `evaluations`, `alerts` | Única versão ativa, snapshot de entrada/configuração, evidências e histórico imutável. |
| Autoria do mentor | `triage`, `notes`, `note_revisions`, `documents`, `document_revisions`, `interventions`, `messages` | Privacidade, autoria, revisões, revisão explícita e estado de publicação. |
| Entrega/qualidade | `notifications`, `labelled_events`, `audit` | Canal efetivo, timestamp, rótulos de referência e logs minimizados. |

`signal_observations` mantém a origem e o namespace desacoplados. A classificação aceita somente as métricas acadêmicas/operacionais enumeradas no motor. Uma integração futura de outras fontes deverá ter módulo, finalidade, autorização, revogação e retenção próprios; nenhuma ausência dessas fontes modifica o nível acadêmico. Sono e tempo de tela não são coletados, importados, apresentados ou exigidos.

## Autorização e privacidade

- Senhas são armazenadas com PBKDF2-HMAC-SHA256, salt aleatório e comparação em tempo constante. Tokens de sessão aleatórios são persistidos somente como hash.
- Sessões usam cookie `HttpOnly`, `SameSite` e expiração. Mutações exigem token CSRF e validação da origem aplicável. O logout invalida a sessão no servidor.
- Sem sessão, respostas de dados retornam 401. Papel sem permissão ou vínculo indevido retorna 403. Todo ID de aluno, alerta, documento ou tarefa é verificado no servidor.
- Admin administra regras, vínculos e auditoria autorizada. O papel não concede consulta irrestrita a notas privadas e documentos individuais.
- Mentor lê e altera apenas alunos vinculados. Notas privadas têm revisões e autoria e não são incluídas nas respostas do aluno/responsável.
- Aluno consulta seu conteúdo e registra sua execução. Uma alteração de tarefa feita pelo aluno mantém o autor original e registra o aluno como executor da mudança.
- Responsável recebe acesso controlado somente aos relatórios publicados do menor indicado na concessão. Usa o domínio de autenticação do Aluno, sem quarto papel, sem carteira, sem notas privadas e sem acesso genérico ao perfil do menor.
- Adultos não geram destinatários “pais”; concessões de responsáveis não liberam relatórios de adultos.
- Entradas têm limites e tipos validados; SQL é parametrizado. Texto do mentor é renderizado como texto, sem HTML ativo.
- Auditoria de ações de conteúdo registra identificadores, estados e revisões; não replica corpo de nota privada, senha ou token de sessão. Snapshots de regras podem ser completos porque descrevem parâmetros, não conteúdo privado.

A política de consentimento de demonstração é uma decisão técnica provisória: a concessão explícita registra quem autorizou e quando. Ela não representa coleta real de consentimento ou homologação jurídica. Gestão de contas, recuperação de senha, retenção/exclusão, canal externo, TLS de implantação e operação com dados reais permanecem fora desta demonstração.

## Regras determinísticas e decisões provisórias

A classificação recebe os fatos da semana, histórico e **um snapshot integral** da configuração ativa. O motor não consulta relógio, banco ou UI; classificação e simulação usam a mesma função. A versão é capturada e persistida com a avaliação. A animação de varredura não calcula regras nem atrasa o acesso aos fatos.

Configuração inicial:

| Condição | Parâmetro inicial | Resultado |
|---|---|---|
| Um sinal distinto | 1 | Observar, no resumo semanal. |
| Dois sinais distintos | 2, peso agregado mínimo 0 | Atenção, na fila. |
| Variação persistente | 2 semanas consecutivas | Atenção. |
| Ausência de acesso | 7 dias | Prioridade e aviso interno no dia da detecção. |
| Faltas consecutivas | 2 | Prioridade e aviso interno. |
| Presença, cronograma ou execução de tarefas | Queda relativa de 20% da linha de base | Sinal acadêmico. |
| Simulados ou redações | Queda relativa de 15% | Sinal acadêmico. |
| Questões difíceis puladas em estudo | 30%, em pelo menos 2 sessões de estudo | Sinal acadêmico; simulado não compõe esse indicador. |
| Tempo registrado por questão | Aumento relativo de 40% | Sinal objetivo, sem interpretação psicológica. |
| Sessões de estudo iniciadas a partir das 23h | Aumento relativo de 50% | Contagem por horário de início em `America/Sao_Paulo`; não infere rotina ou sono. |
| Mensagens sem resposta | Desabilitado; quantidade/prazo `null` | Exige definição explícita do Admin antes de habilitar. |

A referência inicial é a média dos períodos anteriores dentro de quatro semanas, exigindo ao menos dois períodos válidos. Janela e mínimo são editáveis. Uma queda de 20% é **relativa**, não 20 pontos percentuais: de 80% para 64% representa queda relativa de 20%. Histórico incompleto, valor ausente ou referência zero geram explicação de insuficiência; não geram queda presumida. Períodos históricos duplicados não multiplicam amostras.

Persistência compara semanas consecutivas com uma linha de base anterior à primeira semana da sequência. Isso evita que a própria queda dilua a referência. Lacunas na sequência não são tratadas como persistência. O resultado inclui regras avaliadas, evidências e indicadores sem dados; “Sem dados” é diferente de “Em dia”.

Regras sobre a mesma métrica não contam como sinais independentes. A precedência de regra é editável entre 0 e 100; para múltiplas regras aplicáveis à mesma métrica, vence maior precedência, depois gatilho forte, maior peso e ID estável. Todas as evidências são preservadas com indicação de aplicação. Os níveis mantêm a hierarquia de segurança Prioridade > Atenção > Observar > Em dia. Esta separação permite configurar a resolução das regras sem inverter o significado dos níveis.

Faixas provisórias de validação:

| Parâmetro | Faixa/condição |
|---|---|
| Regras por versão | 1–64; IDs únicos e métricas permitidas. |
| Peso de regra | 0–100. |
| Precedência de regra | Inteiro 0–100. |
| Janela histórica | 1–52 semanas. |
| Mínimo de histórico | 1–26, sem superar a janela. |
| Persistência | 2–8 semanas. |
| Quantidade para Observar | 1–12 sinais distintos. |
| Quantidade para Atenção | 2–13, maior que Observar. |
| Peso agregado para Atenção | 0–1300. |
| Queda relativa | 1–100%. |
| Aumento relativo | 1–1000%. |
| Quantidade/prazo de mensagens | 1–1000 mensagens e 1–365 dias, ambos definidos para habilitar. |
| Repetição em estudo | Ao menos 2 sessões; limite de amostra 10000. |

Valores não finitos, tipos errados, campos inesperados, IDs repetidos, métricas não acadêmicas, regras equivalentes e condições opostas sobrepostas são rejeitados. Limiares absolutos obedecem também à unidade/faixa da métrica. Esses intervalos servem à demonstração e precisam de validação de negócio antes do piloto.

Métricas aceitas e limites dos valores/limiares absolutos (`gte`/`lte`):

| Métrica | Unidade | Intervalo |
|---|---|---|
| `days_since_access` | Dias | 0–3650 |
| `consecutive_absences` | Faltas | 0–100 |
| `attendance_pct`, `schedule_pct`, `task_completion_pct` | Percentual | 0–100 |
| `exam_score`, `essay_score` | Pontos na escala sintética declarada | 0–1000 |
| `skipped_hard_study_pct` | Percentual de questões difíceis puladas em estudo | 0–100 |
| `hard_study_sessions` | Sessões com questões difíceis puladas | 0–10000 |
| `question_seconds` | Segundos por questão de estudo | 0–7200 |
| `late_study_sessions` | Sessões de estudo iniciadas a partir das 23h | 0–10000 |
| `unanswered_messages` | Mensagens | 0–1000 |
| `oldest_unanswered_days` | Dias | 0–3650 |

Valores fora desses intervalos são tratados como evidência indisponível pelo motor. Os limites de configuração não criam pesos oficiais de ENEM/TRI/SISU; a escala de notas do seed é ilustrativa.

Rascunhos podem ser salvos e validados; somente configuração válida pode ser ativada. A política provisória de aprovação é ação explícita do Administrador autenticado, acompanhada de justificativa. Restauração cria versão identificada a partir de uma anterior, com trilha de origem. A ativação é transacional; um índice impede duas versões ativas simultaneamente. Configurações publicadas não podem ser editadas. Regras futuras afetam apenas avaliações futuras; evidências antigas não são silenciosamente reescritas.

Reprocessamento explícito preserva avaliações anteriores. Repetir os mesmos dados/versão na mesma janela reutiliza a avaliação; um alerta do mesmo aluno/período/nível não é duplicado. Mudança de nível pode gerar uma nova ocorrência identificada, preservando o nível anterior. Notificação interna tem identidade por destinatário/alerta.

## Autoria, publicação e acompanhamento

Interpretação, notas, intervenções, mensagens, planos e relatórios começam vazios. Não há rascunho pedagógico, recomendação de ação ou texto gerado por máquina. Dados factuais permanecem disponíveis separadamente para consulta.

Notas são privadas, com revisão/autoria. Planos têm período e atividades definidas manualmente, com título, prazo e prioridade. Publicação preserva a revisão e disponibiliza o conteúdo autenticado; tarefas atribuídas mantêm identidade para não serem duplicadas em reenvios. O aluno pode atualizar execução sem assumir a autoria do plano.

Relatórios têm estados **rascunho → revisado → publicado**. O mentor deve revisar explicitamente antes de publicar. Alterar conteúdo revoga a validação da revisão em edição; o histórico preserva revisões já publicadas. Menor e responsável autorizado consultam o mesmo conteúdo publicado. Sem canal externo, a interface informa que o conteúdo não foi enviado externamente.

Mensagens são escritas pelo mentor e disponibilizadas internamente. O sistema não inventa confirmação de leitura. Prioridade gera evento na central de notificações do mentor com timestamp no dia em que a avaliação identifica a condição. Há avaliação na inicialização, nas atualizações integradas e a cada 60 segundos por padrão enquanto o servidor estiver em execução (intervalo configurável, mínimo 15 segundos); `--evaluate` executa uma avaliação e sai. Este compromisso é relativo à avaliação efetivamente executada; não há monitor externo que opere com o servidor parado.

A comparação após intervenção apresenta dados da semana da ação e da semana seguinte, com unidades e diferenças observadas. Se não houver período posterior, informa a ausência. Nenhum aumento, queda ou mudança de nível é rotulado automaticamente como intervenção eficaz.

## Qualidade dos alertas

Utilidade é avaliação humana útil/não útil, armazenada com autor e alerta. Não equivale automaticamente a verdadeiro/falso positivo e não muda pesos.

O esquema aceita eventos rotulados para análise. O cálculo disponível usa uma janela de 28 dias antes do período rotulado, considera alertas Atenção/Prioridade detectados até o instante do evento e distingue:

- **Falso alarme:** janela rotulada sem afastamento que possui ao menos um alerta Atenção/Prioridade anterior ao evento. É uma contagem de janelas rotuladas, não de todos os alertas.
- **Afastamento não detectado:** evento rotulado com afastamento e sem alerta anterior na janela.
- **Antecedência:** diferença em dias entre o primeiro alerta anterior na janela e o evento; a média usa somente eventos de afastamento detectados.

Sem rótulos, contagens e antecedência são indisponíveis; não é inventada uma taxa de precisão. Sem eventos detectados, a antecedência fica indisponível mesmo que existam rótulos. As definições são provisórias e acompanham a resposta da API; números sintéticos não demonstram eficácia de um piloto real.

## Contratos de integração e validação

A API usa JSON e a mesma sessão protegida das visões. Identidade do ator é sempre derivada da sessão, nunca aceita como autoridade de um campo enviado pelo cliente. Consulte [API.md](API.md) para rotas, corpos, permissões e exemplo executável sem dependências adicionais.

Atualizações de tarefas/agenda/estudo devem enviar um identificador estável de evento. Repetir o evento com o mesmo conteúdo devolve o resultado anterior sem duplicar registros; reutilizar o ID para outro conteúdo é conflito. Revisão da entidade permite detectar uma atualização baseada em estado antigo. A resposta deve ser aplicada antes de o cliente confirmar o salvamento. Falha/offline não é apresentada como sincronização concluída.

Os testes automatizados devem cobrir regras iniciais e insuficiência de histórico; simulado versus estudo; rascunho/validação/simulação/ativação/restauração; snapshots; 401/403 e acesso cruzado; autoria, notas privadas, planos/relatórios; destinatários de menor/adulto; sincronização idempotente e persistência após reabertura. A matriz distingue os contratos disponíveis dos fluxos móveis pendentes.

A interface oferece estados de carregamento, ausência de dados, erro/offline, pendência de gravação e sucesso; navegação por teclado, foco no painel de aluno e respeito a movimento reduzido devem ser verificados no roteiro de smoke. A disponibilidade de um elemento visual não substitui seu teste contra a API.

## Verificação executada

- **47 testes `unittest` aprovados:** 20 do motor, 17 de serviços/SQLite e 10 HTTP com servidor real em porta local temporária. Incluem 401/403, CSRF, IDOR, conflitos de revisão, idempotência, edição de atividades sem perder execução, agenda, snapshots de regras, menor/responsável/adulto, evolução factual, métricas rotuladas e persistência após reinício.
- **Smoke completo no Chromium aprovado:** login; carteira; abas/teclado/foco/ESC; triagem; criação e revisão de nota privada; tentativa offline que preserva o texto; escape de HTML; intervenção; plano/atividade; revisão e publicação de relatório; conclusão pelo aluno visível ao mentor; consulta do responsável; simulação/ativação/restauração administrativa e auditoria. Viewports de 1440 e 390 pixels, sem transbordamento horizontal no painel móvel. Esse teste não equivale a uma auditoria integral de acessibilidade.
- Revisão visual das capturas de desktop e celular; `git diff --check`; compilação dos módulos Python.

Para repetir o smoke em ambiente que possua Playwright e Chromium:

```bash
python3 scripts/smoke_browser.py
```

O script inicializa e encerra seu próprio servidor, usa banco temporário e deixa capturas em `/tmp/farol-mentor.png` e `/tmp/farol-mobile.png`. A aplicação e a suíte `unittest` continuam sem dependências externas. Nesta execução, as ferramentas e bibliotecas de navegador foram baixadas e extraídas em `/tmp`, sem instalar pacotes do sistema ou alterar o ambiente de runtime do projeto.

## Limites e próximos componentes de integração

Permanecem fora desta entrega: aplicativo móvel completo, quadro Kanban e checklist completos, gestão integral de contas, serviço externo de mensagens, ingestão de bases oficiais TRI/SISU, sincronização offline com resolução completa de conflitos, piloto real e homologação para dados pessoais reais. A [matriz RF/CA](RASTREABILIDADE_V4.md) registra esses limites item a item.
