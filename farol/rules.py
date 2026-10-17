"""Deterministic academic signals for Farol v4 (Python standard library only).

The caller supplies a single immutable configuration snapshot. This module never
persists, sends notifications, creates pedagogical text or learns new weights.
Periods are ISO calendar dates; historical windows use elapsed calendar weeks.
"""

from __future__ import annotations

import copy
import math
import re
from datetime import date, timedelta
from statistics import mean
from typing import Any


METRICS = {
    "days_since_access": (0, 3650, "dias"),
    "consecutive_absences": (0, 100, "faltas"),
    "attendance_pct": (0, 100, "%"),
    "schedule_pct": (0, 100, "%"),
    "exam_score": (0, 1000, "pontos"),
    "essay_score": (0, 1000, "pontos"),
    "skipped_hard_study_pct": (0, 100, "%"),
    "hard_study_sessions": (0, 10000, "sessões"),
    "question_seconds": (0, 7200, "segundos/questão"),
    "late_study_sessions": (0, 10000, "sessões a partir de 23h"),
    "unanswered_messages": (0, 1000, "mensagens"),
    "oldest_unanswered_days": (0, 3650, "dias"),
    "task_completion_pct": (0, 100, "%"),
}


def _rule(rule_id, label, metric, condition, threshold, *, priority=False,
          enabled=True, weight=1, min_samples=None, **extra):
    return {
        "id": rule_id, "label": label, "metric": metric,
        "condition": condition, "threshold": threshold, "weight": weight,
        "window_weeks": 4, "min_history": 2, "min_samples": min_samples,
        "enabled": enabled, "priority": priority, "precedence": 0, **extra,
    }


