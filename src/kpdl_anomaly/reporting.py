from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from kpdl_preprocess.config import ConfigError, resolve_path
from kpdl_preprocess.utils import ensure_dir

from .config import AnomalyConfig, load_anomaly_config
from .io import read_json, write_json

REPORT_SCHEMA_VERSION = "spec_10.report.v1"
DEFAULT_CASE_LIMIT = 5
DEFAULT_CLUSTER_LIMIT = 12
DEFAULT_RULE_LIMIT = 10


@dataclass(frozen=True)
class ReportOptions:
    config_path: str | Path
    project_root: str | Path = "."
    analysis_dir: str | Path = "src/outputs/analysis/ucsd_ped2_smoke"
    results_dir: str | Path | None = None
    visualizations_dir: str | Path | None = None
    evaluation_dir: str | Path | None = None
    latex_dir: str | Path = "latex"
    dataset: str | None = None
    case_limit: int = DEFAULT_CASE_LIMIT
    artifact_label: str = ""
    no_copy_figures: bool = False
    sections_only: bool = False


def generate_report_artifacts(options: ReportOptions) -> dict[str, Any]:
    config = load_anomaly_config(options.config_path, project_root=options.project_root)
    dataset = options.dataset or config.dataset
    latex_dir = resolve_path(options.latex_dir, config.project_root)
    generated_dir = ensure_dir(latex_dir / "generated" / dataset)
    figures_dir = ensure_dir(latex_dir / "figures" / dataset)
    warnings: list[str] = []

    sources = _resolve_sources(config, options)
    analysis_payloads = _load_analysis_payloads(sources["analysis"], warnings)
    metrics = _read_optional_json(sources.get("evaluation"), "metrics.json", warnings)
    visualization_stats = _read_optional_json(sources.get("visualizations"), "visualization_stats.json", warnings)
    scoring_stats = _read_optional_json(sources.get("results"), "scoring_stats.json", warnings)

    figures = []
    if not options.sections_only:
        figures = _copy_case_figures(
            cases=analysis_payloads["casebook"].get("cases", []),
            project_root=config.project_root,
            latex_dir=latex_dir,
            figures_dir=figures_dir,
            dataset=dataset,
            case_limit=options.case_limit,
            no_copy=options.no_copy_figures,
            warnings=warnings,
        )

    tables = _write_tables(
        generated_dir=generated_dir,
        config=config,
        dataset=dataset,
        cluster_profiles=analysis_payloads["cluster_profiles"],
        rule_evidence=analysis_payloads["rule_evidence"],
        casebook=analysis_payloads["casebook"],
        metrics=metrics,
        visualization_stats=visualization_stats,
        scoring_stats=scoring_stats,
        figures=figures,
        case_limit=options.case_limit,
        warnings=warnings,
    )
    sections = _write_sections(
        latex_dir=latex_dir,
        dataset=dataset,
        generated_rel=_latex_rel(generated_dir, latex_dir),
        config=config,
        artifact_label=options.artifact_label,
        warnings=warnings,
    )

    manifest = _manifest(
        config=config,
        dataset=dataset,
        options=options,
        generated_dir=generated_dir,
        latex_dir=latex_dir,
        sources=sources,
        analysis_payloads=analysis_payloads,
        metrics=metrics,
        visualization_stats=visualization_stats,
        scoring_stats=scoring_stats,
        figures=figures,
        tables=tables,
        sections=sections,
        warnings=warnings,
    )
    manifest_path = generated_dir / "report_artifacts_manifest.json"
    write_json(manifest_path, manifest)
    return manifest


def _resolve_sources(config: AnomalyConfig, options: ReportOptions) -> dict[str, Path | None]:
    analysis = resolve_path(options.analysis_dir, config.project_root)
    results = resolve_path(options.results_dir, config.project_root) if options.results_dir else None
    visualizations = (
        resolve_path(options.visualizations_dir, config.project_root) if options.visualizations_dir else None
    )
    evaluation = resolve_path(options.evaluation_dir, config.project_root) if options.evaluation_dir else None
    return {
        "config": resolve_path(options.config_path, config.project_root),
        "analysis": analysis,
        "results": results,
        "visualizations": visualizations,
        "evaluation": evaluation,
    }


