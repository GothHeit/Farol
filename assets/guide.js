// Guia do Farol: assistente que explica métricas ao mentor.
// Demonstração: respostas escritas à mão e conversas anteriores simuladas; nenhuma chamada externa.
// O guia explica o que um número significa. Interpretar e decidir o que fazer continua sendo do mentor.

const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const plain = s => String(s).toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[̀-ͯ]/g, '');
const rich = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\{\{(.+?)\}\}/g, '<button type="button" class="guide-src" data-src>$1</button>').replace(/\n/g, '<br>');
const num = v => typeof v === 'number' ? new Intl.NumberFormat('pt-BR', {maximumFractionDigits: 1}).format(v) : String(v ?? '—');

const DECISION = 'O que fazer com isso é decisão sua: o Farol mostra os fatos, e você interpreta.';

// Cada tópico: palavras-chave (sem acento), resposta e sugestões de continuação.
const TOPICS = [
  {id: 'levels', words: ['nivel', 'niveis', 'prioridade', 'atencao', 'observar', 'em dia', 'cores', 'cor ', 'significam'],
   text: 'O Farol agrupa cada aluno em um de quatro níveis, sempre do mais urgente ao mais tranquilo:\n• **Prioridade** — falar hoje (por exemplo, 7 dias ou mais sem acessar, ou 2 faltas seguidas).\n• **Atenção** — conversar nesta semana (dois ou mais sinais diferentes mudaram).\n• **Observar** — só acompanhar (um sinal isolado).\n• **Em dia** — nenhuma mudança relevante.\nA cor ajuda, mas o nome do nível está sempre escrito.',
   next: ['O que é "costuma ser"?', 'Como leio um alerta?', 'O que é "Sem dados suficientes"?']},
  {id: 'baseline', words: ['costuma', 'historico', 'referencia', 'propria', 'comparacao', 'comparar', 'baseline'],
   text: 'O Farol não compara um aluno com os colegas: compara **com ele mesmo**. "Costuma ser 90 %" é a média das últimas semanas dele. Se o cronograma caiu para 45 %, o sinal é essa queda em relação ao próprio normal, não a nota em si.\nPor isso um aluno com número baixo, mas estável, pode estar em dia.',
   next: ['O que significam os níveis?', 'Explique o cronograma', 'Como leio um alerta?']},
  {id: 'alert', words: ['alerta', 'por que', 'porque', 'evidencia', 'sinais', 'como leio'],
   text: 'Um alerta é a soma dos sinais que mudaram. Na ficha do aluno, em **Entender**, cada linha mostra:\n• o sinal (por exemplo, "Dias sem acesso à plataforma");\n• **Agora** — o valor desta semana;\n• **costuma ser** — o valor de referência dele;\n• o motivo, em uma frase.\nO bloco "Detalhes técnicos" guarda a regra exata, o peso e os dados brutos, caso você queira conferir.',
   next: ['O que é "costuma ser"?', 'Como registro minha decisão?', 'Resumo da semana']},
  {id: 'triage', words: ['triagem', 'registrar', 'util', 'registro', 'salvar', 'decisao'],
   text: 'Na ficha, depois de ler "Por que este alerta?", você responde "O que você faz com ele?":\n• uma anotação opcional com a sua interpretação;\n• **Em acompanhamento** — você vai seguir esse caso;\n• **Decidi agir** — você tomou uma atitude;\n• **Este alerta foi útil?** — ajuda a avaliar a qualidade dos alertas.\nNada disso é enviado ao aluno: é seu registro de trabalho.',
   next: ['Como leio um alerta?', 'O que o guia não faz?', 'Resumo da semana']},
  {id: 'schedule', words: ['cronograma', 'schedule'],
   text: '**Cumprimento do cronograma** é a porcentagem das atividades planejadas que o aluno realmente fez na semana. 100 % é tudo feito.\nO Farol dispara o sinal quando a queda passa de 20 % em relação ao que o aluno costuma cumprir (por exemplo, de 90 % para 45 %).',
   next: ['O que é "costuma ser"?', 'Explique a execução de tarefas', 'Explique a presença']},
  {id: 'attendance', words: ['presenca', 'falta', 'faltas', 'consecutiva', 'encontro'],
   text: '**Presença** é a porcentagem de encontros em que o aluno esteve presente. **Faltas consecutivas** conta quantos encontros seguidos ele perdeu.\nDuas faltas seguidas já colocam o aluno em Prioridade, porque é um sinal que costuma pedir contato rápido. Uma queda de presença maior que 20 % em relação ao normal dele também gera sinal.',
   next: ['Explique os dias sem acesso', 'Explique o cronograma', 'O que significam os níveis?']},
  {id: 'access', words: ['acesso', 'acessa', 'plataforma', 'login', 'sumiu'],
   text: '**Dias sem acesso** é quantos dias se passaram desde a última vez que o aluno entrou na plataforma. Com **7 dias ou mais**, o aluno vai direto para Prioridade.\nUm número alto pode ter muitas causas (viagem, prova, problema técnico). O Farol só mostra o dado; entender o motivo fica com você.',
   next: ['Explique a presença', 'O que significam os níveis?', 'O que o guia não faz?']},
  {id: 'scores', words: ['simulado', 'redacao', 'nota', 'notas', 'prova'],
   text: 'As **notas de simulado e de redação** entram como sinal quando caem mais de 15 % em relação à referência do aluno. As escalas desta demonstração são ilustrativas, sem cálculo oficial de TRI nem pesos oficiais de cursos.\nUma queda isolada de nota costuma aparecer como "Observar"; junto com outros sinais, pode subir para "Atenção".',
   next: ['Como leio um alerta?', 'Explique o cronograma', 'O que significam os níveis?']},
  {id: 'skipped', words: ['puladas', 'pulou', 'dificeis', 'dificil', 'questoes'],
   text: '**Questões difíceis puladas** é a porcentagem de questões de dificuldade alta que o aluno deixou em branco nas sessões de estudo. A regra só vale com pelo menos 2 sessões difíceis na semana, para evitar conclusões com poucos dados.\nCom 30 % ou mais puladas, o Farol gera um sinal.',
   next: ['Explique o tempo por questão', 'Como leio um alerta?', 'O que significam os níveis?']},
  {id: 'time', words: ['tempo por questao', 'segundos', 'tempo por', 'demora'],
   text: '**Tempo por questão** é o tempo médio, em segundos, que o aluno leva em cada questão registrada. O sinal aparece quando o tempo **sobe mais de 40 %** em relação ao normal dele.\nTempo maior pode indicar dificuldade; tempo muito menor, pressa. O número sozinho não diz qual das duas.',
   next: ['Explique as sessões depois das 23h', 'Explique questões puladas', 'Como leio um alerta?']},
  {id: 'late', words: ['23h', 'noite', 'madrugada', 'tarde da noite', 'sessoes depois'],
   text: '**Sessões a partir de 23h** contam quantas vezes o aluno estudou muito tarde na semana. O sinal aparece quando esse número sobe mais de 50 % em relação ao normal dele.\nÉ um sinal de mudança de rotina, não de erro.',
   next: ['Explique o tempo por questão', 'Explique o cronograma', 'O que significam os níveis?']},
  {id: 'tasks', words: ['tarefa', 'tarefas', 'execucao', 'atividades concluidas'],
   text: '**Execução de tarefas** é a porcentagem das tarefas da semana que o aluno marcou como concluídas. O Farol gera um sinal quando a execução cai mais de 20 % em relação ao normal dele.\nPlanos publicados criam tarefas; por isso, ao publicar um plano, a execução da semana passa a considerá-las.',
   next: ['Explique o cronograma', 'Explique a presença', 'Como leio um alerta?']},
  {id: 'nodata', words: ['sem dados', 'insuficiente', 'sem sincronizacao', 'novo aluno', 'sincroniza'],
   text: '**Sem dados suficientes** significa que o Farol ainda não tem histórico para comparar o aluno com ele mesmo (por exemplo, um aluno recém-chegado). Isso **não** quer dizer que está tudo bem: apenas que não dá para medir mudanças ainda.\nQuando o aluno passa a ter 2 semanas ou mais de dados, ele entra nos níveis normais.',
   next: ['O que significam os níveis?', 'O que é "costuma ser"?', 'Resumo da semana']},
  {id: 'limits', words: ['nao faz', 'limites', 'diagnostico', 'o que fazer', 'devo', 'aconselha', 'recomenda', 'conselho', 'como ajudo'],
   text: 'Eu **explico** métricas e mostro os fatos do painel. Eu **não** dou diagnóstico, não recomendo o que dizer ao aluno e não escrevo planos, mensagens ou relatórios por você.\n' + DECISION,
   next: ['O que significam os níveis?', 'Como leio um alerta?', 'Resumo da semana']},
  {id: 'thanks', words: ['obrigad', 'valeu', 'ajudou', 'show', 'otimo'],
   text: 'Que bom! Se quiser, posso explicar outra métrica ou resumir a sua semana.',
   next: ['Resumo da semana', 'O que significam os níveis?']},
  {id: 'hello', words: ['oi', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'e ai'],
   text: 'Olá! Posso explicar as métricas do painel com palavras simples. Escolha uma pergunta abaixo ou escreva a sua.',
   next: ['Resumo da semana', 'O que significam os níveis?', 'Como leio um alerta?']},
];