DEFAULT_CONFIG = {
    "schema_version": 1,
    "precedence": ["prio", "att", "obs", "ok"],
    "aggregation": {
        "observe_min_distinct": 1,
        "attention_min_distinct": 2,
        "attention_min_weight": 0,
        "persistent_weeks": 2,
    },
    "rules": [
        _rule("access_gap", "Dias sem acesso à plataforma", "days_since_access",
              "gte", 7, priority=True),
        _rule("consecutive_absences", "Faltas consecutivas", "consecutive_absences",
              "gte", 2, priority=True),
        _rule("attendance_decline", "Variação da presença", "attendance_pct", "drop_pct", 20),
        _rule("schedule_decline", "Variação do cumprimento do cronograma", "schedule_pct", "drop_pct", 20),
        _rule("exam_decline", "Variação da nota de simulados", "exam_score", "drop_pct", 15),
        _rule("essay_decline", "Variação da nota de redações", "essay_score", "drop_pct", 15),
        _rule("skipped_hard_study", "Questões difíceis puladas repetidamente no estudo",
              "skipped_hard_study_pct", "gte", 30,
              min_samples={"metric": "hard_study_sessions", "minimum": 2}),
        _rule("question_time_change", "Variação do tempo registrado por questão",
              "question_seconds", "increase_pct", 40),
        _rule("study_schedule_change", "Variação das sessões a partir de 23h",
              "late_study_sessions", "increase_pct", 50),
        _rule("task_completion_decline", "Variação da execução de tarefas",
              "task_completion_pct", "drop_pct", 20),
        _rule("unanswered_messages", "Mensagens sem resposta no prazo configurado",
              "unanswered_messages", "unanswered", None, days_threshold=None,
              enabled=False, priority=True),
    ],
}


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _integer(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def validate_config(config: Any) -> list[str]:
    """Return all validation errors without changing the supplied document.

    Safe bounds and compulsory priority precedence are product constraints.
    Parallel thresholds for a metric are allowed, but never count as separate
    signals. Equivalent rules and overlapping opposite absolute conditions are
    rejected. Disabled message rules may retain unapproved (null) parameters.
    """
    errors = []
    if not isinstance(config, dict):
        return ["A configuração deve ser um objeto JSON."]
    allowed_top = {"schema_version", "rules", "aggregation", "precedence"}
    if set(config) - allowed_top:
        errors.append("Campos de configuração desconhecidos: " + ", ".join(sorted(set(config) - allowed_top)))
    if config.get("schema_version") != 1 or isinstance(config.get("schema_version"), bool):
        errors.append("schema_version deve ser 1.")
    if config.get("precedence") != ["prio", "att", "obs", "ok"]:
        errors.append("A precedência segura é obrigatoriamente prio > att > obs > ok.")
    aggregation = config.get("aggregation")
    if not isinstance(aggregation, dict):
        errors.append("aggregation deve ser um objeto.")
    else:
        bounds = {"observe_min_distinct": (1, 12), "attention_min_distinct": (2, 13), "persistent_weeks": (2, 8)}
        if set(aggregation) - {*bounds, "attention_min_weight"}:
            errors.append("aggregation contém campos desconhecidos.")
        for key, (low, high) in bounds.items():
            if not _integer(aggregation.get(key), low, high):
                errors.append(f"aggregation.{key} deve ser inteiro entre {low} e {high}.")
        weight = aggregation.get("attention_min_weight")
        if not _number(weight) or not 0 <= weight <= 1300:
            errors.append("aggregation.attention_min_weight deve estar entre 0 e 1300.")
        observe, attention = aggregation.get("observe_min_distinct"), aggregation.get("attention_min_distinct")
        if _number(observe) and _number(attention) and attention <= observe:
            errors.append("Atenção exige mais sinais distintos do que Observar.")
    rules = config.get("rules")
    if not isinstance(rules, list) or not 1 <= len(rules) <= 64:
        return errors + ["rules deve conter de 1 a 64 regras."]
    ids, signatures, enabled_rules = set(), set(), []
    allowed_rule = {"id", "label", "metric", "condition", "threshold", "weight", "window_weeks",
                    "min_history", "min_samples", "enabled", "priority", "days_threshold", "precedence"}
    for index, rule in enumerate(rules):
        prefix = f"Regra {index + 1}"
        if not isinstance(rule, dict):
            errors.append(f"{prefix}: deve ser um objeto.")
            continue
        if set(rule) - allowed_rule:
            errors.append(f"{prefix}: campos desconhecidos.")
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", rule_id):
            errors.append(f"{prefix}: id deve conter até 64 letras minúsculas, números e sublinhados.")
        elif rule_id in ids:
            errors.append(f"{prefix}: id duplicado {rule_id}.")
        else:
            ids.add(rule_id)
        label = rule.get("label")
        if not isinstance(label, str) or not label.strip() or len(label) > 160:
            errors.append(f"{prefix}: label deve conter de 1 a 160 caracteres.")
        metric = rule.get("metric")
        if not isinstance(metric, str) or metric not in METRICS:
            errors.append(f"{prefix}: métrica acadêmica não permitida.")
            metric = None
        condition = rule.get("condition")
        if condition not in ("gte", "lte", "drop_pct", "increase_pct", "unanswered"):
            errors.append(f"{prefix}: condição não permitida.")
        for flag in ("enabled", "priority"):
            if not isinstance(rule.get(flag), bool):
                errors.append(f"{prefix}: {flag} deve ser booleano.")
        weight = rule.get("weight")
        if not _number(weight) or not 0 <= weight <= 100:
            errors.append(f"{prefix}: peso deve estar entre 0 e 100.")
        if not _integer(rule.get("precedence", 0), 0, 100):
            errors.append(f"{prefix}: precedence deve ser inteiro entre 0 e 100.")
        window, minimum = rule.get("window_weeks"), rule.get("min_history")
        if not _integer(window, 1, 52):
            errors.append(f"{prefix}: window_weeks deve estar entre 1 e 52.")
        if not _integer(minimum, 1, 26):
            errors.append(f"{prefix}: min_history deve estar entre 1 e 26.")
        elif _number(window) and minimum > window:
            errors.append(f"{prefix}: min_history não pode superar window_weeks.")
        threshold = rule.get("threshold")
        if condition == "unanswered":
            if metric != "unanswered_messages":
                errors.append(f"{prefix}: unanswered exige a métrica unanswered_messages.")
            for key, maximum in (("threshold", 1000), ("days_threshold", 365)):
                value = rule.get(key)
                if value is None and rule.get("enabled") is False:
                    continue
                if not _integer(value, 1, maximum):
                    errors.append(f"{prefix}: {key} precisa ser aprovado como inteiro entre 1 e {maximum}.")
        elif condition in ("drop_pct", "increase_pct"):
            maximum = 100 if condition == "drop_pct" else 1000
            if not _number(threshold) or not 1 <= threshold <= maximum:
                errors.append(f"{prefix}: variação percentual deve estar entre 1 e {maximum}.")
        elif metric and (not _number(threshold) or not METRICS[metric][0] <= threshold <= METRICS[metric][1]):
            errors.append(f"{prefix}: limiar fora dos limites da métrica {metric}.")
        if condition != "unanswered" and "days_threshold" in rule:
            errors.append(f"{prefix}: days_threshold só se aplica a mensagens sem resposta.")
        samples = rule.get("min_samples")
        if samples is not None:
            if (not isinstance(samples, dict) or set(samples) != {"metric", "minimum"}
                    or not isinstance(samples.get("metric"), str) or samples.get("metric") not in METRICS
                    or not _integer(samples.get("minimum"), 1, 10000)):
                errors.append(f"{prefix}: min_samples deve definir métrica permitida e minimum inteiro entre 1 e 10000.")
        if metric == "skipped_hard_study_pct" and (not isinstance(samples, dict)
                or samples.get("metric") != "hard_study_sessions"
                or not _integer(samples.get("minimum"), 2, 10000)):
            errors.append(f"{prefix}: questões difíceis puladas exigem repetição em pelo menos duas sessões de estudo.")
        if rule.get("enabled") is True and metric and isinstance(condition, str) and (_number(threshold) or threshold is None):
            signature = (metric, condition, threshold)
            if signature in signatures:
                errors.append(f"{prefix}: regras equivalentes ou com prioridades conflitantes para a mesma métrica.")
            signatures.add(signature)
            enabled_rules.append(rule)
    for i, first in enumerate(enabled_rules):
        for second in enabled_rules[i + 1:]:
            if first["metric"] != second["metric"] or {first["condition"], second["condition"]} != {"gte", "lte"}:
                continue
            lower = first if first["condition"] == "gte" else second
            upper = second if first["condition"] == "gte" else first
            if _number(lower["threshold"]) and _number(upper["threshold"]) and lower["threshold"] <= upper["threshold"]:
                errors.append(f"Regras {first.get('id', '?')} e {second.get('id', '?')}: condições opostas se sobrepõem.")
    return errors


def _date(value):
    if not isinstance(value, str):
        return None
    try:
        result = date.fromisoformat(value)
        return result if result.isoformat() == value else None
    except ValueError:
        return None


def _value(record, metric):
    values = record.get("metrics", {})
    value = values.get(metric) if isinstance(values, dict) else None
    bounds = METRICS[metric]
    return value if _number(value) and bounds[0] <= value <= bounds[1] else None


def _baseline(records, before, rule):
    start = before - timedelta(weeks=rule["window_weeks"])
    eligible = [record for record in records
                if start <= _date(record["period"]) < before and _value(record, rule["metric"]) is not None]
    if len(eligible) < rule["min_history"]:
        return None, eligible
    return mean(_value(record, rule["metric"]) for record in eligible), eligible


def _comparison(value, baseline, rule):
    if rule["condition"] in ("gte", "unanswered"):
        return value >= rule["threshold"], None
    if rule["condition"] == "lte":
        return value <= rule["threshold"], None
    if baseline is None or baseline <= 0:
        return False, None
    change = ((baseline - value) if rule["condition"] == "drop_pct" else (value - baseline)) / baseline * 100
    return change + 1e-9 >= rule["threshold"], change


def _sample_ok(record, rule):
    requirement = rule.get("min_samples")
    if requirement is None:
        return True
    count = _value(record, requirement["metric"])
    return count is not None and count >= requirement["minimum"]


def _source_ids(records):
    return sorted({str(source) for record in records for source in (record.get("source_ids") or [])
                   if isinstance(source, (str, int)) and not isinstance(source, bool)})


def evaluate(current: dict, history: list[dict], config: dict | None = None) -> dict:
    """Classify facts using explicit, version-independent deterministic rules.

    A persistent change compares consecutive weeks to one baseline entirely
    before those weeks. Missing/zero baselines never manufacture a change. The
    simulator and production evaluator can safely share this pure function.
    """
    config = DEFAULT_CONFIG if config is None else config
    errors = validate_config(config)
    if errors:
        raise ValueError(" ".join(errors))
    if not isinstance(current, dict) or _date(current.get("period")) is None:
        raise ValueError("O período atual deve ser uma data ISO YYYY-MM-DD.")
    today = _date(current["period"])
    # A period is one observation. Replayed entries cannot inflate sample counts.
    periods = {}
    for item in history or []:
        if isinstance(item, dict) and _date(item.get("period")) is not None and _date(item["period"]) < today:
            periods[item["period"]] = item
    records = [periods[key] for key in sorted(periods)]
    evidence, missing, evaluated_rules = [], [], []
    persistent_count = config["aggregation"]["persistent_weeks"]
    for rule in config["rules"]:
        if not rule["enabled"]:
            continue
        metric, value = rule["metric"], _value(current, rule["metric"])
        if value is None:
            missing.append(f"{rule['id']}: valor atual ausente ou inválido ({metric}).")
            continue
        if not _sample_ok(current, rule):
            missing.append(f"{rule['id']}: amostra insuficiente para o mínimo de sessões configurado.")
            continue
        baseline, baseline_records, persistent_periods = None, [], []
        historical = rule["condition"] in ("drop_pct", "increase_pct")
        if historical:
            baseline, baseline_records = _baseline(records, today, rule)
            if baseline is None:
                missing.append(f"{rule['id']}: histórico insuficiente; exige {rule['min_history']} períodos na janela de {rule['window_weeks']} semanas.")
                continue
            if baseline <= 0:
                missing.append(f"{rule['id']}: linha de base zero; variação relativa indisponível.")
                continue
        second_value = None
        if rule["condition"] == "unanswered":
            second_value = _value(current, "oldest_unanswered_days")
            if second_value is None:
                missing.append(f"{rule['id']}: prazo da mensagem sem resposta indisponível.")
                continue
        evaluated_rules.append(rule["id"])
        triggered, change = _comparison(value, baseline, rule)
        if second_value is not None:
            triggered = triggered and second_value >= rule["days_threshold"]
        # Re-evaluate a possible persistent fall against a non-overlapping base.
        # This also preserves a fall that a moving mean could otherwise dilute.
        if historical:
            first_period = today - timedelta(weeks=persistent_count - 1)
            run = [periods.get((first_period + timedelta(weeks=offset)).isoformat())
                   for offset in range(persistent_count - 1)] + [current]
            fixed_baseline, fixed_records = _baseline(records, first_period, rule)
            if fixed_baseline is not None and fixed_baseline > 0 and all(
                item is not None and _value(item, metric) is not None and _sample_ok(item, rule)
                and _comparison(_value(item, metric), fixed_baseline, rule)[0] for item in run
            ):
                triggered = True
                baseline, baseline_records = fixed_baseline, fixed_records
                _, change = _comparison(value, baseline, rule)
                persistent_periods = [item["period"] for item in run]
        if not triggered:
            continue
        unit = METRICS[metric][2]
        if historical:
            direction = "queda" if rule["condition"] == "drop_pct" else "aumento"
            reason = f"{value:g} {unit}; referência própria {baseline:g} {unit}; {direction} de {change:.1f}% (limiar {rule['threshold']:g}%)."
        elif second_value is not None:
            reason = f"{value:g} mensagens sem resposta; a mais antiga há {second_value:g} dias; limiares {rule['threshold']:g} mensagens e {rule['days_threshold']:g} dias."
        else:
            operator = "≥" if rule["condition"] == "gte" else "≤"
            reason = f"{value:g} {unit}; condição aplicada: {operator} {rule['threshold']:g} {unit}."
        if persistent_periods:
            reason += f" Variação presente em {len(persistent_periods)} semanas consecutivas."
        observation_records = [periods[p] for p in persistent_periods if p in periods] + [current]
        evidence.append({
            "rule_id": rule["id"], "label": rule["label"], "metric": metric,
            "observed": value, "baseline": round(baseline, 6) if baseline is not None else None,
            "threshold": rule["threshold"], "weight": rule["weight"], "unit": unit,
            "condition": rule["condition"], "priority": rule["priority"],
            "precedence": rule.get("precedence", 0),
            "change_pct": round(change, 6) if change is not None else None,
            "window": {
                "current_period": current["period"], "weeks": rule["window_weeks"],
                "history_start": baseline_records[0]["period"] if baseline_records else None,
                "history_end": baseline_records[-1]["period"] if baseline_records else None,
                "baseline_periods": [item["period"] for item in baseline_records],
                "persistent_periods": persistent_periods,
            },
            "source_ids": _source_ids(baseline_records + observation_records),
            "current_source_ids": _source_ids([current]),
            "reason": reason,
            "rule_snapshot": copy.deepcopy(rule),
            "related_observed": {"oldest_unanswered_days": second_value} if second_value is not None else (
                {rule["min_samples"]["metric"]: _value(current, rule["min_samples"]["metric"])} if rule.get("min_samples") else {}
            ),
        })
    # Editable rule precedence resolves multiple matches for the same metric.
    # Ties prefer a strong trigger, then greatest weight, then stable rule ID.
    # All matched evidence remains available, including rules not aggregated.
    evidence.sort(key=lambda item: (-item["precedence"], -int(item["priority"]), -item["weight"], item["rule_id"]))
    selected = {}
    for item in evidence:
        item["applied"] = item["metric"] not in selected
        if item["applied"]:
            selected[item["metric"]] = item
        else:
            item["reason"] += f" Não agregada: precedência da regra {selected[item['metric']]['rule_id']} para esta mesma métrica."
    weights = {metric: item["weight"] for metric, item in selected.items()}
    score = sum(weights.values())
    persistent = sorted({item["metric"] for item in selected.values() if item["window"]["persistent_periods"]})
    aggregation = config["aggregation"]
    if any(item["priority"] for item in selected.values()):
        level = "prio"
    elif ((len(weights) >= aggregation["attention_min_distinct"] or persistent)
          and score >= aggregation["attention_min_weight"]):
        level = "att"
    elif len(weights) >= aggregation["observe_min_distinct"]:
        level = "obs"
    elif evaluated_rules:
        level = "ok"
    else:
        level = "unknown"
    return {
        "period": current["period"], "level": level, "evidence": evidence,
        "missing": missing, "score": score, "distinct_signals": len(weights),
        "persistent_signals": persistent, "evaluated_rules": evaluated_rules,
        "has_data": bool(evaluated_rules),
        "configuration_snapshot": copy.deepcopy(config),
    }
