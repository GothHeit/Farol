# Farol Aluno

Protótipo da **visão do aluno** do Farol, apresentado no site com formato de aplicativo de celular. No computador, a interface aparece em uma moldura de app; no celular, ocupa a tela inteira e usa navegação fixa na parte inferior. Feito com HTML, CSS e JavaScript puro, com identidade azul escuro e amarelo. Não precisa de instalação, compilação, conta ou backend.

## Abrir no computador

Abra `index.html` no navegador. Para uma prévia com servidor local, você também pode usar um servidor HTTP estático de sua preferência na pasta do projeto.

## O que funciona nesta demonstração

- **Início:** atividades pendentes, agenda próxima, plano publicado e histórico recente.
- **Kanban e checklist:** criar, editar, priorizar, mover e excluir tarefas; marcar etapas e acompanhar o progresso.
- **Agenda:** visualizações diária e semanal; criar, reagendar, concluir, marcar como não realizado e excluir compromissos.
- **Estudos:** responder ou pular questões ilustrativas, ver correção, registrar a causa percebida do erro e consultar o histórico.
- **Mentor:** consultar um plano demonstrativo já publicado pela mentora e incorporar atividades ao quadro ou à agenda sem duplicações.

As alterações são guardadas no `localStorage` do navegador. O botão **Reiniciar demo** recupera os dados iniciais. As datas da agenda demonstrativa são geradas em relação ao dia em que você abre o app.

## Publicar no GitHub Pages

1. Crie um repositório no GitHub e envie **os arquivos desta pasta diretamente para a raiz** do repositório: `index.html`, `style.css`, `app.js`, `favicon.svg` e `README.md`. O `index.html` precisa ficar na raiz publicada.
2. Abra **Settings → Pages** no repositório.
3. Em **Build and deployment → Source**, escolha **Deploy from a branch**.
4. Selecione a branch usada para os arquivos, normalmente `main`, e a pasta **/(root)**. Clique em **Save**.
5. Aguarde a publicação. O endereço do site aparecerá na página **Pages** do repositório.

Instruções oficiais: [Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Estrutura

```text
farol-aluno/
├── index.html    # Estrutura das telas e formulários
├── style.css     # Identidade visual e adaptação para celular
├── app.js        # Navegação, dados de demonstração e interações
├── favicon.svg   # Ícone do projeto
└── README.md     # Este arquivo
```

## Limites do protótipo

Esta entrega é uma **demonstração web com aparência de app**, não um aplicativo nativo para instalar pela loja. Contém apenas a visão demonstrativa do aluno. Não há autenticação, banco de dados, sincronização entre dispositivos, notificações reais, painel do mentor ou painel do administrador. O plano exibido é um exemplo estático atribuído à mentora; o aluno não edita nem publica orientações em nome dela. Os dados e as questões são fictícios e não representam questões oficiais do ENEM. Evite inserir informações pessoais reais, especialmente se for compartilhar o navegador ou publicar uma versão personalizada.

Para transformar o protótipo em produto operacional, serão necessários backend, controle de acesso por papel, persistência segura, sincronização, gestão de consentimento e integração com as visões de mentor e administrador previstas no documento de requisitos.
