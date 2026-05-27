from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .config import AnomalyConfig
from .io import read_json
from .tokenization import row_to_tokens


@dataclass(frozen=True)
class RuleScore:
    tokens: list[str]
    rare_token_score: float
    rare_itemset: list[str]
    rare_itemset_support: float
    rule_violation_score: float
    violated_rules: list[str]
    reasons: list[str]


@dataclass(frozen=True)
class RuleLoadResult:
    scorer: "RuleScorer | None"
    rule_dir: Path | None
    warnings: list[str]


class RuleScorer:
    def __init__(
        self,
        rule_dir: Path,
        manifest: dict[str, Any],
        token_bins: dict[str, Any],
        itemsets: list[dict[str, Any]],
        rules: list[dict[str, Any]],
        config: AnomalyConfig,
    ) -> None:
        self.rule_dir = rule_dir
        self.manifest = manifest
        self.token_bins = token_bins
        self.rules = rules
        self.min_support = float(manifest.get("min_support", config.rules.min_support))
        self.rare_itemset_size = config.rules.rare_itemset_size
        self.rare_score_cap = config.rules.rare_score_cap
        self.token_schema = dict(manifest.get("token_schema", {}))
        self.itemset_support = {
            tuple(sorted(str(item) for item in record.get("items", []))): float(record.get("support", 0.0))
            for record in itemsets
        }

    def score(self, row: Mapping[str, Any], nearest_cluster: int | str | None) -> RuleScore:
        tokens = row_to_tokens(
            row,
            self.token_bins,
            nearest_cluster,
            include_cell_token=bool(self.token_schema.get("include_cell_token", True)),
            include_cluster_token=bool(self.token_schema.get("include_cluster_token", True)),
            include_brightness_token=bool(self.token_schema.get("include_brightness_token", True)),
            include_direction_token=bool(self.token_schema.get("include_direction_token", False)),
        )
        rare_score, rare_itemset, rare_support, rare_reason = self._rare_score(tokens)
        violation_score, violated_rules, violation_reasons = self._rule_violation_score(tokens)
        reasons = []
        if rare_reason:
            reasons.append(rare_reason)
        reasons.extend(violation_reasons)
        return RuleScore(
            tokens=tokens,
            rare_token_score=rare_score,
            rare_itemset=rare_itemset,
            rare_itemset_support=rare_support,
            rule_violation_score=violation_score,
            violated_rules=violated_rules,
            reasons=reasons,
        )

    def _rare_score(self, tokens: list[str]) -> tuple[float, list[str], float, str | None]:
        candidates = _rare_candidates(tokens, self.rare_itemset_size)
        if not candidates:
            return 0.0, [], 0.0, None

        best_score = -1.0
        best_itemset: list[str] = []
        best_support = 0.0
        denominator = max(self.min_support, 1.0e-12)
        for candidate in candidates:
            key = tuple(sorted(candidate))
            support = self.itemset_support.get(key, 0.0)
            score = 1.0 - min(support / denominator, 1.0)
            score = min(float(np.clip(score, 0.0, 1.0)), self.rare_score_cap)
            if score > best_score:
                best_score = score
                best_itemset = list(key)
                best_support = support

        reason = None
        if best_itemset and best_support < self.min_support:
            reason = (
                "token combination {{{items}}} has support={support:.4f} below min_support={minimum:.4f}".format(
                    items=", ".join(best_itemset),
                    support=best_support,
                    minimum=self.min_support,
                )
            )
        return float(np.clip(best_score, 0.0, 1.0)), best_itemset, float(best_support), reason

    def _rule_violation_score(self, tokens: list[str]) -> tuple[float, list[str], list[str]]:
        transaction = set(tokens)
        violations: list[dict[str, Any]] = []
        for rule in self.rules:
            antecedent = {str(item) for item in rule.get("antecedent", [])}
            consequent = {str(item) for item in rule.get("consequent", [])}
            if not antecedent or not consequent or not antecedent.issubset(transaction):
                continue
            if consequent.issubset(transaction):
                continue
            strength = float(rule.get("confidence", 0.0)) * min(float(rule.get("lift", 0.0)) / 2.0, 1.0)
            strength = float(np.clip(strength, 0.0, 1.0))
            missing = sorted(consequent - transaction)
            violations.append(
                {
                    "rule_id": str(rule.get("rule_id", "")),
                    "strength": strength,
                    "antecedent": sorted(antecedent),
                    "missing": missing,
                    "reason": _violation_reason(rule, transaction, missing),
                }
            )

        if not violations:
            return 0.0, [], []
        violations.sort(key=lambda item: (-float(item["strength"]), item["rule_id"]))
        top = violations[:3]
        return (
            float(top[0]["strength"]),
            [str(item["rule_id"]) for item in top if item["rule_id"]],
            [str(item["reason"]) for item in top],
        )


