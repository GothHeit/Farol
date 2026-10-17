"""HTTP smoke tests against the real local server and a disposable SQLite database.

No external accounts, services, browser drivers or network requests are required.
"""

import copy
from contextlib import closing
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
import json
from pathlib import Path
import tempfile
import threading
import unittest

from farol.db import connect, digest, migrate, now, week
from farol.rules import DEFAULT_CONFIG
from farol.seed import seed
from server import create_server


PASSWORD = "synthetic-http-test-password"


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_dir = tempfile.TemporaryDirectory()
        cls.template_path = Path(cls.template_dir.name) / "template.sqlite3"
        migrate(cls.template_path)
        with closing(connect(cls.template_path)) as db, db:
            seed(db, password=PASSWORD, examples=False)

    @classmethod
    def tearDownClass(cls):
        cls.template_dir.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "http.sqlite3"
        with closing(connect(self.template_path)) as source, closing(connect(self.path)) as target:
            source.backup(target)
        self.start_server()

    def tearDown(self):
        self.stop_server()
        self.tmp.cleanup()

    def start_server(self):
        self.server = create_server(self.path, host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.assertFalse(self.thread.is_alive())

    def request(self, method, path, data=None, session=None, headers=None, raw=None):
        request_headers = {"Content-Type": "application/json"}
        if session:
            request_headers.update(Cookie=session["cookie"], **{"X-CSRF-Token": session["csrf"]})
        request_headers.update(headers or {})
        body = raw if raw is not None else (json.dumps(data) if data is not None else None)
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            payload = response.read()
            response_headers = dict(response.getheaders())
            if "application/json" in response_headers.get("Content-Type", ""):
                payload = json.loads(payload)
            else:
                payload = payload.decode()
            return response.status, payload, response_headers
        finally:
            connection.close()

    def successful(self, method, path, data=None, session=None):
        status, result, _ = self.request(method, path, data, session)
        self.assertEqual(status, 200, result)
        return result

    def login(self, email="ana@farol.local"):
        status, response, headers = self.request("POST", "/api/login", {"email": email, "password": PASSWORD})
        self.assertEqual(status, 200, response)
        return {"cookie": headers["Set-Cookie"].split(";", 1)[0], "csrf": response["csrf_token"], "user": response["user"]}

    def document(self, status="draft", kind="plan", **extra):
        return {"title": "Título escrito pelo mentor", "body": "Texto de autoria humana inserido no teste HTTP.",
                "period": week(), "status": status,
                "activities": [{"title": "Atividade definida pelo mentor", "priority": "high", "due_at": week()}] if kind == "plan" else [],
                **extra}

    def publish_report(self, mentor, student_id):
        data = self.document(kind="report")
        draft = self.successful("POST", f"/api/students/{student_id}/reports", data, mentor)
        reviewed = self.successful("PUT", f"/api/reports/{draft['id']}", {**data, "revision": draft["revision"], "status": "reviewed"}, mentor)
        return self.successful("PUT", f"/api/reports/{draft['id']}", {**data, "revision": reviewed["revision"], "status": "published"}, mentor)

    def test_real_login_cookie_csrf_session_rotation_expiry_and_logout(self):
        self.assertEqual(self.request("GET", "/api/dashboard")[0], 401)
        self.assertEqual(self.request("POST", "/api/login", {"email": "ana@farol.local", "password": "wrong"})[0], 401)
        status, payload, headers = self.request("POST", "/api/login", {"email": "ana@farol.local", "password": PASSWORD})
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn("password", json.dumps(payload))
        first = {"cookie": headers["Set-Cookie"].split(";", 1)[0], "csrf": payload["csrf_token"]}
        self.assertEqual(self.successful("GET", "/api/session", session=first)["user"]["role"], "mentor")
        for token in ("", "incorrect", "inválido"):
            self.assertEqual(self.request("POST", "/api/evaluate", {}, first, {"X-CSRF-Token": token})[0], 403)
        status, rotated, headers = self.request("POST", "/api/login", {"email": "ana@farol.local", "password": PASSWORD}, first)
        self.assertEqual(status, 200)
        second = {"cookie": headers["Set-Cookie"].split(";", 1)[0], "csrf": rotated["csrf_token"]}
        self.assertNotEqual(first["cookie"], second["cookie"])
        self.assertEqual(self.request("GET", "/api/session", session=first)[0], 401)
        status, payload, headers = self.request("POST", "/api/logout", {}, second)
        self.assertEqual(status, 200, payload)
        self.assertIn("Max-Age=0", headers["Set-Cookie"])
        self.assertEqual(self.request("GET", "/api/dashboard", session=second)[0], 401)
        expired = self.login()
        with closing(connect(self.path)) as db, db:
            token = expired["cookie"].split("=", 1)[1]
            db.execute("UPDATE sessions SET expires_at=? WHERE token_hash=?", ("2000-01-01T00:00:00+00:00", digest(token)))
        self.assertEqual(self.request("GET", "/api/session", session=expired)[0], 401)

    def test_origin_host_json_validation_and_static_file_allowlist(self):
        mentor = self.login()
        for headers in ({"Origin": "https://attacker.invalid"}, {"Sec-Fetch-Site": "cross-site"}, {"Host": "attacker.invalid"}):
            self.assertEqual(self.request("POST", "/api/evaluate", {}, mentor, headers)[0], 403)
        for body in ("{", "[]", '{"number":NaN}', '{"number":Infinity}'):
            self.assertEqual(self.request("POST", "/api/evaluate", session=mentor, raw=body)[0], 400)
        self.assertEqual(self.request("POST", "/api/evaluate", {}, mentor, {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/api/evaluate", {}, mentor, {"Content-Length": "262145"})[0], 413)
        for path in ("/.env", "/data/farol.sqlite3", "/../server.py", "/assets/../../server.py"):
            self.assertEqual(self.request("GET", path)[0], 404)
        status, html, headers = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Farol", html)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_invalid_reference_types_are_rejected_without_partial_writes(self):
        mentor, admin = self.login(), self.login("admin@farol.local")
        before = self.successful("GET", "/api/students/student_beatriz", session=mentor)["interventions"]
        self.assertEqual(self.request("POST", "/api/students/student_beatriz/interventions",
                                      {"body": "Texto manual", "alert_id": {"invalid": "reference"}}, mentor)[0], 400)
        self.assertEqual(self.successful("GET", "/api/students/student_beatriz", session=mentor)["interventions"], before)
        self.assertEqual(self.request("POST", "/api/rules/rules_v1/simulate", {"compare_id": ["rules_v1"]}, admin)[0], 400)

    def test_server_enforces_mentor_student_admin_boundaries_and_idor(self):
        mentor = self.login()
        other = self.login("bruno@farol.local")
        student = self.login("beatriz@farol.local")
        admin = self.login("admin@farol.local")
        dashboard = self.successful("GET", "/api/dashboard", session=mentor)
        self.assertNotIn("student_marina", [item["id"] for item in dashboard["students"]])
        for account, target in ((mentor, "student_marina"), (other, "student_beatriz")):
            self.assertEqual(self.request("GET", f"/api/students/{target}", session=account)[0], 403)
            for kind in ("notes", "interventions", "messages", "plans", "reports"):
                self.assertEqual(self.request("POST", f"/api/students/{target}/{kind}", {"body": "Acesso indevido"}, account)[0], 403)
        rules = self.successful("GET", "/api/rules", session=mentor)
        active_id = rules["active_id"]
        self.assertTrue(rules["versions"][0]["config"])
        for method, path, data in (("POST", "/api/rules", {}), ("PUT", f"/api/rules/{active_id}", {}),
                                  ("POST", f"/api/rules/{active_id}/simulate", {}), ("POST", f"/api/rules/{active_id}/activate", {})):
            self.assertEqual(self.request(method, path, data, mentor)[0], 403)
        self.assertEqual(self.request("GET", "/api/audit", session=mentor)[0], 403)
        self.assertEqual(self.request("GET", "/api/assignments", session=mentor)[0], 403)
        for account in (student, admin):
            self.assertEqual(self.request("GET", "/api/dashboard", session=account)[0], 403)
            self.assertEqual(self.request("GET", "/api/students/student_beatriz", session=account)[0], 403)
        self.assertEqual(self.request("GET", "/api/rules", session=student)[0], 403)
        self.assertEqual(self.request("POST", "/api/evaluate", {}, student)[0], 403)

    def test_admin_drafts_simulation_activation_and_restore_preserve_historical_alerts(self):
        admin, mentor = self.login("admin@farol.local"), self.login()
        before = self.successful("GET", "/api/students/student_beatriz", session=mentor)
        original_rules = before["alerts"]
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["rules"][0]["threshold"] = 14
        draft = self.successful("POST", "/api/rules", {"name": "Edição manual administrativa", "reason": "Teste HTTP", "config": config}, admin)
        self.assertEqual(draft["errors"], [])
        self.assertEqual(self.successful("GET", "/api/rules", session=mentor)["active_id"], "rules_v1")
        simulation = self.successful("POST", f"/api/rules/{draft['id']}/simulate", {}, admin)
        self.assertFalse(simulation["production_changed"])
        self.assertEqual(simulation["before_version"], "rules_v1")
        self.assertEqual(self.successful("GET", "/api/students/student_beatriz", session=mentor)["alerts"], original_rules)
        self.successful("POST", f"/api/rules/{draft['id']}/activate", {"reason": "Ativação explícita de teste"}, admin)
        self.assertEqual(self.successful("GET", "/api/students/student_beatriz", session=mentor)["evaluation"]["version_id"], before["evaluation"]["version_id"])
        self.successful("POST", "/api/evaluate", {"reason": "Avaliação futura explícita"}, mentor)
        after = self.successful("GET", "/api/students/student_beatriz", session=mentor)
        self.assertEqual(after["evaluation"]["version_id"], draft["id"])
        self.assertEqual(after["alerts"], original_rules)
        restored = self.successful("POST", "/api/rules/rules_v1/restore", {"reason": "Restaurar configuração de teste"}, admin)
        self.assertNotEqual(restored["active_id"], "rules_v1")
        config["rules"][0]["threshold"] = -1
        invalid = self.successful("POST", "/api/rules", {"name": "Inválida", "reason": "Teste limites", "config": config}, admin)
        self.assertTrue(invalid["errors"])
        self.assertEqual(self.request("POST", f"/api/rules/{invalid['id']}/activate", {"reason": "Teste rejeição"}, admin)[0], 400)
        self.assertEqual(self.successful("GET", "/api/rules", session=admin)["active_id"], restored["active_id"])

    def test_manual_mentor_flow_plan_note_triage_intervention_message_and_real_notifications(self):
        mentor, student, other = self.login(), self.login("beatriz@farol.local"), self.login("bruno@farol.local")
        detail = self.successful("GET", "/api/students/student_beatriz", session=mentor)
        alert = detail["alerts"][0]
        triage = {"interpretation": "Interpretação escrita pela mentora", "useful": True, "following": True, "acted": True}
        triaged = self.successful("POST", f"/api/alerts/{alert['id']}/triage", triage, mentor)
        self.assertEqual(triaged["triage"]["author_id"], "mentor_ana")
        self.assertEqual(self.request("POST", f"/api/alerts/{alert['id']}/triage", triage, other)[0], 403)
        note_body = "Conteúdo privado escrito no teste, sem exposição no aluno ou na auditoria."
        note = self.successful("POST", "/api/students/student_beatriz/notes", {"body": note_body}, mentor)
        self.assertEqual(note["visibility"], "private")
        edited = self.successful("PUT", f"/api/notes/{note['id']}", {"revision": 1, "body": note_body + " Revisado."}, mentor)
        self.assertEqual(edited["revision"], 2)
        self.assertEqual(self.request("PUT", f"/api/notes/{note['id']}", {"revision": 1, "body": "Conflito"}, mentor)[0], 409)
        intervention = self.successful("POST", "/api/students/student_beatriz/interventions", {"body": "Intervenção decidida pela mentora.", "alert_id": alert["id"]}, mentor)
        self.assertEqual(intervention["source"], "mentor")
        self.assertEqual(intervention["baseline"], detail["metrics"])
        data = self.document()
        plan = self.successful("POST", "/api/students/student_beatriz/plans", data, mentor)
        self.assertEqual(self.request("GET", f"/api/plans/{plan['id']}", session=student)[0], 403)
        published = self.successful("PUT", f"/api/plans/{plan['id']}", {**data, "activities": plan["activities"], "status": "published", "revision": 1}, mentor)
        self.assertEqual(published["author_id"], "mentor_ana")
        self.assertEqual(self.successful("GET", f"/api/plans/{plan['id']}", session=student)["body"], data["body"])
        message = self.successful("POST", "/api/students/student_beatriz/messages", {"body": "Mensagem humana em branco até este envio manual."}, mentor)
        self.assertEqual(message["external_status"], "not_sent")
        self.assertIsNone(message["read_at"])
        home = self.successful("GET", "/api/student/home", session=student)
        self.assertNotIn(note_body, json.dumps(home))
        self.assertNotIn("notes", home)
        notice = self.successful("GET", "/api/notifications", session=student)["notifications"][0]
        self.assertEqual(notice["channel"], "in_app")
        self.assertEqual(notice["created_at"][:10], now()[:10])
        self.assertEqual(self.request("POST", f"/api/notifications/{notice['id']}/read", {}, other)[0], 403)
        self.successful("POST", f"/api/notifications/{notice['id']}/read", {}, student)
        self.successful("POST", f"/api/messages/{message['id']}/read", {}, student)
        self.successful("POST", f"/api/messages/{message['id']}/respond", {}, student)
        updated = self.successful("GET", "/api/students/student_beatriz", session=mentor)["messages"][0]
        self.assertIsNotNone(updated["read_at"])
        self.assertIsNotNone(updated["response_at"])
        admin = self.login("admin@farol.local")
        self.assertNotIn(note_body, json.dumps(self.successful("GET", "/api/audit", session=admin)))

    def test_reports_require_review_and_follow_minor_guardian_adult_access_policy(self):
        mentor, child = self.login(), self.login("beatriz@farol.local")
        guardian, adult = self.login("responsavel@farol.local"), self.login("rafael@farol.local")
        draft = self.successful("POST", "/api/students/student_beatriz/reports", self.document(kind="report"), mentor)
        self.assertEqual(self.request("PUT", f"/api/reports/{draft['id']}", self.document(status="published", kind="report", revision=1), mentor)[0], 409)
        self.assertEqual(self.request("GET", f"/api/reports/{draft['id']}", session=guardian)[0], 403)
        report = self.publish_report(mentor, "student_beatriz")
        child_content = self.successful("GET", f"/api/reports/{report['id']}", session=child)
        guardian_content = self.successful("GET", f"/api/reports/{report['id']}", session=guardian)
        self.assertEqual(child_content, guardian_content)
        self.assertEqual(child_content["audience"], "student_and_authorized_guardians")
        self.assertEqual(child_content["external_status"], "not_sent")
        self.assertEqual(self.request("GET", f"/api/reports/{report['id']}", session=adult)[0], 403)
        adult_report = self.publish_report(mentor, "student_rafael")
        self.assertEqual(self.successful("GET", f"/api/reports/{adult_report['id']}", session=adult)["audience"], "student")
        self.assertEqual(self.request("GET", f"/api/reports/{adult_report['id']}", session=guardian)[0], 403)
        with closing(connect(self.path)) as db, db:
            db.execute("UPDATE report_grants SET revoked_at=? WHERE student_id='student_beatriz'", (now(),))
        self.assertEqual(self.request("GET", f"/api/reports/{report['id']}", session=guardian)[0], 403)

    def test_task_sync_updates_dashboard_idempotently_and_persists_after_server_restart(self):
        mentor, student = self.login(), self.login("beatriz@farol.local")
        home = self.successful("GET", "/api/student/home", session=student)
        task = next(item for item in home["tasks"] if item["status"] == "todo")
        data = {"event_id": "http-task-event-001", "revision": task["revision"], "status": "done"}
        first = self.successful("PATCH", f"/api/tasks/{task['id']}", data, student)
        replayed = self.successful("PATCH", f"/api/tasks/{task['id']}", data, student)
        self.assertTrue(replayed["replayed"])
        self.assertEqual(first["revision"], replayed["revision"])
        self.assertEqual(first["updated_by"], "user_beatriz")
        self.assertEqual(first["author_id"], task["author_id"])
        self.assertEqual(self.request("PATCH", f"/api/tasks/{task['id']}", {**data, "status": "doing"}, student)[0], 409)
        self.assertEqual(self.request("PATCH", f"/api/tasks/{task['id']}", data, mentor)[0], 403)
        before_restart = self.successful("GET", "/api/dashboard", session=mentor)
        metric = next(item for item in before_restart["students"] if item["id"] == "student_beatriz")["metrics"]["task_completion_pct"]
        self.assertEqual(metric, 100)
        self.stop_server()
        self.start_server()
        persisted = self.successful("GET", "/api/students/student_beatriz", session=mentor)
        stored_task = next(item for item in persisted["tasks"] if item["id"] == task["id"])
        self.assertEqual(stored_task["status"], "done")
        self.assertEqual(len(stored_task["history"]), 1)
        self.assertEqual(persisted["metrics"]["task_completion_pct"], metric)
        self.assertTrue(self.successful("PATCH", f"/api/tasks/{task['id']}", data, student)["replayed"])

    def test_study_api_preserves_context_author_and_disallows_unsupported_metrics(self):
        student, mentor = self.login("beatriz@farol.local"), self.login()
        payload = {"event_id": "http-study-event-001", "context": "exam", "subject": "Álgebra", "duration_minutes": 20,
                   "started_at": (datetime.now(timezone.utc) - timedelta(minutes=21)).isoformat(),
                   "questions": [{"theme": "Equações", "difficulty": "hard", "seconds": 80, "skipped": True,
                                  "correct": None, "error_cause": "tempo"}]}
        recorded = self.successful("POST", "/api/integration/study", payload, student)
        self.assertEqual(recorded["source"], "student")
        replayed = self.successful("POST", "/api/integration/study", payload, student)
        self.assertEqual(replayed["id"], recorded["id"])
        self.assertTrue(replayed["replayed"])
        detail = self.successful("GET", "/api/students/student_beatriz", session=mentor)
        rows = [item for item in detail["study"] if item["id"] == recorded["id"]]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["context"], "exam")
        self.assertEqual(rows[0]["recorded_by"], "user_beatriz")
        self.assertEqual(rows[0]["questions"][0]["error_cause"], "tempo")
        self.assertEqual(self.request("POST", "/api/integration/study", {**payload, "sleep_hours": 8}, student)[0], 400)
        self.assertEqual(self.request("POST", "/api/integration/study", {**payload, "screen_time": 20}, student)[0], 400)
        self.assertEqual(self.request("POST", "/api/integration/study", {**payload, "student_id": "student_marina"}, student)[0], 403)
        self.assertEqual(self.request("POST", "/api/integration/study", payload, mentor)[0], 403)

    def test_student_agenda_reschedule_is_authorized_idempotent_and_preserves_author(self):
        mentor, student, adult = self.login(), self.login("beatriz@farol.local"), self.login("rafael@farol.local")
        appointment = self.successful("GET", "/api/student/home", session=student)["agenda"][0]
        start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=1)
        data = {"event_id": "http-agenda-event-001", "revision": appointment["revision"],
                "starts_at": start.isoformat(), "ends_at": (start + timedelta(minutes=45)).isoformat(),
                "title": "Horário replanejado pelo aluno"}
        updated = self.successful("PATCH", f"/api/agenda/{appointment['id']}", data, student)
        replayed = self.successful("PATCH", f"/api/agenda/{appointment['id']}", data, student)
        self.assertTrue(replayed["replayed"])
        self.assertEqual(replayed["revision"], updated["revision"])
        self.assertEqual(updated["revision"], appointment["revision"] + 1)
        self.assertEqual(updated["author_id"], appointment["author_id"])
        self.assertEqual(updated["updated_by"], "user_beatriz")
        for account in (mentor, adult):
            self.assertEqual(self.request("PATCH", f"/api/agenda/{appointment['id']}", data, account)[0], 403)
        self.assertEqual(self.request("PATCH", f"/api/agenda/{appointment['id']}", {**data, "event_id": "http-agenda-stale-002"}, student)[0], 409)
        self.assertEqual(self.request("PATCH", f"/api/agenda/{appointment['id']}", {**data, "title": "Conteúdo alterado"}, student)[0], 409)
        invalid = {**data, "event_id": "http-agenda-invalid-003", "revision": updated["revision"], "ends_at": start.isoformat()}
        self.assertEqual(self.request("PATCH", f"/api/agenda/{appointment['id']}", invalid, student)[0], 400)
        detail = self.successful("GET", "/api/students/student_beatriz", session=mentor)
        visible = next(item for item in detail["agenda"] if item["id"] == appointment["id"])
        self.assertEqual(visible["starts_at"], start.isoformat())
        self.assertEqual(visible["revision"], updated["revision"])
        with closing(connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM agenda_events WHERE agenda_id=?", (appointment["id"],)).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
