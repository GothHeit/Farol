# Product — Farol v4.0

<!-- impeccable:product-schema 1 -->

## Platform

Web responsiva, com servidor local para a demonstração funcional. A entrega principal é a visão do Mentor. Há interface administrativa de configuração de regras e contratos autenticados para integração do Aluno; não há aplicativo móvel completo nesta entrega.

## Stack

HTML, CSS e JavaScript sem framework ou build. Servidor Python com biblioteca padrão, SQLite e migrações. A escolha acrescenta persistência, autenticação e autorização ao protótipo com poucas dependências. GitHub Pages isoladamente não executa os serviços autenticados; abrir `index.html` como arquivo também não substitui o servidor.

## Users

- **Mentor:** consulta somente sua carteira; interpreta alertas e fatos, escreve planos, metas, instruções, mensagens e relatórios, registra intervenções e acompanha a execução.
- **Administrador (dono):** configura regras, pesos, limiares, janelas e precedências; valida, simula, ativa e restaura versões com auditoria. Também altera vínculos aluno–mentor e consulta a auditoria. Gestão integral da operação é uma evolução fora desta entrega.
- **Aluno:** consulta suas informações e o conteúdo publicado pelo mentor; contratos permitem sincronizar registros de execução com o painel. Kanban, checklist e aplicativo móvel completos permanecem pendentes.

Existem exatamente três papéis autenticados. Responsáveis autorizados de menores acessam o mesmo conteúdo do relatório por acesso controlado, sem uma quarta visão. Adultos são destinatários dos próprios relatórios.

## Product Purpose

Reunir evidências acadêmicas e de execução dos estudos para apoiar o acompanhamento humano. A plataforma coleta, organiza, compara e classifica fatos. Toda interpretação e orientação pedagógica pertence ao mentor.

## Positioning

O Farol dá visibilidade ao histórico do aluno e à origem de cada alerta. A pessoa responsável pela mentoria dispõe dos fatos e de campos em branco para registrar sua interpretação e sua decisão. O histórico permite consultar a variação dos indicadores após uma intervenção, sem atribuir causalidade nem julgar automaticamente sua eficácia.

## Operating Context

- Proposta da equipe FNMM para o Case 2 do Hackathon PotiCode 2026; cliente-alvo original: AMentoria.
- Demonstração inteiramente sintética, com dados persistentes e fluxo de autoria real dentro da aplicação local.
- Ciclo semanal: consultar resumo, revisar fila e evidências, decidir se deseja agir, escrever/publicar e consultar os registros seguintes.
- Sinais acadêmicos e operacionais: presença, cumprimento do cronograma, acesso, simulados/redações, questões, tempo por questão, horário registrado de estudo, resposta ao mentor e execução de tarefas. A regra de mensagens inicia desabilitada, aguardando quantidade/prazo definidos pelo Administrador. O indicador de horário conta sessões iniciadas a partir das 23h em `America/Sao_Paulo`.
- O contexto de estudo e o de simulado são distintos; questões difíceis puladas em simulado não acionam automaticamente o padrão usado em estudo.

## Capabilities and Constraints

- Níveis: Em dia, Observar, Atenção e Prioridade. Sem dados é um estado separado; histórico ausente não é queda presumida.
- Regras determinísticas em versões administrativas. Valores iniciais são exemplos configuráveis, com limites e validações explícitos.
- Alertas preservam evidências, período, valores, comparações, parâmetros e versão aplicada. Ativação/restauração afeta avaliações futuras.
- Rascunhos e simulações não alteram a carteira. Mentor consulta explicações, mas não altera nem ativa regras.
- Avaliação útil/não útil apoia revisão manual; pesos nunca são recalibrados automaticamente.
- Notas do mentor são privadas e devem conter apenas informações necessárias. Conteúdo publicado é identificado separadamente.
- Relatórios passam por elaboração e validação humana antes da publicação. Disponibilização interna não equivale a envio externo ou leitura.
- Não há geração de feedback, sugestão de intervenção, perfil psicológico, diagnóstico ou planejamento automático.
- TRI/Inep e pesos SISU exigem fonte verificada; não há pesos oficiais inventados.
- Sono e tempo de tela não são coletados, importados, exibidos nem usados na classificação. A extensibilidade futura é separada do núcleo acadêmico, conforme RNF-12–RNF-14.

## Brand Commitments

Nome Farol, equipe FNMM. Preservar azul marítimo, luz âmbar, legibilidade e metáfora do farol. A varredura é apresentação; o carregamento e a classificação independem da animação. Respeitar movimento reduzido, foco, teclado e tamanhos de tela.

## Evidence on Hand

A versão 4.0 do PDF local, datada de 17/10/2026, é a referência normativa disponível; o DOCX não estava no workspace. O prompt delimita a entrega principal no Mentor e nos serviços compartilhados.

Todos os nomes, alunos, números e eventos do seed são sintéticos. Rafael, adulto com plantões, é uma persona fictícia; não é um caso real confirmado. O depoimento anônimo de aluno presente em `proposta.html` foi registrado pela equipe na pesquisa original. Não há métricas de eficácia de um piloto real.

## Product Principles

1. Todo alerta expõe seus fatos, parâmetros e versão.
2. Somente o mentor interpreta, decide, escreve e publica orientação pedagógica.
3. Comparar o aluno com seu próprio histórico e indicar evidência insuficiente.
4. Preservar autoria, privacidade, vínculos e histórico.
5. Informar origem, atualização e estado real de sincronização ou entrega.
6. Configurar regras de forma explícita, validada, versionada e auditável.
7. Declarar limites da demonstração e requisitos parciais sem confundir uma tela com um fluxo implementado.