const DEFAULT_CARDS = ['Resumo da semana', 'O que significam os níveis?', 'O que é "costuma ser"?', 'Como leio um alerta?'];
const FALLBACK = {
  text: 'Não encontrei essa pergunta nas minhas explicações. Eu sei falar sobre níveis, alertas, presença, cronograma, notas, tarefas, tempo por questão e acesso. Tente uma destas:',
  next: ['O que significam os níveis?', 'Como leio um alerta?', 'O que o guia não faz?'],
};

// Conversas anteriores simuladas (somente para demonstração).
const PAST = [
  {id: 'p0', student: 'student_lucas', title: 'Lucas S. · resumo da semana', when: 'Hoje · 08:10', messages: [
    {from: 'bot', text: 'Questões difíceis puladas: **80 %** (costuma ser 20 %) {{Estudo}}\nCumprimento do cronograma: **45 %** (costuma ser 90 %) {{Cronograma}}\nO último simulado e as redações seguem no padrão dele {{Simulados}}'},
    {from: 'user', text: 'O que mudou mais em relação ao normal?'},
    {from: 'bot', text: 'A maior mudança foi nas questões difíceis puladas: de 20 % para 80 % nas sessões desta semana. O cronograma também caiu, de 90 % para 45 %. As notas não mudaram. {{Estudo}}\nO que isso significa para a conversa com Lucas é decisão sua.'},
  ]},
  {id: 'p1', title: 'O que é "costuma ser"?', when: 'Ontem · 14:20', messages: [
    {from: 'user', text: 'No alerta aparece "costuma ser 90 %". De onde vem esse 90?'},
    {from: 'bot', text: 'Vem do **próprio histórico do aluno**: é a média das últimas semanas dele. O Farol não compara com os colegas, só com o normal de cada um.'},
    {from: 'user', text: 'Então se a nota dele é baixa, mas sempre foi baixa, não alerta?'},
    {from: 'bot', text: 'Isso mesmo. O sinal é a **mudança**, não o valor. Um aluno com número baixo e estável pode estar em dia.\n' + DECISION},
  ]},
  {id: 'p2', title: 'Diferença entre Atenção e Observar', when: 'Há 3 dias · 09:05', messages: [
    {from: 'user', text: 'Qual a diferença entre Atenção e Observar?'},
    {from: 'bot', text: '**Observar** é um sinal isolado: só acompanhar. **Atenção** é quando dois ou mais sinais diferentes mudaram na mesma semana: vale conversar nesta semana.'},
    {from: 'user', text: 'E Prioridade?'},
    {from: 'bot', text: '**Prioridade** é para sinais que pedem contato rápido, como 7 dias ou mais sem acesso ou 2 faltas seguidas. Aparece primeiro na fila.'},
  ]},
  {id: 'p3', title: 'Por que a presença caiu?', when: 'Semana passada · 17:40', messages: [
    {from: 'user', text: 'A presença da Marina aparece como 0 %. Isso é erro?'},
    {from: 'bot', text: 'Não é erro de cálculo: 0 % significa que ela não esteve em nenhum dos encontros registrados na semana. Duas faltas seguidas também levam à Prioridade.'},
    {from: 'user', text: 'Você sabe o motivo das faltas?'},
    {from: 'bot', text: 'Não. O Farol só tem o registro de presença, não o motivo. ' + DECISION},
  ]},
];

