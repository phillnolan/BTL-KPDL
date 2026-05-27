from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .config import AnomalyConfig
from .io import read_json, write_json

IMPORTANT_RULE_TAGS = ("motion", "density", "direction", "cluster", "brightness", "brightness_delta")
POSITION_RULE_TAGS = ("cell", "cell_row", "cell_col")


@dataclass(frozen=True)
class RuleEvidenceResult:
    records: list[dict[str, Any]]
    evidence_by_id: dict[str, dict[str, Any]]
    min_support: float
    rule_dir: Path | None
    requested: bool
    active: bool
    warnings: list[str]


def write_rule_evidence_index(
    config: AnomalyConfig,
    output_dir: str | Path,
    rules_dir: str | Path | None = None,
    requested: bool = True,
) -> RuleEvidenceResult:
    output_path = Path(output_dir)
    warnings: list[str] = []
    if not requested:
        write_json(output_path / "rule_evidence_index.json", [])
        return RuleEvidenceResult(
            records=[],
            evidence_by_id={},
            min_support=config.rules.min_support,
            rule_dir=None,
            requested=False,
            active=False,
            warnings=["rule evidence skipped because rules were disabled for this run"],
        )

    rule_path = Path(rules_dir) if rules_dir is not None else config.rules.output_root / config.dataset
    manifest_path = rule_path / "rule_manifest.json"
    rules_path = rule_path / "rules.json"
    missing = [str(path) for path in (manifest_path, rules_path) if not path.exists()]
    if missing:
        warnings.append(f"rule evidence unavailable; missing artifact file(s): {', '.join(missing)}")
        write_json(output_path / "rule_evidence_index.json", [])
        return RuleEvidenceResult(
            records=[],
            evidence_by_id={},
            min_support=config.rules.min_support,
            rule_dir=rule_path,
            requested=True,
            active=False,
            warnings=warnings,
        )

    manifest = read_json(manifest_path)
    if manifest.get("dataset") != config.dataset:
        warnings.append(
            f"rule evidence skipped because rule dataset={manifest.get('dataset')!r} "
            f"does not match config dataset={config.dataset!r}"
        )
        write_json(output_path / "rule_evidence_index.json", [])
        return RuleEvidenceResult(
            records=[],
            evidence_by_id={},
            min_support=config.rules.min_support,
            rule_dir=rule_path,
            requested=True,
            active=False,
            warnings=warnings,
        )
    if list(manifest.get("feature_columns", [])) != config.feature_columns:
        warnings.append("rule evidence skipped because rule feature_columns do not match config")
        write_json(output_path / "rule_evidence_index.json", [])
        return RuleEvidenceResult(
            records=[],
            evidence_by_id={},
            min_support=config.rules.min_support,
            rule_dir=rule_path,
            requested=True,
            active=False,
            warnings=warnings,
        )

    raw_rules = read_json(rules_path)
    min_support = _probability(manifest.get("min_support"), config.rules.min_support)
    records = [_rule_record(rule, index) for index, rule in enumerate(raw_rules, start=1)]
    records.sort(key=_rule_sort_key)
    write_json(output_path / "rule_evidence_index.json", records)
    return RuleEvidenceResult(
        records=records,
        evidence_by_id={str(record["rule_id"]): record for record in records},
        min_support=min_support,
        rule_dir=rule_path,
        requested=True,
        active=True,
        warnings=warnings,
    )


