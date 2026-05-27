from __future__ import annotations

from typing import Any


def assign_severities(
    records: list[dict[str, Any]],
    medium_threshold: float,
    high_threshold: float,
    min_consecutive: int,
) -> None:
    for record in records:
        record["severity"] = "none"

    _mark_runs(records, high_threshold, min_consecutive, "high")
    _mark_runs(records, medium_threshold, min_consecutive, "medium", preserve_higher=True)


def _mark_runs(
    records: list[dict[str, Any]],
    threshold: float,
    min_consecutive: int,
    severity: str,
    preserve_higher: bool = False,
) -> None:
    run_start: int | None = None
    for index, record in enumerate(records):
        if float(record["smoothed_frame_score"]) >= threshold:
            if run_start is None:
                run_start = index
            continue
        _apply_run(records, run_start, index, min_consecutive, severity, preserve_higher)
        run_start = None
    _apply_run(records, run_start, len(records), min_consecutive, severity, preserve_higher)


def _apply_run(
    records: list[dict[str, Any]],
    start: int | None,
    end: int,
    min_consecutive: int,
    severity: str,
    preserve_higher: bool,
) -> None:
    if start is None or end - start < min_consecutive:
        return
    for record in records[start:end]:
        if preserve_higher and record["severity"] == "high":
            continue
        record["severity"] = severity


def build_alerts(
    dataset: str,
    records_by_video: dict[str, list[dict[str, Any]]],
    min_consecutive: int,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for video_id, records in records_by_video.items():
        segment: list[dict[str, Any]] = []
        active_severity = "none"
        for record in records:
            severity = str(record["severity"])
            if severity == "none":
                _flush_segment(alerts, dataset, video_id, segment, active_severity, min_consecutive)
                segment = []
                active_severity = "none"
                continue
            if segment and severity != active_severity:
                _flush_segment(alerts, dataset, video_id, segment, active_severity, min_consecutive)
                segment = []
            active_severity = severity
            segment.append(record)
        _flush_segment(alerts, dataset, video_id, segment, active_severity, min_consecutive)
    return alerts


def _flush_segment(
    alerts: list[dict[str, Any]],
    dataset: str,
    video_id: str,
    segment: list[dict[str, Any]],
    severity: str,
    min_consecutive: int,
) -> None:
    if not segment or severity == "none":
        return

    peak = max(segment, key=lambda item: float(item["smoothed_frame_score"]))
    top_entries = list(peak.get("top_entries", []))
    top_cells = [entry["cell_id"] for entry in top_entries]
    reasons = _reasons(peak, severity, min_consecutive)
    alerts.append(
        {
            "dataset": dataset,
            "video_id": video_id,
            "start_frame_id": int(segment[0]["frame_id"]),
            "end_frame_id": int(segment[-1]["frame_id"]),
            "max_score": float(peak["smoothed_frame_score"]),
            "severity": severity,
            "top_cells": top_cells,
            "reasons": reasons,
        }
    )


def _reasons(record: dict[str, Any], severity: str, min_consecutive: int) -> list[str]:
    top_entries = list(record.get("top_entries", []))
    reasons: list[str] = []
    if top_entries:
        top = top_entries[0]
        threshold = float(top["cluster_threshold"])
        distance = float(top["cluster_distance"])
        relation = "above" if distance > threshold else "within"
        reasons.append(
            f"cell={top['cell_id']} has cluster_distance={distance:.6f} "
            f"{relation} train threshold={threshold:.6f}"
        )
        nearest = int(top["nearest_cluster"])
        if nearest >= 0:
            reasons.append(f"nearest normal cluster is C{nearest}")
        for reason in top.get("token_rule_reasons", []):
            if reason:
                reasons.append(str(reason))
    reasons.append(
        f"smoothed frame score met {severity} threshold for at least "
        f"{min_consecutive} consecutive frames"
    )
    return reasons
