"""Casos de uso, RBAC e persistência transacional da demonstração Farol."""
import json
import math
import re
import secrets
from datetime import datetime, date, timedelta, timezone

from .db import now, week, uid, dumps, digest, audit, age, password_hash, password_matches, LOCAL_TZ
from .rules import DEFAULT_CONFIG, evaluate, validate_config


class APIError(Exception):
    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status, self.message, self.details = status, message, details


def require(condition, message, status=400):
    if not condition:
        raise APIError(status, message)


def text(data, key, limit=10000, optional=False):
    value = data.get(key, '')
    require(isinstance(value, str), f'{key}: texto obrigatório.')
    value = value.strip()
    require((optional or bool(value)) and len(value) <= limit and '\x00' not in value,
            f'{key}: informe até {limit} caracteres' + ('.' if optional else ', sem deixar em branco.'))
    return value


def iso_date(value, field='period'):
    try:
        require(isinstance(value, str) and len(value) == 10, f'{field}: use AAAA-MM-DD.')
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise APIError(400, f'{field}: data inválida.')


def iso_time(value, field='timestamp'):
    try:
        require(isinstance(value, str), f'{field}: data/hora obrigatória.')
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(dt.tzinfo is not None, f'{field}: inclua fuso horário explícito.')
        return dt.astimezone(timezone.utc).isoformat(timespec='seconds')
    except ValueError:
        raise APIError(400, f'{field}: data/hora inválida.')


def boolean(data, key, nullable=False):
    value = data.get(key)
    require(type(value) is bool or (nullable and value is None), f'{key}: booleano obrigatório.')
    return value


def rowdict(row):
    return dict(row) if row else None


def public_user(row):
    return {key: row[key] for key in ('id', 'name', 'email', 'role')}


