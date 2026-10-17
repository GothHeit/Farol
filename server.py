#!/usr/bin/env python3
"""Servidor local Farol. Execute python3 server.py --seed e python3 server.py."""
import argparse
from contextlib import closing
import hmac
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import threading
from urllib.parse import urlsplit

from farol.db import ROOT, connect, migrate, now, digest, audit, dumps
from farol.service import APIError, Service, require, text
from farol.seed import seed


def load_env():
    allowed = {'FAROL_HOST','FAROL_PORT','FAROL_DB','FAROL_DEMO_PASSWORD','FAROL_SECURE_COOKIE','FAROL_EVALUATION_INTERVAL'}
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                if key.strip() in allowed:
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Handler(BaseHTTPRequestHandler):
    server_version = 'FarolLocal/4.0'

    def log_message(self, fmt, *args):
        # Não registrar cookies, query strings, corpos ou credenciais.
        if len(args) >= 2:
            print(f'HTTP {self.command} {urlsplit(self.path).path} {args[1]}', flush=True)

    def respond(self, status, payload, cookie=None, content_type='application/json; charset=utf-8'):
        body = payload if isinstance(payload, bytes) else dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data:; font-src 'self' https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def session_cookie(self, token='', expire=False):
        return f'farol_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={0 if expire else 28800}' + ('; Secure' if self.server.secure_cookie else '')

    def body_json(self):
        require(self.headers.get_content_type() == 'application/json', 'Envie Content-Type: application/json.', 415)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            require(0 < size <= 262144, 'Corpo JSON deve ter até 256 KiB.', 413)
            data = json.loads(self.rfile.read(size), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            require(isinstance(data, dict), 'Envie um objeto JSON.')
            return data
        except (ValueError, UnicodeDecodeError):
            raise APIError(400, 'JSON inválido.')

    def handle_request(self):
        path = urlsplit(self.path).path
        mutating = self.command not in ('GET', 'HEAD')
        try:
            host = self.headers.get('Host', '')
            require(host in self.server.allowed_hosts, 'Host não autorizado.', 403)
            if mutating:
                origin = self.headers.get('Origin')
                require(not origin or origin in ('http://' + host, 'https://' + host), 'Origem não autorizada.', 403)
                require(self.headers.get('Sec-Fetch-Site') not in ('cross-site',), 'Origem não autorizada.', 403)
            if not path.startswith('/api/'):
                require(self.command in ('GET','HEAD'), 'Método não permitido.', 405)
                assets = {'/': ('index.html', 'text/html; charset=utf-8'), '/index.html': ('index.html', 'text/html; charset=utf-8'),
                          '/proposta.html': ('proposta.html', 'text/html; charset=utf-8'), '/assets/app.js': ('assets/app.js', 'application/javascript; charset=utf-8'),
                          '/assets/app.css': ('assets/app.css', 'text/css; charset=utf-8')}
                require(path in assets, 'Página não encontrada.', 404)
                filename, content_type = assets[path]
                return self.respond(200, (ROOT / filename).read_bytes(), content_type=content_type)
            data = self.body_json() if mutating else {}
            with closing(connect(self.server.db_path)) as db:
                db.execute('BEGIN IMMEDIATE')
                try:
                    token = ''
                    cookie = SimpleCookie()
                    try:
                        cookie.load(self.headers.get('Cookie', ''))
                        token = cookie['farol_session'].value if 'farol_session' in cookie else ''
                    except Exception:
                        pass
                    session = db.execute('SELECT s.*,u.name,u.email,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?', (digest(token), now())).fetchone() if token else None
                    user = {'id': session['user_id'], 'name': session['name'], 'email': session['email'], 'role': session['role']} if session else None
                    service = Service(db, user)
                    if path == '/api/login' and self.command == 'POST':
                        result, new_token = service.login(data, self.client_address[0])
                        if session:
                            db.execute('DELETE FROM sessions WHERE token_hash=?', (session['token_hash'],))
                        db.commit()
                        return self.respond(200, result, self.session_cookie(new_token))
                    require(user is not None, 'Autenticação necessária.', 401)
                    if mutating:
                        require(hmac.compare_digest(self.headers.get('X-CSRF-Token', '').encode(), session['csrf_token'].encode()), 'Sessão sem token de proteção válido.', 403)
                    result, status, response_cookie = self.dispatch(service, path, data, session), 200, None
                    if path == '/api/logout':
                        response_cookie = self.session_cookie(expire=True)
                    db.commit()
                except APIError as error:
                    # Login inválido e validações rejeitadas devem deixar trilha, sem salvar mutações parciais.
                    if path == '/api/login' or (path.startswith('/api/rules/') and path.endswith(('/activate','/restore','/simulate')) and error.message == 'Configuração inválida.'):
                        db.commit()
                    else:
                        db.rollback()
                    raise
                except Exception:
                    db.rollback()
                    raise
            self.respond(status, result, response_cookie)
        except APIError as error:
            self.respond(error.status, {'error': error.message, 'details': error.details})
        except (sqlite3.Error, ValueError, KeyError, TypeError) as error:
            print(f'Falha interna {type(error).__name__}: {error}', flush=True)
            self.respond(500, {'error': 'Falha ao processar a operação. Nenhuma alteração parcial foi salva.'})

    def dispatch(self, service, path, data, session):
        method, db = self.command, service.db
        if path == '/api/session' and method == 'GET':
            return {'user': service.user, 'csrf_token': session['csrf_token'], 'synthetic': True}
        if path == '/api/logout' and method == 'POST':
            db.execute('DELETE FROM sessions WHERE token_hash=?', (session['token_hash'],))
            audit(db, service.user['id'], 'logout', 'session', 'redacted')
            return {'ok': True}
        if path == '/api/dashboard' and method == 'GET':
            return service.dashboard()
        if path == '/api/evaluate' and method == 'POST':
            return service.process(text(data, 'reason', 1000, optional=True) or 'Reprocessamento explícito pelo usuário.')
        if path == '/api/student/home' and method == 'GET':
            return service.student_home()
        if path == '/api/notifications' and method == 'GET':
            return {'notifications': service.notifications()}
        match = re.fullmatch(r'/api/notifications/([\w-]+)/read', path)
        if match and method == 'POST':
            changed = db.execute('UPDATE notifications SET read_at=? WHERE id=? AND user_id=?', (now(), match[1], service.user['id']))
            require(changed.rowcount, 'Notificação indisponível.', 403)
            return {'ok': True}
        match = re.fullmatch(r'/api/students/([\w-]+)', path)
        if match and method == 'GET':
            return service.detail(match[1])
        match = re.fullmatch(r'/api/students/([\w-]+)/(notes|interventions|messages|plans|reports)', path)
        if match and method == 'POST':
            if match[2] in ('plans','reports'):
                return service.save_document(match[1], 'plan' if match[2] == 'plans' else 'report', data)
            return service.add_authored(match[1], match[2], data)
        match = re.fullmatch(r'/api/alerts/([\w-]+)/triage', path)
        if match and method == 'POST':
            return service.triage_alert(match[1], data)
        match = re.fullmatch(r'/api/notes/([\w-]+)', path)
        if match and method == 'PUT':
            return service.edit_note(match[1], data)
        match = re.fullmatch(r'/api/(plans|reports)/([\w-]+)', path)
        if match:
            kind = 'plan' if match[1] == 'plans' else 'report'
            if method == 'GET':
                return service.get_document(match[2], kind)
            if method == 'PUT':
                service.role('mentor')
                document = service.get_document(match[2], kind)
                return service.save_document(document['student_id'], kind, data, match[2])
        match = re.fullmatch(r'/api/tasks/([\w-]+)', path)
        if match and method == 'PATCH':
            return service.update_task(match[1], data)
        match = re.fullmatch(r'/api/agenda/([\w-]+)', path)
        if match and method == 'PATCH':
            return service.update_agenda(match[1], data)
        if path == '/api/integration/study' and method == 'POST':
            return service.record_study(data)
        match = re.fullmatch(r'/api/messages/([\w-]+)/(read|respond)', path)
        if match and method == 'POST':
            student = service.own_student()
            column = 'read_at' if match[2] == 'read' else 'response_at'
            require(db.execute(f'UPDATE messages SET {column}=? WHERE id=? AND student_id=?', (now(), match[1], student['id'])).rowcount, 'Mensagem indisponível.', 403)
            audit(db, service.user['id'], 'message.' + match[2], 'message', match[1])
            service.evaluate_student(student['id'])
            return {'ok': True, column: now()}
        if path == '/api/rules':
            if method == 'GET':
                return service.rules()
            if method == 'POST':
                return service.save_rules(data)
        match = re.fullmatch(r'/api/rules/([\w-]+)', path)
        if match and method == 'PUT':
            return service.save_rules(data, match[1])
        match = re.fullmatch(r'/api/rules/([\w-]+)/(validate|simulate|activate|restore)', path)
        if match and method == 'POST':
            return service.rule_action(match[1], match[2], data)
        if path == '/api/assignments' and method == 'GET':
            return service.assignments()
        match = re.fullmatch(r'/api/assignments/([\w-]+)', path)
        if match and method == 'PUT':
            return service.assign(match[1], data)
        if path == '/api/audit' and method == 'GET':
            return service.audit_log()
        raise APIError(404, 'Rota não encontrada.')

    do_GET = handle_request
    do_HEAD = handle_request
    do_POST = handle_request
    do_PUT = handle_request
    do_PATCH = handle_request
    do_DELETE = handle_request


def create_server(db_path, host='127.0.0.1', port=8000):
    migrate(db_path)
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.db_path = str(db_path)
    server.secure_cookie = os.environ.get('FAROL_SECURE_COOKIE', '').lower() == 'true'
    bound_port = server.server_address[1]
    server.allowed_hosts = {f'{host}:{bound_port}', f'127.0.0.1:{bound_port}', f'localhost:{bound_port}'}
    return server


def main():
    load_env()
    parser = argparse.ArgumentParser(description='Farol MVP v4 · demonstração local sintética')
    parser.add_argument('--seed', action='store_true', help='criar base sintética e imprimir credenciais; não apaga dados existentes')
    parser.add_argument('--db', default=os.environ.get('FAROL_DB', str(ROOT / 'data/farol.sqlite3')))
    parser.add_argument('--host', default=os.environ.get('FAROL_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('FAROL_PORT', 8000)))
    parser.add_argument('--evaluate', action='store_true', help='processar dados atuais e sair, com auditoria')
    args = parser.parse_args()
    migrate(args.db)
    if args.seed:
        with closing(connect(args.db)) as db, db:
            result = seed(db)
        if result['created']:
            print('Base inteiramente SINTÉTICA criada. Senha das contas de demonstração:', result['password'])
            for account in result['accounts']:
                print(f'  {account["role"]:8} {account["email"]}')
            print('Guarde a senha; o seed não a imprime novamente. Execute python3 server.py para iniciar.')
        else:
            print('Base já inicializada. Nenhum dado ou senha foi alterado.')
        return
    with closing(connect(args.db)) as db, db:
        if not db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
            parser.error('Base vazia. Execute python3 server.py --seed primeiro.')
        Service(db).process('Reavaliação atual na inicialização; histórico preservado.')
    if args.evaluate:
        print('Avaliações atuais concluídas; histórico preservado.')
        return
    server = create_server(args.db, args.host, args.port)
    stop = threading.Event()
    interval = max(15, int(os.environ.get('FAROL_EVALUATION_INTERVAL', '60')))
    def scheduler():
        while not stop.wait(interval):
            try:
                with closing(connect(args.db)) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    Service(db).process('Avaliação periódica de sinais acadêmicos atuais.')
            except Exception as error:
                print(f'Falha na avaliação periódica: {type(error).__name__}', flush=True)
    thread = threading.Thread(target=scheduler, daemon=True)
    thread.start()
    print(f'Farol · dados sintéticos · http://{args.host}:{server.server_address[1]}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == '__main__':
    main()
