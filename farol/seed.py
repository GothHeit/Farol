"""Seed repetível por data, com identidades fictícias. Os textos do mentor são exemplos sintéticos marcados como tal."""
import json
import os
import secrets
from datetime import date, datetime, timedelta, timezone

from .db import now, week, dumps, password_hash, audit
from .rules import DEFAULT_CONFIG
from .service import Service

ACCOUNTS = [
    ('admin', 'admin@farol.local', 'Administradora demo', 'admin'),
    ('mentor_ana', 'ana@farol.local', 'Ana Souza', 'mentor'),
    ('mentor_bruno', 'bruno@farol.local', 'Bruno Costa', 'mentor'),
    ('user_beatriz', 'beatriz@farol.local', 'Beatriz A.', 'student'),
    ('user_rafael', 'rafael@farol.local', 'Rafael M.', 'student'),
    ('guardian_beatriz', 'responsavel@farol.local', 'Responsável autorizado · demo', 'student'),
]


# Situação de cada aluno no mês sintético: define o tom dos exemplos de texto do mentor.
SITUATIONS = {
    'beatriz': 'prio', 'isabela': 'prio', 'marina': 'prio',
    'lucas': 'att', 'mateus': 'att', 'rafael': 'att', 'pedro': 'att', 'daniel': 'att', 'thiago': 'att', 'helena': 'att',
    'sofia': 'ok', 'igor': 'ok', 'carla': 'ok', 'gabriel': 'ok', 'larissa': 'ok',
}
PUBLISHED_PLAN = {'beatriz', 'rafael', 'lucas', 'carla', 'marina'}
PUBLISHED_REPORT = {'beatriz', 'rafael'}
REVIEWED_REPORT = {'lucas', 'marina'}
TAG = ' (exemplo sintético)'


def example_texts(first, course, situation):
    """Textos de exemplo escritos como o mentor escreveria; nada aqui é produzido por regras do sistema."""
    if situation == 'prio':
        return {
            'note': f'{first} faltou aos últimos encontros e não acessa a plataforma há dias. Vou ligar para entender o que mudou antes de propor qualquer ajuste no plano.{TAG}',
            'note2': f'Conversei com {first}: a rotina da semana ficou apertada. Combinamos retomar com blocos curtos de estudo.{TAG}',
            'intervention': f'Liguei para {first}, ouvi o que está acontecendo e combinamos dois blocos curtos de estudo nesta semana, com revisão na sexta.{TAG}',
            'message': f'Oi, {first}! Senti sua falta nos últimos encontros. Quando puder, me conte como está sua semana e vemos juntos o que dá para ajustar.{TAG}',
            'plan_title': f'Retomada gradual · {course}{TAG}',
            'plan_body': f'Plano de retomada para {first}: poucas atividades, curtas, para recuperar o ritmo antes de aumentar a carga.',
            'activities': [('Bloco de estudo de 30 minutos', 'high'), ('Revisar o último simulado', 'normal'), ('Conversa de acompanhamento', 'normal')],
            'report_title': f'Relatório semanal · {first}{TAG}',
            'report_body': f'Semana de menor presença e menos acessos. Fiz contato direto com {first} e combinamos uma retomada gradual. Próximo passo: acompanhar a presença e a execução das atividades curtas.',
        }
    if situation == 'att':
        return {
            'note': f'O cumprimento do cronograma de {first} ficou abaixo do que costuma ser. Vale conversar sobre a distribuição das atividades ao longo da semana.{TAG}',
            'note2': f'{first} comentou que o conteúdo mais difícil ficou para o fim do dia. Posso sugerir trocar a ordem das sessões de estudo.{TAG}',
            'intervention': f'Conversei com {first} sobre o cronograma e sugeri começar o dia pelo conteúdo mais difícil, em sessões de 40 minutos.{TAG}',
            'message': f'Oi, {first}! Vi que o cronograma ficou mais apertado esta semana. Podemos conversar no próximo encontro sobre como organizar melhor as atividades?{TAG}',
            'plan_title': f'Organização da semana · {course}{TAG}',
            'plan_body': f'Plano de ajuste de rotina para {first}: priorizar o conteúdo mais difícil no início das sessões e manter uma revisão curta no fim da semana.',
            'activities': [('Sessão de estudo no conteúdo mais difícil', 'high'), ('Lista de exercícios da semana', 'normal'), ('Revisão curta de sexta', 'low')],
            'report_title': f'Relatório semanal · {first}{TAG}',
            'report_body': f'O cronograma de {first} teve menor cumprimento nesta semana. Combinamos ajustar a ordem das sessões de estudo. Vou acompanhar o efeito nas próximas duas semanas.',
        }
    return {
        'note': f'{first} segue com rotina estável de estudos para {course}. Nada a ajustar por enquanto; manter o ritmo e a conversa quinzenal.{TAG}',
        'note2': f'{first} contou que está confortável com a carga atual e quer reforçar a redação nas próximas semanas.{TAG}',
        'intervention': f'Reconheci o bom ritmo de {first} e combinamos reforçar a redação com uma produção por semana.{TAG}',
        'message': f'Oi, {first}! Sua semana foi consistente, parabéns. Se quiser, na próxima conversa planejamos o reforço de redação.{TAG}',
        'plan_title': f'Reforço de redação · {course}{TAG}',
        'plan_body': f'Plano de manutenção para {first}: uma redação por semana com devolutiva e uma revisão de repertório.',
        'activities': [('Escrever uma redação', 'normal'), ('Revisar repertório sociocultural', 'low')],
        'report_title': f'Relatório semanal · {first}{TAG}',
        'report_body': f'Semana estável, com presença e execução dentro do esperado. Seguimos com o plano de manutenção e o reforço de redação.',
    }