def load_rule_scorer(
    config: AnomalyConfig,
    rule_dir: str | Path | None,
    requested: bool,
) -> RuleLoadResult:
    if not requested:
        return RuleLoadResult(scorer=None, rule_dir=None, warnings=[])

    resolved_dir = Path(rule_dir) if rule_dir is not None else config.rules.model_dir or (config.rules.output_root / config.dataset)
    required = [
        resolved_dir / "rule_manifest.json",
        resolved_dir / "token_bins.json",
        resolved_dir / "itemsets.json",
        resolved_dir / "rules.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        return RuleLoadResult(
            scorer=None,
            rule_dir=resolved_dir,
            warnings=[f"rule scoring disabled because artifact file(s) are missing: {', '.join(missing)}"],
        )

    manifest = read_json(required[0])
    warnings: list[str] = []
    if manifest.get("dataset") != config.dataset:
        warnings.append(
            f"rule scoring disabled because rule dataset={manifest.get('dataset')!r} does not match config dataset={config.dataset!r}"
        )
        return RuleLoadResult(scorer=None, rule_dir=resolved_dir, warnings=warnings)
    if list(manifest.get("feature_columns", [])) != config.feature_columns:
        warnings.append("rule scoring disabled because rule feature_columns do not match config scoring.feature_columns")
        return RuleLoadResult(scorer=None, rule_dir=resolved_dir, warnings=warnings)

    scorer = RuleScorer(
        rule_dir=resolved_dir,
        manifest=manifest,
        token_bins=read_json(required[1]),
        itemsets=read_json(required[2]),
        rules=read_json(required[3]),
        config=config,
    )
    return RuleLoadResult(scorer=scorer, rule_dir=resolved_dir, warnings=warnings)


def _rare_candidates(tokens: list[str], max_size: int) -> list[list[str]]:
    by_prefix = {token.split("=", 1)[0]: token for token in tokens if "=" in token}
    specs = [
        ("cell", "motion", "density"),
        ("cell", "motion", "cluster"),
        ("cell", "density", "cluster"),
        ("cell", "brightness", "motion"),
        ("cell", "direction", "motion"),
        ("cell", "direction", "cluster"),
        ("cell", "direction", "density"),
    ]
    candidates: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for spec in specs:
        if len(spec) > max_size:
            continue
        if not all(prefix in by_prefix for prefix in spec):
            continue
        candidate = tuple(sorted(by_prefix[prefix] for prefix in spec))
        if candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(list(candidate))
    return candidates


def _violation_reason(rule: dict[str, Any], transaction: set[str], missing: list[str]) -> str:
    antecedent = ", ".join(str(item) for item in rule.get("antecedent", []))
    expected = ", ".join(missing)
    observed = _observed_for_missing(transaction, missing)
    if observed:
        return f"rule {rule.get('rule_id')} expected {expected} for {{{antecedent}}}, but transaction has {observed}"
    return f"rule {rule.get('rule_id')} expected {expected} for {{{antecedent}}}"


def _observed_for_missing(transaction: set[str], missing: list[str]) -> str:
    prefixes = [item.split("=", 1)[0] for item in missing if "=" in item]
    observed: list[str] = []
    for prefix in prefixes:
        observed.extend(sorted(item for item in transaction if item.startswith(f"{prefix}=")))
    return ", ".join(observed)