def load_cluster_profile_index(payload: Mapping[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    index: dict[str, dict[str, dict[str, Any]]] = {}
    for cell in payload.get("cells", []):
        cell_id = str(cell.get("cell_id", ""))
        if not cell_id:
            continue
        clusters = index.setdefault(cell_id, {})
        for cluster in cell.get("clusters", []):
            cluster_id = str(cluster.get("cluster_id", ""))
            if cluster_id:
                clusters[cluster_id] = dict(cluster)
    return index


def load_frame_scores(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "dataset": str(row.get("dataset", "")),
                    "split": str(row.get("split", "")),
                    "video_id": str(row.get("video_id", "")),
                    "frame_id": _int(row.get("frame_id")),
                    "frame_score": _float(row.get("frame_score")),
                    "smoothed_frame_score": _float(row.get("smoothed_frame_score")),
                    "severity": str(row.get("severity", "none")),
                    "top_cells": _json_list(row.get("top_cells", "")),
                }
            )
    return rows


def load_alerts(path: str | Path) -> list[dict[str, Any]]:
    if not Path(path).exists():
        return []
    alerts = read_json(path)
    normalized: list[dict[str, Any]] = []
    for index, alert in enumerate(alerts, start=1):
        item = dict(alert)
        item["start_frame_id"] = _int(item.get("start_frame_id"))
        item["end_frame_id"] = _int(item.get("end_frame_id"))
        item["max_score"] = _float(item.get("max_score"))
        item["alert_id"] = f"{item.get('video_id')}:{item['start_frame_id']}-{item['end_frame_id']}"
        item["rank"] = index
        normalized.append(item)
    return normalized


def load_cell_scores_for_frames(
    path: str | Path,
    selected_keys: set[tuple[str, int]],
) -> dict[tuple[str, int], list[dict[str, Any]]]:
    scores: dict[tuple[str, int], list[dict[str, Any]]] = {key: [] for key in selected_keys}
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (str(row.get("video_id", "")), _int(row.get("center_frame_id")))
            if key not in scores:
                continue
            scores[key].append(_cell_score_row(row))
    for rows in scores.values():
        rows.sort(key=lambda item: float(item.get("cell_score", 0.0)), reverse=True)
    return scores


def build_explanation_record(
    dataset: str,
    case: Mapping[str, Any],
    cell_rows: list[dict[str, Any]],
    cluster_index: Mapping[str, Mapping[str, dict[str, Any]]],
    rule_evidence: RuleEvidenceResult,
    overlay: Mapping[str, Any],
    top_cell_limit: int = 3,
) -> dict[str, Any]:
    top_cells = [
        _explain_cell(row, cluster_index, rule_evidence)
        for row in cell_rows[: max(1, top_cell_limit)]
    ]
    frame_id = _int(case.get("frame_id"))
    record = {
        "dataset": dataset,
        "case_id": str(case.get("case_id", "")),
        "selection_type": str(case.get("selection_type", "")),
        "video_id": str(case.get("video_id", "")),
        "frame_id": frame_id,
        "alert_range": _alert_range(case),
        "score": {
            "frame_score": _bounded_float(case.get("frame_score")),
            "smoothed_frame_score": _bounded_float(case.get("smoothed_frame_score")),
            "severity": str(case.get("severity", "none")),
        },
        "top_cells": top_cells,
        "overlay": dict(overlay),
        "manual_review": {
            "label": "TBD",
            "notes": "TBD",
        },
    }
    record["plain_language"] = _case_plain_language(record)
    return record


def _cell_score_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "dataset": str(row.get("dataset", "")),
        "split": str(row.get("split", "")),
        "video_id": str(row.get("video_id", "")),
        "cube_id": str(row.get("cube_id", "")),
        "start_frame_id": _int(row.get("start_frame_id")),
        "end_frame_id": _int(row.get("end_frame_id")),
        "center_frame_id": _int(row.get("center_frame_id")),
        "cell_id": str(row.get("cell_id", "")),
        "cell_row": _int(row.get("cell_row")),
        "cell_col": _int(row.get("cell_col")),
        "nearest_cluster": _int(row.get("nearest_cluster"), default=-1),
        "cluster_distance": _float(row.get("cluster_distance")),
        "cluster_threshold": _float(row.get("cluster_threshold")),
        "cluster_distance_score": _bounded_float(row.get("cluster_distance_score")),
        "temporal_change_score": _bounded_float(row.get("temporal_change_score")),
        "cell_score": _bounded_float(row.get("cell_score")),
        "tokens": _json_list(row.get("tokens", "")),
        "rare_token_score": _bounded_float(row.get("rare_token_score")),
        "rare_itemset": _json_list(row.get("rare_itemset", "")),
        "rare_itemset_support": _bounded_float(row.get("rare_itemset_support")),
        "rule_violation_score": _bounded_float(row.get("rule_violation_score")),
        "violated_rules": _json_list(row.get("violated_rules", "")),
        "token_rule_reasons": _json_list(row.get("token_rule_reasons", "")),
    }


