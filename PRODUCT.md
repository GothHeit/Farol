# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

HTML/CSS estático, sem backend e sem build, publicado no GitHub Pages (`index.html`, `proposta.html`). Escolha confirmada pela equipe para o hackathon.

## Users

- **Mentor** (usuário do painel): acompanha muitos alunos de mentoria para o ENEM, com informações espalhadas entre presença, simulados, cronograma e mensagens. Precisa saber, no começo da semana, quem precisa de atenção, por quê e o que fazer.
- **Aluno** (usuário do próximo passo): estudante que se prepara para o ENEM com mentoria, em geral adolescente de escola particular. Recebe números de desempenho, mas não sabe o que mudar na rotina.
- **Coordenador** (supervisiona os mentores): verifica se os alertas estão sendo atendidos a tempo, quais mentores estão sobrecarregados e se os alertas são úteis. Lê os feedbacks que cada mentor enviou aos alunos; as anotações privadas do mentor não são compartilhadas.
- **Família**: recebe o relatório semanal quando o aluno é menor de idade, com consentimento. O aluno vê o mesmo conteúdo.

## Product Purpose

O Farol detecta cedo quando um aluno começa a se afastar da preparação, avisa o mentor mostrando os sinais que motivaram o alerta e sugere uma ação. Para o aluno, transforma o diagnóstico ("errei X, acertei Y") em um próximo passo concreto para a semana. Sucesso: menos alunos abandonando a mentoria e alunos que sabem o que fazer.

## Positioning

As mentorias atuais entregam diagnóstico; o Farol entrega a próxima ação e confere se ela funcionou. Os alertas são explicáveis: cada um lista os sinais simples que o geraram, comparados com o histórico do próprio aluno.

## Operating Context

- Proposta para o Case 2 (Engajamento e permanência nos estudos) do Hackathon PotiCode 2026, equipe FNMM.
- Cliente-alvo: AMentoria, mentoria para o ENEM.
- Ciclo semanal: o mentor abre o painel na segunda-feira, revisa a fila de alertas, registra ações e faz follow-up na semana seguinte.
- Sinais usados: presença nos encontros, cumprimento do cronograma, simulados e redações, questões puladas e tempo por questão, tempo de resposta ao mentor, horário de estudo.

## Capabilities and Constraints

- Níveis de atenção: Observar, Atenção, Prioridade.
- Perfis prováveis, sempre como hipótese e nunca como diagnóstico: sobrecarga, perda de motivação, dificuldade numa área, conciliar trabalho e estudo.
- Dificuldade das questões a partir dos parâmetros TRI dos microdados do ENEM (Inep).
- O mentor revisa todo alerta antes de qualquer contato com a família.
- O mentor envia feedback personalizado ao aluno a partir de um rascunho gerado com base nos sinais; os feedbacks enviados ficam num histórico visível para o mentor e para a coordenação.
- Linguagem sem rótulos estigmatizantes: "precisa de atenção", nunca "aluno em risco".
- Protótipo visual: a lógica de score não está implementada; as telas usam dados fixos.

## Brand Commitments

- Nome do produto: Farol. Equipe: FNMM.
- Metáfora do farol definida pela equipe: o facho de luz que varre e revela quem precisa de atenção. No login, a luz só gira ao clicar em Entrar, revela o painel e o farol se dissolve nele; no painel, a varredura acontece uma vez.

## Evidence on Hand

- Depoimento real de um aluno entrevistado pela equipe: "a mentoria me diz: errei X, acertei Y, ok, mas e aí? e agora? o que eu tenho que adaptar na minha rotina? como?" Pode ser citado sem nome.
- Todos os alunos, nomes e números nas telas são sintéticos. Não há dados reais de alunos, métricas de precisão medidas, clientes ou depoimentos além do citado acima; não inventar.
- O aluno adulto que trabalha em escala de plantões (Rafael, 29 anos, nas telas) é uma persona fictícia criada pela equipe. Nunca apresentá-lo como caso real, confirmado ou relatado pela AMentoria.

## Product Principles

1. Toda indicação vem com o motivo: nenhum alerta sem os sinais que o geraram.
2. Ação antes de classificação: cada alerta termina em uma ação sugerida e registrável.
3. O humano decide: o sistema sugere, o mentor confirma.
4. Comparar o aluno com ele mesmo, não com uma régua única.
5. Cuidado com menores: dados mínimos, consentimento dos responsáveis e transparência com o aluno.
