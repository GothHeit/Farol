# Farol · Design System (decisões e motivos)

Escopo: app do **Mentor** (`index.html`, `assets/app.css`, `assets/app.js`) e app do **Aluno** (`farol-aluno/`). As mudanças são visuais e de apresentação; regras de negócio, API e persistência não foram alteradas.

## 1. Princípios

1. **Claro de primeira.** Todo número, nível ou botão diz o que significa e o que fazer, em linguagem simples. *Por quê:* mentor e aluno devem entender a tela só batendo o olho.
2. **Nunca só cor.** Todo nível aparece também por texto. *Por quê:* acessibilidade (daltonismo) e clareza.
3. **Interface calma, estilo Notion.** Fundo branco, bordas finas, cantos pouco arredondados, sombras quase imperceptíveis. *Por quê:* o mentor acompanha muitos alunos; menos ruído visual reduz cansaço.
4. **O farol é a identidade.** A animação do facho é curta e respeita `prefers-reduced-motion`. *Por quê:* marca sem prejudicar quem é sensível a movimento.

## 2. Cores

Tokens no `:root` de `assets/app.css` e `farol-aluno/style.css`. Os nomes antigos (`--night`, `--panel`, `--warn`, `--navy`…) continuam existindo como **apelidos** dos tokens novos, para o CSS legado não quebrar.

| Token | Valor | Uso | Por quê |
|---|---|---|---|
| `--bg` | `#ffffff` | fundo | tema claro, leitura confortável |
| `--bg-soft` | `#f7f6f3` | chips, estados vazios, fundo da página do aluno | separa áreas sem borda forte |
| `--bg-hover` | `#efeeeb` | hover de botões neutros | feedback discreto |
| `--line` | `#e9e9e7` | bordas de cards, divisórias | divisória leve |
| `--line-strong` | `#d3d1cb` | bordas de inputs e botões | controles precisam parecer clicáveis |
| `--ink` | `#37352f` | texto principal | cinza-quente, menos agressivo que preto puro |
| `--muted` | `#6b6a66` | texto secundário | contraste ≥ 5:1 no branco |
| `--dim` | `#8a8883` | hover de borda, terciário | só onde o contraste não é crítico |
| `--brand` | `#1f4e8c` | ação primária, foco, abas ativas | azul de caderno: confiança e contexto escolar |
| `--brand-soft` | `#e7eef8` | avatar, seleção, pílula de status | variação suave da marca |
| `--beam` | `#f5b301` | facho, marcadores de atenção | amarelo de lápis, remete ao farol |

### Níveis de aluno

Sempre exibidos do mais urgente ao mais tranquilo, **com texto além da cor**.

| Nível | Chave | Texto | Fundo | Borda | Significado |
|---|---|---|---|---|---|
| Prioridade | `prio` | `--red` `#c4432b` | `--red-bg` `#fbe4e0` | `--red-line` `#e8907f` | falar hoje |
| Atenção | `att` | `--yellow` `#8a5a00` (marcadores `--beam`) | `--yellow-bg` `#fbf3db` | `--yellow-line` `#e8c15a` | conversar nesta semana |
| Observar | `obs` | `--blue` `#0b6e99` | `--blue-bg` `#ddebf1` | `#c3dbe7` | só acompanhar |
| Em dia | `ok` | `--green` `#0f7b6c` | `--green-bg` `#ddedea` | — | nada a fazer |

Regras:
- Não criar cores fora desta tabela.
- Azul de marca é para **ação** (botões, links, foco); as cores de nível são só para **nível**.
- Cada nível tem cor de texto e de fundo separadas, para manter contraste.

## 3. Tipografia

Fonte **Inter** (400–800) via Google Fonts, nos dois apps. Corpo 15px/1.55, inputs 16px (evita zoom no iOS), títulos com `text-wrap: balance` e `letter-spacing: -.01em`, números de contadores com `tabular-nums`. *Por quê:* legível em telas pequenas e neutra.

## 4. Forma e layout

- Raios: 4px (etiquetas, chips), 6px (botões, inputs), 8px (cards, tiles), 10px (painéis), 999px (pílulas).
- Bordas de 1px: `--line` em cards, `--line-strong` em controles.
- Área de toque mínima de 44px em botões, campos e abas.
- Foco visível: `outline: 2px solid var(--brand); outline-offset: 2px`.
- O app do aluno mantém o formato de aplicativo em moldura de celular (decisão anterior de layout, não alterada).

