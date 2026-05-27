from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

POSITION_PREFIXES = ("cell=", "cell_row=", "cell_col=")
PREFERRED_CONSEQUENT_PREFIXES = (
    "motion=",
    "density=",
    "cluster=",
    "brightness=",
    "brightness_delta=",
)


def update_itemset_counts(counter: Counter[tuple[str, ...]], tokens: list[str], max_size: int) -> None:
    unique_tokens = tuple(sorted(set(tokens)))
    upper = min(max_size, len(unique_tokens))
    for size in range(1, upper + 1):
        counter.update(combinations(unique_tokens, size))


def itemset_records(
    counter: Counter[tuple[str, ...]],
    num_transactions: int,
    min_support: float = 0.0,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if num_transactions <= 0:
        return records
    for items, count in counter.items():
        support = count / num_transactions
        if support < min_support:
            continue
        records.append(
            {
                "items": list(items),
                "count": int(count),
                "support": float(support),
            }
        )
    records.sort(key=lambda item: (-float(item["support"]), len(item["items"]), item["items"]))
    return records


def generate_association_rules(
    counter: Counter[tuple[str, ...]],
    num_transactions: int,
    min_support: float,
    min_confidence: float,
    min_lift: float,
    max_rules: int,
) -> list[dict[str, Any]]:
    if num_transactions <= 0:
        return []

    supports = {items: count / num_transactions for items, count in counter.items()}
    candidates: list[dict[str, Any]] = []
    for itemset, support in supports.items():
        if len(itemset) < 2 or support < min_support:
            continue
        if _position_only(itemset):
            continue

        itemset_set = set(itemset)
        for antecedent_size in range(1, len(itemset)):
            for antecedent in combinations(itemset, antecedent_size):
                consequent = tuple(sorted(itemset_set - set(antecedent)))
                if not consequent or _position_only(antecedent + consequent):
                    continue
                if not _preferred_consequent(consequent):
                    continue

                antecedent_support = supports.get(tuple(sorted(antecedent)), 0.0)
                consequent_support = supports.get(tuple(sorted(consequent)), 0.0)
                if antecedent_support <= 0.0 or consequent_support <= 0.0:
                    continue
                confidence = support / antecedent_support
                lift = confidence / consequent_support
                if confidence < min_confidence or lift < min_lift:
                    continue

                candidates.append(
                    {
                        "antecedent": list(sorted(antecedent)),
                        "consequent": list(consequent),
                        "support": float(support),
                        "confidence": float(confidence),
                        "lift": float(lift),
                    }
                )

    candidates.sort(
        key=lambda item: (
            -float(item["confidence"]),
            -float(item["lift"]),
            -float(item["support"]),
            len(item["antecedent"]),
            item["antecedent"],
            item["consequent"],
        )
    )
    selected = candidates[:max_rules]
    for index, rule in enumerate(selected, start=1):
        rule["rule_id"] = f"R{index:04d}"
    return selected


def _position_only(items: tuple[str, ...]) -> bool:
    return all(any(item.startswith(prefix) for prefix in POSITION_PREFIXES) for item in items)


def _preferred_consequent(consequent: tuple[str, ...]) -> bool:
    return any(any(item.startswith(prefix) for prefix in PREFERRED_CONSEQUENT_PREFIXES) for item in consequent)