function reducedMotion() { try { return matchMedia('(prefers-reduced-motion: reduce)').matches; } catch { return false; } }

const LEVEL = {prio: 'Prioridade', att: 'Atenção', obs: 'Observar', ok: 'Em dia', unknown: 'Sem dados suficientes'};
const first = name => String(name || '').split(' ')[0];
const evidenceOf = item => { const raw = item?.evidence || []; return Array.isArray(raw) ? raw : (raw.signals || []); };

function studentOf(data, id) {
  const base = (data?.students || []).find(x => x.id === id);
  const alert = (data?.queue || []).find(x => x.student_id === id);
  return base ? {id, name: base.name, level: base.level, alert} : null;
}

const sigName = e => e.title || e.label || e.signal || 'Sinal';

function signalLine(e, withSource) {
  const u = e.unit ? ' ' + e.unit : '';
  const base = e.baseline != null ? ` (costuma ser ${num(e.baseline)}${u})` : '';
  return `${sigName(e)}: **${num(e.observed)}${u}**${base}${withSource ? ' {{Alerta}}' : ''}`;
}

// Linhas do cartão de resumo: cada frase traz um link para a fonte na ficha.
function summaryLines(info) {
  if (!info) return [];
  const list = evidenceOf(info.alert);
  if (list.length) return list.slice(0, 4).map(e => signalLine(e, true));
  return [`Nível: **${LEVEL[info.level] || 'sem avaliação'}**. Nenhum sinal de mudança nesta semana. {{Painel}}`];
}

