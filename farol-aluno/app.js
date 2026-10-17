/* Farol Aluno — protótipo local, sem serviços externos ou dados reais. */
(() => {
  'use strict';
  const KEY = 'farol-aluno-demo-v1';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const pad = n => String(n).padStart(2, '0');
  const dateKey = date => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  const fromKey = key => new Date(`${key}T12:00:00`);
  const offset = days => { const d = new Date(); d.setHours(12, 0, 0, 0); d.setDate(d.getDate() + days); return dateKey(d); };
  const formatDate = (key, options = { day: '2-digit', month: 'short' }) => new Intl.DateTimeFormat('pt-BR', options).format(fromKey(key));
  const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  const uid = () => globalThis.crypto?.randomUUID?.() || `id-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const statuses = [{ key: 'todo', name: 'A fazer' }, { key: 'doing', name: 'Em andamento' }, { key: 'done', name: 'Concluído' }];
  const questions = [
    { id: 'q1', subject: 'Matemática', topic: 'Porcentagem', context: 'Estudo', text: 'Uma mochila de R$ 120 recebeu desconto de 25%. Qual é o preço final?', options: ['R$ 75', 'R$ 90', 'R$ 95', 'R$ 100'], answer: 1, explanation: '25% de 120 é 30. O preço final é 120 − 30 = R$ 90.' },
    { id: 'q2', subject: 'Linguagens', topic: 'Interpretação', context: 'Estudo', text: 'Em “Apesar da chuva, a turma participou”, a expressão inicial indica:', options: ['causa', 'concessão', 'finalidade', 'conclusão'], answer: 1, explanation: '“Apesar de” apresenta uma concessão: a chuva não impediu a participação.' },
    { id: 'q3', subject: 'Ciências da Natureza', topic: 'Ecologia', context: 'Simulado', text: 'Em uma cadeia alimentar, qual grupo produz matéria orgânica a partir de energia luminosa?', options: ['Decompositores', 'Consumidores primários', 'Produtores', 'Predadores'], answer: 2, explanation: 'Produtores, como plantas, realizam fotossíntese e formam matéria orgânica.' },
    { id: 'q4', subject: 'Ciências Humanas', topic: 'Geografia', context: 'Estudo', text: 'Qual processo está diretamente associado à saída da população do campo para a cidade?', options: ['Êxodo rural', 'Imigração internacional', 'Transumância', 'Sedentarização'], answer: 0, explanation: 'Êxodo rural é o deslocamento da população do campo para áreas urbanas.' }
  ];
  const mentorPlan = {
    title: 'Plano da semana', author: 'Marina Costa', published: offset(-2),
    message: 'Ana, nesta semana vamos consolidar porcentagem e praticar leitura atenta dos enunciados. Use os blocos de estudo que combinamos e registre suas dúvidas para nosso encontro.',
    priorities: ['Revisar porcentagem e aplicações em problemas.', 'Resolver questões de interpretação com atenção aos conectivos.', 'Registrar os erros e o que você percebeu em cada tentativa.'],
    activities: [
      { id: 'm1', title: 'Revisar porcentagem', subject: 'Matemática', minutes: 45, due: offset(1) },
      { id: 'm2', title: 'Praticar interpretação de texto', subject: 'Linguagens', minutes: 40, due: offset(2) }
    ]
  };
  const seed = () => ({
    tasks: [
      { id: 't1', title: 'Revisar funções do 1º grau', subject: 'Matemática', priority: 'alta', due: offset(1), minutes: 50, status: 'doing', sourceId: null, checklist: [{ id: 'c1', text: 'Rever anotações', done: true }, { id: 'c2', text: 'Resolver 5 exercícios', done: false }, { id: 'c3', text: 'Anotar dúvidas', done: false }] },
      { id: 't2', title: 'Ler capítulo de ecologia', subject: 'Biologia', priority: 'normal', due: offset(2), minutes: 35, status: 'todo', sourceId: null, checklist: [{ id: 'c4', text: 'Ler o capítulo', done: false }, { id: 'c5', text: 'Fazer resumo', done: false }] },
      { id: 't3', title: 'Escrever redação', subject: 'Redação', priority: 'alta', due: offset(3), minutes: 90, status: 'todo', sourceId: null, checklist: [] },
      { id: 't4', title: 'Revisar citologia', subject: 'Biologia', priority: 'normal', due: offset(-1), minutes: 40, status: 'done', sourceId: null, checklist: [{ id: 'c6', text: 'Rever resumo', done: true }] }
    ],
    events: [
      { id: 'e1', title: 'Estudar Matemática', type: 'Estudo', date: offset(0), time: '14:00', minutes: 50, status: 'planned', sourceId: null },
      { id: 'e2', title: 'Encontro com Marina', type: 'Encontro', date: offset(1), time: '16:00', minutes: 40, status: 'planned', sourceId: null },
      { id: 'e3', title: 'Praticar redação', type: 'Estudo', date: offset(2), time: '09:00', minutes: 90, status: 'planned', sourceId: null },
      { id: 'e4', title: 'Revisão de Biologia', type: 'Estudo', date: offset(-1), time: '15:00', minutes: 40, status: 'done', sourceId: null }
    ],
    attempts: [],
    history: [{ id: uid(), when: new Date().toISOString(), text: 'Dados demonstrativos carregados' }]
  });
  function load() { try { const data = JSON.parse(localStorage.getItem(KEY)); if (data && Array.isArray(data.tasks) && Array.isArray(data.events) && Array.isArray(data.attempts)) return data; } catch {} return seed(); }
  let state = load();
  let agendaView = 'semana';
  let selectedDate = offset(0);
  let questionIndex = 0;
  let selectedOption = null;
  let questionResult = null;
  let toastTimer;
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { toast('O navegador não permitiu salvar os dados.'); } render(); }
  function log(text) { state.history.unshift({ id: uid(), when: new Date().toISOString(), text }); state.history = state.history.slice(0, 40); }
  function toast(message) { const el = $('#toast'); el.textContent = message; el.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 3200); }
  function route() { const page = ['inicio', 'kanban', 'agenda', 'estudos', 'mentor'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'inicio'; $$('.page').forEach(el => el.hidden = el.id !== page); $$('[data-nav]').forEach(el => { el.classList.toggle('active', el.dataset.nav === page); if (el.dataset.nav === page) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current'); }); $('#page-name').textContent = ({ inicio: 'Início', kanban: 'Kanban e checklist', agenda: 'Agenda', estudos: 'Estudos', mentor: 'Mentor' })[page]; $('.sidebar').classList.remove('open'); $('#menu-toggle').setAttribute('aria-expanded', 'false'); window.scrollTo(0, 0); }
  function render() { renderHome(); renderBoard(); renderAgenda(); renderStudies(); renderMentor(); }
  function renderHome() {
    $('#today-date').textContent = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'long' }).format(new Date());
    const pending = state.tasks.filter(t => t.status !== 'done').length;
    const completed = state.tasks.filter(t => t.status === 'done').length;
    const todayEvents = state.events.filter(e => e.date === offset(0) && e.status === 'planned').length;
    const correct = state.attempts.filter(a => a.result === 'correct').length;
    $('#home-stats').innerHTML = [
      ['Tarefas pendentes', pending, 'no seu quadro', '▦'], ['Concluídas', completed, 'atividades realizadas', '✓'], ['Agenda de hoje', todayEvents, 'compromissos planejados', '▤'], ['Questões certas', correct, 'nesta demonstração', '◉']
    ].map(([label, value, detail, icon]) => `<div class="stat"><div class="stat-top"><span>${label}</span><span class="stat-icon">${icon}</span></div><strong>${value}</strong><small>${detail}</small></div>`).join('');
    const tasks = state.tasks.filter(t => t.status !== 'done').sort((a, b) => (a.due || '9999').localeCompare(b.due || '9999')).slice(0, 3);
    $('#home-tasks').innerHTML = tasks.length ? tasks.map(t => `<div class="task-line"><span class="task-check" aria-hidden="true"></span><div class="task-line-main"><strong>${safe(t.title)}</strong><small>${safe(t.subject || 'Estudo')} · ${t.due ? formatDate(t.due) : 'Sem prazo'}</small></div><span class="tag ${safe(t.priority)}">${t.priority === 'alta' ? 'Alta' : 'Normal'}</span></div>`).join('') : '<p class="empty">Nenhuma tarefa pendente.</p>';
    const events = state.events.filter(e => e.status === 'planned' && e.date >= offset(0)).sort((a, b) => `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`)).slice(0, 3);
    $('#home-agenda').innerHTML = events.length ? events.map(e => `<div class="event-line"><span class="event-time">${safe(e.time)}</span><div class="event-line-main"><strong>${safe(e.title)}</strong><small>${formatDate(e.date)} · ${safe(e.type)}</small></div></div>`).join('') : '<p class="empty">Nenhum compromisso próximo.</p>';
    $('#home-mentor').textContent = `${mentorPlan.author} publicou: “${mentorPlan.message}”`;
    $('#home-history').innerHTML = state.history.slice(0, 4).map(h => `<div class="timeline-item"><strong>${safe(h.text)}</strong><small>${new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(h.when))}</small></div>`).join('');
  }
  function renderBoard() {
    $('#kanban-summary').innerHTML = statuses.map(s => `<span class="summary-chip"><strong>${state.tasks.filter(t => t.status === s.key).length}</strong> ${s.name.toLowerCase()}</span>`).join('');
    $('#board').innerHTML = statuses.map(s => `<div class="column" data-status="${s.key}"><div class="column-head"><span>${s.name}</span><span>${state.tasks.filter(t => t.status === s.key).length}</span></div>${state.tasks.filter(t => t.status === s.key).map(taskCard).join('') || '<p class="empty">Nenhuma tarefa aqui.</p>'}</div>`).join('');
  }
  function taskCard(t) {
    const done = t.checklist.filter(c => c.done).length;
    const total = t.checklist.length;
    return `<article class="task-card" data-id="${safe(t.id)}"><div class="card-top"><span class="tag">${safe(t.subject || 'Estudo')}</span>${t.priority === 'alta' ? '<span class="priority-dot" title="Prioridade alta">● Alta</span>' : ''}</div><h3>${safe(t.title)}</h3><p>${t.sourceId ? 'Atividade da mentora · ' : ''}${t.due ? `Prazo ${formatDate(t.due)}` : 'Sem prazo'}</p><div class="task-meta"><span>◷ ${t.minutes ? `${t.minutes} min` : 'Sem estimativa'}</span><span>• ${statuses.find(s => s.key === t.status).name}</span></div>${total ? `<div class="checklist"><div class="checklist-head"><span>Checklist</span><span>${done}/${total}</span></div><div class="progress"><span style="width:${Math.round(done / total * 100)}%"></span></div>${t.checklist.map(c => `<label><input type="checkbox" data-check="${safe(c.id)}" ${c.done ? 'checked' : ''}><span>${safe(c.text)}</span></label>`).join('')}</div>` : ''}<div class="card-controls">${t.status !== 'todo' ? `<button type="button" data-task-action="back">← Voltar</button>` : ''}${t.status !== 'done' ? `<button type="button" data-task-action="next">${t.status === 'todo' ? 'Iniciar' : 'Concluir'} →</button>` : ''}<button type="button" data-task-action="edit">Editar</button><button type="button" data-task-action="delete">Excluir</button></div></article>`;
  }
  function weekStart(key) { const d = fromKey(key); d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); return d; }
  function renderAgenda() {
    $$('[data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === agendaView));
    const selected = fromKey(selectedDate);
    if (agendaView === 'dia') {
      $('#date-range').textContent = formatDate(selectedDate, { weekday: 'long', day: '2-digit', month: 'long' });
      const events = state.events.filter(e => e.date === selectedDate).sort((a, b) => a.time.localeCompare(b.time));
      $('#agenda-content').innerHTML = `<div class="day-list">${events.length ? events.map(agendaItem).join('') : '<div class="card empty">Nada planejado para este dia.</div>'}</div>`;
    } else {
      const start = weekStart(selectedDate); const end = new Date(start); end.setDate(end.getDate() + 6);
      $('#date-range').textContent = `${formatDate(dateKey(start))} – ${formatDate(dateKey(end))}`;
      $('#agenda-content').innerHTML = `<div class="calendar-week">${Array.from({ length: 7 }, (_, i) => { const d = new Date(start); d.setDate(d.getDate() + i); const key = dateKey(d); const events = state.events.filter(e => e.date === key).sort((a, b) => a.time.localeCompare(b.time)); return `<div class="day-column ${key === offset(0) ? 'today' : ''}"><div class="day-heading">${new Intl.DateTimeFormat('pt-BR', { weekday: 'short' }).format(d).replace('.', '')}<strong>${pad(d.getDate())}</strong></div>${events.map(e => `<div class="calendar-event ${safe(e.status)}"><span>${safe(e.time)} · ${safe(e.type)}</span><strong>${safe(e.title)}</strong><button type="button" data-event-edit="${safe(e.id)}">Editar</button></div>`).join('')}</div>`; }).join('')}</div>`;
    }
  }
  function agendaItem(e) { return `<div class="agenda-item"><span class="event-time">${safe(e.time)}</span><div class="event-line-main"><strong>${safe(e.title)}</strong><small>${safe(e.type)} · ${e.minutes} min${e.sourceId ? ' · plano da mentora' : ''}</small></div><span class="agenda-status ${safe(e.status)}">${e.status === 'done' ? 'Concluído' : e.status === 'missed' ? 'Não realizado' : 'Planejado'}</span><div class="event-actions"><button type="button" data-event-edit="${safe(e.id)}">Reagendar</button>${e.status !== 'done' ? `<button type="button" data-event-status="done" data-id="${safe(e.id)}">Concluir</button>` : ''}${e.status !== 'missed' ? `<button type="button" data-event-status="missed" data-id="${safe(e.id)}">Não realizado</button>` : ''}<button type="button" data-event-delete="${safe(e.id)}">Excluir</button></div></div>`; }
  function renderStudies() {
    const q = questions[questionIndex];
    $('#question-index').textContent = `Questão ${questionIndex + 1} de ${questions.length}`;
    const answered = Boolean(questionResult);
    $('#question-area').innerHTML = `<div class="question-context">${safe(q.subject)} · ${safe(q.topic)} · Contexto: ${safe(q.context)}</div><div class="question-text">${safe(q.text)}</div><div class="options">${q.options.map((option, i) => `<button class="option ${selectedOption === i ? 'selected' : ''} ${answered && i === q.answer ? 'correct' : ''} ${answered && i === selectedOption && i !== q.answer ? 'incorrect' : ''}" type="button" data-option="${i}" ${answered ? 'disabled' : ''}><span class="option-letter">${String.fromCharCode(65 + i)}.</span>${safe(option)}</button>`).join('')}</div><div class="question-actions">${answered ? `<button class="button button-dark" type="button" id="next-question">Próxima questão →</button>` : `<button class="button button-primary" type="button" id="answer-question" ${selectedOption === null ? 'disabled' : ''}>Responder</button><button class="button button-ghost" type="button" id="skip-question">Pular</button>`}</div>${answered ? `<div class="feedback"><strong>${questionResult === 'correct' ? 'Resposta correta!' : questionResult === 'skipped' ? 'Questão pulada.' : 'Resposta registrada.'}</strong><br>${safe(q.explanation)}</div>${questionResult === 'incorrect' ? `<div class="cause-box"><label for="error-cause">O que você acha que causou o erro?</label><select id="error-cause"><option value="">Selecione uma causa</option><option value="conteúdo">Conteúdo</option><option value="leitura">Leitura</option><option value="descuido">Descuido</option><option value="tempo">Tempo</option></select><button class="button button-primary button-small" id="save-cause" type="button" style="margin-top:10px">Salvar registro</button></div>` : ''}` : ''}`;
    const total = state.attempts.length; const correct = state.attempts.filter(a => a.result === 'correct').length;
    $('#study-stats').innerHTML = `<div class="mini-stat"><strong>${total}</strong><small>Tentativas</small></div><div class="mini-stat"><strong>${correct}</strong><small>Acertos</small></div><div class="mini-stat"><strong>${total ? Math.round(correct / total * 100) : 0}%</strong><small>Aproveitamento</small></div>`;
    $('#study-history').innerHTML = total ? state.attempts.map(a => { const question = questions.find(q => q.id === a.questionId); return `<div class="history-entry"><strong>${safe(question?.subject || 'Questão')} · ${safe(question?.topic || '')}</strong><small>${new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(a.when))} · ${safe(a.context)} · ${a.result === 'correct' ? 'Acerto' : a.result === 'skipped' ? 'Pulada' : 'Erro'}</small>${a.cause ? `<p>Causa percebida: ${safe(a.cause)}</p>` : ''}</div>`; }).join('') : '<p class="empty">Suas tentativas aparecerão aqui.</p>';
  }
  function renderMentor() {
    $('#mentor-content').innerHTML = `<div class="mentor-layout"><div><div class="card plan-card"><span class="eyebrow">PLANO PUBLICADO</span><h2>${safe(mentorPlan.title)}</h2><p class="plan-date">Publicado em ${formatDate(mentorPlan.published, { day: '2-digit', month: 'long', year: 'numeric' })}</p><p class="plan-body">${safe(mentorPlan.message)}</p><h3>Prioridades definidas pela mentora</h3><ul class="plan-list">${mentorPlan.priorities.map(p => `<li>${safe(p)}</li>`).join('')}</ul><p class="byline">Autoria: ${safe(mentorPlan.author)} · Exemplo demonstrativo</p></div></div><div class="card"><span class="eyebrow">ATIVIDADES PUBLICADAS</span><h2>Para incorporar ao seu plano</h2><p class="plan-date">Você escolhe onde organizar cada atividade.</p>${mentorPlan.activities.map(a => { const inBoard = state.tasks.some(t => t.sourceId === a.id); const inAgenda = state.events.some(e => e.sourceId === a.id); return `<div class="mentor-activity"><div><strong>${safe(a.title)}</strong><small>${safe(a.subject)} · ${a.minutes} min · até ${formatDate(a.due)}</small></div><div class="event-actions"><button type="button" data-mentor-task="${safe(a.id)}" ${inBoard ? 'disabled' : ''}>${inBoard ? 'No quadro ✓' : '+ Quadro'}</button><button type="button" data-mentor-event="${safe(a.id)}" ${inAgenda ? 'disabled' : ''}>${inAgenda ? 'Na agenda ✓' : '+ Agenda'}</button></div></div>`; }).join('')}</div></div>`;
  }
  function openTask(task = null) { const form = $('#task-form'); form.reset(); form.elements.id.value = task?.id || ''; form.elements.title.value = task?.title || ''; form.elements.subject.value = task?.subject || ''; form.elements.priority.value = task?.priority || 'normal'; form.elements.due.value = task?.due || ''; form.elements.minutes.value = task?.minutes || ''; form.elements.checklist.value = task?.checklist.map(c => c.text).join('\n') || ''; $('#task-dialog-title').textContent = task ? 'Editar tarefa' : 'Nova tarefa'; $('#task-dialog').showModal(); form.elements.title.focus(); }
  function openEvent(event = null) { const form = $('#event-form'); form.reset(); form.elements.id.value = event?.id || ''; form.elements.title.value = event?.title || ''; form.elements.type.value = event?.type || 'Estudo'; form.elements.date.value = event?.date || selectedDate; form.elements.time.value = event?.time || '14:00'; form.elements.minutes.value = event?.minutes || 60; $('#event-dialog-title').textContent = event ? 'Reagendar compromisso' : 'Novo compromisso'; $('#event-dialog').showModal(); form.elements.title.focus(); }
  $('#task-form').addEventListener('submit', event => { event.preventDefault(); const f = event.currentTarget.elements; const id = f.id.value; const existing = state.tasks.find(t => t.id === id); const lines = f.checklist.value.split('\n').map(v => v.trim()).filter(Boolean); const previous = existing?.checklist || []; const data = { id: id || uid(), title: f.title.value.trim(), subject: f.subject.value.trim(), priority: f.priority.value, due: f.due.value, minutes: Number(f.minutes.value) || null, status: existing?.status || 'todo', sourceId: existing?.sourceId || null, checklist: lines.map((line, i) => ({ id: previous[i]?.text === line ? previous[i].id : uid(), text: line, done: previous[i]?.text === line ? previous[i].done : false })) }; if (!data.title) return; if (existing) Object.assign(existing, data); else state.tasks.push(data); log(`${existing ? 'Tarefa atualizada' : 'Tarefa criada'}: ${data.title}`); $('#task-dialog').close(); save(); toast('Tarefa salva.'); });
  $('#event-form').addEventListener('submit', event => { event.preventDefault(); const f = event.currentTarget.elements; const id = f.id.value; const existing = state.events.find(e => e.id === id); const data = { id: id || uid(), title: f.title.value.trim(), type: f.type.value, date: f.date.value, time: f.time.value, minutes: Number(f.minutes.value), status: existing?.status || 'planned', sourceId: existing?.sourceId || null }; if (!data.title || !data.date || !data.time) return; if (existing) Object.assign(existing, data); else state.events.push(data); log(`${existing ? 'Compromisso reagendado' : 'Compromisso criado'}: ${data.title}`); $('#event-dialog').close(); selectedDate = data.date; save(); toast('Agenda atualizada.'); });
  document.addEventListener('click', event => {
    const target = event.target.closest('button'); if (!target) return;
    if (target.id === 'menu-toggle') { const open = $('.sidebar').classList.toggle('open'); target.setAttribute('aria-expanded', String(open)); }
    if (target.id === 'reset-demo' && confirm('Restaurar todos os dados demonstrativos? Suas alterações locais serão apagadas.')) { state = seed(); save(); toast('Demonstração reiniciada.'); }
    if (target.id === 'new-task') openTask(); if (target.id === 'new-event') openEvent();
    if (target.classList.contains('close-dialog')) target.closest('dialog').close();
    const action = target.dataset.taskAction;
    if (action) { const t = state.tasks.find(x => x.id === target.closest('.task-card').dataset.id); if (!t) return; if (action === 'edit') return openTask(t); if (action === 'delete') { if (!confirm(`Excluir “${t.title}”?`)) return; state.tasks = state.tasks.filter(x => x.id !== t.id); log(`Tarefa excluída: ${t.title}`); } else { const index = statuses.findIndex(s => s.key === t.status); t.status = statuses[index + (action === 'next' ? 1 : -1)].key; if (t.status === 'done') t.checklist.forEach(c => c.done = true); log(`Tarefa movida para ${statuses.find(s => s.key === t.status).name}: ${t.title}`); } save(); return; }
    if (target.dataset.eventEdit) return openEvent(state.events.find(e => e.id === target.dataset.eventEdit));
    if (target.dataset.eventStatus) { const e = state.events.find(x => x.id === target.dataset.id); e.status = target.dataset.eventStatus; log(`${e.status === 'done' ? 'Compromisso concluído' : 'Compromisso não realizado'}: ${e.title}`); save(); return; }
    if (target.dataset.eventDelete) { const e = state.events.find(x => x.id === target.dataset.eventDelete); if (!confirm(`Excluir “${e.title}”?`)) return; state.events = state.events.filter(x => x.id !== e.id); log(`Compromisso excluído: ${e.title}`); save(); return; }
    if (target.dataset.view) { agendaView = target.dataset.view; renderAgenda(); }
    if (target.id === 'date-prev' || target.id === 'date-next') { const d = fromKey(selectedDate); d.setDate(d.getDate() + (target.id === 'date-next' ? 1 : -1) * (agendaView === 'dia' ? 1 : 7)); selectedDate = dateKey(d); renderAgenda(); }
    if (target.id === 'date-today') { selectedDate = offset(0); renderAgenda(); }
    if (target.dataset.option !== undefined && !questionResult) { selectedOption = Number(target.dataset.option); renderStudies(); }
    if (target.id === 'answer-question' || target.id === 'skip-question') { const q = questions[questionIndex]; const result = target.id === 'skip-question' ? 'skipped' : selectedOption === q.answer ? 'correct' : 'incorrect'; state.attempts.unshift({ id: uid(), questionId: q.id, context: q.context, result, cause: '', when: new Date().toISOString() }); questionResult = result; log(`Questão de ${q.subject} ${result === 'correct' ? 'respondida corretamente' : result === 'skipped' ? 'pulada' : 'respondida'}`); save(); }
    if (target.id === 'save-cause') { const cause = $('#error-cause').value; if (!cause) return toast('Selecione uma causa percebida.'); state.attempts[0].cause = cause; save(); toast('Causa registrada.'); }
    if (target.id === 'next-question') { questionIndex = (questionIndex + 1) % questions.length; selectedOption = null; questionResult = null; renderStudies(); }
    if (target.dataset.mentorTask) { const a = mentorPlan.activities.find(x => x.id === target.dataset.mentorTask); if (state.tasks.some(t => t.sourceId === a.id)) return; state.tasks.push({ id: uid(), title: a.title, subject: a.subject, priority: 'normal', due: a.due, minutes: a.minutes, status: 'todo', sourceId: a.id, checklist: [] }); log(`Atividade da mentora adicionada ao quadro: ${a.title}`); save(); toast('Atividade adicionada ao quadro.'); }
    if (target.dataset.mentorEvent) { const a = mentorPlan.activities.find(x => x.id === target.dataset.mentorEvent); if (state.events.some(e => e.sourceId === a.id)) return; state.events.push({ id: uid(), title: a.title, type: 'Estudo', date: a.due, time: '14:00', minutes: a.minutes, status: 'planned', sourceId: a.id }); log(`Atividade da mentora adicionada à agenda: ${a.title}`); save(); toast('Atividade adicionada à agenda.'); }
  });
  document.addEventListener('change', event => { const id = event.target.dataset.check; if (!id) return; const t = state.tasks.find(x => x.checklist.some(c => c.id === id)); const item = t?.checklist.find(c => c.id === id); if (!item) return; item.done = event.target.checked; log(`${item.done ? 'Etapa concluída' : 'Etapa reaberta'}: ${item.text}`); save(); });
  window.addEventListener('hashchange', route);
  render(); route();
})();