def _load_analysis_payloads(analysis_dir: Path | None, warnings: list[str]) -> dict[str, Any]:
    if analysis_dir is None:
        raise ConfigError("analysis_dir is required for SPEC 10 report generation")
    if not analysis_dir.exists():
        raise ConfigError(f"Analysis artifact directory not found: {analysis_dir}")

    cluster_profiles = _read_required_json(analysis_dir / "cluster_profiles.json")
    rule_evidence = _read_optional_json(analysis_dir, "rule_evidence_index.json", warnings, default=[])
    casebook = _read_required_json(analysis_dir / "alert_casebook.json")
    analysis_manifest = _read_optional_json(analysis_dir, "analysis_manifest.json", warnings, default={})
    return {
        "cluster_profiles": cluster_profiles,
        "rule_evidence": rule_evidence,
        "casebook": casebook,
        "analysis_manifest": analysis_manifest,
    }


def _read_required_json(path: Path) -> Any:
    if not path.exists():
        raise ConfigError(f"Required report artifact not found: {path}")
    return read_json(path)


def _read_optional_json(
    directory: Path | None,
    filename: str,
    warnings: list[str],
    default: Any | None = None,
) -> Any:
    if directory is None:
        return {} if default is None else default
    path = directory / filename
    if not path.exists():
        warnings.append(f"optional report artifact missing: {_display(path)}")
        return {} if default is None else default
    return read_json(path)


def _copy_case_figures(
    cases: list[Mapping[str, Any]],
    project_root: Path,
    latex_dir: Path,
    figures_dir: Path,
    dataset: str,
    case_limit: int,
    no_copy: bool,
    warnings: list[str],
) -> list[dict[str, Any]]:
    figure_records: list[dict[str, Any]] = []
    for index, case in enumerate(cases[: max(0, case_limit)], start=1):
        overlay = dict(case.get("overlay", {}))
        raw_source = overlay.get("image_path")
        if not raw_source:
            warnings.append(f"case {case.get('case_id')} has no overlay image")
            continue
        source = _resolve_artifact_path(raw_source, project_root)
        if not source.exists():
            warnings.append(f"case figure source not found: {_display(source)}")
            continue

        extension = source.suffix.lower() or ".png"
        target = figures_dir / f"case_{index:03d}_heatmap{extension}"
        if no_copy:
            latex_path = _latex_rel(source, latex_dir)
        else:
            shutil.copy2(source, target)
            latex_path = _latex_rel(target, latex_dir)
        figure_records.append(
            {
                "case_id": str(case.get("case_id", f"Case {index:03d}")),
                "video_id": str(case.get("video_id", "")),
                "frame_id": int(case.get("frame_id", 0)),
                "source": _display(source, project_root),
                "latex_path": _display(target if not no_copy else source, project_root),
                "relative_latex_path": latex_path,
                "dataset": dataset,
            }
        )
    return figure_records


def _write_tables(
    generated_dir: Path,
    config: AnomalyConfig,
    dataset: str,
    cluster_profiles: Mapping[str, Any],
    rule_evidence: list[Mapping[str, Any]],
    casebook: Mapping[str, Any],
    metrics: Mapping[str, Any],
    visualization_stats: Mapping[str, Any],
    scoring_stats: Mapping[str, Any],
    figures: list[Mapping[str, Any]],
    case_limit: int,
    warnings: list[str],
) -> list[str]:
    table_paths = {
        "pipeline_summary": generated_dir / "pipeline_summary.tex",
        "config_table": generated_dir / "config_table.tex",
        "metrics_table": generated_dir / "metrics_table.tex",
        "cluster_profile_table": generated_dir / "cluster_profile_table.tex",
        "rule_evidence_table": generated_dir / "rule_evidence_table.tex",
        "casebook_cases": generated_dir / "casebook_cases.tex",
    }
    _write_text(table_paths["pipeline_summary"], _pipeline_summary_tex(dataset, config, casebook, visualization_stats, scoring_stats))
    _write_text(table_paths["config_table"], _config_table_tex(config))
    _write_text(table_paths["metrics_table"], _metrics_table_tex(metrics))
    _write_text(table_paths["cluster_profile_table"], _cluster_profile_table_tex(cluster_profiles))
    _write_text(table_paths["rule_evidence_table"], _rule_evidence_table_tex(rule_evidence))
    _write_text(table_paths["casebook_cases"], _casebook_cases_tex(casebook, figures, case_limit, warnings))
    return [_display(path) for path in table_paths.values()]