function weekSummary(data) {
  const s = data?.summary || {};
  const queue = data?.queue || [];
  const total = (s.prio || 0) + (s.att || 0) + (s.obs || 0) + (s.ok || 0) + (s.unknown || 0);
  if (!total) return 'Ainda não tenho dados da sua carteira nesta sessão.';
  let t = `Esta semana, entre os seus **${total} alunos**:\n• **${s.prio || 0}** em Prioridade\n• **${s.att || 0}** em Atenção\n• **${s.obs || 0}** em Observar\n• **${s.ok || 0}** em dia`;
  if (s.unknown) t += `\n• **${s.unknown}** sem dados suficientes`;
  if (queue.length) t += `\n\nNa fila de acompanhamento, os casos mais urgentes são: ${queue.slice(0, 3).map(q => q.student_name).join(', ')}.`;
  return t + '\nEscolha um aluno em "Sobre" para ver o resumo dele.';
}

function studentAnswer(q, info) {
  const name = info.name, list = evidenceOf(info.alert);
  const cards = studentCards(info);
  if (/historic|costuma|compar|normal|referencia/.test(q)) {
    const rows = list.filter(e => e.baseline != null).slice(0, 5).map(e => `• ${sigName(e)}: agora ${num(e.observed)}${e.unit ? ' ' + e.unit : ''}, costuma ser ${num(e.baseline)}${e.unit ? ' ' + e.unit : ''} {{Histórico}}`);
    return {text: rows.length ? `Comparando ${name} com o próprio histórico:\n${rows.join('\n')}\n${DECISION}` : `Não há comparação com o histórico de ${name} nos alertas desta semana. {{Painel}}`, next: cards};
  }
  if (/dados|disponiv|falta|sincron/.test(q)) {
    return {text: `Nível de ${name}: **${LEVEL[info.level] || 'sem avaliação'}**. ${info.level === 'unknown' ? 'Ainda não há histórico para comparar com ele mesmo.' : 'Há histórico suficiente para comparar com ele mesmo.'} {{Painel}}\nDetalhes de presença, simulados e estudo estão na ficha, em Entender.`, next: cards};
  }
  if (/mudou|destac|por que|porque|alerta|sinais|resumo|semana/.test(q)) {
    if (!list.length) return {text: `**${name}** não tem alerta de Atenção ou Prioridade nesta semana. Nível: **${LEVEL[info.level] || 'sem avaliação'}**. {{Painel}}`, next: cards};
    return {text: `**${name}** tem ${list.length} ${list.length > 1 ? 'sinais' : 'sinal'} nesta semana:\n${list.slice(0, 5).map(e => '• ' + signalLine(e, true)).join('\n')}\nCada linha compara a semana atual com o normal do próprio aluno. ${DECISION}`, next: cards};
  }
  return null;
}

