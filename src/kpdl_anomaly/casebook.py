from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from kpdl_preprocess.config import ConfigError
from kpdl_preprocess.utils import ensure_dir

from .cluster_profiles import ANALYSIS_SCHEMA_VERSION
from .config import AnomalyConfig
from .explanations import (
    RuleEvidenceResult,
    build_explanation_record,
    load_alerts,
    load_cell_scores_for_frames,
    load_cluster_profile_index,
    load_frame_scores,
)
from .io import read_json, write_json

DEFAULT_CASE_LIMIT = 20
TOP_CELLS_PER_CASE = 3


def generate_casebook(
    config: AnomalyConfig,
    result_dir: str | Path,
    output_dir: str | Path,
    cluster_profiles: Mapping[str, Any],
    rule_evidence: RuleEvidenceResult,
    model_dir: str | Path,
    visualizations_dir: str | Path | None = None,
    top_alerts: int | None = DEFAULT_CASE_LIMIT,
    top_frames: int | None = None,
    video_id: str | None = None,
    start_frame: int | None = None,
    end_frame: int | None = None,
) -> dict[str, Any]:
    result_path = Path(result_dir)
    output_path = ensure_dir(output_dir)
    frame_scores_path = result_path / "frame_scores.csv"
    cell_scores_path = result_path / "cell_scores.csv"
    alerts_path = result_path / "alerts.json"
    missing = [str(path) for path in (frame_scores_path, cell_scores_path) if not path.exists()]
    if missing:
        raise ConfigError(f"Required result file(s) not found: {', '.join(missing)}")

    warnings: list[str] = []
    frame_scores = load_frame_scores(frame_scores_path)
    alerts = load_alerts(alerts_path)
    selected_cases = select_cases(
        frame_scores=frame_scores,
        alerts=alerts,
        top_alerts=top_alerts,
        top_frames=top_frames,
        video_id=video_id,
        start_frame=start_frame,
        end_frame=end_frame,
    )
    if not selected_cases:
        warnings.append("no alert or frame score cases matched the selection filters")

    selected_keys = {(str(case["video_id"]), int(case["frame_id"])) for case in selected_cases}
    cell_scores = load_cell_scores_for_frames(cell_scores_path, selected_keys) if selected_keys else {}
    cluster_index = load_cluster_profile_index(cluster_profiles)
    visualization_index = _load_visualization_index(config, visualizations_dir, warnings)

    case_records: list[dict[str, Any]] = []
    for case in selected_cases:
        key = (str(case["video_id"]), int(case["frame_id"]))
        overlay = _overlay_for_case(config, case, visualization_index, visualizations_dir, warnings)
        case_records.append(
            build_explanation_record(
                dataset=config.dataset,
                case=case,
                cell_rows=cell_scores.get(key, []),
                cluster_index=cluster_index,
                rule_evidence=rule_evidence,
                overlay=overlay,
                top_cell_limit=TOP_CELLS_PER_CASE,
            )
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    warnings.extend(rule_evidence.warnings)
    warnings.extend(str(warning) for warning in cluster_profiles.get("warnings", []))
    warnings = _dedupe(warnings)
    casebook = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "dataset": config.dataset,
        "generated_at": generated_at,
        "config_path": str(config.config_path),
        "model_dir": str(model_dir),
        "rule_dir": str(rule_evidence.rule_dir) if rule_evidence.rule_dir is not None else None,
        "result_dir": str(result_path),
        "visualizations_dir": str(visualizations_dir) if visualizations_dir is not None else None,
        "selection": {
            "top_alerts": top_alerts,
            "top_frames": top_frames,
            "video_id": video_id,
            "start_frame": start_frame,
            "end_frame": end_frame,
        },
        "cases": case_records,
        "warnings": warnings,
    }
    write_json(output_path / "alert_casebook.json", casebook)
    write_casebook_markdown(output_path / "alert_casebook.md", casebook)
    manifest = _analysis_manifest(
        config=config,
        generated_at=generated_at,
        output_path=output_path,
        model_dir=model_dir,
        result_dir=result_path,
        visualizations_dir=visualizations_dir,
        casebook=casebook,
        cluster_profiles=cluster_profiles,
        rule_evidence=rule_evidence,
    )
    write_json(output_path / "analysis_manifest.json", manifest)
    return {
        "casebook": casebook,
        "manifest": manifest,
    }


