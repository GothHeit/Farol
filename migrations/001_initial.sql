CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE users (
 id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('admin','mentor','student')),
 password_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE students (
 id TEXT PRIMARY KEY, user_id TEXT UNIQUE REFERENCES users(id), name TEXT NOT NULL,
 birth_date TEXT NOT NULL, course TEXT NOT NULL, availability TEXT NOT NULL DEFAULT '',
 restrictions TEXT NOT NULL DEFAULT '', shifts TEXT NOT NULL DEFAULT '',
 last_access_at TEXT, last_sync TEXT, created_at TEXT NOT NULL
);
CREATE TABLE mentor_students (
 mentor_id TEXT NOT NULL REFERENCES users(id), student_id TEXT NOT NULL REFERENCES students(id),
 linked_at TEXT NOT NULL, PRIMARY KEY(mentor_id,student_id)
);
CREATE TABLE report_grants (
 student_id TEXT NOT NULL REFERENCES students(id), user_id TEXT NOT NULL REFERENCES users(id),
 consented_by TEXT NOT NULL REFERENCES users(id), consented_at TEXT NOT NULL, revoked_at TEXT,
 PRIMARY KEY(student_id,user_id)
);
CREATE TABLE sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
 csrf_token TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE login_attempts (bucket TEXT PRIMARY KEY, attempts INTEGER NOT NULL, reset_at TEXT NOT NULL);
CREATE TABLE periods (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), period TEXT NOT NULL,
 metrics TEXT NOT NULL, source_ids TEXT NOT NULL, source TEXT NOT NULL,
 updated_at TEXT NOT NULL, UNIQUE(student_id,period)
);
CREATE TABLE signal_observations (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), period TEXT NOT NULL,
 namespace TEXT NOT NULL, metric TEXT NOT NULL, value_json TEXT NOT NULL,
 source TEXT NOT NULL, observed_at TEXT NOT NULL
);
CREATE TABLE academic_records (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), period TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('exam','essay')), subject TEXT NOT NULL,
 score REAL NOT NULL, max_score REAL NOT NULL, source TEXT NOT NULL, recorded_at TEXT NOT NULL
);
CREATE TABLE attendance (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id),
 occurred_at TEXT NOT NULL, present INTEGER NOT NULL CHECK(present IN (0,1)), source TEXT NOT NULL
);
CREATE TABLE study_sessions (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), period TEXT NOT NULL,
 context TEXT NOT NULL CHECK(context IN ('study','exam')), subject TEXT NOT NULL,
 started_at TEXT NOT NULL, duration_minutes INTEGER NOT NULL, questions TEXT NOT NULL,
 recorded_by TEXT NOT NULL REFERENCES users(id), source TEXT NOT NULL
);
CREATE TABLE tasks (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), plan_id TEXT,
 title TEXT NOT NULL, priority TEXT NOT NULL CHECK(priority IN ('high','normal','low')),
 status TEXT NOT NULL CHECK(status IN ('todo','doing','done')), due_at TEXT NOT NULL,
 author_id TEXT NOT NULL REFERENCES users(id), updated_by TEXT NOT NULL REFERENCES users(id),
 revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE task_events (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), actor_id TEXT NOT NULL REFERENCES users(id),
 before_json TEXT NOT NULL, after_json TEXT NOT NULL, occurred_at TEXT NOT NULL
);
CREATE TABLE agenda (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), title TEXT NOT NULL,
 starts_at TEXT NOT NULL, ends_at TEXT NOT NULL, author_id TEXT NOT NULL REFERENCES users(id)
);
CREATE TABLE rule_versions (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, config TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('draft','active','archived')),
 author_id TEXT REFERENCES users(id), created_at TEXT NOT NULL, activated_at TEXT,
 restored_from TEXT REFERENCES rule_versions(id), reason TEXT NOT NULL
);
CREATE UNIQUE INDEX one_active_rule ON rule_versions(status) WHERE status='active';
CREATE TRIGGER immutable_rule_config BEFORE UPDATE OF config ON rule_versions
 WHEN OLD.status != 'draft' BEGIN SELECT RAISE(ABORT,'Versão publicada é imutável'); END;