const studentCards = info => [`O que mudou com ${first(info.name)}?`, `Por que ${first(info.name)} foi destacado?`, `Compare ${first(info.name)} com o próprio histórico`, 'Quais dados existem?'];

// Palavras curtas só valem inteiras (evita "oi" dentro de "noite").
const hit = (q, w) => w.trim().length <= 4 ? q.includes(' ' + w.trim() + ' ') : q.includes(w);

function answer(question, data, studentId) {
  const q = ' ' + plain(question) + ' ';
  const info = studentId ? studentOf(data, studentId) : null;
  if (info) { const r = studentAnswer(q, info); if (r) return r; }
  if (!info && /resumo|minha semana|como esta a turma|quem esta|visao geral/.test(q)) {
    return {text: weekSummary(data), next: ['O que significam os níveis?', 'Como leio um alerta?']};
  }
  let best = null, bestScore = 0;
  for (const topic of TOPICS) {
    const score = topic.words.reduce((n, w) => n + (hit(q, w) ? 1 + (w.length > 6 ? 1 : 0) : 0), 0);
    if (score > bestScore) { best = topic; bestScore = score; }
  }
  if (best) return {text: best.text, next: best.next};
  return info ? {text: FALLBACK.text, next: studentCards(info)} : FALLBACK;
}

let root = null, state = null;