def _write_sections(
    latex_dir: Path,
    dataset: str,
    generated_rel: str,
    config: AnomalyConfig,
    artifact_label: str,
    warnings: list[str],
) -> list[str]:
    sections_dir = ensure_dir(latex_dir / "sections")
    sections = {
        "background.tex": _background_section(),
        "system_design.tex": _system_design_section(generated_rel),
        "implementation.tex": _implementation_section(config),
        "experiments.tex": _experiments_section(dataset, generated_rel, artifact_label),
        "results_discussion.tex": _results_section(generated_rel),
        "conclusion.tex": _conclusion_section(warnings),
    }
    written: list[str] = []
    for filename, content in sections.items():
        path = sections_dir / filename
        _write_text(path, content)
        written.append(_display(path))
    return written


def _pipeline_summary_tex(
    dataset: str,
    config: AnomalyConfig,
    casebook: Mapping[str, Any],
    visualization_stats: Mapping[str, Any],
    scoring_stats: Mapping[str, Any],
) -> str:
    cases = list(casebook.get("cases", []))
    lines = [
        "% Generated by src/report.py; do not edit by hand.",
        "\\begin{itemize}",
        f"  \\item Dataset bao cao: \\texttt{{{_tex(dataset)}}}.",
        f"  \\item Mo hinh: MiniBatchKMeans theo tung cell, K={config.clusters_per_cell}, threshold percentile={config.threshold_percentile:.1f}.",
        f"  \\item Grid {config.raw.get('grid', {}).get('rows')}x{config.raw.get('grid', {}).get('cols')}, cube length {config.raw.get('cube', {}).get('length')}, stride {config.raw.get('cube', {}).get('stride')}.",
        f"  \\item Feature scoring gom {len(config.feature_columns)} cot; chi tiet nam trong bang cau hinh.",
        f"  \\item So case trong casebook: {len(cases)}.",
    ]
    if visualization_stats:
        lines.append(
            "  \\item Visualization da ghi "
            f"{int(visualization_stats.get('num_images_written', 0))} anh va "
            f"{int(visualization_stats.get('num_videos_written', 0))} video overlay."
        )
    if scoring_stats:
        lines.append("  \\item Scoring artifact co file thong ke va ket qua frame/cell de tai lap case.")
    lines.extend(["\\end{itemize}", ""])
    return "\n".join(lines)


def _config_table_tex(config: AnomalyConfig) -> str:
    raw = config.raw
    rows = [
        ("Dataset", config.dataset),
        ("Input", _nested(raw, "video", "input_type")),
        ("Resize", f"{_nested(raw, 'video', 'resize_width')}x{_nested(raw, 'video', 'resize_height')}"),
        ("Grid", f"{_nested(raw, 'grid', 'rows')} rows x {_nested(raw, 'grid', 'cols')} cols"),
        ("Cube", f"length={_nested(raw, 'cube', 'length')}, stride={_nested(raw, 'cube', 'stride')}"),
        ("Motion feature", str(_nested(raw, "features", "motion_method"))),
        ("Feature columns", ", ".join(config.feature_columns)),
        ("Model", f"{config.model_type}, K={config.clusters_per_cell}, min_samples={config.min_samples_per_cell}"),
        ("Threshold", f"percentile={config.threshold_percentile:.1f}, floor={config.threshold_floor:g}"),
        (
            "Score weights",
            f"cluster={config.cluster_weight:.2f}, temporal={config.temporal_weight:.2f}, "
            f"rare={config.rare_token_weight:.2f}, rule={config.rule_weight:.2f}",
        ),
        (
            "Alert",
            f"medium={config.alert_threshold_medium:.2f}, high={config.alert_threshold_high:.2f}, "
            f"min consecutive={config.min_consecutive_alerts}",
        ),
        (
            "Rules",
            f"enabled={config.rules.enabled}, support={config.rules.min_support:.3f}, "
            f"confidence={config.rules.min_confidence:.2f}, lift={config.rules.min_lift:.2f}",
        ),
    ]
    return _two_column_longtable("Cau hinh pipeline dung trong bao cao.", rows)


