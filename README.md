# Farol — Mentor, MVP v4.0

Interface funcional para acompanhar alunos de mentoria para o ENEM. O Farol reúne dados acadêmicos, compara cada aluno com seu próprio histórico e classifica evidências por regras versionadas. **Somente o mentor interpreta, escreve e publica orientações, planos, mensagens e relatórios.**

Esta entrega usa **dados totalmente sintéticos** e roda localmente. A interface preserva a identidade do Farol e acrescenta autenticação, autorização no servidor e persistência SQLite. Os papéis são Administrador, Mentor e Aluno; o aplicativo móvel completo e a gestão administrativa integral não fazem parte desta implementação.

## Executar

Requer Python 3.10+ com `sqlite3` e base de fusos horários IANA disponível ao `zoneinfo` (padrão em instalações Linux comuns). Desenvolvimento e testes realizados com Python 3.14; não há instalação de pacotes Python, build ou Docker obrigatório.

```bash
python3 server.py --seed
python3 server.py
```

Abra **http://127.0.0.1:8000**. O seed imprime as contas sintéticas e uma senha de demonstração gerada no terminal. O formulário de login inicia vazio. Para definir uma senha de demonstração, forneça `FAROL_DEMO_PASSWORD` com ao menos 12 caracteres antes do seed. Não use uma senha real.

O banco fica em `data/farol.sqlite3`, fora do controle de versão. Encerrar e iniciar novamente o servidor preserva os registros. O seed não apaga uma base existente nem redefine sua senha. Para outra demonstração independente, use `--db /tmp/farol-outra-demo.sqlite3` nos dois comandos. Consulte `python3 server.py --help` para as opções.

Opcionalmente copie `.env.example` para `.env`. O servidor lê automaticamente as opções documentadas; variáveis já exportadas no shell prevalecem. A avaliação acontece na inicialização, nas atualizações integradas e periodicamente enquanto o servidor estiver em execução. `python3 server.py --evaluate` permite executar uma avaliação e sair.

## Testar

```bash
python3 -m unittest discover -s tests -v
```

Os testes usam bancos temporários e incluem regras, autenticação, permissões e fluxos da API. A documentação registra separadamente verificações automatizadas e validações de interface.

Também há um teste opcional de navegador em `scripts/smoke_browser.py`. Ele requer Playwright/Chromium apenas para verificação, sem adicionar dependências à aplicação. A entrega foi verificada com **47 testes automatizados e o fluxo completo no Chromium**, incluindo viewport móvel, teclado, erro offline e escape de HTML.

## Usar a demonstração

1. Entre como mentor com uma conta impressa pelo seed. Consulte resumo semanal, fila de acompanhamento, carteira e central interna de notificações.
2. Abra um aluno para consultar evidências, histórico, disponibilidade, tarefas e agenda. Registre sua interpretação e utilidade do alerta.
3. Escreva uma nota privada, intervenção, plano ou relatório. Os campos começam em branco; publicação disponibiliza o conteúdo autenticado ao destinatário autorizado.
4. Entre como Administrador para criar um rascunho de regras, validar, simular, ativar e restaurar versões. Um rascunho não modifica os alertas existentes.
5. Use os contratos do aluno para consultar conteúdo publicado e registrar execução. Atualizações persistentes alimentam os indicadores do mentor.

Publicação e avisos são **internos à aplicação**. A demonstração não envia e-mails, WhatsApp ou mensagens a responsáveis por canal externo. Parâmetros TRI e pesos oficiais de cursos permanecem indisponíveis enquanto não houver fonte verificada.

## Arquivos e documentação

- `index.html`, `assets/`: interface autenticada, responsiva, com metáfora do farol.
- `server.py`, `farol/`, `migrations/`: servidor, serviços, motor de regras e banco.
- `tests/`: testes automatizados.
- `proposta.html`: apresentação alinhada à v4.0.
- [PRODUCT.md](PRODUCT.md): propósito, papéis e limites do produto.
- [Implementação](docs/IMPLEMENTACAO_MENTOR_V4.md): arquitetura, decisões provisórias, segurança e validação.
- [Contratos da API](docs/API.md): sessão, permissões, corpos das operações, idempotência e exemplo executável.
- [Rastreabilidade RF/CA](docs/RASTREABILIDADE_V4.md): estado de cada requisito e critério de aceite.

A fonte local lida foi **Farol_Documento_de_Requisitos_v4.pdf**, versão 4.0, de 17/10/2026. O DOCX solicitado não estava no workspace. A política existente ignora PDFs no Git; o documento local foi preservado. A matriz considera o recorte desta tarefa, priorizando o Mentor e contratos compartilhados, sem declarar o aplicativo completo do aluno como entregue.

Projeto da equipe **FNMM**, Case 2 — Engajamento e permanência, Hackathon PotiCode 2026.