def _explain_cell(
    row: Mapping[str, Any],
    cluster_index: Mapping[str, Mapping[str, dict[str, Any]]],
    rule_evidence: RuleEvidenceResult,
) -> dict[str, Any]:
    cell_id = str(row.get("cell_id", ""))
    cluster_id = _cluster_label(row.get("nearest_cluster"))
    profile = dict(cluster_index.get(cell_id, {}).get(cluster_id, {}))
    tokens = [str(token) for token in row.get("tokens", [])]
    violated_rules = [str(rule_id) for rule_id in row.get("violated_rules", [])]
    rule_records = [rule_evidence.evidence_by_id[rule_id] for rule_id in violated_rules if rule_id in rule_evidence.evidence_by_id]
    distance = _float(row.get("cluster_distance"))
    threshold = _float(row.get("cluster_threshold"))
    rare_itemset = _rare_itemset(row, rule_evidence.min_support)
    explained = {
        "cell_id": cell_id,
        "cell_score": _bounded_float(row.get("cell_score")),
        "nearest_cluster": cluster_id,
        "cluster_profile": _profile_fragment(profile),
        "observed_tokens": tokens,
        "cluster_distance": {
            "distance": distance,
            "threshold": threshold,
            "above_threshold": bool(distance > threshold if threshold > 0.0 else distance > 0.0),
            "score": _bounded_float(row.get("cluster_distance_score")),
        },
        "temporal_change_score": _bounded_float(row.get("temporal_change_score")),
        "rare_itemset": rare_itemset,
        "rare_token_score": _bounded_float(row.get("rare_token_score")),
        "rule_violation_score": _bounded_float(row.get("rule_violation_score")),
        "violated_rules": violated_rules,
        "rule_evidence": rule_records,
        "raw_token_rule_reasons": [str(reason) for reason in row.get("token_rule_reasons", [])],
    }
    explained["plain_language"] = _cell_plain_language(explained, profile)
    return explained


def _profile_fragment(profile: Mapping[str, Any]) -> dict[str, Any]:
    if not profile:
        return {
            "summary": "No cluster profile was available for this cell/cluster.",
            "tokens": [],
            "support": None,
            "support_count": None,
            "interpretation_status": "missing_profile",
        }
    return {
        "summary": str(profile.get("summary", "")),
        "tokens": [str(token) for token in profile.get("tokens", [])],
        "support": _nullable_probability(profile.get("support")),
        "support_count": profile.get("support_count"),
        "interpretation_status": str(profile.get("interpretation_status", "")),
    }


def _rare_itemset(row: Mapping[str, Any], min_support: float) -> dict[str, Any] | None:
    items = [str(item) for item in row.get("rare_itemset", [])]
    if not items:
        return None
    support = _bounded_float(row.get("rare_itemset_support"))
    return {
        "items": items,
        "support": support,
        "min_support": min_support,
        "below_min_support": support < min_support,
    }


def _cell_plain_language(explained: Mapping[str, Any], profile: Mapping[str, Any]) -> list[str]:
    cell_id = str(explained.get("cell_id", ""))
    cluster_id = str(explained.get("nearest_cluster", "unknown"))
    distance_info = dict(explained.get("cluster_distance", {}))
    distance = _float(distance_info.get("distance"))
    threshold = _float(distance_info.get("threshold"))
    above = bool(distance_info.get("above_threshold"))
    lines: list[str] = []
    if above:
        lines.append(
            f"Cell {cell_id} is far from nearest normal cluster {cluster_id}: "
            f"distance {distance:.4f} exceeds threshold {threshold:.4f}."
        )
    else:
        lines.append(
            f"Cell {cell_id} is nearest to normal cluster {cluster_id}; "
            f"cluster distance {distance:.4f} is within threshold {threshold:.4f}."
        )

    summary = str(profile.get("summary", "")).strip()
    if summary:
        lines.append(f"Nearest normal pattern: {summary}.")

    lines.extend(_token_difference_reasons(explained, profile))
    rare = explained.get("rare_itemset")
    if isinstance(rare, Mapping) and rare.get("below_min_support"):
        lines.append(
            "Observed token combination {{{items}}} has support {support:.4f}, below min_support {minimum:.4f}.".format(
                items=", ".join(str(item) for item in rare.get("items", [])),
                support=_float(rare.get("support")),
                minimum=_float(rare.get("min_support")),
            )
        )

    for rule in explained.get("rule_evidence", [])[:2]:
        lines.append(f"Violated {rule.get('rule_id')}: {rule.get('plain_language')}")

    if _bounded_float(explained.get("temporal_change_score")) >= 0.25:
        lines.append(
            f"Temporal change score is {_bounded_float(explained.get('temporal_change_score')):.4f}, "
            "so the cell also changed sharply from nearby cubes."
        )

    if not lines:
        lines.append(f"Cell {cell_id} contributed score {_bounded_float(explained.get('cell_score')):.4f}.")
    return lines