def _metrics_table_tex(metrics: Mapping[str, Any]) -> str:
    metric_map = dict(metrics.get("metrics", {})) if isinstance(metrics, Mapping) else {}
    if not metric_map:
        return "\\textit{Chua co artifact metric hoac metric khong nam trong pham vi bao cao nay.}\n"
    lines = [
        "% Generated by src/report.py; do not edit by hand.",
        "\\begin{longtable}{@{}p{0.17\\textwidth}p{0.12\\textwidth}p{0.11\\textwidth}p{0.11\\textwidth}p{0.11\\textwidth}p{0.12\\textwidth}@{}}",
        "\\caption{Metric sanity-check frame-level neu co ground truth.}\\\\",
        "\\textbf{Score} & \\textbf{Frames} & \\textbf{ROC} & \\textbf{PR} & \\textbf{EER} & \\textbf{Best F1}\\\\",
        "\\hline",
        "\\endfirsthead",
        "\\textbf{Score} & \\textbf{Frames} & \\textbf{ROC} & \\textbf{PR} & \\textbf{EER} & \\textbf{Best F1}\\\\",
        "\\hline",
        "\\endhead",
    ]
    for name, values in metric_map.items():
        row = dict(values)
        lines.append(
            " & ".join(
                [
                    _mono(str(name)),
                    str(int(row.get("num_frames", 0))),
                    _fmt(row.get("roc_auc")),
                    _fmt(row.get("pr_auc")),
                    _fmt(row.get("eer")),
                    _fmt(row.get("best_f1")),
                ]
            )
            + "\\\\"
        )
    lines.extend(["\\end{longtable}", ""])
    return "\n".join(lines)


def _cluster_profile_table_tex(cluster_profiles: Mapping[str, Any]) -> str:
    rows = _cluster_rows(cluster_profiles)[:DEFAULT_CLUSTER_LIMIT]
    if not rows:
        return "\\textit{Chua co cluster profile de dua vao bao cao.}\n"
    lines = [
        "% Generated by src/report.py; do not edit by hand.",
        "\\begin{longtable}{@{}p{0.10\\textwidth}@{}p{0.07\\textwidth}@{}p{0.08\\textwidth}@{}p{0.10\\textwidth}@{}p{0.10\\textwidth}@{}p{0.33\\textwidth}@{}}",
        "\\caption{Mot so cluster profile dai dien tu artifact phan tich.}\\\\",
        "\\textbf{Cell} & \\textbf{Cum} & \\textbf{Supp.} & \\textbf{Motion} & \\textbf{D/B} & \\textbf{Ghi chu}\\\\",
        "\\hline",
        "\\endfirsthead",
        "\\textbf{Cell} & \\textbf{Cum} & \\textbf{Supp.} & \\textbf{Motion} & \\textbf{D/B} & \\textbf{Ghi chu}\\\\",
        "\\hline",
        "\\endhead",
    ]
    for row in rows:
        tokens = dict(row.get("tokens", {}))
        lines.append(
            " & ".join(
                [
                    _mono(row["cell_id"]),
                    _mono(row["cluster_id"]),
                    _fmt(row.get("support")),
                    _tex(tokens.get("motion", "")),
                    _tex(", ".join(part for part in [tokens.get("density", ""), tokens.get("brightness", "")] if part)),
                    _tex(row.get("summary", "")),
                ]
            )
            + "\\\\"
        )
    lines.extend(["\\end{longtable}", ""])
    return "\n".join(lines)


def _rule_evidence_table_tex(rule_evidence: list[Mapping[str, Any]]) -> str:
    rows = [dict(rule) for rule in rule_evidence if not rule.get("is_context_only")][:DEFAULT_RULE_LIMIT]
    if not rows:
        return "\\textit{Chua co rule evidence phu hop de dua vao bao cao.}\n"
    lines = [
        "% Generated by src/report.py; do not edit by hand.",
        "\\begin{longtable}{@{}p{0.09\\textwidth}p{0.31\\textwidth}p{0.22\\textwidth}p{0.08\\textwidth}p{0.08\\textwidth}p{0.08\\textwidth}@{}}",
        "\\caption{Rule evidence rut gon tu artifact association rules.}\\\\",
        "\\textbf{Rule} & \\textbf{Antecedent} & \\textbf{Consequent} & \\textbf{Supp.} & \\textbf{Conf.} & \\textbf{Lift}\\\\",
        "\\hline",
        "\\endfirsthead",
        "\\textbf{Rule} & \\textbf{Antecedent} & \\textbf{Consequent} & \\textbf{Supp.} & \\textbf{Conf.} & \\textbf{Lift}\\\\",
        "\\hline",
        "\\endhead",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    _mono(row.get("rule_id", "")),
                    _tex(", ".join(str(item) for item in row.get("antecedent", []))),
                    _tex(", ".join(str(item) for item in row.get("consequent", []))),
                    _fmt(row.get("support")),
                    _fmt(row.get("confidence")),
                    _fmt(row.get("lift")),
                ]
            )
            + "\\\\"
        )
    lines.extend(["\\end{longtable}", ""])
    return "\n".join(lines)