export function mountGuide({userId, getData, openStudent}) {
  unmountGuide();
  state = {userId, getData, openStudent, open: false, view: 'chat', who: '', threads: {}, cards: null, busy: false, trigger: null};
  try { const saved = JSON.parse(localStorage.getItem('farol.guide.v2.' + userId) || 'null'); if (saved && typeof saved === 'object') { state.threads = saved.threads || {}; state.who = saved.who || ''; } } catch { /* sem armazenamento */ }
  root = document.createElement('div');
  root.id = 'guideRoot';
  root.innerHTML = `
    <button type="button" class="guide-tab" id="guideOpen" aria-expanded="false" aria-controls="guidePanel"><svg class="guide-ico" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 3v18"/><path d="M12.5 8h3.5M12.5 12h3.5M12.5 16h2"/><path d="M3 7h3M3 12h3M3 17h3"/></svg><span>Caderneta</span></button>
    <aside class="guide-panel" id="guidePanel" role="complementary" aria-label="Caderneta do mentor" hidden>
      <header class="guide-head">
        <div class="guide-title"><svg class="guide-ico" viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 3v18"/><path d="M12.5 8h3.5M12.5 12h3.5M12.5 16h2"/><path d="M3 7h3M3 12h3M3 17h3"/></svg><div><h2>Caderneta</h2><p>Guia de métricas e suas anotações</p></div></div>
        <div class="guide-head-actions">
          <button type="button" class="guide-icon" id="guideHistory" title="Conversas anteriores" aria-label="Conversas anteriores" aria-pressed="false">🕘</button>
          <button type="button" class="guide-icon" id="guideNew" title="Nova conversa" aria-label="Nova conversa">＋</button>
          <button type="button" class="guide-icon" id="guideClose" title="Fechar caderneta" aria-label="Fechar caderneta">×</button>
        </div>
      </header>
      <div class="guide-who-pick"><label for="guideWho">Sobre</label><select id="guideWho"></select></div>
      <div class="guide-body" id="guideBody"></div>
      <div class="guide-foot" id="guideFoot">
        <div class="guide-cards" id="guideCards" role="group" aria-label="Sugestões de perguntas"></div>
        <form class="guide-form" id="guideForm" autocomplete="off">
          <label class="sr" for="guideInput">Escreva sua pergunta</label>
          <input id="guideInput" type="text" maxlength="300" enterkeyhint="send">
          <button type="submit" class="btn-sm solid" id="guideSend">Enviar</button>
        </form>
        <p class="guide-note">Demonstração: respostas simuladas. O guia explica métricas; a decisão é sua.</p>
      </div>
    </aside>`;
  document.body.appendChild(root);
  bind();
  render();
}

export function unmountGuide() {
  if (root) root.remove();
  root = null;
  document.body.classList.remove('guide-open');
}

export function setGuideInert(value) { if (root) root.inert = !!value; }

const $ = s => root.querySelector(s);
const thread = () => state.threads[state.who || 'all'] || (state.threads[state.who || 'all'] = []);

function save() {
  try { localStorage.setItem('farol.guide.v2.' + state.userId, JSON.stringify({who: state.who, threads: Object.fromEntries(Object.entries(state.threads).map(([k, v]) => [k, v.slice(-60)]))})); } catch { /* sem armazenamento */ }
}

function setOpen(open) {
  state.open = open;
  $('#guidePanel').hidden = !open;
  $('#guideOpen').hidden = open;
  $('#guideOpen').setAttribute('aria-expanded', String(open));
  document.body.classList.toggle('guide-open', open);
  if (open) { state.trigger = document.activeElement; render(); $('#guideInput').focus(); scrollDown(); }
  else if (state.trigger?.isConnected) state.trigger.focus();
  else $('#guideOpen').focus();
}

function scrollDown() { const b = $('#guideBody'); if (b) b.scrollTop = b.scrollHeight; }

function bubble(m) {
  return `<div class="guide-msg ${m.from === 'user' ? 'me' : 'bot'}"><span class="guide-who">${m.from === 'user' ? 'Você' : 'Guia'}</span><div class="guide-bubble">${rich(m.text)}</div></div>`;
}

function fillPicker(data) {
  const order = {prio: 0, att: 1, obs: 2, unknown: 3, ok: 4};
  const students = [...(data?.students || [])].sort((a, b) => (order[a.level] ?? 5) - (order[b.level] ?? 5) || a.name.localeCompare(b.name, 'pt-BR'));
  const sel = $('#guideWho');
  sel.innerHTML = `<option value="">Minha turma</option>` + students.map(s => `<option value="${esc(s.id)}">${esc(s.name)} · ${esc(LEVEL[s.level] || '')}</option>`).join('');
  sel.value = students.some(s => s.id === state.who) ? state.who : '';
  state.who = sel.value;
}

function summaryCard(info) {
  const title = info ? `${esc(info.name)} · resumo da semana` : 'Guia do Farol';
  const lines = info ? summaryLines(info) : ['Explico as métricas do painel com palavras simples.', 'Escolha um aluno em "Sobre" para ver o resumo dele.'];
  return `<section class="guide-summary" aria-label="${title}"><div class="guide-summary-head"><h2>${title}</h2><span class="guide-ai">Gerado por IA · confira os fatos</span></div>${lines.map(l => `<p>${rich(l)}</p>`).join('')}<hr></section>`;
}

