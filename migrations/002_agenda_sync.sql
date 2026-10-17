ALTER TABLE agenda ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE agenda ADD COLUMN updated_by TEXT REFERENCES users(id);
ALTER TABLE agenda ADD COLUMN updated_at TEXT;
UPDATE agenda SET updated_by=author_id,updated_at=starts_at;
CREATE TABLE agenda_events (
 id TEXT PRIMARY KEY, agenda_id TEXT NOT NULL REFERENCES agenda(id),
 actor_id TEXT NOT NULL REFERENCES users(id), before_json TEXT NOT NULL,
 after_json TEXT NOT NULL, occurred_at TEXT NOT NULL
);