def _casebook_cases_tex(
    casebook: Mapping[str, Any],
    figures: list[Mapping[str, Any]],
    case_limit: int,
    warnings: list[str],
) -> str:
    cases = list(casebook.get("cases", []))[: max(0, case_limit)]
    figure_by_case = {str(item.get("case_id")): dict(item) for item in figures}
    if not cases:
        return "\\textit{Chua co casebook case de dua vao bao cao.}\n"
    lines = ["% Generated by src/report.py; do not edit by hand."]
    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", f"Case {index:03d}"))
        score = dict(case.get("score", {}))
        figure = figure_by_case.get(case_id)
        lines.extend(
            [
                f"\\subsection{{{_tex(case_id)}: video {_tex(case.get('video_id', ''))}, frame {int(case.get('frame_id', 0))}}}",
                "",
                "\\begin{itemize}",
                f"  \\item Selection: {_mono(case.get('selection_type', ''))}.",
                f"  \\item Smoothed frame score: {_fmt(score.get('smoothed_frame_score'))}; severity: {_mono(score.get('severity', ''))}.",
                f"  \\item Manual review: {_mono('TBD')}.",
                "\\end{itemize}",
                "",
            ]
        )
        if figure:
            lines.extend(
                [
                    "\\begin{figure}[H]",
                    "\\centering",
                    f"\\includegraphics[width=0.82\\textwidth]{{{figure['relative_latex_path']}}}",
                    "\\caption{Heatmap/case artifact cho "
                    f"{_tex(case_id)}, video {_tex(case.get('video_id', ''))}, frame {int(case.get('frame_id', 0))}. "
                    f"Nguon: {_tex(figure.get('source', ''))}.}}",
                    "\\end{figure}",
                    "",
                ]
            )
        else:
            warnings.append(f"case {case_id} has no figure included in LaTeX")
            lines.append("\\textit{Case nay chua co hinh minh hoa trong manifest.}\n")
        top_cells = list(case.get("top_cells", []))[:3]
        if top_cells:
            lines.extend(["Bang chung chinh:", "", "\\begin{itemize}"])
            for cell in top_cells:
                profile = dict(cell.get("cluster_profile", {}))
                distance = dict(cell.get("cluster_distance", {}))
                reasons = list(cell.get("plain_language", []))
                lines.append(
                    "  \\item "
                    f"Cell {_mono(cell.get('cell_id', ''))}, nearest {_mono(cell.get('nearest_cluster', ''))}, "
                    f"score {_fmt(cell.get('cell_score'))}."
                )
                lines.append(
                    "  \\item "
                    f"Distance {_fmt(distance.get('distance'))}; threshold {_fmt(distance.get('threshold'))}. "
                    f"Normal pattern: {_tex(profile.get('summary', ''))}"
                )
                for reason in reasons[:2]:
                    lines.append(f"  \\item {_tex(reason)}")
            lines.extend(["\\end{itemize}", ""])
    return "\n".join(lines)