def seed_mentor_content(db, students, current_week):
    """Anotações, intervenções, mensagens, planos e relatórios de exemplo, gravados pelo mesmo serviço da API."""
    mentors = {m: Service(db, {'id': m, 'role': 'mentor'}) for m in ('mentor_ana', 'mentor_bruno')}
    next_week = current_week + timedelta(days=7)
    for slug, name, _age, course, user_id, _last, mentor_id in students:
        situation = SITUATIONS.get(slug)
        if not situation:
            continue  # Júlia R. permanece sem registros, para demonstrar o estado vazio
        sid, svc, first = 'student_' + slug, mentors[mentor_id], name.split()[0]
        texts = example_texts(first, course, situation)
        note = svc.add_authored(sid, 'notes', {'body': texts['note']})
        if situation != 'ok':
            svc.edit_note(note['id'], {'body': texts['note'] + ' ' + texts['note2'], 'revision': 1})
        else:
            svc.add_authored(sid, 'notes', {'body': texts['note2']})
        alert = db.execute('SELECT id FROM alerts WHERE student_id=? ORDER BY detected_at DESC LIMIT 1', (sid,)).fetchone()
        svc.add_authored(sid, 'interventions', {'body': texts['intervention'], **({'alert_id': alert['id']} if alert and situation != 'ok' else {})})
        message = svc.add_authored(sid, 'messages', {'body': texts['message']})
        if user_id:
            db.execute('UPDATE messages SET read_at=?,response_at=? WHERE id=?', (message['created_at'], message['created_at'], message['id']))
        plan = {'title': texts['plan_title'], 'body': texts['plan_body'], 'period': current_week.isoformat(),
                'activities': [{'title': t, 'priority': p, 'due_at': (next_week + timedelta(days=i)).isoformat()} for i, (t, p) in enumerate(texts['activities'])]}
        draft = svc.save_document(sid, 'plan', {**plan, 'status': 'draft'})
        if slug in PUBLISHED_PLAN:
            svc.save_document(sid, 'plan', {**plan, 'status': 'published', 'revision': draft['revision']}, draft['id'])
        report = {'title': texts['report_title'], 'body': texts['report_body'], 'period': current_week.isoformat()}
        draft = svc.save_document(sid, 'report', {**report, 'status': 'draft'})
        if slug in PUBLISHED_REPORT | REVIEWED_REPORT:
            reviewed = svc.save_document(sid, 'report', {**report, 'status': 'reviewed', 'revision': draft['revision']}, draft['id'])
            if slug in PUBLISHED_REPORT:
                svc.save_document(sid, 'report', {**report, 'status': 'published', 'revision': reviewed['revision']}, draft['id'])