def select_cases(
    frame_scores: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    top_alerts: int | None,
    top_frames: int | None,
    video_id: str | None,
    start_frame: int | None,
    end_frame: int | None,
) -> list[dict[str, Any]]:
    filtered_frames = [
        frame
        for frame in frame_scores
        if _matches_frame_filter(frame, video_id=video_id, start_frame=start_frame, end_frame=end_frame)
    ]
    frames_by_video: dict[str, list[dict[str, Any]]] = {}
    for frame in filtered_frames:
        frames_by_video.setdefault(str(frame["video_id"]), []).append(frame)
    for rows in frames_by_video.values():
        rows.sort(key=lambda item: int(item["frame_id"]))

    cases: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    if top_alerts is not None and top_alerts > 0:
        ranked_alerts = [
            alert
            for alert in alerts
            if _matches_alert_filter(alert, video_id=video_id, start_frame=start_frame, end_frame=end_frame)
        ]
        ranked_alerts.sort(key=lambda item: float(item.get("max_score", 0.0)), reverse=True)
        for alert in ranked_alerts[:top_alerts]:
            peak = _peak_frame_for_alert(frames_by_video.get(str(alert.get("video_id")), []), alert)
            if peak is None:
                continue
            key = (str(peak["video_id"]), int(peak["frame_id"]))
            if key in seen:
                continue
            seen.add(key)
            cases.append(_case_from_frame(peak, "alert_peak", len(cases) + 1, alert))

    if top_frames is not None and top_frames > 0:
        _append_top_frames(cases, seen, filtered_frames, top_frames)
    elif not cases:
        _append_top_frames(cases, seen, filtered_frames, DEFAULT_CASE_LIMIT)

    for index, case in enumerate(cases, start=1):
        case["case_id"] = f"Case {index:03d}"
    return cases


def write_casebook_markdown(path: str | Path, payload: Mapping[str, Any]) -> None:
    cases = list(payload.get("cases", []))
    lines = [
        f"# Alert Casebook - {payload.get('dataset')}",
        "",
        "## Summary",
        "",
        f"- Result dir: `{payload.get('result_dir')}`",
        f"- Model dir: `{payload.get('model_dir')}`",
        f"- Rule dir: `{payload.get('rule_dir')}`",
        f"- Cases: `{len(cases)}`",
        f"- Warnings: `{len(payload.get('warnings', []))}`",
        "",
    ]
    warnings = list(payload.get("warnings", []))
    if warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")

    lines.extend(["## Cases", ""])
    if not cases:
        lines.append("No cases were selected from the available alert/frame score artifacts.")
    for case in cases:
        lines.extend(_case_markdown(case))
    lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _append_top_frames(
    cases: list[dict[str, Any]],
    seen: set[tuple[str, int]],
    frames: list[dict[str, Any]],
    limit: int,
) -> None:
    candidates = sorted(frames, key=lambda item: float(item.get("smoothed_frame_score", 0.0)), reverse=True)
    for frame in candidates:
        if len([case for case in cases if case["selection_type"] == "top_frame"]) >= limit:
            break
        key = (str(frame["video_id"]), int(frame["frame_id"]))
        if key in seen:
            continue
        seen.add(key)
        cases.append(_case_from_frame(frame, "top_frame", len(cases) + 1, None))


def _case_from_frame(
    frame: Mapping[str, Any],
    selection_type: str,
    rank: int,
    alert: Mapping[str, Any] | None,
) -> dict[str, Any]:
    case = {
        "case_id": f"Case {rank:03d}",
        "selection_type": selection_type,
        "dataset": str(frame.get("dataset", "")),
        "video_id": str(frame.get("video_id", "")),
        "frame_id": int(frame.get("frame_id", 0)),
        "frame_score": float(frame.get("frame_score", 0.0)),
        "smoothed_frame_score": float(frame.get("smoothed_frame_score", 0.0)),
        "severity": str(frame.get("severity", "none")),
        "top_cells": list(frame.get("top_cells", [])),
        "rank": rank,
    }
    if alert is not None:
        case.update(
            {
                "alert_id": str(alert.get("alert_id", "")),
                "alert_start_frame_id": int(alert.get("start_frame_id", 0)),
                "alert_end_frame_id": int(alert.get("end_frame_id", 0)),
                "alert_max_score": float(alert.get("max_score", 0.0)),
                "alert_reasons": list(alert.get("reasons", [])),
            }
        )
    return case