def _background_section() -> str:
    return r"""\chapter{Co so ly thuyet va huong tiep can}

\section{Bai toan phat hien bat thuong theo ngu canh}

Video tu camera co dinh thuong co cau truc khong gian on dinh: cung mot vung anh lap lai cac kieu chuyen dong gan giong nhau theo thoi gian. Bao cao nay vi vay xem moi cell trong grid nhu mot ngu canh rieng, hoc mau hanh vi binh thuong tu du lieu train va gan diem bat thuong khi mau moi lech khoi mau do.

\section{Phan cum hanh vi-khong gian-thoi gian}

Pipeline dung spatio-temporal cube ngan de gom thong tin nhieu frame lien tiep. Feature motion, density, brightness va vi tri cell duoc dua vao MiniBatchKMeans theo tung cell. Cach nay giu duoc tinh giai thich: cluster C0 o cell 09\_11 chi co y nghia trong cell do, khong bi dong nhat voi cluster cung ten o cell khac.

\section{Token va association rule}

Feature lien tuc duoc roi rac hoa thanh token nhu \texttt{motion=very\_fast}, \texttt{density=high}, \texttt{brightness=dark}, \texttt{cluster=C1}. Cac token nay tao transaction cho association rule mining. Rule khong duoc xem la bang chung duy nhat cua bat thuong; no la lop giai thich phu tro cho cluster distance va temporal change.

\section{Tai lieu tham khao ve tu duy xu ly nhanh}

Huong tiep can chiu anh huong tu y tuong camera co dinh co cau truc khong gian-thoi gian lap lai. Bao cao khong dat muc tieu tai hien mot paper cu the, ma tap trung dong goi pipeline hien co va cac artifact giai thich thanh bang chung co the kiem tra lai.
"""


def _system_design_section(generated_rel: str) -> str:
    return rf"""\chapter{{Thiet ke he thong}}

\section{{Tong quan pipeline}}

\begin{{figure}}[H]
\centering
\begin{{tikzpicture}}[
  node distance=1.0cm and 0.55cm,
  pipebox/.style={{draw, rounded corners=2pt, align=center, minimum width=2.7cm, minimum height=0.75cm}},
  arrow/.style={{-Latex, thick}}
]
\node[pipebox] (video) {{Video\\camera co dinh}};
\node[pipebox, right=of video] (pre) {{Preprocess\\resize + gray}};
\node[pipebox, right=of pre] (cube) {{Grid/cube\\cell theo thoi gian}};
\node[pipebox, below=of cube] (feat) {{Feature\\motion + brightness}};
\node[pipebox, left=of feat] (cluster) {{Per-cell\\KMeans}};
\node[pipebox, right=of feat] (token) {{Token/rule\\support + lift}};
\node[pipebox, below=of feat] (score) {{Scoring\\smooth + alert}};
\node[pipebox, below=of score] (report) {{Heatmap\\casebook + report}};
\draw[arrow] (video) -- (pre);
\draw[arrow] (pre) -- (cube);
\draw[arrow] (cube) -- (feat);
\draw[arrow] (feat) -- (cluster);
\draw[arrow] (feat) -- (token);
\draw[arrow] (cluster) |- (score);
\draw[arrow] (token) |- (score);
\draw[arrow] (score) -- (report);
\end{{tikzpicture}}
\caption{{Pipeline tu video dau vao den heatmap, casebook va artifact bao cao.}}
\end{{figure}}

\section{{Cau hinh chinh}}

\input{{{generated_rel}/config_table.tex}}

\section{{Tom tat artifact duoc dung}}

\input{{{generated_rel}/pipeline_summary.tex}}
"""


def _implementation_section(config: AnomalyConfig) -> str:
    return rf"""\chapter{{Trien khai}}

\section{{Cau truc module}}

\begin{{longtable}}{{@{{}}p{{0.38\textwidth}}p{{0.56\textwidth}}@{{}}}}
\caption{{Cac module chinh trong source code.}}\\
\textbf{{Module}} & \textbf{{Vai tro}}\\
\hline
\endfirsthead
\textbf{{Module}} & \textbf{{Vai tro}}\\
\hline
\endhead
\texttt{{kpdl\_preprocess}} & Doc frame/video, chia grid, tao cube va trich xuat feature tien xu ly.\\
\texttt{{kpdl\_anomaly/train.py}} & Train MiniBatchKMeans theo cell, scaler va threshold distance.\\
\texttt{{kpdl\_anomaly/test.py}} & Tinh cell score, frame score, smoothing va alert JSON.\\
\texttt{{kpdl\_anomaly/rule\_model.py}} & Tao transaction token va khai pha association rules.\\
\texttt{{kpdl\_anomaly/visualization}} & Render heatmap, top frame, alert peak va overlay video.\\
\texttt{{kpdl\_anomaly/casebook.py}} & Noi cluster profile, rule evidence va overlay thanh casebook.\\
\texttt{{kpdl\_anomaly/reporting.py}} & Sinh bang/hinh/manifest va section LaTeX cho SPEC 10.\\
\end{{longtable}}

\section{{Lenh tai lap artifact bao cao}}

\begin{{verbatim}}
python src/report.py --config src/configs/{config.dataset}.yaml \
  --analysis src/outputs/analysis/{config.dataset}_smoke \
  --results src/outputs/results/{config.dataset} \
  --visualizations src/outputs/visualizations/{config.dataset} \
  --evaluation src/outputs/evaluation/{config.dataset}_smoke \
  --latex-dir latex --dataset {config.dataset} --case-limit 5 \
  --artifact-label smoke
\end{{verbatim}}

Lenh nay khong train lai model va khong thay doi scoring. No chi doc artifact da co, copy hinh can dung vao \texttt{{latex/figures}}, tao bang trong \texttt{{latex/generated}} va ghi manifest nguon.
"""