## 5. Decisões de interface

### Mentor
- **Login:** caderno pautado com margem vermelha, mar claro e a torre do farol com o formulário. Reforça escola + identidade.
- **Fila primeiro:** "Fila de acompanhamento" vem antes de "Sua turma" (à esquerda no desktop, no topo no mobile). *Por quê:* responde "quem precisa de mim hoje?" logo no topo.
- **Uma frase por aluno:** o card mostra o sinal principal como frase, por exemplo "Variação do cumprimento do cronograma: 45 % (costuma ser 90 %) · e mais 1 sinal". A comparação com o histórico só aparece quando o alerta traz uma referência. *Por quê:* leitura rápida; os detalhes completos ficam na ficha, em "Evidências".
- **Níveis:** contadores/filtros por nível com ponto colorido e texto; tiles em destaque para Atenção e Prioridade.
- **Ficha lateral (drawer):** painel branco com cabeçalho fixo, botão de fechar de 44px e fundo escurecido.

- **Cabeçalho enxuto:** só "Olá, Ana." e uma linha com o número de alunos e a última atualização. *Por quê:* textos de boas-vindas não ajudam a decidir.
- **Painel enxuto:** três números com rótulos curtos; o filtro por nível fica só nos botões coloridos (o seletor repetido saiu); "Variações depois de intervenções" e "Qualidade dos alertas" ficam em "Mais análises", recolhido.
- **Turma:** alunos "Em dia" ficam recolhidos num grupo ("Em dia (2) · mostrar alunos"), que abre sozinho ao buscar ou filtrar por Em dia. A data de sincronização só aparece quando falta ou está atrasada (2 dias ou mais).
- **Demonstração:** o aviso virou uma etiqueta "Demonstração" na barra do topo, no lugar da faixa de uma linha inteira.
- **Triagem simplificada:** "Por que este alerta?" (um sinal por linha, "Agora: X · costuma ser: Y") e "O que você faz com ele?" (anotação opcional, acompanhamento, decidi agir, útil, Salvar). Regra, peso, janela, dados brutos e histórico ficam em "Detalhes técnicos"; alertas anteriores ficam recolhidos.
- **Ficha em 3 abas:** **Entender** (alertas e panorama), **Agir** (planos e agenda, anotações e intervenções, mensagens; uma seção aberta por vez) e **Relatórios**.

### Aluno
- **"O que fazer agora":** card no topo da home com a próxima tarefa pendente (a de prazo mais próximo), matéria, prazo, etiqueta "Alta" quando for o caso e botão "Começar" que leva ao quadro. Sem pendências: "Tudo em dia!" com botão para os estudos. *Por quê:* uma pergunta, uma ação, menos decisão para o aluno.
- **Contadores com ação:** cada número é um link que leva à tela relacionada ("Ver quadro →", "Abrir agenda →"). Ficam abaixo do card "O que fazer agora".
- **Texto mínimo de 12px** nos dois apps (antes havia 9–11px).

### Segurança e fonte
A política de segurança do servidor (`server.py`) passou a permitir `fonts.googleapis.com` (estilos) e `fonts.gstatic.com` (fontes), somente para carregar a Inter.

## 6. Movimento e acessibilidade

- Animações curtas (.3 a .5s); `prefers-reduced-motion` é respeitado (no mentor, as animações são desligadas).
- Link "Ir ao conteúdo", ficha como `dialog` com foco preso, regiões vivas para status e alertas.
- Texto secundário com contraste ≥ 4.5:1.

## 7. Tom de voz

Português claro e direto, verbos de ação nos botões ("Começar", "Ver evidências e registrar triagem"), mensagens vazias que dizem o que fazer em seguida.

## 8. Lacunas conhecidas (ainda não aplicadas)

- Callout "Como usar esta tela" e ficha dividida nas quatro caixas do documento original.
- Botão "Pular animação" da varredura e animação de login com giro do facho.
- Um único botão primário por card no mentor.
- Prioridades "Hoje / Esta semana / Depois" no aluno.
- Estados de carregamento e erro: já existem mensagens simples ("Carregando seus dados…", "Tentar novamente"), sem padronização visual própria.
- `proposta.html` mantém o visual anterior.