def _peak_frame_for_alert(frames: list[dict[str, Any]], alert: Mapping[str, Any]) -> dict[str, Any] | None:
    start = int(alert.get("start_frame_id", 0))
    end = int(alert.get("end_frame_id", 0))
    in_range = [frame for frame in frames if start <= int(frame["frame_id"]) <= end]
    if not in_range:
        return None
    return max(in_range, key=lambda item: float(item.get("smoothed_frame_score", 0.0)))


def _matches_frame_filter(
    frame: Mapping[str, Any],
    video_id: str | None,
    start_frame: int | None,
    end_frame: int | None,
) -> bool:
    frame_id = int(frame.get("frame_id", 0))
    return (
        (video_id is None or str(frame.get("video_id")) == video_id)
        and (start_frame is None or frame_id >= start_frame)
        and (end_frame is None or frame_id <= end_frame)
    )


def _matches_alert_filter(
    alert: Mapping[str, Any],
    video_id: str | None,
    start_frame: int | None,
    end_frame: int | None,
) -> bool:
    if video_id is not None and str(alert.get("video_id")) != video_id:
        return False
    alert_start = int(alert.get("start_frame_id", 0))
    alert_end = int(alert.get("end_frame_id", 0))
    if start_frame is not None and alert_end < start_frame:
        return False
    if end_frame is not None and alert_start > end_frame:
        return False
    return True


def _load_visualization_index(
    config: AnomalyConfig,
    visualizations_dir: str | Path | None,
    warnings: list[str],
) -> dict[tuple[str, str], dict[str, Any]]:
    if visualizations_dir is None:
        warnings.append("visualization directory not provided; overlay paths will be empty")
        return {}
    index_path = Path(visualizations_dir) / "visualization_index.json"
    if not index_path.exists():
        warnings.append(f"visualization index missing: {index_path}")
        return {}
    records = read_json(index_path)
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            continue
        video_id = str(record.get("video_id", ""))
        frame_id = int(record.get("frame_id", 0))
        normalized = dict(record)
        image_path = normalized.get("image_path")
        if image_path:
            normalized["image_path"] = _existing_display_path(image_path, config.project_root, warnings)
        index[(video_id, f"frame:{frame_id}")] = normalized
        alert_id = normalized.get("alert_id")
        if alert_id:
            index[(video_id, f"alert:{alert_id}")] = normalized
    return index


def _overlay_for_case(
    config: AnomalyConfig,
    case: Mapping[str, Any],
    visualization_index: Mapping[tuple[str, str], Mapping[str, Any]],
    visualizations_dir: str | Path | None,
    warnings: list[str],
) -> dict[str, Any]:
    video_id = str(case.get("video_id", ""))
    frame_key = (video_id, f"frame:{int(case.get('frame_id', 0))}")
    alert_key = (video_id, f"alert:{case.get('alert_id')}")
    record = dict(visualization_index.get(frame_key, {}) or visualization_index.get(alert_key, {}))
    image_path = record.get("image_path")
    relative_path = record.get("relative_path")
    video_path = None
    if visualizations_dir is not None:
        candidate = Path(visualizations_dir) / "videos" / f"{case.get('video_id')}_overlay.mp4"
        if candidate.exists():
            video_path = _display_path(candidate, config.project_root)
        if not image_path and case.get("alert_start_frame_id") is not None:
            fallback = _alert_image_fallback(config, case, Path(visualizations_dir))
            if fallback is not None:
                image_path = fallback["image_path"]
                relative_path = fallback["relative_path"]
    if not image_path and visualizations_dir is not None:
        warnings.append(f"overlay image not found for {case.get('video_id')} frame {case.get('frame_id')}")
    return {
        "image_path": image_path,
        "video_path": video_path,
        "relative_path": relative_path,
    }


def _alert_image_fallback(
    config: AnomalyConfig,
    case: Mapping[str, Any],
    visualizations_dir: Path,
) -> dict[str, str] | None:
    alert_dir = visualizations_dir / "alerts"
    if not alert_dir.exists():
        return None
    video_id = str(case.get("video_id", ""))
    start = int(case.get("alert_start_frame_id", 0))
    end = int(case.get("alert_end_frame_id", 0))
    candidates = []
    for path in sorted(alert_dir.glob(f"{video_id}_*_peak.*")):
        match = re.match(rf"{re.escape(video_id)}_(\d+)_(\d+)_peak\.", path.name)
        if not match:
            continue
        image_start = int(match.group(1))
        image_end = int(match.group(2))
        overlaps = image_start <= end and image_end >= start
        if overlaps:
            overlap_size = min(end, image_end) - max(start, image_start) + 1
            candidates.append((overlap_size, -abs(image_start - start), path))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    path = candidates[0][2]
    return {
        "image_path": _display_path(path, config.project_root),
        "relative_path": str(path.relative_to(visualizations_dir)).replace("\\", "/"),
    }