def _experiments_section(dataset: str, generated_rel: str, artifact_label: str) -> str:
    label_text = artifact_label or "artifact hien co"
    return rf"""\chapter{{Thuc nghiem va artifact}}

\section{{Dataset va pham vi chay}}

Bao cao su dung dataset \texttt{{{_tex(dataset)}}} voi nhan artifact \texttt{{{_tex(label_text)}}}. Neu artifact duoc gan nhan smoke, cac con so chi nen doc nhu sanity check va vi du minh hoa pipeline, khong phai ket luan benchmark.

\section{{Artifact dau vao}}

Nguon chinh gom config YAML, ket qua scoring \texttt{{frame\_scores.csv}} va \texttt{{cell\_scores.csv}}, heatmap trong \texttt{{visualization\_index.json}}, cluster profile, rule evidence va alert casebook tu SPEC 9.

\section{{Metric sanity-check}}

\input{{{generated_rel}/metrics_table.tex}}
"""


def _results_section(generated_rel: str) -> str:
    return rf"""\chapter{{Ket qua dinh tinh va thao luan}}

\section{{Cluster profile rut gon}}

\input{{{generated_rel}/cluster_profile_table.tex}}

\section{{Rule evidence rut gon}}

\input{{{generated_rel}/rule_evidence_table.tex}}

\section{{Case heatmap va giai thich}}

\input{{{generated_rel}/casebook_cases.tex}}

\section{{Thao luan}}

Bang va hinh tren cho thay pipeline co the noi ba loai bang chung: cell score/cluster distance, token hiem va rule violation. Rule evidence giup giai thich ngu canh cua alert, nhung khong duoc dung mot minh de ket luan bat thuong. Khi manual review chua duoc dien, cac case chi nen xem la vi du dinh tinh can nguoi xem xac nhan.
"""


def _conclusion_section(warnings: list[str]) -> str:
    warning_text = (
        "\\section{Canh bao khi doc bao cao}\n\n"
        + "\\begin{itemize}\n"
        + "\n".join(f"  \\item {_tex(warning)}." for warning in warnings[:8])
        + "\n\\end{itemize}\n"
        if warnings
        else ""
    )
    return rf"""\chapter{{Ket luan va huong phat trien}}

\section{{Muc da hoan thanh}}

Pipeline hien tai da co cac thanh phan chinh theo PRD: tien xu ly video, chia grid/cube, feature motion/brightness, phan cum MiniBatchKMeans theo cell, token/rule, scoring, smoothing, heatmap va casebook giai thich. SPEC 10 dong goi cac artifact nay thanh section LaTeX, bang tom tat, hinh minh hoa va manifest de tai lap.

\section{{Han che}}

\begin{{itemize}}
  \item Grid hien tai chua phai zone ngu nghia do nguoi dung ve.
  \item Rule support co the thap va chi nen doc nhu tin hieu giai thich phu.
  \item Smoke artifact khong thay the cho danh gia benchmark day du.
  \item Manual review trong casebook van de \texttt{{TBD}}, nen khong gan nhan true positive/false positive trong bao cao chinh.
\end{{itemize}}

{warning_text}
\section{{Huong phat trien}}

Huong tiep theo la review thu cong mot tap case tieu bieu, bo sung zone ngu nghia, thu object detector nhe khi can phan biet nguoi/xe, va mo rong bao cao bang phu luc tai lap pipeline khi artifact production day du hon.
"""


