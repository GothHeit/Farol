"""Integration coverage for real SQLite transactions and role boundaries."""

import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from farol.db import connect, digest, dumps, migrate, now, password_matches, week
from farol.rules import DEFAULT_CONFIG
from farol.seed import seed
from farol.service import APIError, Service


PASSWORD = "synthetic-test-password"


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_dir = tempfile.TemporaryDirectory()
        cls.template_path = Path(cls.template_dir.name) / "template.sqlite3"
        migrate(cls.template_path)
        with connect(cls.template_path) as db:
            seed(db, password=PASSWORD)
        db.close()

    @classmethod
    def tearDownClass(cls):
        cls.template_dir.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.sqlite3"
        self.db = connect(self.path)
        with connect(self.template_path) as source:
            source.backup(self.db)
        source.close()
        self.mentor = self.as_user("mentor_ana")
        self.other = self.as_user("mentor_bruno")
        self.admin = self.as_user("admin")
        self.student = self.as_user("user_beatriz")
        self.adult = self.as_user("user_rafael")
        self.guardian = self.as_user("guardian_beatriz")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def as_user(self, user_id):
        row = self.db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        self.assertIsNotNone(row, user_id)
        return Service(self.db, dict(row))

    def error(self, status, call, *args, **kwargs):
        with self.assertRaises(APIError) as error:
            call(*args, **kwargs)
        self.assertEqual(error.exception.status, status, str(error.exception))

    def count(self, table):
        return self.db.execute("SELECT count(*) FROM " + table).fetchone()[0]

    def document(self, kind="plan", status="draft", **extra):
        return {"title": "Texto manual do mentor", "body": "Corpo escrito manualmente para esta avaliação.",
                "period": week(), "status": status, "activities": [] if kind == "report" else [
                    {"title": "Atividade definida pelo mentor", "priority": "high", "due_at": week()}
                ], **extra}

    def publish_report(self, student_id):
        data = self.document("report")
        draft = self.mentor.save_document(student_id, "report", data)
        reviewed = self.mentor.save_document(student_id, "report", {**data, "revision": draft["revision"], "status": "reviewed"}, draft["id"])
        return self.mentor.save_document(student_id, "report", {**data, "revision": reviewed["revision"], "status": "published"}, draft["id"])

    def test_authentication_password_hash_sessions_and_rate_limit(self):
        row = self.db.execute("SELECT * FROM users WHERE id='mentor_ana'").fetchone()
        self.assertNotEqual(row["password_hash"], PASSWORD)
        self.assertTrue(password_matches(PASSWORD, row["password_hash"]))
        self.assertFalse(password_matches("incorrect", row["password_hash"]))
        anonymous = Service(self.db)
        self.error(401, anonymous.dashboard)
        response, token = anonymous.login({"email": row["email"], "password": PASSWORD}, "127.0.0.1")
        self.assertEqual(response["user"]["role"], "mentor")
        self.assertNotIn("password_hash", response["user"])
        stored = self.db.execute("SELECT * FROM sessions WHERE token_hash=?", (digest(token),)).fetchone()
        self.assertIsNotNone(stored)
        self.assertNotEqual(stored["token_hash"], token)
        self.assertTrue(response["csrf_token"])
        self.assertGreater(stored["expires_at"], now())
        for _ in range(10):
            self.error(401, anonymous.login, {"email": row["email"], "password": "wrong"}, "test-rate")
        self.error(429, anonymous.login, {"email": row["email"], "password": PASSWORD}, "test-rate")

    def test_role_and_assignment_boundaries_cover_direct_ids(self):
        self.assertEqual(self.mentor.detail("student_beatriz")["student"]["id"], "student_beatriz")
        self.error(403, self.mentor.detail, "student_marina")
        self.error(403, self.other.detail, "student_beatriz")
        self.error(403, self.mentor.detail, "nonexistent-student")
        self.error(403, self.admin.detail, "student_beatriz")
        self.error(403, self.student.detail, "student_beatriz")
        self.error(403, self.student.student, "student_marina")
        self.error(403, self.guardian.own_student)
        self.error(403, self.other.add_authored, "student_beatriz", "notes", {"body": "Proibido"})
        self.error(403, self.other.save_document, "student_beatriz", "plan", self.document())
        self.assertTrue(self.mentor.rules()["versions"])
        version = self.admin.rules()["active_id"]
        self.error(403, self.mentor.save_rules, {"name": "Proibido", "reason": "Teste", "config": DEFAULT_CONFIG})
        for action in ("validate", "simulate", "activate", "restore"):
            self.error(403, self.mentor.rule_action, version, action, {"reason": "Teste"})

    def test_rule_draft_simulation_activation_restoration_preserve_production_history(self):
        self.mentor.process("teste inicial")
        active = self.admin.active_rules()
        old_alerts = [dict(row) for row in self.db.execute("SELECT * FROM alerts ORDER BY id")]
        old_evaluations = [dict(row) for row in self.db.execute("SELECT * FROM evaluations ORDER BY id")]
        config = json.loads(active["config"])
        config["rules"][0]["threshold"] = 365
        draft = self.admin.save_rules({"name": "Janela alterada", "reason": "Verificar dados sintéticos", "config": config})
        self.assertEqual(draft["errors"], [])
        self.assertEqual(self.admin.active_rules()["id"], active["id"])
        self.assertNotIn(draft["id"], [r["id"] for r in self.mentor.rules()["versions"]])
        simulation = self.admin.rule_action(draft["id"], "simulate", {})
        self.assertFalse(simulation["production_changed"])
        self.assertEqual(simulation["before_version"], active["id"])
        self.assertTrue(simulation["results"])
        self.assertEqual(self.count("evaluations"), len(old_evaluations))
        self.assertEqual(self.count("alerts"), len(old_alerts))
        self.admin.rule_action(draft["id"], "activate", {"reason": "Aprovação humana de teste"})
        self.assertEqual(self.count("evaluations"), len(old_evaluations))
        self.mentor.process("avaliar após ativação")
        self.assertGreater(self.count("evaluations"), len(old_evaluations))
        self.assertEqual(self.mentor.latest_evaluation("student_beatriz")["version_id"], draft["id"])
        for original in old_alerts:
            self.assertEqual(dict(self.db.execute("SELECT * FROM alerts WHERE id=?", (original["id"],)).fetchone()), original)
        for original in old_evaluations:
            self.assertEqual(dict(self.db.execute("SELECT * FROM evaluations WHERE id=?", (original["id"],)).fetchone()), original)
        self.error(409, self.admin.save_rules, {"name": "Mutação proibida", "reason": "Teste", "config": config}, draft["id"])
        restored = self.admin.rule_action(active["id"], "restore", {"reason": "Restaurar parâmetros iniciais"})
        self.assertNotEqual(restored["id"], active["id"])
        self.assertEqual(json.loads(self.admin.active_rules()["config"]), json.loads(active["config"]))
        self.assertEqual(self.mentor.latest_evaluation("student_beatriz")["version_id"], draft["id"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM rule_versions WHERE status='active'").fetchone()[0], 1)

    def test_invalid_configuration_and_database_immutability(self):
        invalid = copy.deepcopy(DEFAULT_CONFIG)
        invalid["rules"][0]["threshold"] = -2
        draft = self.admin.save_rules({"name": "Inválido", "reason": "Teste limites", "config": invalid})
        self.assertTrue(draft["errors"])
        self.assertFalse(self.admin.rule_action(draft["id"], "validate", {})["valid"])
        active_id = self.admin.active_rules()["id"]
        self.error(400, self.admin.rule_action, draft["id"], "activate", {"reason": "Não pode ativar"})
        self.error(400, self.admin.rule_action, draft["id"], "simulate", {})
        self.assertEqual(self.admin.active_rules()["id"], active_id)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE rule_versions SET config='{}' WHERE id=?", (active_id,))

    def test_priority_notification_is_same_day_and_processing_is_idempotent(self):
        student_id = "student_novo"
        last_access = (datetime.now(timezone.utc) - timedelta(days=7, minutes=1)).isoformat()
        self.db.execute("UPDATE students SET last_access_at=? WHERE id=?", (last_access, student_id))
        evaluated = self.mentor.evaluate_student(student_id)
        self.assertEqual(evaluated["level"], "prio")
        alert = next(a for a in self.mentor.alerts(student_id) if a["period"] == week() and a["level"] == "prio")
        notices = [dict(r) for r in self.db.execute("SELECT * FROM notifications WHERE alert_id=?", (alert["id"],))]
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]["channel"], "in_app")
        self.assertEqual(notices[0]["status"], "available")
        self.assertEqual(notices[0]["created_at"][:10], alert["detected_at"][:10])
        self.assertEqual(alert["detected_at"][:10], now()[:10])
        counts = tuple(self.count(t) for t in ("evaluations", "alerts", "notifications"))
        self.assertEqual(self.mentor.evaluate_student(student_id)["id"], evaluated["id"])
        self.assertEqual(tuple(self.count(t) for t in ("evaluations", "alerts", "notifications")), counts)

    def test_dashboard_separates_observation_and_priority_queue(self):
        self.mentor.process("teste resumo")
        dashboard = self.mentor.dashboard()
        self.assertTrue(dashboard["synthetic"])
        self.assertEqual(dashboard["period"], week())
        self.assertTrue(dashboard["observe"])
        self.assertTrue(all(item["level"] == "obs" for item in dashboard["observe"]))
        self.assertTrue(all(item["level"] in ("att", "prio") for item in dashboard["queue"]))
        students = {item["id"] for item in dashboard["students"]}
        self.assertNotIn("student_marina", students)
        self.assertEqual(sum(dashboard["summary"][key] for key in ("prio", "att", "obs", "ok", "unknown")), len(students))
        self.assertTrue(any(item["level"] == "unknown" for item in dashboard["students"]))
        self.assertEqual(self.mentor.detail("student_beatriz")["reference_data"], {"tri": "unavailable", "sisu": "unavailable"})

    def test_manual_triage_notes_intervention_message_and_private_audit(self):
        self.mentor.process("teste autoria")
        alert = next(a for a in self.mentor.alerts("student_beatriz"))
        triaged = self.mentor.triage_alert(alert["id"], {"interpretation": "Interpretação escrita pela mentora", "useful": True, "following": True, "acted": True})
        self.assertEqual(triaged["triage"]["author_id"], "mentor_ana")
        self.assertTrue(triaged["triage"]["useful"])
        triaged = self.mentor.triage_alert(alert["id"], {"interpretation": "Reavaliação humana", "useful": False, "following": False, "acted": False})
        self.assertFalse(triaged["triage"]["useful"])
        self.assertGreaterEqual(len(triaged["triage_history"]), 2)
        self.error(403, self.other.triage_alert, alert["id"], {"interpretation": "Proibido", "useful": True, "following": True, "acted": True})
        private_body = "Conteúdo privado exclusivo que não deve constar em auditoria."
        note = self.mentor.add_authored("student_beatriz", "notes", {"body": private_body})
        self.assertEqual(note["visibility"], "private")
        edited = self.mentor.edit_note(note["id"], {"body": private_body + " Revisado.", "revision": 1})
        self.assertEqual(edited["revision"], 2)
        self.assertEqual(len(edited["history"]), 2)
        self.error(409, self.mentor.edit_note, note["id"], {"body": "Mudança concorrente", "revision": 1})
        self.error(403, self.other.edit_note, note["id"], {"body": "Proibido", "revision": 2})
        intervention = self.mentor.add_authored("student_beatriz", "interventions", {"body": "Intervenção escolhida pela mentora.", "alert_id": alert["id"]})
        self.assertEqual(intervention["source"], "mentor")
        self.assertTrue(intervention["baseline"])
        message = self.mentor.add_authored("student_beatriz", "messages", {"body": "Mensagem escrita pela mentora."})
        self.assertEqual(message["status"], "available_in_app")
        self.assertEqual(message["external_status"], "not_sent")
        self.assertIsNone(message["read_at"])
        student_home = self.student.student_home()
        self.assertNotIn("notes", student_home)
        self.assertNotIn(private_body, dumps(student_home))
        self.assertNotIn(private_body, dumps(self.admin.audit_log()))
        for kind in ("notes", "interventions", "messages"):
            self.error(400, self.mentor.add_authored, "student_beatriz", kind, {"body": "   "})

    def test_manual_plan_publication_revision_and_student_execution(self):
        data = self.document()
        draft = self.mentor.save_document("student_beatriz", "plan", data)
        self.assertEqual(draft["source"], "mentor")
        self.error(403, self.student.get_document, draft["id"], "plan")
        publication = {**data, "activities": draft["activities"], "status": "published", "revision": draft["revision"]}
        published = self.mentor.save_document("student_beatriz", "plan", publication, draft["id"])
        visible = self.student.get_document(draft["id"], "plan")
        self.assertEqual(visible["body"], data["body"])
        self.assertEqual(visible["author_id"], "mentor_ana")
        self.assertEqual(visible["external_status"], "not_sent")
        tasks = [task for task in self.mentor.tasks("student_beatriz") if task["plan_id"] == draft["id"]]
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        result = self.student.update_task(task["id"], {"event_id": "manual-plan-task-001", "revision": task["revision"], "status": "done"})
        self.assertEqual(result["author_id"], "mentor_ana")
        self.assertEqual(result["updated_by"], "user_beatriz")
        republication = self.mentor.save_document("student_beatriz", "plan", {**publication, "revision": published["revision"]}, draft["id"])
        self.assertEqual(len([t for t in self.mentor.tasks("student_beatriz") if t["plan_id"] == draft["id"]]), 1)
        self.assertEqual(next(t for t in self.mentor.tasks("student_beatriz") if t["id"] == task["id"])["status"], "done")
        edited = self.mentor.save_document("student_beatriz", "plan", {**publication, "revision": republication["revision"], "status": "draft", "body": "Novo rascunho privado do mentor."}, draft["id"])
        self.assertEqual(edited["body"], "Novo rascunho privado do mentor.")
        self.assertEqual(self.student.get_document(draft["id"], "plan")["body"], data["body"])
        self.error(403, self.other.get_document, draft["id"], "plan")
        self.error(403, self.guardian.get_document, draft["id"], "plan")
        self.error(403, self.student.save_document, "student_beatriz", "plan", data)

    def test_revised_plan_preserves_execution_and_archives_removed_activities(self):
        original_activities = [{"title": "Primeira atividade manual", "priority": "normal", "due_at": week()},
                               {"title": "Segunda atividade manual", "priority": "high", "due_at": week()}]
        data = self.document(activities=original_activities)
        draft = self.mentor.save_document("student_beatriz", "plan", data)
        published = self.mentor.save_document("student_beatriz", "plan", {**data, "activities": draft["activities"],
                                             "status": "published", "revision": draft["revision"]}, draft["id"])
        tasks = [task for task in self.student.student_home()["tasks"] if task["plan_id"] == draft["id"]]
        removed_task = next(task for task in tasks if task["title"] == original_activities[0]["title"])
        retained_task = next(task for task in tasks if task["title"] == original_activities[1]["title"])
        self.student.update_task(retained_task["id"], {"event_id": "complete-retained-task", "status": "done", "revision": retained_task["revision"]})
        # The remaining activity is moved to the first position without an ID;
        # its exact content must retain identity and completed execution.
        changed_activities = [original_activities[1], {"title": "Nova atividade manual", "priority": "low", "due_at": week()}]
        revised = self.mentor.save_document("student_beatriz", "plan", {**data, "activities": changed_activities,
                                           "status": "published", "revision": published["revision"]}, draft["id"])
        self.assertEqual(revised["activities"][0]["id"], published["activities"][1]["id"])
        self.assertNotIn(revised["activities"][1]["id"], [item["id"] for item in published["activities"]])
        active_tasks = [task for task in self.student.student_home()["tasks"] if task["plan_id"] == draft["id"]]
        self.assertEqual(len(active_tasks), 2)
        self.assertNotIn(removed_task["id"], [task["id"] for task in active_tasks])
        self.assertEqual(next(task for task in active_tasks if task["id"] == retained_task["id"])["status"], "done")
        new_task = next(task for task in active_tasks if task["title"] == "Nova atividade manual")
        self.assertEqual(new_task["status"], "todo")
        self.assertNotEqual(new_task["id"], removed_task["id"])
        removed = self.db.execute("SELECT * FROM tasks WHERE id=?", (removed_task["id"],)).fetchone()
        self.assertIsNotNone(removed["archived_at"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM tasks WHERE plan_id=?", (draft["id"],)).fetchone()[0], 3)
        self.assertEqual(self.mentor.detail("student_beatriz")["metrics"]["task_completion_pct"], 71.4)
        self.error(403, self.student.update_task, removed_task["id"], {"event_id": "archived-task-change", "revision": removed_task["revision"], "status": "done"})

    def test_reviewed_report_same_content_for_minor_and_authorized_guardian(self):
        data = self.document("report")
        draft = self.mentor.save_document("student_beatriz", "report", data)
        self.error(409, self.mentor.save_document, "student_beatriz", "report", {**data, "revision": draft["revision"], "status": "published"}, draft["id"])
        self.error(403, self.guardian.get_document, draft["id"], "report")
        reviewed = self.mentor.save_document("student_beatriz", "report", {**data, "revision": draft["revision"], "status": "reviewed"}, draft["id"])
        self.error(409, self.mentor.save_document, "student_beatriz", "report", {**data, "revision": reviewed["revision"], "status": "published", "body": "Alterado depois da revisão"}, draft["id"])
        published = self.mentor.save_document("student_beatriz", "report", {**data, "revision": reviewed["revision"], "status": "published"}, draft["id"])
        child = self.student.get_document(published["id"], "report")
        guardian = self.guardian.get_document(published["id"], "report")
        self.assertEqual(child, guardian)
        self.assertEqual(child["reviewer_id"], "mentor_ana")
        self.assertIsNotNone(child["reviewed_at"])
        self.assertEqual(child["audience"], "student_and_authorized_guardians")
        self.assertEqual(child["external_status"], "not_sent")
        self.error(403, self.adult.get_document, published["id"], "report")
        self.db.execute("UPDATE report_grants SET revoked_at=? WHERE student_id='student_beatriz'", (now(),))
        self.error(403, self.guardian.get_document, published["id"], "report")

    def test_adult_report_has_no_guardian_audience_even_with_stale_grant(self):
        report = self.publish_report("student_rafael")
        self.db.execute("INSERT INTO report_grants VALUES (?,?,?,?,?)", ("student_rafael", "guardian_beatriz", "user_rafael", now(), None))
        content = self.adult.get_document(report["id"], "report")
        self.assertEqual(content["audience"], "student")
        self.error(403, self.guardian.get_document, report["id"], "report")
        self.assertNotIn(report["id"], [r["id"] for r in self.guardian.student_home()["reports"]])

    def test_task_integration_idempotency_concurrency_and_restart_persistence(self):
        task = self.mentor.tasks("student_beatriz")[0]
        data = {"event_id": "task-event-replay-001", "revision": task["revision"], "status": "done"}
        before_events = self.count("task_events")
        first = self.student.update_task(task["id"], data)
        second = self.student.update_task(task["id"], data)
        self.assertEqual(first["revision"], task["revision"] + 1)
        self.assertTrue(second["replayed"])
        self.assertEqual(first["revision"], second["revision"])
        self.assertEqual(self.count("task_events"), before_events + 1)
        self.error(409, self.student.update_task, task["id"], {**data, "status": "doing"})
        self.error(409, self.student.update_task, task["id"], {**data, "event_id": "stale-task-event-002"})
        self.error(403, self.adult.update_task, task["id"], {**data, "event_id": "other-student-task"})
        self.error(403, self.mentor.update_task, task["id"], data)
        expected = self.mentor.detail("student_beatriz")["metrics"]["task_completion_pct"]
        self.db.commit()
        self.db.close()
        self.db = connect(self.path)
        reopened = self.as_user("mentor_ana")
        detail = reopened.detail("student_beatriz")
        self.assertEqual(detail["metrics"]["task_completion_pct"], expected)
        self.assertIn("aluno", detail["metric_metadata"]["task_completion_pct"]["source"])
        self.assertEqual(detail["metric_metadata"]["exam_score"]["source"], "seed sintético v4")
        for alert in detail["alerts"]:
            self.assertEqual(alert["raw_inputs"]["current"]["period"], alert["period"])
            self.assertTrue(alert["raw_inputs"]["current"]["source_ids"])
        persisted = next(t for t in detail["tasks"] if t["id"] == task["id"])
        self.assertEqual(persisted["status"], "done")
        self.assertEqual(persisted["updated_by"], "user_beatriz")
        self.assertEqual(persisted["author_id"], task["author_id"])

    def test_study_and_exam_context_do_not_mix_and_import_is_idempotent(self):
        # A new week with no prior study rows provides an isolated integration fixture.
        self.db.execute("DELETE FROM study_sessions WHERE student_id='student_beatriz'")
        started = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        payload = {"event_id": "exam-skipped-hard-001", "context": "exam", "subject": "Matemática", "started_at": started,
                   "duration_minutes": 20, "questions": [{"theme": "Geometria", "difficulty": "hard", "seconds": 30,
                                                             "skipped": True, "correct": None, "error_cause": "tempo"}]}
        exam = self.student.record_study(payload)
        replay = self.student.record_study(payload)
        self.assertEqual(exam["id"], replay["id"])
        self.assertTrue(replay["replayed"])
        metrics = self.mentor.current_input("student_beatriz")[0]["metrics"]
        self.assertIsNone(metrics["skipped_hard_study_pct"])
        self.assertEqual(metrics["hard_study_sessions"], 0)
        self.student.record_study({**payload, "event_id": "study-skipped-hard-001", "context": "study"})
        self.assertNotIn("skipped_hard_study", [e["rule_id"] for e in self.mentor.latest_evaluation("student_beatriz")["evidence"]])
        self.student.record_study({**payload, "event_id": "study-skipped-hard-002", "context": "study"})
        self.assertIn("skipped_hard_study", [e["rule_id"] for e in self.mentor.latest_evaluation("student_beatriz")["evidence"]])
        study = self.mentor.detail("student_beatriz")["study"]
        self.assertEqual(len(study), 3)
        self.assertEqual(study[0]["questions"][0]["error_cause"], "tempo")
        self.error(400, self.student.record_study, {**payload, "event_id": "unsupported-signals", "sleep_hours": 8})
        self.error(403, self.student.record_study, {**payload, "student_id": "student_marina"})

    def test_quality_without_labels_does_not_invent_accuracy(self):
        self.db.execute("DELETE FROM labelled_events")
        quality = self.mentor.dashboard()["quality"]
        self.assertEqual(quality["labelled_count"], 0)
        self.assertIsNone(quality["false_alarms"])
        self.assertIsNone(quality["missed_events"])
        self.assertIsNone(quality["lead_days"])
        self.assertNotIn("precision", quality)

    def test_quality_uses_labelled_windows_and_keeps_human_usefulness_separate(self):
        self.db.execute("DELETE FROM labelled_events")
        occurred = datetime.now(timezone.utc).replace(microsecond=0)
        for student_id, days in (("student_lucas", 3), ("student_beatriz", 2)):
            self.db.execute("UPDATE alerts SET detected_at=? WHERE student_id=? AND level IN ('att','prio')",
                            ((occurred - timedelta(days=days)).isoformat(), student_id))
        events = [("label-detected", "student_lucas", 1), ("label-false", "student_beatriz", 0),
                  ("label-missed", "student_novo", 1), ("label-other-mentor", "student_marina", 0)]
        for event_id, student_id, disengaged in events:
            self.db.execute("INSERT INTO labelled_events VALUES (?,?,?,?,?,?,?)",
                            (event_id, student_id, week(), disengaged, occurred.isoformat(), "admin", "rótulo sintético de teste"))
        alert = self.mentor.alerts("student_lucas")[0]
        self.mentor.triage_alert(alert["id"], {"interpretation": "Útil para a mentora", "useful": True, "following": True, "acted": False})
        quality = self.mentor.dashboard()["quality"]
        self.assertEqual(quality["labelled_count"], 3)
        self.assertEqual(quality["false_alarms"], 1)
        self.assertEqual(quality["missed_events"], 1)
        self.assertEqual(quality["lead_days"], 3.0)
        self.assertEqual(quality["useful"], 1)
        self.assertEqual(quality["not_useful"], 0)
        self.assertIn("28 dias", quality["definition"])
        self.assertNotIn("precision", quality)

    def test_intervention_evolution_compares_the_following_week_without_success_judgment(self):
        student_id = "student_beatriz"
        previous_period = (date.fromisoformat(week()) - timedelta(days=7)).isoformat()
        baseline = {"schedule_pct": 70, "task_completion_pct": 60, "exam_score": 680, "attendance_pct": 100}
        self.db.execute("INSERT INTO interventions VALUES (?,?,?,?,?,?,?,?)",
                        ("intervention-previous-week", student_id, None, "mentor_ana", "Decisão humana registrada na semana anterior.",
                         dumps(baseline), previous_period, previous_period + "T18:00:00+00:00"))
        rows = self.mentor.detail(student_id)["evolution"]
        self.assertEqual(len(rows), 4)
        current = self.mentor.current_input(student_id)[0]["metrics"]
        for row in rows:
            self.assertEqual(row["before"], baseline[row["metric"]])
            self.assertEqual(row["after"], current[row["metric"]])
            self.assertEqual(row["before_period"], previous_period)
            self.assertEqual(row["after_period"], week())
            self.assertEqual(row["intervention_id"], "intervention-previous-week")
            self.assertIn(row["unit"], ("%", "pontos"))
            self.assertNotIn("success", row)
            self.assertNotIn("effective", row)
        self.assertEqual(self.other.dashboard()["evolution"], [])
        self.mentor.add_authored(student_id, "interventions", {"body": "Outra decisão humana nesta semana."})
        self.assertEqual(len(self.mentor.detail(student_id)["evolution"]), 4)

    def test_assignment_revocation_removes_access_and_old_notifications(self):
        self.mentor.process("teste vínculo")
        self.admin.assign("student_beatriz", {"mentor_id": "mentor_bruno", "reason": "Reatribuição de teste"})
        self.error(403, self.mentor.detail, "student_beatriz")
        self.assertEqual(self.other.detail("student_beatriz")["student"]["id"], "student_beatriz")
        self.assertFalse(any(n["student_id"] == "student_beatriz" for n in self.mentor.notifications()))


if __name__ == "__main__":
    unittest.main()