class Service:
    def __init__(self, db, user=None):
        self.db, self.user = db, user

    def role(self, *roles):
        require(self.user is not None, 'Autenticação necessária.', 401)
        require(self.user['role'] in roles, 'Você não tem autorização para esta operação.', 403)

    def student(self, student_id, write=False):
        self.role('mentor', 'student')
        student = rowdict(self.db.execute('SELECT * FROM students WHERE id=?', (student_id,)).fetchone())
        require(student is not None, 'Aluno indisponível para esta conta.', 403)
        if self.user['role'] == 'mentor':
            linked = self.db.execute('SELECT 1 FROM mentor_students WHERE mentor_id=? AND student_id=?',
                                     (self.user['id'], student_id)).fetchone()
            require(linked is not None, 'Aluno indisponível para esta conta.', 403)
        else:
            require(student['user_id'] == self.user['id'], 'Aluno indisponível para esta conta.', 403)
        student['age'] = age(student['birth_date'])
        student.pop('birth_date', None)
        return student

    def mentor_student(self, student_id):
        self.role('mentor')
        return self.student(student_id)

    def own_student(self):
        self.role('student')
        result = self.db.execute('SELECT id FROM students WHERE user_id=?', (self.user['id'],)).fetchone()
        require(result is not None, 'Esta conta tem acesso somente a relatórios autorizados.', 403)
        return self.student(result['id'])

    def login(self, data, remote):
        email = text(data, 'email', 254).lower()
        password = text(data, 'password', 1024)
        bucket = digest(remote + ':' + email)
        attempt = self.db.execute('SELECT * FROM login_attempts WHERE bucket=?', (bucket,)).fetchone()
        require(not attempt or attempt['reset_at'] < now() or attempt['attempts'] < 10,
                'Muitas tentativas. Aguarde 15 minutos.', 429)
        user = self.db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        valid = password_matches(password, user['password_hash'] if user else password_hash('invalid-password'))
        if not user or not valid:
            reset = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(timespec='seconds')
            count = attempt['attempts'] + 1 if attempt and attempt['reset_at'] >= now() else 1
            self.db.execute('INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)', (bucket, count, reset))
            raise APIError(401, 'E-mail ou senha inválidos.')
        self.db.execute('DELETE FROM login_attempts WHERE bucket=?', (bucket,))
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        expiry = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(timespec='seconds')
        self.db.execute('DELETE FROM sessions WHERE expires_at<?', (now(),))
        self.db.execute('INSERT INTO sessions VALUES (?,?,?,?,?)', (digest(token), user['id'], csrf, now(), expiry))
        if user['role'] == 'student':
            self.db.execute('UPDATE students SET last_access_at=? WHERE user_id=?', (now(), user['id']))
        audit(self.db, user['id'], 'login', 'session', 'redacted')
        return {'user': public_user(user), 'csrf_token': csrf, 'synthetic': True}, token

    def current_input(self, student_id, period=None):
        period = period or week()
        rows = self.db.execute('SELECT * FROM periods WHERE student_id=? AND period<=? ORDER BY period',
                               (student_id, period)).fetchall()
        history = [{'period': r['period'], 'metrics': json.loads(r['metrics']),
                    'source_ids': json.loads(r['source_ids']), 'source': r['source'], 'updated_at': r['updated_at']}
                   for r in rows]
        current = next((h for h in history if h['period'] == period),
                       {'period': period, 'metrics': {}, 'source_ids': [], 'source': 'sem dados', 'updated_at': None})
        history = [h for h in history if h['period'] < period]
        if period == week():
            student = self.db.execute('SELECT last_access_at FROM students WHERE id=?', (student_id,)).fetchone()
            if student['last_access_at']:
                current['metrics']['days_since_access'] = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(student['last_access_at'])).days)
                current['source_ids'] = sorted(set(current['source_ids'] + [f'access:{student_id}:{student["last_access_at"]}']))
            messages = self.db.execute('SELECT id,created_at FROM messages WHERE student_id=? AND response_at IS NULL', (student_id,)).fetchall()
            if messages:
                current['metrics']['unanswered_messages'] = len(messages)
                current['metrics']['oldest_unanswered_days'] = max((datetime.now(timezone.utc) - datetime.fromisoformat(m['created_at'])).days for m in messages)
                current['source_ids'] += [m['id'] for m in messages]
        return current, history

    def active_rules(self):
        row = self.db.execute("SELECT * FROM rule_versions WHERE status='active'").fetchone()
        require(row is not None, 'Nenhuma configuração ativa.', 503)
        return rowdict(row)

    def evaluate_student(self, student_id, version=None, period=None, detected_at=None):
        version = version or self.active_rules()
        current, history = self.current_input(student_id, period)
        config = json.loads(version['config'])
        result = evaluate(current, history, config)
        payload = {'current': current, 'history': history}
        fingerprint = digest(dumps(payload))
        existing = self.db.execute('SELECT * FROM evaluations WHERE student_id=? AND period=? AND version_id=? AND input_hash=?',
                                    (student_id, current['period'], version['id'], fingerprint)).fetchone()
        if existing:
            return self.evaluation_dict(existing)
        evaluation_id, timestamp = uid('eval'), detected_at or now()
        self.db.execute('INSERT INTO evaluations VALUES (?,?,?,?,?,?,?,?,?)',
                        (evaluation_id, student_id, current['period'], version['id'], version['config'], fingerprint,
                         dumps(payload), dumps(result), timestamp))
        if result['level'] in ('prio', 'att', 'obs'):
            alert_id = uid('alert')
            cursor = self.db.execute('INSERT OR IGNORE INTO alerts VALUES (?,?,?,?,?,?,?,?,?)',
                (alert_id, student_id, current['period'], result['level'], evaluation_id, version['id'],
                 dumps(result['evidence']), version['config'], timestamp))
            if cursor.rowcount and result['level'] == 'prio':
                for mentor in self.db.execute('SELECT mentor_id FROM mentor_students WHERE student_id=?', (student_id,)):
                    self.db.execute('INSERT INTO notifications VALUES (?,?,?,?,?,?,?,?,?)',
                         (uid('notice'), mentor['mentor_id'], student_id, alert_id,
                          'Aluno precisa de atenção · Prioridade', 'in_app', 'available', timestamp, None))
        return {**result, 'id': evaluation_id, 'version_id': version['id'], 'config_snapshot': config,
                'evaluated_at': timestamp, 'source': current['source'], 'updated_at': current['updated_at']}

    @staticmethod
    def evaluation_dict(row):
        inputs = json.loads(row['inputs'])
        return {**json.loads(row['result']), 'id': row['id'], 'version_id': row['version_id'],
                'config_snapshot': json.loads(row['config_snapshot']), 'evaluated_at': row['evaluated_at'],
                'source': inputs['current']['source'], 'updated_at': inputs['current']['updated_at']}

    def latest_evaluation(self, student_id):
        row = self.db.execute('SELECT * FROM evaluations WHERE student_id=? AND period=? ORDER BY rowid DESC LIMIT 1',
                              (student_id, week())).fetchone()
        return self.evaluation_dict(row) if row else {'level': 'unknown', 'evidence': [], 'missing': ['Sem avaliação para o período atual.']}

    def process(self, reason='automatic_schedule'):
        if self.user:
            self.role('mentor', 'admin')
        version = self.active_rules()
        if self.user and self.user['role'] == 'mentor':
            ids = [r[0] for r in self.db.execute('SELECT student_id FROM mentor_students WHERE mentor_id=?', (self.user['id'],))]
        else:
            ids = [r[0] for r in self.db.execute('SELECT id FROM students')]
        count = 0
        before = self.db.total_changes
        for student_id in ids:
            self.evaluate_student(student_id, version)
            count += 1
        if self.db.total_changes > before or self.user:
            audit(self.db, self.user['id'] if self.user else None, 'evaluation.run', 'rule_version', version['id'], reason, after={'students': count})
        return {'processed': count, 'version_id': version['id'], 'evaluated_at': now()}

    def alerts(self, student_id, include_inputs=False):
        output = []
        for row in self.db.execute('SELECT * FROM alerts WHERE student_id=? ORDER BY detected_at DESC,rowid DESC', (student_id,)):
            alert = dict(row)
            alert['evidence'] = json.loads(alert['evidence'])
            alert['config_snapshot'] = json.loads(alert['config_snapshot'])
            if include_inputs:
                evaluation = self.db.execute('SELECT inputs FROM evaluations WHERE id=?', (alert['evaluation_id'],)).fetchone()
                alert['raw_inputs'] = json.loads(evaluation['inputs'])
            decisions = [dict(r) for r in self.db.execute('SELECT t.*,u.name author_name FROM triage t JOIN users u ON u.id=t.author_id WHERE alert_id=? ORDER BY t.rowid DESC', (alert['id'],))]
            for decision in decisions:
                decision['useful'] = bool(decision['useful']) if decision['useful'] is not None else None
                decision['following'], decision['acted'] = bool(decision['following']), bool(decision['acted'])
            alert['triage'] = decisions[0] if decisions else None
            alert['triage_history'] = decisions
            output.append(alert)
        return output

    def authored(self, table, student_id):
        require(table in ('notes', 'interventions', 'messages'), 'Tabela inválida.')
        sql = f'SELECT x.*,u.name author_name FROM {table} x JOIN users u ON u.id=x.author_id WHERE student_id=?'
        params = [student_id]
        if table == 'notes':
            sql += ' AND x.author_id=?'
            params.append(self.user['id'])
        rows = [dict(r) for r in self.db.execute(sql + ' ORDER BY x.rowid DESC', params)]
        for row in rows:
            row['source'] = 'mentor'
            if table == 'notes':
                row['visibility'] = 'private'
                row['history'] = [dict(r) for r in self.db.execute('SELECT revision,body,created_at FROM note_revisions WHERE note_id=? ORDER BY revision DESC', (row['id'],))]
            if table == 'messages':
                row.update(status='available_in_app', external_status='not_sent')
            if table == 'interventions':
                row['baseline'] = json.loads(row['baseline'])
        return rows

    def document_dict(self, row, published=False):
        document = dict(row)
        if published:
            require(document['published_revision'] is not None, 'Conteúdo ainda não publicado.', 403)
            revision = self.db.execute('SELECT snapshot FROM document_revisions WHERE document_id=? AND revision=?',
                                       (document['id'], document['published_revision'])).fetchone()
            document = json.loads(revision['snapshot'])
        if isinstance(document['activities'], str):
            document['activities'] = json.loads(document['activities'])
        author = self.db.execute('SELECT name FROM users WHERE id=?', (document['author_id'],)).fetchone()
        document['author_name'] = author[0]
        document['source'] = 'mentor'
        document['external_status'] = 'not_sent'
        student = self.db.execute('SELECT birth_date FROM students WHERE id=?', (document['student_id'],)).fetchone()
        granted = self.db.execute('SELECT count(*) FROM report_grants WHERE student_id=? AND revoked_at IS NULL', (document['student_id'],)).fetchone()[0]
        document['audience'] = 'student_and_authorized_guardians' if document['kind'] == 'report' and age(student[0]) < 18 and granted else 'student'
        if not published:
            document['history'] = [{'revision': r['revision'], 'actor_id': r['actor_id'], 'created_at': r['created_at'],
                                    'status': json.loads(r['snapshot'])['status'], 'body': json.loads(r['snapshot'])['body'],
                                    'title': json.loads(r['snapshot'])['title']}
                                   for r in self.db.execute('SELECT * FROM document_revisions WHERE document_id=? ORDER BY revision DESC', (document['id'],))]
        return document

    def documents(self, student_id, kind, published=False):
        return [self.document_dict(row, published) for row in self.db.execute(
            'SELECT * FROM documents WHERE student_id=? AND kind=?' + (' AND published_revision IS NOT NULL' if published else '') + ' ORDER BY rowid DESC', (student_id, kind))]

    def tasks(self, student_id):
        rows = [dict(r) for r in self.db.execute('SELECT t.*,u.name author_name,x.name updated_by_name FROM tasks t JOIN users u ON u.id=t.author_id JOIN users x ON x.id=t.updated_by WHERE student_id=? AND archived_at IS NULL ORDER BY due_at,title', (student_id,))]
        for row in rows:
            row['overdue'] = row['status'] != 'done' and row['due_at'] < datetime.now(LOCAL_TZ).date().isoformat()
            row['history'] = [dict(r) for r in self.db.execute('SELECT actor_id,before_json,after_json,occurred_at FROM task_events WHERE task_id=? ORDER BY rowid', (row['id'],))]
        return rows

    def detail(self, student_id):
        student = self.mentor_student(student_id)
        current, history = self.current_input(student_id)
        study = [dict(r) for r in self.db.execute('SELECT * FROM study_sessions WHERE student_id=? ORDER BY started_at DESC', (student_id,))]
        for item in study:
            item['questions'] = json.loads(item['questions'])
        metric_metadata = {}
        for record in self.db.execute("SELECT metric,source,observed_at,id FROM signal_observations WHERE student_id=? AND period=? AND namespace='academic' ORDER BY rowid DESC", (student_id, week())):
            metric_metadata.setdefault(record['metric'], {'source': record['source'], 'updated_at': record['observed_at'], 'source_id': record['id']})
        if student['last_access_at']:
            metric_metadata['days_since_access'] = {'source': 'registro de acesso à plataforma', 'updated_at': student['last_access_at'], 'source_id': 'access:' + student_id}
        return {'student': student, 'period': week(), 'metrics': current['metrics'], 'metric_metadata': metric_metadata, 'history': history + [current],
                'evaluation': self.latest_evaluation(student_id), 'alerts': self.alerts(student_id, include_inputs=True),
                'notes': self.authored('notes', student_id), 'plans': self.documents(student_id, 'plan'),
                'reports': self.documents(student_id, 'report'), 'interventions': self.authored('interventions', student_id),
                'messages': self.authored('messages', student_id), 'tasks': self.tasks(student_id),
                'agenda': [dict(r) for r in self.db.execute('SELECT * FROM agenda WHERE student_id=? ORDER BY starts_at', (student_id,))],
                'academic': [dict(r) for r in self.db.execute('SELECT * FROM academic_records WHERE student_id=? ORDER BY period DESC', (student_id,))],
                'attendance': [dict(r) for r in self.db.execute('SELECT * FROM attendance WHERE student_id=? ORDER BY occurred_at DESC', (student_id,))],
                'study': study, 'reference_data': {'tri': 'unavailable', 'sisu': 'unavailable'},
                'observations': [dict(r) for r in self.db.execute("SELECT * FROM signal_observations WHERE student_id=? AND namespace='academic' ORDER BY period DESC,metric", (student_id,))],
                'source': current['source'], 'sync_status': 'synced' if student['last_sync'] else 'no_data',
                'evolution': self.evolution([student_id])}

    def evolution(self, student_ids):
        output = []
        metrics = {'schedule_pct': '%', 'task_completion_pct': '%', 'exam_score': 'pontos', 'attendance_pct': '%'}
        for student_id in student_ids:
            student_name = self.db.execute('SELECT name FROM students WHERE id=?', (student_id,)).fetchone()[0]
            for intervention in self.db.execute('SELECT * FROM interventions WHERE student_id=? ORDER BY created_at DESC', (student_id,)):
                next_week = (date.fromisoformat(intervention['period']) + timedelta(days=7)).isoformat()
                after = self.db.execute('SELECT metrics FROM periods WHERE student_id=? AND period=?', (student_id, next_week)).fetchone()
                if not after:
                    continue
                baseline, later = json.loads(intervention['baseline']), json.loads(after[0])
                for metric, unit in metrics.items():
                    if metric in baseline and metric in later and baseline[metric] is not None and later[metric] is not None:
                        output.append({'student_id': student_id, 'student_name': student_name, 'intervention_id': intervention['id'],
                                       'metric': metric, 'before': baseline[metric], 'after': later[metric], 'unit': unit,
                                       'before_period': intervention['period'], 'after_period': next_week,
                                       'intervention_at': intervention['created_at']})
        return output

    def quality(self, student_ids):
        useful = not_useful = false_alarms = missed = 0
        lead, labelled = [], []
        for student_id in student_ids:
            for alert in self.alerts(student_id):
                decision = alert['triage']
                if decision and decision['useful'] is not None:
                    useful += int(decision['useful'])
                    not_useful += int(not decision['useful'])
            labelled += [dict(r) for r in self.db.execute('SELECT * FROM labelled_events WHERE student_id=?', (student_id,))]
        for event in labelled:
            start = (date.fromisoformat(event['period']) - timedelta(days=28)).isoformat()
            first = self.db.execute("SELECT min(detected_at) FROM alerts WHERE student_id=? AND period>=? AND period<=? AND detected_at<=? AND level IN ('att','prio')",
                                    (event['student_id'], start, event['period'], event['occurred_at'])).fetchone()[0]
            if event['disengaged']:
                if first:
                    lead.append((datetime.fromisoformat(event['occurred_at']) - datetime.fromisoformat(first)).total_seconds() / 86400)
                else:
                    missed += 1
            elif first:
                false_alarms += 1
        return {'useful': useful, 'not_useful': not_useful, 'labelled_count': len(labelled),
                'false_alarms': false_alarms if labelled else None, 'missed_events': missed if labelled else None,
                'lead_days': round(sum(lead) / len(lead), 1) if lead else None,
                'definition': 'Eventos rotulados: falso alarme = janela sem afastamento com Atenção/Prioridade; não detectado = afastamento sem alerta anterior na janela de 28 dias; antecedência = dias entre primeiro alerta nessa janela e evento. Utilidade é avaliação humana distinta desses rótulos. Definições provisórias para demonstração.'}

    def dashboard(self):
        self.role('mentor')
        student_ids = [r[0] for r in self.db.execute('SELECT student_id FROM mentor_students WHERE mentor_id=?', (self.user['id'],))]
        students, queue, observe = [], [], []
        summary = dict(prio=0, att=0, obs=0, ok=0, unknown=0, new_alerts=0, followed=0, interventions=0)
        for student_id in student_ids:
            student = self.student(student_id)
            current, _ = self.current_input(student_id)
            evaluation = self.latest_evaluation(student_id)
            alerts = self.alerts(student_id)
            summary[evaluation['level']] += 1
            current_alerts = [a for a in alerts if a['period'] == week()]
            summary['new_alerts'] += len([a for a in current_alerts if a['triage'] is None])
            summary['followed'] += int(any(a['triage'] and a['triage']['following'] for a in current_alerts))
            summary['interventions'] += self.db.execute('SELECT count(*) FROM interventions WHERE student_id=? AND period=?', (student_id, week())).fetchone()[0]
            item = {**student, 'level': evaluation['level'], 'evaluation': evaluation, 'metrics': current['metrics'],
                    'alert_count': len(current_alerts), 'source': current['source'], 'sync_status': 'synced' if student['last_sync'] else 'no_data'}
            students.append(item)
            if item['level'] in ('att', 'prio'):
                alert = next((a for a in current_alerts if a['level'] == item['level']), None)
                if alert:
                    queue.append({**alert, 'student_name': item['name']})
            elif item['level'] == 'obs':
                observe.append(item)
        queue.sort(key=lambda a: (0 if a['level'] == 'prio' else 1, a['student_name']))
        return {'period': week(), 'updated_at': now(), 'students': students, 'summary': summary, 'queue': queue,
                'observe': observe, 'notifications': self.notifications(), 'quality': self.quality(student_ids),
                'evolution': self.evolution(student_ids), 'synthetic': True}

    def notifications(self):
        self.role('mentor', 'student', 'admin')
        return [dict(r) for r in self.db.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC,rowid DESC LIMIT 100', (self.user['id'],))]

    def triage_alert(self, alert_id, data):
        self.role('mentor')
        alert = self.db.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone()
        require(alert is not None, 'Alerta indisponível.', 403)
        self.mentor_student(alert['student_id'])
        interpretation = text(data, 'interpretation', optional=True)
        useful, following, acted = boolean(data, 'useful', True), boolean(data, 'following'), boolean(data, 'acted')
        triage_id = uid('triage')
        self.db.execute('INSERT INTO triage VALUES (?,?,?,?,?,?,?,?)',
                        (triage_id, alert_id, self.user['id'], interpretation, useful, following, acted, now()))
        audit(self.db, self.user['id'], 'alert.triage', 'alert', alert_id,
              after={'useful': useful, 'following': following, 'acted': acted, 'interpretation_length': len(interpretation)})
        return next(a for a in self.alerts(alert['student_id']) if a['id'] == alert_id)

    def add_authored(self, student_id, kind, data):
        self.mentor_student(student_id)
        body, entity_id, timestamp = text(data, 'body'), uid(kind), now()
        if kind == 'notes':
            self.db.execute('INSERT INTO notes VALUES (?,?,?,?,?,?,?)', (entity_id, student_id, self.user['id'], body, 1, timestamp, timestamp))
            self.db.execute('INSERT INTO note_revisions VALUES (?,?,?,?,?,?)', (uid('rev'), entity_id, self.user['id'], body, 1, timestamp))
        elif kind == 'interventions':
            alert_id = data.get('alert_id') or None
            if alert_id:
                require(isinstance(alert_id, str) and len(alert_id) <= 100, 'alert_id: identificador inválido.')
                require(self.db.execute('SELECT 1 FROM alerts WHERE id=? AND student_id=?', (alert_id, student_id)).fetchone(), 'Alerta não pertence ao aluno.', 403)
            current, _ = self.current_input(student_id)
            self.db.execute('INSERT INTO interventions VALUES (?,?,?,?,?,?,?,?)', (entity_id, student_id, alert_id, self.user['id'], body, dumps(current['metrics']), week(), timestamp))
        elif kind == 'messages':
            self.db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?)', (entity_id, student_id, self.user['id'], body, timestamp, None, None))
            self.notify_student(student_id, 'Mensagem do mentor disponível', timestamp)
        else:
            raise APIError(404, 'Operação inexistente.')
        audit(self.db, self.user['id'], kind + '.create', kind, entity_id, after={'student_id': student_id, 'body_length': len(body)})
        return next(x for x in self.authored(kind, student_id) if x['id'] == entity_id)

    def edit_note(self, note_id, data):
        self.role('mentor')
        note = self.db.execute('SELECT * FROM notes WHERE id=? AND author_id=?', (note_id, self.user['id'])).fetchone()
        require(note is not None, 'Anotação indisponível.', 403)
        self.mentor_student(note['student_id'])
        require(type(data.get('revision')) is int and data['revision'] == note['revision'], 'Anotação mudou; recarregue antes de salvar.', 409)
        body, revision, timestamp = text(data, 'body'), note['revision'] + 1, now()
        self.db.execute('UPDATE notes SET body=?,revision=?,updated_at=? WHERE id=?', (body, revision, timestamp, note_id))
        self.db.execute('INSERT INTO note_revisions VALUES (?,?,?,?,?,?)', (uid('rev'), note_id, self.user['id'], body, revision, timestamp))
        audit(self.db, self.user['id'], 'notes.update', 'notes', note_id, before={'revision': note['revision']}, after={'revision': revision, 'body_length': len(body)})
        return next(n for n in self.authored('notes', note['student_id']) if n['id'] == note_id)

    def notify_student(self, student_id, title, timestamp):
        user = self.db.execute('SELECT user_id FROM students WHERE id=?', (student_id,)).fetchone()[0]
        if user:
            self.db.execute('INSERT INTO notifications VALUES (?,?,?,?,?,?,?,?,?)',
                            (uid('notice'), user, student_id, None, title, 'in_app', 'available', timestamp, None))

    def save_document(self, student_id, kind, data, document_id=None):
        self.mentor_student(student_id)
        previous = self.db.execute('SELECT * FROM documents WHERE id=? AND student_id=? AND kind=?', (document_id, student_id, kind)).fetchone() if document_id else None
        if document_id:
            require(previous is not None, 'Documento indisponível.', 403)
            require(type(data.get('revision')) is int and data['revision'] == previous['revision'], 'Documento mudou; recarregue antes de salvar.', 409)
        title_value, body = text(data, 'title', 180), text(data, 'body')
        period = iso_date(data.get('period', week()))
        require(period == week(period), 'O período deve começar na segunda-feira.')
        status = data.get('status', 'draft')
        require(status in ('draft', 'published') if kind == 'plan' else status in ('draft', 'reviewed', 'published'), 'Estado inválido.')
        reviewer_id = reviewed_at = None
        if kind == 'report' and status == 'published':
            require(previous is not None and previous['status'] == 'reviewed', 'Revise explicitamente o relatório antes de publicar.', 409)
            require(body == previous['body'] and title_value == previous['title'] and period == previous['period'], 'O conteúdo mudou após revisão. Salve e revise novamente.', 409)
            reviewer_id, reviewed_at = previous['reviewer_id'], previous['reviewed_at']
        elif kind == 'report' and status == 'reviewed':
            require(previous is not None, 'Salve um rascunho antes da revisão.', 409)
            reviewer_id, reviewed_at = self.user['id'], now()
        activities = data.get('activities', []) if kind == 'plan' else []
        require(isinstance(activities, list) and len(activities) <= 50, 'Informe até 50 atividades.')
        clean_activities = []
        old_activities = json.loads(previous['activities']) if previous else []
        for activity in activities:
            require(isinstance(activity, dict), 'Atividade inválida.')
            priority = activity.get('priority', 'normal')
            require(priority in ('high', 'normal', 'low'), 'Prioridade de atividade inválida.')
            activity_title = text(activity, 'title', 180)
            activity_due = iso_date(activity.get('due_at', period), 'due_at')
            used_ids = {a['id'] for a in clean_activities}
            matching = next((a for a in old_activities if a['id'] not in used_ids and
                             (a['title'], a['priority'], a['due_at']) == (activity_title, priority, activity_due)), None)
            activity_id = activity.get('id') or (matching['id'] if matching else uid('activity'))
            require(isinstance(activity_id, str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', activity_id), 'ID de atividade inválido.')
            require(not any(a['id'] == activity_id for a in clean_activities), 'Atividades duplicadas.')
            clean_activities.append({'id': activity_id, 'title': activity_title, 'priority': priority, 'due_at': activity_due})
        timestamp, revision = now(), previous['revision'] + 1 if previous else 1
        document_id = document_id or uid(kind)
        published_revision = revision if status == 'published' else previous['published_revision'] if previous else None
        record = {'id': document_id, 'student_id': student_id, 'kind': kind, 'title': title_value, 'body': body,
                  'period': period, 'activities': dumps(clean_activities), 'status': status, 'revision': revision,
                  'published_revision': published_revision, 'author_id': self.user['id'], 'reviewer_id': reviewer_id,
                  'reviewed_at': reviewed_at, 'created_at': previous['created_at'] if previous else timestamp, 'updated_at': timestamp}
        if previous:
            keys = [k for k in record if k != 'id']
            self.db.execute('UPDATE documents SET ' + ','.join(k + '=?' for k in keys) + ' WHERE id=?', [record[k] for k in keys] + [document_id])
        else:
            self.db.execute('INSERT INTO documents (' + ','.join(record) + ') VALUES (' + ','.join('?' for _ in record) + ')', list(record.values()))
        self.db.execute('INSERT INTO document_revisions VALUES (?,?,?,?,?)', (document_id, revision, dumps(record), self.user['id'], timestamp))
        if status == 'published':
            if kind == 'plan':
                active_tasks = set()
                affected_periods = {period}
                for activity in clean_activities:
                    task_id = 'task_' + digest(document_id + ':' + activity['id'])[:24]
                    active_tasks.add(task_id)
                    old_task = self.db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
                    if old_task:
                        affected_periods.add(week(old_task['due_at']))
                        changes = any(old_task[k] != activity[k] for k in ('title', 'priority', 'due_at')) or old_task['archived_at'] is not None
                        if changes:
                            before = {k: old_task[k] for k in ('title', 'priority', 'due_at', 'archived_at')}
                            self.db.execute('UPDATE tasks SET title=?,priority=?,due_at=?,archived_at=NULL,updated_by=?,revision=revision+1,updated_at=? WHERE id=?', (activity['title'], activity['priority'], activity['due_at'], self.user['id'], timestamp, task_id))
                            self.db.execute('INSERT INTO task_events VALUES (?,?,?,?,?,?)', (uid('event'), task_id, self.user['id'], dumps(before), dumps(activity), timestamp))
                    else:
                        self.db.execute('INSERT INTO tasks(id,student_id,plan_id,title,priority,status,due_at,author_id,updated_by,revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (task_id, student_id, document_id, activity['title'], activity['priority'], 'todo', activity['due_at'], self.user['id'], self.user['id'], 1, timestamp, timestamp))
                    affected_periods.add(week(activity['due_at']))
                for withdrawn in self.db.execute('SELECT * FROM tasks WHERE plan_id=? AND archived_at IS NULL', (document_id,)).fetchall():
                    if withdrawn['id'] not in active_tasks:
                        affected_periods.add(week(withdrawn['due_at']))
                        self.db.execute('UPDATE tasks SET archived_at=?,updated_at=?,updated_by=?,revision=revision+1 WHERE id=?',
                                        (timestamp, timestamp, self.user['id'], withdrawn['id']))
                        self.db.execute('INSERT INTO task_events VALUES (?,?,?,?,?,?)',
                                        (uid('event'), withdrawn['id'], self.user['id'], dumps({'archived_at': None}), dumps({'archived_at': timestamp}), timestamp))
                self.refresh_tasks(student_id, affected_periods)
            self.notify_student(student_id, 'Plano publicado pelo mentor' if kind == 'plan' else 'Relatório revisado disponível', timestamp)
        audit(self.db, self.user['id'], f'{kind}.{status}', kind, document_id,
              before={'revision': previous['revision'], 'status': previous['status']} if previous else None,
              after={'revision': revision, 'status': status, 'body_length': len(body), 'student_id': student_id, 'reviewer_id': reviewer_id})
        return self.document_dict(self.db.execute('SELECT * FROM documents WHERE id=?', (document_id,)).fetchone())

    def get_document(self, document_id, kind):
        self.role('mentor', 'student')
        row = self.db.execute('SELECT * FROM documents WHERE id=? AND kind=?', (document_id, kind)).fetchone()
        require(row is not None, 'Documento indisponível.', 403)
        if self.user['role'] == 'mentor':
            self.mentor_student(row['student_id'])
            return self.document_dict(row)
        student = self.db.execute('SELECT * FROM students WHERE id=?', (row['student_id'],)).fetchone()
        allowed = student['user_id'] == self.user['id']
        if not allowed and kind == 'report' and age(student['birth_date']) < 18:
            allowed = self.db.execute('SELECT 1 FROM report_grants WHERE student_id=? AND user_id=? AND revoked_at IS NULL', (row['student_id'], self.user['id'])).fetchone() is not None
        require(allowed, 'Documento indisponível.', 403)
        return self.document_dict(row, published=True)

    def student_home(self):
        self.role('student')
        row = self.db.execute('SELECT id FROM students WHERE user_id=?', (self.user['id'],)).fetchone()
        if not row:
            reports = []
            for item in self.db.execute("SELECT d.id FROM documents d JOIN report_grants g ON g.student_id=d.student_id WHERE g.user_id=? AND g.revoked_at IS NULL AND d.kind='report' AND d.published_revision IS NOT NULL", (self.user['id'],)):
                try:
                    reports.append(self.get_document(item['id'], 'report'))
                except APIError:
                    pass
            return {'student': None, 'reports_only': True, 'reports': reports, 'plans': [], 'tasks': [], 'messages': [], 'agenda': [], 'notifications': [], 'synthetic': True}
        student = self.student(row['id'])
        messages = [dict(r) for r in self.db.execute('SELECT m.*,u.name author_name FROM messages m JOIN users u ON u.id=m.author_id WHERE student_id=? ORDER BY m.created_at DESC', (student['id'],))]
        return {'student': student, 'reports_only': False, 'plans': self.documents(student['id'], 'plan', True),
                'reports': self.documents(student['id'], 'report', True), 'tasks': self.tasks(student['id']), 'messages': messages,
                'agenda': [dict(r) for r in self.db.execute('SELECT * FROM agenda WHERE student_id=? ORDER BY starts_at', (student['id'],))],
                'notifications': self.notifications(), 'synthetic': True}

    def update_period(self, student_id, metrics, source_id, source, period=None):
        period = period or week()
        row = self.db.execute('SELECT * FROM periods WHERE student_id=? AND period=?', (student_id, period)).fetchone()
        existing = json.loads(row['metrics']) if row else {}
        existing.update(metrics)
        sources = json.loads(row['source_ids']) if row else []
        if source_id not in sources:
            sources.append(source_id)
        source_actor = {'student': 'aluno', 'mentor': 'mentor', 'admin': 'administrador'}.get(self.user['role'], 'sistema') if self.user else 'sistema'
        for metric, value in metrics.items():
            observation_id = uid('signal')
            self.db.execute('INSERT INTO signal_observations VALUES (?,?,?,?,?,?,?,?)',
                            (observation_id, student_id, period, 'academic', metric, dumps(value), source_actor + ' · ' + source, now()))
            sources.append(observation_id)
        self.db.execute('INSERT INTO periods VALUES (?,?,?,?,?,?,?) ON CONFLICT(student_id,period) DO UPDATE SET metrics=excluded.metrics,source_ids=excluded.source_ids,source=excluded.source,updated_at=excluded.updated_at',
                        (row['id'] if row else uid('period'), student_id, period, dumps(existing), dumps(sources), source, now()))
        self.db.execute('UPDATE students SET last_sync=? WHERE id=?', (now(), student_id))

    def refresh_tasks(self, student_id, extra_periods=None):
        periods = set(extra_periods or []) | {week()}
        for period in periods:
            end = (date.fromisoformat(period) + timedelta(days=7)).isoformat()
            rows = self.db.execute('SELECT id,status FROM tasks WHERE student_id=? AND due_at>=? AND due_at<? AND archived_at IS NULL', (student_id, period, end)).fetchall()
            completion = round(100 * sum(t['status'] == 'done' for t in rows) / len(rows), 1) if rows else None
            self.update_period(student_id, {'task_completion_pct': completion}, 'tasks:' + period, 'tarefas persistentes', period)
        self.evaluate_student(student_id)

    def idempotent(self, data, operation):
        event_id = text(data, 'event_id', 100)
        require(re.fullmatch(r'[A-Za-z0-9_-]{8,100}', event_id) is not None, 'event_id precisa ter 8–100 caracteres alfanuméricos, hífen ou sublinhado.')
        fingerprint = digest(dumps(data))
        existing = self.db.execute('SELECT * FROM integration_events WHERE actor_id=? AND event_id=?', (self.user['id'], event_id)).fetchone()
        if existing:
            require(existing['payload_hash'] == fingerprint, 'event_id já utilizado com outro conteúdo.', 409)
            return {**json.loads(existing['response']), 'replayed': True}
        result = operation()
        self.db.execute('INSERT INTO integration_events VALUES (?,?,?,?,?)', (self.user['id'], event_id, fingerprint, dumps(result), now()))
        return result

    def update_task(self, task_id, data):
        student = self.own_student()
        require(set(data) <= {'event_id','revision','status','due_at'}, 'Campos não suportados na atualização da tarefa.')
        task = self.db.execute('SELECT * FROM tasks WHERE id=? AND student_id=? AND archived_at IS NULL', (task_id, student['id'])).fetchone()
        require(task is not None, 'Tarefa indisponível.', 403)
        def change():
            require(type(data.get('revision')) is int and data['revision'] == task['revision'], 'Tarefa mudou; recarregue e reconcilie a revisão.', 409)
            status = data.get('status', task['status'])
            require(status in ('todo', 'doing', 'done'), 'Estado de tarefa inválido.')
            due_at = iso_date(data.get('due_at', task['due_at']), 'due_at')
            after = {'status': status, 'due_at': due_at, 'revision': task['revision'] + 1}
            self.db.execute('UPDATE tasks SET status=?,due_at=?,revision=revision+1,updated_by=?,updated_at=? WHERE id=?', (status, due_at, self.user['id'], now(), task_id))
            self.db.execute('INSERT INTO task_events VALUES (?,?,?,?,?,?)', (uid('event'), task_id, self.user['id'], dumps({k: task[k] for k in after}), dumps(after), now()))
            audit(self.db, self.user['id'], 'task.update', 'task', task_id, before={k: task[k] for k in after}, after=after)
            self.refresh_tasks(student['id'], [week(task['due_at']), week(due_at)])
            return next(t for t in self.tasks(student['id']) if t['id'] == task_id)
        return self.idempotent({**data, '_task_id': task_id}, change)

    def update_agenda(self, agenda_id, data):
        student = self.own_student()
        require(set(data) <= {'event_id','revision','title','starts_at','ends_at'}, 'Campos não suportados na atualização da agenda.')
        record = self.db.execute('SELECT * FROM agenda WHERE id=? AND student_id=?', (agenda_id, student['id'])).fetchone()
        require(record is not None, 'Compromisso indisponível.', 403)
        def change():
            require(type(data.get('revision')) is int and data['revision'] == record['revision'], 'Agenda mudou; recarregue e reconcilie a revisão.', 409)
            starts_at = iso_time(data.get('starts_at', record['starts_at']), 'starts_at')
            ends_at = iso_time(data.get('ends_at', record['ends_at']), 'ends_at')
            require(starts_at < ends_at, 'O término deve ser posterior ao início.')
            require((datetime.fromisoformat(ends_at) - datetime.fromisoformat(starts_at)).total_seconds() <= 86400, 'Compromisso deve ter até 24 horas.')
            title_value = text(data, 'title', 180) if 'title' in data else record['title']
            after = {'title': title_value, 'starts_at': starts_at, 'ends_at': ends_at, 'revision': record['revision'] + 1}
            before = {key: record[key] for key in after}
            self.db.execute('UPDATE agenda SET title=?,starts_at=?,ends_at=?,revision=revision+1,updated_by=?,updated_at=? WHERE id=?',
                            (title_value, starts_at, ends_at, self.user['id'], now(), agenda_id))
            self.db.execute('INSERT INTO agenda_events VALUES (?,?,?,?,?,?)',
                            (uid('agenda_event'), agenda_id, self.user['id'], dumps(before), dumps(after), now()))
            self.db.execute('UPDATE students SET last_sync=? WHERE id=?', (now(), student['id']))
            audit(self.db, self.user['id'], 'agenda.reschedule', 'agenda', agenda_id,
                  before={k:v for k,v in before.items() if k != 'title'}, after={k:v for k,v in after.items() if k != 'title'})
            return dict(self.db.execute('SELECT * FROM agenda WHERE id=?', (agenda_id,)).fetchone())
        return self.idempotent({**data, '_agenda_id': agenda_id}, change)

    def record_study(self, data):
        student = self.own_student()
        require(not data.get('student_id') or data['student_id'] == student['id'], 'Aluno indisponível.', 403)
        require(set(data) <= {'event_id','student_id','context','subject','started_at','duration_minutes','questions'}, 'Campos não suportados nesta integração acadêmica.')
        context = data.get('context')
        require(context in ('study', 'exam'), 'Contexto deve ser study ou exam.')
        started_at = iso_time(data.get('started_at'), 'started_at')
        require(started_at <= now(), 'Não é possível registrar estudo futuro.')
        duration = data.get('duration_minutes')
        require(type(duration) is int and 1 <= duration <= 720, 'Duração deve estar entre 1 e 720 minutos.')
        questions = data.get('questions')
        require(isinstance(questions, list) and 1 <= len(questions) <= 180, 'Informe entre 1 e 180 questões.')
        clean = []
        for q in questions:
            require(isinstance(q, dict) and set(q) <= {'theme','difficulty','seconds','skipped','correct','error_cause'}, 'Questão inválida.')
            seconds = q.get('seconds')
            require(type(seconds) in (int, float) and math.isfinite(seconds) and 0 <= seconds <= 7200, 'Tempo da questão inválido.')
            require(q.get('difficulty') in ('easy','medium','hard','unknown'), 'Dificuldade inválida.')
            require(q.get('error_cause') in (None,'conteudo','leitura','descuido','tempo'), 'Causa de erro inválida.')
            skipped, correct = boolean(q, 'skipped'), boolean(q, 'correct', True)
            require(not (skipped and correct is True), 'Questão pulada não pode estar correta.')
            clean.append({'theme': text(q, 'theme', 100), 'difficulty': q['difficulty'], 'seconds': seconds,
                          'skipped': skipped, 'correct': correct, 'error_cause': q.get('error_cause')})
        subject = text(data, 'subject', 100)
        def change():
            study_id = uid('study')
            period = week(datetime.fromisoformat(started_at).astimezone(LOCAL_TZ).date())
            self.db.execute('INSERT INTO study_sessions VALUES (?,?,?,?,?,?,?,?,?,?)',
                            (study_id, student['id'], period, context, subject, started_at, duration, dumps(clean), self.user['id'], 'aluno · integração'))
            rows = self.db.execute("SELECT questions,started_at FROM study_sessions WHERE student_id=? AND period=? AND context='study'", (student['id'], period)).fetchall()
            hard, all_questions, hard_sessions, late = [], [], 0, 0
            for row in rows:
                qs = json.loads(row['questions'])
                hs = [q for q in qs if q['difficulty'] == 'hard']
                hard += hs
                all_questions += qs
                hard_sessions += int(any(q['skipped'] for q in hs))
                late += int(datetime.fromisoformat(row['started_at']).astimezone(LOCAL_TZ).hour >= 23)
            metrics = {'hard_study_sessions': hard_sessions, 'skipped_hard_study_pct': round(sum(q['skipped'] for q in hard) * 100 / len(hard), 1) if hard else None,
                       'question_seconds': round(sum(q['seconds'] for q in all_questions) / len(all_questions), 1) if all_questions else None,
                       'late_study_sessions': late}
            self.update_period(student['id'], metrics, study_id, 'registros de estudo', period)
            self.evaluate_student(student['id'])
            audit(self.db, self.user['id'], 'study.record', 'study', study_id, after={'student_id': student['id'], 'context': context, 'questions': len(clean)})
            return {'id': study_id, 'student_id': student['id'], 'period': period, 'source': 'student', 'synced_at': now()}
        return self.idempotent(data, change)

    def rules(self):
        self.role('admin', 'mentor')
        versions = []
        for row in self.db.execute('SELECT * FROM rule_versions' + (" WHERE status!='draft'" if self.user['role'] == 'mentor' else '') + ' ORDER BY rowid DESC'):
            item = dict(row)
            item['config'] = json.loads(item['config'])
            versions.append(item)
        return {'versions': versions, 'active_id': self.active_rules()['id']}

    def save_rules(self, data, version_id=None):
        self.role('admin')
        reason, name = text(data, 'reason', 1000), text(data, 'name', 120)
        config = data.get('config')
        require(isinstance(config, dict), 'Configuração deve ser um objeto JSON.')
        require(len(dumps(config)) <= 100000, 'Configuração muito grande.')
        previous = None
        if version_id:
            previous = self.db.execute('SELECT * FROM rule_versions WHERE id=?', (version_id,)).fetchone()
            require(previous is not None, 'Versão não encontrada.', 404)
            require(previous['status'] == 'draft', 'Versões ativadas são imutáveis. Crie um rascunho.', 409)
            self.db.execute('UPDATE rule_versions SET name=?,config=?,reason=? WHERE id=?', (name, dumps(config), reason, version_id))
        else:
            version_id = uid('rules')
            self.db.execute('INSERT INTO rule_versions VALUES (?,?,?,?,?,?,?,?,?)', (version_id, name, dumps(config), 'draft', self.user['id'], now(), None, self.active_rules()['id'], reason))
        audit(self.db, self.user['id'], 'rules.draft', 'rule_version', version_id, reason,
              before=json.loads(previous['config']) if previous else None, after=config)
        return {'id': version_id, 'name': name, 'config': config, 'status': 'draft', 'errors': validate_config(config)}

    def rule_action(self, version_id, action, data):
        self.role('admin')
        version = self.db.execute('SELECT * FROM rule_versions WHERE id=?', (version_id,)).fetchone()
        require(version is not None, 'Versão não encontrada.', 404)
        config = json.loads(version['config'])
        errors = validate_config(config)
        if action == 'validate':
            audit(self.db, self.user['id'], 'rules.validate', 'rule_version', version_id, after={'valid': not errors, 'errors': errors})
            return {'valid': not errors, 'errors': errors}
        if errors:
            audit(self.db, self.user['id'], 'rules.rejected', 'rule_version', version_id, after={'action': action, 'errors': errors})
            raise APIError(400, 'Configuração inválida.', errors)
        current_version = self.active_rules()
        if action == 'simulate':
            compare_id = data.get('compare_id') or current_version['id']
            require(isinstance(compare_id, str) and len(compare_id) <= 100, 'compare_id: identificador inválido.')
            compare = self.db.execute('SELECT * FROM rule_versions WHERE id=?', (compare_id,)).fetchone()
            require(compare is not None, 'Versão de comparação não encontrada.', 404)
            compare_config = json.loads(compare['config'])
            require(not validate_config(compare_config), 'Versão de comparação inválida.')
            results = []
            for student in self.db.execute('SELECT id FROM students ORDER BY id'):
                current, history = self.current_input(student['id'])
                before, after = evaluate(current, history, compare_config), evaluate(current, history, config)
                # Admin recebe pseudônimo e resultado agregado, sem notas/corpos ou evidências individuais.
                results.append({'student_id': student['id'], 'student_name': 'Sintético ' + student['id'], 'before': before['level'], 'after': after['level'], 'before_score': before['score'], 'after_score': after['score']})
            audit(self.db, self.user['id'], 'rules.simulate', 'rule_version', version_id,
                  after={'compare_id': compare_id, 'students': len(results), 'changes': sum(r['before'] != r['after'] for r in results)})
            return {'results': results, 'before_version': compare_id, 'after_version': version_id, 'production_changed': False}
        require(action in ('activate', 'restore'), 'Operação inexistente.', 404)
        reason = text(data, 'reason', 1000)
        if action == 'activate':
            require(version['status'] == 'draft', 'Somente rascunhos podem ser ativados.', 409)
        else:
            require(version['status'] == 'archived', 'Restaure uma versão anterior arquivada.', 409)
        self.db.execute("UPDATE rule_versions SET status='archived' WHERE status='active'")
        target = version_id
        if action == 'restore':
            target = uid('rules')
            self.db.execute('INSERT INTO rule_versions VALUES (?,?,?,?,?,?,?,?,?)', (target, 'Restauração · ' + version['name'], version['config'], 'active', self.user['id'], now(), now(), version_id, reason))
        else:
            self.db.execute("UPDATE rule_versions SET status='active',activated_at=?,reason=? WHERE id=?", (now(), reason, target))
        audit(self.db, self.user['id'], 'rules.' + action, 'rule_version', target, reason,
              before={'id': current_version['id'], 'config': json.loads(current_version['config'])},
              after={'id': target, 'config': config, 'restored_from': version_id if action == 'restore' else None})
        return {'id': target, 'active_id': target, 'status': 'active', 'applies_to': 'future_evaluations'}

    def assignments(self):
        self.role('admin')
        return {'mentors': [dict(r) for r in self.db.execute("SELECT id,name FROM users WHERE role='mentor'")],
                'students': [dict(r) for r in self.db.execute('SELECT id,name FROM students')],
                'links': [dict(r) for r in self.db.execute('SELECT * FROM mentor_students')]}

    def assign(self, student_id, data):
        self.role('admin')
        mentor_id, reason = text(data, 'mentor_id', 100), text(data, 'reason', 1000)
        require(self.db.execute('SELECT 1 FROM students WHERE id=?', (student_id,)).fetchone(), 'Aluno não encontrado.', 404)
        require(self.db.execute("SELECT 1 FROM users WHERE id=? AND role='mentor'", (mentor_id,)).fetchone(), 'Mentor inválido.')
        before = [r[0] for r in self.db.execute('SELECT mentor_id FROM mentor_students WHERE student_id=?', (student_id,))]
        self.db.execute('DELETE FROM mentor_students WHERE student_id=?', (student_id,))
        self.db.execute('INSERT INTO mentor_students VALUES (?,?,?)', (mentor_id, student_id, now()))
        # Notificações nominativas não sobrevivem à revogação do vínculo.
        self.db.execute("DELETE FROM notifications WHERE student_id=? AND user_id IN (SELECT id FROM users WHERE role='mentor') AND user_id!=?", (student_id, mentor_id))
        audit(self.db, self.user['id'], 'assignment.update', 'student', student_id, reason, before=before, after=[mentor_id])
        return {'student_id': student_id, 'mentor_id': mentor_id}

    def audit_log(self):
        self.role('admin')
        return {'events': [dict(r) for r in self.db.execute('SELECT a.*,u.name actor_name FROM audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.rowid DESC LIMIT 200')]}