def _existing_display_path(raw_path: str | Path, project_root: str | Path, warnings: list[str]) -> str:
    path = Path(raw_path)
    candidate = path if path.is_absolute() else Path(project_root) / path
    if candidate.exists():
        return _display_path(candidate, project_root)
    warnings.append(f"visualization path from index does not exist: {raw_path}")
    return str(raw_path).replace("\\", "/")


def _analysis_manifest(
    config: AnomalyConfig,
    generated_at: str,
    output_path: Path,
    model_dir: str | Path,
    result_dir: str | Path,
    visualizations_dir: str | Path | None,
    casebook: Mapping[str, Any],
    cluster_profiles: Mapping[str, Any],
    rule_evidence: RuleEvidenceResult,
) -> dict[str, Any]:
    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "dataset": config.dataset,
        "generated_at": generated_at,
        "config_path": str(config.config_path),
        "inputs": {
            "model_dir": str(model_dir),
            "rule_dir": str(rule_evidence.rule_dir) if rule_evidence.rule_dir is not None else None,
            "result_dir": str(result_dir),
            "visualizations_dir": str(visualizations_dir) if visualizations_dir is not None else None,
        },
        "outputs": {
            "cluster_profiles_json": str(output_path / "cluster_profiles.json"),
            "cluster_profiles_md": str(output_path / "cluster_profiles.md"),
            "rule_evidence_index_json": str(output_path / "rule_evidence_index.json"),
            "alert_casebook_json": str(output_path / "alert_casebook.json"),
            "alert_casebook_md": str(output_path / "alert_casebook.md"),
            "analysis_manifest_json": str(output_path / "analysis_manifest.json"),
        },
        "counts": {
            "cluster_profile_cells": int(cluster_profiles.get("num_cells", 0)),
            "cluster_profiles": int(cluster_profiles.get("num_clusters", 0)),
            "rule_evidence": len(rule_evidence.records),
            "cases": len(casebook.get("cases", [])),
        },
        "warnings": list(casebook.get("warnings", [])),
    }


def _case_markdown(case: Mapping[str, Any]) -> list[str]:
    score = dict(case.get("score", {}))
    overlay = dict(case.get("overlay", {}))
    top_cells = [str(cell.get("cell_id")) for cell in case.get("top_cells", [])]
    lines = [
        f"### {case.get('case_id')} - {case.get('video_id')} frame {case.get('frame_id')}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Selection | `{case.get('selection_type')}` |",
        f"| Score | `{float(score.get('smoothed_frame_score', 0.0)):.4f}` |",
        f"| Severity | `{score.get('severity')}` |",
        f"| Top cells | `{', '.join(top_cells)}` |",
        f"| Overlay | `{overlay.get('image_path') or ''}` |",
        "| Manual label | `TBD` |",
        "",
        "Cluster/rule evidence:",
        "",
    ]
    for cell in case.get("top_cells", []):
        profile = dict(cell.get("cluster_profile", {}))
        lines.append(
            f"- cell={cell.get('cell_id')} nearest {cell.get('nearest_cluster')}: {profile.get('summary', '')}"
        )
        observed = ", ".join(str(token) for token in cell.get("observed_tokens", [])[:8])
        if observed:
            lines.append(f"  observed tokens: `{observed}`")
        rare = cell.get("rare_itemset")
        if isinstance(rare, Mapping):
            items = ", ".join(str(item) for item in rare.get("items", []))
            lines.append(
                f"  rare itemset: `{items}` support={float(rare.get('support', 0.0)):.4f} "
                f"min_support={float(rare.get('min_support', 0.0)):.4f}"
            )
        for rule in cell.get("rule_evidence", [])[:2]:
            lines.append(
                f"  violated `{rule.get('rule_id')}`: confidence={float(rule.get('confidence', 0.0)):.2f}, "
                f"lift={float(rule.get('lift', 0.0)):.2f}"
            )
    lines.append("")
    return lines


def _display_path(path: str | Path, project_root: str | Path) -> str:
    path_obj = Path(path).resolve()
    root = Path(project_root).resolve()
    try:
        return str(path_obj.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path_obj).replace("\\", "/")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