function render() {
  const data = state.getData();
  fillPicker(data);
  const info = state.who ? studentOf(data, state.who) : null;
  const body = $('#guideBody');
  $('#guideHistory').setAttribute('aria-pressed', String(state.view === 'history'));
  $('#guideInput').placeholder = info ? `Pergunte sobre ${first(info.name)}…` : 'Pergunte sobre as métricas…';
  if (state.view === 'history') {
    body.innerHTML = `<h3 class="guide-sub">Conversas anteriores</h3><ul class="guide-past">${PAST.map(p => `<li><button type="button" data-past="${p.id}"><strong>${esc(p.title)}</strong><small>${esc(p.when)} · ${p.messages.length} mensagens</small></button></li>`).join('')}</ul><p class="guide-note">Abra uma conversa para continuar de onde parou.</p>`;
    $('#guideFoot').hidden = true;
    return;
  }
  $('#guideFoot').hidden = false;
  body.innerHTML = summaryCard(info) + thread().map(bubble).join('') + (state.busy ? '<div class="guide-msg bot" role="status"><span class="guide-who">Guia</span><div class="guide-bubble guide-typing">Escrevendo…</div></div>' : '');
  const defaults = info ? studentCards(info) : ['Resumo da semana', 'O que significam os níveis?', 'O que é "costuma ser"?', 'Como leio um alerta?'];
  $('#guideCards').innerHTML = (state.cards || defaults).map(l => `<button type="button" class="guide-card" data-card="${esc(l)}"${state.busy ? ' disabled' : ''}>${esc(l)}</button>`).join('');
  scrollDown();
}

function send(text) {
  text = text.trim();
  if (!text || state.busy) return;
  state.view = 'chat';
  const ctx = state.who;
  thread().push({from: 'user', text});
  state.busy = true;
  save();
  render();
  const reply = () => {
    const result = answer(text, state.getData(), ctx);
    (state.threads[ctx || 'all'] ||= []).push({from: 'bot', text: result.text});
    state.cards = result.next;
    state.busy = false;
    save();
    if (root) render();
  };
  if (reducedMotion()) reply(); else setTimeout(reply, 600);
}

function bind() {
  $('#guideOpen').addEventListener('click', () => setOpen(true));
  $('#guideClose').addEventListener('click', () => setOpen(false));
  $('#guidePanel').addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); setOpen(false); } });
  $('#guideHistory').addEventListener('click', () => { state.view = state.view === 'history' ? 'chat' : 'history'; render(); });
  $('#guideNew').addEventListener('click', () => { state.threads[state.who || 'all'] = []; state.cards = null; state.view = 'chat'; state.busy = false; save(); render(); $('#guideInput').focus(); });
  $('#guideWho').addEventListener('change', e => { state.who = e.target.value; state.cards = null; state.view = 'chat'; save(); render(); });
  $('#guideForm').addEventListener('submit', e => { e.preventDefault(); const input = $('#guideInput'); const v = input.value; input.value = ''; send(v); input.focus(); });
  $('#guideCards').addEventListener('click', e => { const b = e.target.closest('[data-card]'); if (b) send(b.dataset.card); });
  $('#guideBody').addEventListener('click', e => {
    const src = e.target.closest('[data-src]');
    if (src && state.who) { state.openStudent?.(state.who); return; }
    const b = e.target.closest('[data-past]');
    if (!b) return;
    const past = PAST.find(p => p.id === b.dataset.past);
    state.who = past.student || '';
    state.threads[state.who || 'all'] = past.messages.map(m => ({...m}));
    state.cards = null;
    state.view = 'chat';
    save();
    render();
    $('#guideInput').focus();
  });
}
