import copy
import unittest

from farol.rules import DEFAULT_CONFIG, evaluate, validate_config


def record(period="2026-10-12", **metrics):
    return {"period": period, "metrics": metrics, "source_ids": [f"academic:{period}"]}


def history(**metrics):
    return [record("2026-09-21", **metrics), record("2026-09-28", **metrics)]


def only(*ids):
    config = copy.deepcopy(DEFAULT_CONFIG)
    for rule in config["rules"]:
        rule["enabled"] = rule["id"] in ids
    return config


class RulesTests(unittest.TestCase):
    def test_initial_configuration_is_valid_and_evaluation_is_pure(self):
        config = copy.deepcopy(DEFAULT_CONFIG)
        current = record(attendance_pct=70)
        past = history(attendance_pct=100)
        snapshot = copy.deepcopy((config, current, past))
        self.assertEqual(validate_config(config), [])
        self.assertEqual(evaluate(current, past, config), evaluate(current, past, config))
        self.assertEqual((config, current, past), snapshot)

    def test_isolated_signal_is_observe_and_contains_traceable_facts(self):
        result = evaluate(record(attendance_pct=70), history(attendance_pct=100))
        self.assertEqual(result["level"], "obs")
        self.assertEqual(result["distinct_signals"], 1)
        evidence = result["evidence"][0]
        self.assertEqual(evidence["baseline"], 100)
        self.assertEqual(evidence["change_pct"], 30)
        self.assertEqual(evidence["observed"], 70)
        self.assertEqual(evidence["threshold"], 20)
        self.assertEqual(evidence["window"]["baseline_periods"], ["2026-09-21", "2026-09-28"])
        self.assertEqual(evidence["source_ids"], ["academic:2026-09-21", "academic:2026-09-28", "academic:2026-10-12"])
        self.assertEqual(evidence["rule_snapshot"]["id"], "attendance_decline")

    def test_two_independent_signals_are_attention(self):
        result = evaluate(record(attendance_pct=70, schedule_pct=60), history(attendance_pct=100, schedule_pct=100))
        self.assertEqual(result["level"], "att")
        self.assertEqual(result["distinct_signals"], 2)

    def test_two_weeks_compare_to_baseline_before_the_fall(self):
        past = history(attendance_pct=100) + [record("2026-10-05", attendance_pct=75)]
        result = evaluate(record(attendance_pct=75), past)
        self.assertEqual(result["level"], "att")
        self.assertEqual(result["evidence"][0]["baseline"], 100)
        self.assertEqual(result["evidence"][0]["window"]["persistent_periods"], ["2026-10-05", "2026-10-12"])
        self.assertNotIn("2026-10-05", result["evidence"][0]["window"]["baseline_periods"])

    def test_missing_week_is_not_persistence(self):
        past = [record("2026-09-14", attendance_pct=100), record("2026-09-21", attendance_pct=100), record("2026-09-28", attendance_pct=70)]
        result = evaluate(record(attendance_pct=60), past)
        self.assertEqual(result["level"], "obs")
        self.assertEqual(result["persistent_signals"], [])

    def test_priority_gates_have_precedence(self):
        for metrics in ({"days_since_access": 7}, {"consecutive_absences": 2}, {"days_since_access": 12, "attendance_pct": 50}):
            with self.subTest(metrics=metrics):
                self.assertEqual(evaluate(record(**metrics), history(attendance_pct=100))["level"], "prio")
        self.assertEqual(evaluate(record(days_since_access=6, consecutive_absences=1), [])["level"], "ok")

    def test_challenge_pattern_only_uses_repeated_study_sessions(self):
        self.assertEqual(evaluate(record(skipped_hard_exam_pct=90, hard_exam_sessions=5), [])["level"], "unknown")
        self.assertEqual(evaluate(record(skipped_hard_study_pct=90, hard_study_sessions=1), [])["level"], "unknown")
        result = evaluate(record(skipped_hard_study_pct=30, hard_study_sessions=2), [])
        self.assertEqual(result["level"], "obs")
        self.assertEqual(result["evidence"][0]["related_observed"], {"hard_study_sessions": 2})

    def test_no_history_or_zero_baseline_never_invents_decline(self):
        config = only("attendance_decline")
        for past in ([], [record("2026-09-28", attendance_pct=100)], history(attendance_pct=0)):
            with self.subTest(past=past):
                result = evaluate(record(attendance_pct=0), past, config)
                self.assertEqual(result["level"], "unknown")
                self.assertEqual(result["evidence"], [])
                self.assertTrue(result["missing"])

    def test_history_window_is_calendar_based_and_ignores_future(self):
        config = only("attendance_decline")
        past = [record("2025-09-21", attendance_pct=100), record("2026-10-19", attendance_pct=100), record("2026-10-12", attendance_pct=100)]
        result = evaluate(record(attendance_pct=10), past, config)
        self.assertEqual(result["level"], "unknown")

    def test_duplicate_periods_do_not_manufacture_history(self):
        one = record("2026-10-05", attendance_pct=100)
        self.assertEqual(evaluate(record(attendance_pct=10), [one, one, one], only("attendance_decline"))["level"], "unknown")

    def test_duplicate_metrics_are_not_independent_and_use_max_weight(self):
        config = only("attendance_decline")
        original = next(rule for rule in config["rules"] if rule["id"] == "attendance_decline")
        original["weight"] = 2
        second = copy.deepcopy(original)
        second.update(id="attendance_large_decline", threshold=30, weight=4)
        config["rules"].append(second)
        result = evaluate(record(attendance_pct=50), history(attendance_pct=100), config)
        self.assertEqual(len(result["evidence"]), 2)
        self.assertEqual(result["distinct_signals"], 1)
        self.assertEqual(result["score"], 4)
        self.assertEqual(result["level"], "obs")

    def test_draft_changes_only_affect_evaluations_supplied_with_that_snapshot(self):
        published = copy.deepcopy(DEFAULT_CONFIG)
        current = record(days_since_access=7)
        old_result = evaluate(current, [], published)
        draft = copy.deepcopy(published)
        draft["rules"][0]["threshold"] = 9
        self.assertEqual(evaluate(current, [], draft)["level"], "ok")
        self.assertEqual(evaluate(current, [], published)["level"], "prio")
        self.assertEqual(old_result["configuration_snapshot"]["rules"][0]["threshold"], 7)
        published["rules"][0]["threshold"] = 10
        self.assertEqual(old_result["configuration_snapshot"]["rules"][0]["threshold"], 7)
        self.assertEqual(old_result["evidence"][0]["rule_snapshot"]["threshold"], 7)

    def test_editable_rule_precedence_selects_one_match_per_metric(self):
        config = only("access_gap")
        alternative = copy.deepcopy(config["rules"][0])
        alternative.update(id="access_observation", threshold=6, priority=False, weight=2, precedence=1)
        config["rules"].append(alternative)
        result = evaluate(record(days_since_access=7), [], config)
        self.assertEqual(result["level"], "obs")
        self.assertEqual(result["score"], 2)
        self.assertEqual(result["evidence"][0]["rule_id"], "access_observation")
        self.assertTrue(result["evidence"][0]["applied"])
        self.assertFalse(result["evidence"][1]["applied"])
        alternative["precedence"] = 0
        self.assertEqual(evaluate(record(days_since_access=7), [], config)["level"], "prio")

    def test_configurable_weights_affect_attention_without_auto_learning(self):
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["aggregation"]["attention_min_weight"] = 3
        current, past = record(attendance_pct=50, schedule_pct=50), history(attendance_pct=100, schedule_pct=100)
        self.assertEqual(evaluate(current, past, config)["level"], "obs")
        for rule in config["rules"]:
            if rule["id"] == "schedule_decline":
                rule["weight"] = 2
        self.assertEqual(evaluate(current, past, config)["level"], "att")

    def test_unanswered_messages_require_explicit_quantity_and_duration(self):
        current = record(unanswered_messages=10, oldest_unanswered_days=30)
        self.assertEqual(evaluate(current, [])["level"], "unknown")
        config = copy.deepcopy(DEFAULT_CONFIG)
        rule = config["rules"][-1]
        rule["enabled"] = True
        self.assertTrue(validate_config(config))
        with self.assertRaises(ValueError):
            evaluate(current, [], config)
        rule.update(threshold=2, days_threshold=3)
        self.assertFalse(validate_config(config))
        self.assertEqual(evaluate(record(unanswered_messages=2, oldest_unanswered_days=3), [], config)["level"], "prio")
        self.assertEqual(evaluate(record(unanswered_messages=1, oldest_unanswered_days=3), [], config)["level"], "ok")
        self.assertEqual(evaluate(record(unanswered_messages=2, oldest_unanswered_days=2), [], config)["level"], "ok")

    def test_optional_non_academic_sources_have_no_effect(self):
        config = only("access_gap")
        base = record(days_since_access=0)
        extras = record(days_since_access=0, sleep_hours=0, screen_time_minutes=999, unrelated_source=None)
        self.assertEqual(evaluate(base, [], config), evaluate(extras, [], config))
        config["rules"][0]["metric"] = "sleep_hours"
        self.assertTrue(validate_config(config))

    def test_invalid_and_conflicting_configurations_fail(self):
        changes = [
            lambda c: c.update(precedence=["obs", "prio", "att", "ok"]),
            lambda c: c["aggregation"].update(persistent_weeks=1),
            lambda c: c["aggregation"].update(attention_min_distinct=1),
            lambda c: c["rules"][0].update(weight=float("nan")),
            lambda c: c["rules"][0].update(precedence=101),
            lambda c: c["rules"][0].update(threshold=-1),
            lambda c: c["rules"][0].update(enabled="false"),
            lambda c: c["rules"][0].update(window_weeks=53),
            lambda c: c["rules"][0].update(min_history=5, window_weeks=4),
            lambda c: c["rules"].append(copy.deepcopy(c["rules"][0])),
            lambda c: c["rules"][6].update(min_samples={"metric": "hard_study_sessions", "minimum": 1}),
        ]
        for mutate in changes:
            with self.subTest(mutate=mutate):
                config = copy.deepcopy(DEFAULT_CONFIG)
                mutate(config)
                self.assertTrue(validate_config(config))
                with self.assertRaises(ValueError):
                    evaluate(record(), [], config)
        config = only("access_gap")
        second = copy.deepcopy(config["rules"][0])
        second.update(id="conflict", condition="lte", threshold=10)
        config["rules"].append(second)
        self.assertTrue(any("sobrepõem" in error for error in validate_config(config)))
        del config["rules"][0]["id"]
        self.assertTrue(validate_config(config))  # malformed IDs must not crash conflict validation

    def test_invalid_values_are_missing_and_not_healthy(self):
        for value in (None, "7", True, float("nan"), float("inf"), -1, 10 ** 1000):
            with self.subTest(value=value):
                result = evaluate(record(days_since_access=value), [], only("access_gap"))
                self.assertEqual(result["level"], "unknown")
                self.assertFalse(result["has_data"])

    def test_known_good_is_distinct_from_no_evidence(self):
        self.assertEqual(evaluate(record(), [])["level"], "unknown")
        self.assertEqual(evaluate(record(days_since_access=0), [])["level"], "ok")

    def test_invalid_period_is_rejected(self):
        for period in (None, "today", "2026-02-30", "20261012"):
            with self.subTest(period=period), self.assertRaises(ValueError):
                evaluate(record(period), [])


if __name__ == "__main__":
    unittest.main()