def _token_difference_reasons(explained: Mapping[str, Any], profile: Mapping[str, Any]) -> list[str]:
    observed = _prefix_map([str(token) for token in explained.get("observed_tokens", [])])
    normal = _prefix_map([str(token) for token in profile.get("tokens", [])])
    reasons: list[str] = []
    for prefix in IMPORTANT_RULE_TAGS:
        observed_token = observed.get(prefix)
        normal_token = normal.get(prefix)
        if not observed_token or not normal_token or observed_token == normal_token:
            continue
        reasons.append(f"Observed {observed_token} differs from cluster profile {normal_token}.")
    return reasons


def _case_plain_language(record: Mapping[str, Any]) -> list[str]:
    cells = list(record.get("top_cells", []))
    if not cells:
        return ["No cell score rows were available for this selected frame."]
    first = dict(cells[0])
    summary = [
        "Top evidence comes from cell {cell} with score {score:.4f} near cluster {cluster}.".format(
            cell=first.get("cell_id"),
            score=_bounded_float(first.get("cell_score")),
            cluster=first.get("nearest_cluster"),
        )
    ]
    first_reasons = list(first.get("plain_language", []))
    summary.extend(str(reason) for reason in first_reasons[:3])
    return summary


def _alert_range(case: Mapping[str, Any]) -> dict[str, int] | None:
    start = case.get("alert_start_frame_id")
    end = case.get("alert_end_frame_id")
    if start is None or end is None:
        return None
    return {"start_frame_id": _int(start), "end_frame_id": _int(end)}


def _rule_record(rule: Mapping[str, Any], index: int) -> dict[str, Any]:
    antecedent = [str(item) for item in rule.get("antecedent", [])]
    consequent = [str(item) for item in rule.get("consequent", [])]
    tags = _evidence_tags(antecedent + consequent)
    rule_id = str(rule.get("rule_id") or f"R{index:04d}")
    support = _bounded_float(rule.get("support"))
    confidence = _bounded_float(rule.get("confidence"))
    lift = _float(rule.get("lift"))
    is_context_only = not any(tag in IMPORTANT_RULE_TAGS for tag in tags)
    warning = "low_support_rule" if support < 0.01 else None
    return {
        "rule_id": rule_id,
        "antecedent": antecedent,
        "consequent": consequent,
        "support": support,
        "confidence": confidence,
        "lift": lift,
        "evidence_tags": tags,
        "is_context_only": is_context_only,
        "warning": warning,
        "plain_language": _plain_rule(rule_id, antecedent, consequent, confidence, lift),
    }


def _rule_sort_key(record: Mapping[str, Any]) -> tuple[int, float, float, str]:
    important = 0 if not record.get("is_context_only") else 1
    return (important, -_float(record.get("confidence")), -_float(record.get("lift")), str(record.get("rule_id")))


def _evidence_tags(items: list[str]) -> list[str]:
    tags: list[str] = []
    for item in items:
        if "=" not in item:
            continue
        prefix = item.split("=", 1)[0]
        if prefix in tags:
            continue
        tags.append(prefix)
    priority = list(IMPORTANT_RULE_TAGS) + list(POSITION_RULE_TAGS)
    return sorted(tags, key=lambda tag: priority.index(tag) if tag in priority else len(priority))


def _plain_rule(
    rule_id: str,
    antecedent: list[str],
    consequent: list[str],
    confidence: float,
    lift: float,
) -> str:
    antecedent_text = ", ".join(antecedent) if antecedent else "this context"
    consequent_text = ", ".join(consequent) if consequent else "the consequent"
    return (
        f"When {{{antecedent_text}}} appears in normal training data, "
        f"it usually also has {{{consequent_text}}} "
        f"(confidence {confidence:.2f}, lift {lift:.2f}; {rule_id})."
    )


def _prefix_map(tokens: list[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            continue
        prefix = token.split("=", 1)[0]
        mapped[prefix] = token
    return mapped


def _json_list(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    try:
        payload = json.loads(str(raw))
    except json.JSONDecodeError:
        return [item.strip() for item in str(raw).split(",") if item.strip()]
    if isinstance(payload, list):
        return [str(item) for item in payload]
    return []


def _cluster_label(raw: Any) -> str:
    value = _int(raw, default=-1)
    return "unknown" if value < 0 else f"C{value}"


def _int(raw: Any, default: int = 0) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _float(raw: Any, default: float = 0.0) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(value):
        return default
    return value


def _bounded_float(raw: Any, default: float = 0.0) -> float:
    return float(np.clip(_float(raw, default), 0.0, 1.0))


def _probability(raw: Any, default: float) -> float:
    return _bounded_float(raw, default)


def _nullable_probability(raw: Any) -> float | None:
    if raw is None:
        return None
    return _bounded_float(raw)