CREATE TABLE evaluations (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), period TEXT NOT NULL,
 version_id TEXT NOT NULL REFERENCES rule_versions(id), config_snapshot TEXT NOT NULL,
 input_hash TEXT NOT NULL, inputs TEXT NOT NULL, result TEXT NOT NULL, evaluated_at TEXT NOT NULL,
 UNIQUE(student_id,period,version_id,input_hash)
);
CREATE TABLE alerts (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), period TEXT NOT NULL,
 level TEXT NOT NULL CHECK(level IN ('obs','att','prio')),
 evaluation_id TEXT NOT NULL REFERENCES evaluations(id), version_id TEXT NOT NULL REFERENCES rule_versions(id),
 evidence TEXT NOT NULL, config_snapshot TEXT NOT NULL, detected_at TEXT NOT NULL,
 UNIQUE(student_id,period,level)
);
CREATE TABLE triage (
 id TEXT PRIMARY KEY, alert_id TEXT NOT NULL REFERENCES alerts(id),
 author_id TEXT NOT NULL REFERENCES users(id), interpretation TEXT NOT NULL,
 useful INTEGER CHECK(useful IN (0,1)), following INTEGER NOT NULL, acted INTEGER NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE notes (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), author_id TEXT NOT NULL REFERENCES users(id),
 body TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE note_revisions (
 id TEXT PRIMARY KEY, note_id TEXT NOT NULL REFERENCES notes(id), author_id TEXT NOT NULL REFERENCES users(id),
 body TEXT NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL, UNIQUE(note_id,revision)
);
CREATE TABLE documents (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id),
 kind TEXT NOT NULL CHECK(kind IN ('plan','report')), title TEXT NOT NULL, body TEXT NOT NULL,
 period TEXT NOT NULL, activities TEXT NOT NULL DEFAULT '[]',
 status TEXT NOT NULL CHECK(status IN ('draft','reviewed','published')),
 revision INTEGER NOT NULL, published_revision INTEGER,
 author_id TEXT NOT NULL REFERENCES users(id), reviewer_id TEXT REFERENCES users(id),
 reviewed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE document_revisions (
 document_id TEXT NOT NULL REFERENCES documents(id), revision INTEGER NOT NULL,
 snapshot TEXT NOT NULL, actor_id TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
 PRIMARY KEY(document_id,revision)
);
CREATE TABLE interventions (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), alert_id TEXT REFERENCES alerts(id),
 author_id TEXT NOT NULL REFERENCES users(id), body TEXT NOT NULL,
 baseline TEXT NOT NULL, period TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE messages (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), author_id TEXT NOT NULL REFERENCES users(id),
 body TEXT NOT NULL, created_at TEXT NOT NULL, read_at TEXT, response_at TEXT
);
CREATE TABLE notifications (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), student_id TEXT REFERENCES students(id),
 alert_id TEXT REFERENCES alerts(id), title TEXT NOT NULL, channel TEXT NOT NULL DEFAULT 'in_app',
 status TEXT NOT NULL DEFAULT 'available', created_at TEXT NOT NULL, read_at TEXT,
 UNIQUE(user_id,alert_id)
);
CREATE TABLE integration_events (
 actor_id TEXT NOT NULL REFERENCES users(id), event_id TEXT NOT NULL,
 payload_hash TEXT NOT NULL, response TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(actor_id,event_id)
);
CREATE TABLE labelled_events (
 id TEXT PRIMARY KEY, student_id TEXT NOT NULL REFERENCES students(id), period TEXT NOT NULL,
 disengaged INTEGER NOT NULL CHECK(disengaged IN (0,1)), occurred_at TEXT NOT NULL,
 labelled_by TEXT NOT NULL REFERENCES users(id), source TEXT NOT NULL
);
CREATE TABLE audit (
 id TEXT PRIMARY KEY, actor_id TEXT REFERENCES users(id), action TEXT NOT NULL, entity_type TEXT NOT NULL,
 entity_id TEXT NOT NULL, reason TEXT NOT NULL, before_json TEXT, after_json TEXT, occurred_at TEXT NOT NULL
);
CREATE INDEX alerts_student_period ON alerts(student_id,period);
CREATE INDEX evaluations_student_period ON evaluations(student_id,period,evaluated_at);
CREATE INDEX audit_time ON audit(occurred_at);