def seed(db, password=None, base_date=None, examples=True):
    if db.execute('SELECT count(*) FROM users').fetchone()[0]:
        return {'created': False, 'accounts': [], 'password': None}
    password = password or os.environ.get('FAROL_DEMO_PASSWORD') or secrets.token_urlsafe(18)
    if len(password) < 12:
        raise ValueError('FAROL_DEMO_PASSWORD deve ter pelo menos 12 caracteres; use somente senha sintética.')
    timestamp = now()
    for account in ACCOUNTS:
        db.execute('INSERT INTO users VALUES (?,?,?,?,?,?)', (*account, password_hash(password), timestamp))
    current_week = date.fromisoformat(week(base_date))
    students = [
        ('beatriz', 'Beatriz A.', 16, 'Direito', 'user_beatriz', 8, 'mentor_ana'),
        ('lucas', 'Lucas S.', 17, 'Medicina', None, 1, 'mentor_ana'),
        ('pedro', 'Pedro H.', 17, 'Engenharia Civil', None, 1, 'mentor_ana'),
        ('rafael', 'Rafael M.', 29, 'Medicina', 'user_rafael', 1, 'mentor_ana'),
        ('daniel', 'Daniel F.', 18, 'Ciência da Computação', None, 1, 'mentor_ana'),
        ('sofia', 'Sofia N.', 17, 'Biologia', None, 0, 'mentor_ana'),
        ('igor', 'Igor C.', 19, 'Arquitetura', None, 0, 'mentor_ana'),
        ('novo', 'Júlia R.', 17, 'Curso ainda não informado', None, None, 'mentor_ana'),
        ('marina', 'Marina T.', 17, 'Letras', None, 8, 'mentor_bruno'),
        ('carla', 'Carla M.', 18, 'Psicologia', None, 0, 'mentor_ana'),
        ('thiago', 'Thiago P.', 17, 'Engenharia Elétrica', None, 2, 'mentor_ana'),
        ('helena', 'Helena V.', 16, 'Medicina Veterinária', None, 1, 'mentor_ana'),
        ('gabriel', 'Gabriel L.', 20, 'Direito', None, 1, 'mentor_bruno'),
        ('isabela', 'Isabela R.', 17, 'Odontologia', None, 8, 'mentor_bruno'),
        ('mateus', 'Mateus O.', 18, 'Administração', None, 1, 'mentor_bruno'),
        ('larissa', 'Larissa K.', 19, 'Jornalismo', None, 0, 'mentor_bruno'),
    ]
    for slug, name, student_age, course, user_id, last_days, mentor_id in students:
        sid = 'student_' + slug
        birth = date.today().replace(year=date.today().year - student_age, month=1, day=1).isoformat()
        last_access = (datetime.now(timezone.utc) - timedelta(days=last_days)).isoformat(timespec='seconds') if last_days is not None else None
        db.execute('INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (sid, user_id, name, birth, course, 'Folgas das 09h às 12h' if slug == 'rafael' else 'Segunda a sexta, 18h às 21h',
             'Escala alternada informada pelo aluno' if slug == 'rafael' else 'Sem restrições informadas',
             'Terça e quinta, 07h–19h (exemplo sintético)' if slug == 'rafael' else 'Não se aplica',
             last_access, timestamp if last_days is not None else None, timestamp))
        db.execute('INSERT INTO mentor_students VALUES (?,?,?)', (mentor_id, sid, timestamp))
        if slug == 'novo':
            continue
        for offset in range(5, -1, -1):
            period = (current_week - timedelta(weeks=offset)).isoformat()
            metrics = {'days_since_access': 1, 'consecutive_absences': 0, 'attendance_pct': 100,
                       'schedule_pct': 90, 'exam_score': 700, 'essay_score': 800,
                       'skipped_hard_study_pct': 20, 'hard_study_sessions': 2, 'question_seconds': 100,
                       'late_study_sessions': 1, 'unanswered_messages': 0, 'oldest_unanswered_days': 0,
                       'task_completion_pct': 80}
            if offset == 0:
                metrics['days_since_access'] = last_days
                if slug in ('beatriz', 'marina', 'isabela'):
                    metrics.update(consecutive_absences=2, attendance_pct=0, schedule_pct=45)
                elif slug in ('lucas', 'mateus'):
                    metrics.update(skipped_hard_study_pct=80, schedule_pct=45)
                elif slug == 'rafael':
                    metrics.update(schedule_pct=50, exam_score=500)
                elif slug in ('daniel', 'helena'):
                    metrics.update(schedule_pct=50)
            if slug in ('pedro', 'thiago') and offset in (0, 1):
                metrics.update(schedule_pct=50)
            sources = []
            for metric, value in metrics.items():
                source_id = f'signal_{slug}_{offset}_{metric}'
                db.execute('INSERT INTO signal_observations VALUES (?,?,?,?,?,?,?,?)',
                           (source_id, sid, period, 'academic', metric, dumps(value), 'seed sintético v4', period + 'T12:00:00+00:00'))
                sources.append(source_id)
            db.execute('INSERT INTO periods VALUES (?,?,?,?,?,?,?)',
                       (f'period_{slug}_{offset}', sid, period, dumps(metrics), dumps(sources), 'seed sintético v4', timestamp))
            for kind, score, maximum in [('exam', metrics['exam_score'], 1000), ('essay', metrics['essay_score'], 1000)]:
                db.execute('INSERT INTO academic_records VALUES (?,?,?,?,?,?,?,?,?)',
                    (f'{kind}_{slug}_{offset}', sid, period, kind, 'Simulado geral' if kind == 'exam' else 'Redação', score, maximum, 'seed sintético · escala ilustrativa, sem TRI', period + 'T15:00:00+00:00'))
            for meeting in range(2):
                db.execute('INSERT INTO attendance VALUES (?,?,?,?,?)',
                     (f'attend_{slug}_{offset}_{meeting}', sid, (date.fromisoformat(period) + timedelta(days=meeting * 2)).isoformat() + 'T21:00:00+00:00', 0 if offset == 0 and slug in ('beatriz', 'marina', 'isabela') else 1, 'seed sintético v4'))
        for index in range(5):
            due_at = (current_week + timedelta(days=index)).isoformat()
            db.execute('INSERT INTO tasks(id,student_id,plan_id,title,priority,status,due_at,author_id,updated_by,revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (f'task_{slug}_{index}', sid, None, f'Atividade sintética {index + 1} · registro de execução', 'normal',
                 'done' if index < 4 else 'todo', due_at, user_id or mentor_id, user_id or mentor_id, 1, timestamp, timestamp))
        agenda_date = (current_week + timedelta(days=3)).isoformat()
        db.execute('INSERT INTO agenda(id,student_id,title,starts_at,ends_at,author_id) VALUES (?,?,?,?,?,?)',
                   ('agenda_' + slug, sid, 'Encontro de mentoria · exemplo sintético', agenda_date + 'T18:00:00-03:00', agenda_date + 'T18:30:00-03:00', mentor_id))
        for context in ('study', 'exam'):
            for session in range(2):
                questions = [{'theme': 'Funções' if slug in ('pedro', 'thiago', 'gabriel') else 'Estequiometria', 'difficulty': 'hard',
                              'seconds': 100, 'skipped': i < (8 if slug in ('lucas', 'mateus') and context == 'study' else 2 if context == 'study' else 9),
                              'correct': False if i % 2 else None, 'error_cause': ('conteudo','leitura','descuido','tempo')[i % 4] if i % 2 else None}
                             for i in range(10)]
                db.execute('INSERT INTO study_sessions VALUES (?,?,?,?,?,?,?,?,?,?)',
                    (f'study_{slug}_{context}_{session}', sid, current_week.isoformat(), context, 'Matemática' if slug in ('pedro', 'thiago', 'gabriel') else 'Química',
                     current_week.isoformat() + f'T{18 if session == 0 else 23}:00:00-03:00', 45, dumps(questions), user_id or mentor_id, 'seed sintético · dificuldade ilustrativa, sem fonte TRI'))
    db.execute('INSERT INTO report_grants VALUES (?,?,?,?,?)',
               ('student_beatriz', 'guardian_beatriz', 'user_beatriz', timestamp, None))
    audit(db, 'user_beatriz', 'report.consent', 'report_grant', 'student_beatriz:guardian_beatriz',
          'Autorização exclusivamente sintética para demonstrar acesso controlado.', after={'grantee_id': 'guardian_beatriz'})
    db.execute('INSERT INTO rule_versions VALUES (?,?,?,?,?,?,?,?,?)',
                ('rules_v1', 'Parâmetros iniciais · demonstração v4', dumps(DEFAULT_CONFIG), 'active', 'admin', timestamp, timestamp, None,
                 'Valores provisórios sintéticos; mensagens fortes desabilitadas até aprovação explícita.'))
    service = Service(db)
    version = service.active_rules()
    for offset in range(5, -1, -1):
        period = (current_week - timedelta(weeks=offset)).isoformat()
        for student in students:
            service.evaluate_student('student_' + student[0], version, period,
                                     timestamp if offset == 0 else period + 'T18:00:00+00:00')
    if examples:
        seed_mentor_content(db, students, current_week)
    audit(db, 'admin', 'seed.create', 'dataset', 'synthetic_v4', 'Demonstração local, sem dados de pessoas reais.', after={'students': len(students), 'weeks': 6})
    return {'created': True, 'accounts': [{'id': a[0], 'email': a[1], 'role': a[3]} for a in ACCOUNTS], 'password': password}