def _manifest(
    config: AnomalyConfig,
    dataset: str,
    options: ReportOptions,
    generated_dir: Path,
    latex_dir: Path,
    sources: Mapping[str, Path | None],
    analysis_payloads: Mapping[str, Any],
    metrics: Mapping[str, Any],
    visualization_stats: Mapping[str, Any],
    scoring_stats: Mapping[str, Any],
    figures: list[Mapping[str, Any]],
    tables: list[str],
    sections: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    cluster_profiles = dict(analysis_payloads["cluster_profiles"])
    casebook = dict(analysis_payloads["casebook"])
    rule_evidence = list(analysis_payloads["rule_evidence"])
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "dataset": dataset,
        "artifact_label": options.artifact_label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {key: _display(value, config.project_root) if value is not None else None for key, value in sources.items()},
        "outputs": {
            "generated_dir": _display(generated_dir, config.project_root),
            "latex_dir": _display(latex_dir, config.project_root),
            "manifest": _display(generated_dir / "report_artifacts_manifest.json", config.project_root),
        },
        "figures": list(figures),
        "tables": tables,
        "sections": sections,
        "counts": {
            "cluster_profile_cells": int(cluster_profiles.get("num_cells", 0)),
            "cluster_profiles": int(cluster_profiles.get("num_clusters", 0)),
            "rule_evidence": len(rule_evidence),
            "cases": len(casebook.get("cases", [])),
            "figures": len(figures),
            "metric_score_columns": len(dict(metrics.get("metrics", {}))) if isinstance(metrics, Mapping) else 0,
            "visualization_images": int(visualization_stats.get("num_images_written", 0)) if visualization_stats else 0,
            "scoring_stats_available": bool(scoring_stats),
        },
        "warnings": _dedupe(warnings),
    }


def _two_column_longtable(caption: str, rows: list[tuple[str, Any]]) -> str:
    lines = [
        "% Generated by src/report.py; do not edit by hand.",
        "\\begin{longtable}{p{0.28\\textwidth}p{0.62\\textwidth}}",
        f"\\caption{{{_tex(caption)}}}\\\\",
        "\\textbf{Muc} & \\textbf{Gia tri}\\\\",
        "\\hline",
        "\\endfirsthead",
        "\\textbf{Muc} & \\textbf{Gia tri}\\\\",
        "\\hline",
        "\\endhead",
    ]
    for key, value in rows:
        lines.append(f"{_tex(key)} & {_tex(value)}\\\\")
    lines.extend(["\\end{longtable}", ""])
    return "\n".join(lines)


def _cluster_rows(cluster_profiles: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell in cluster_profiles.get("cells", []):
        for cluster in cell.get("clusters", []):
            rows.append(
                {
                    "cell_id": str(cell.get("cell_id", "")),
                    "cluster_id": str(cluster.get("cluster_id", "")),
                    "support": _float_or_none(cluster.get("support")),
                    "tokens": dict(cluster.get("token_summary", {})),
                    "summary": str(cluster.get("summary", "")),
                }
            )
    rows.sort(key=lambda row: (-(row["support"] or 0.0), row["cell_id"], row["cluster_id"]))
    return rows


def _resolve_artifact_path(path_value: str | Path, project_root: Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else project_root / path


def _latex_rel(path: str | Path, latex_dir: str | Path) -> str:
    target = Path(path).resolve()
    base = Path(latex_dir).resolve()
    try:
        return str(target.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(Path("..") / target.relative_to(base.parent)).replace("\\", "/")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _nested(raw: Mapping[str, Any], section: str, key: str) -> Any:
    value = raw.get(section, {})
    if isinstance(value, Mapping):
        return value.get(key, "")
    return ""


def _tex(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _mono(value: Any) -> str:
    return f"\\texttt{{{_tex(value)}}}"


def _fmt(raw: Any) -> str:
    value = _float_or_none(raw)
    if value is None:
        return ""
    return f"{value:.4f}"


def _float_or_none(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value or value in {float("inf"), float("-inf")}:
        return None
    return value


def _display(path: str | Path | None, root: str | Path | None = None) -> str:
    if path is None:
        return ""
    path_obj = Path(path)
    if root is not None:
        try:
            return str(path_obj.resolve().relative_to(Path(root).resolve())).replace("\\", "/")
        except ValueError:
            pass
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
