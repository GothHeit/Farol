"""SQLite, migrações e primitivas de segurança; nenhuma dependência externa."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
LOCAL_TZ = ZoneInfo('America/Sao_Paulo')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def week(value=None):
    day = value or datetime.now(LOCAL_TZ).date()
    if isinstance(day, str):
        day = date.fromisoformat(day[:10])
    return (day - timedelta(days=day.weekday())).isoformat()


def uid(prefix):
    return f'{prefix}_{secrets.token_hex(12)}'


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    result = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310000).hex()
    return f'pbkdf2_sha256$310000${salt}${result}'


def password_matches(password, encoded):
    try:
        algorithm, rounds, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256' or rounds != '310000':
            return False
        return hmac.compare_digest(password_hash(password, salt).split('$')[-1], expected)
    except (ValueError, TypeError):
        return False


def connect(path):
    connection = sqlite3.connect(path, timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA busy_timeout=20000')
    return connection


def migrate(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db, db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
        for script in sorted((ROOT / 'migrations').glob('*.sql')):
            version = int(script.name.split('_')[0])
            if not db.execute('SELECT 1 FROM schema_migrations WHERE version=?', (version,)).fetchone():
                db.executescript('BEGIN IMMEDIATE;\n' + script.read_text())
                db.execute('INSERT INTO schema_migrations VALUES (?,?)', (version, now()))
                db.commit()
    os.chmod(path, 0o600)


def audit(db, actor, action, entity, entity_id, reason='', before=None, after=None):
    db.execute('INSERT INTO audit VALUES (?,?,?,?,?,?,?,?,?)',
               (uid('audit'), actor, action, entity, entity_id, reason,
                dumps(before) if before is not None else None,
                dumps(after) if after is not None else None, now()))


def age(birth_date):
    birth = date.fromisoformat(birth_date)
    today = datetime.now(LOCAL_TZ).date()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
