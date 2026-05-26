from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

from .config import AnomalyConfig
from .thresholds import summarize_distances


@dataclass
class TrainingResult:
    models: dict[str, MiniBatchKMeans]
    scalers: dict[str, StandardScaler]
    thresholds: dict[str, dict[str, Any]]
    feature_stats: dict[str, Any]
    num_models_trained: int
    num_fallback_cells: int


def train_per_cell(
    features_by_cell: dict[str, list[list[float]]],
    cell_ids: list[str],
    config: AnomalyConfig,
) -> TrainingResult:
    models: dict[str, MiniBatchKMeans] = {}
    scalers: dict[str, StandardScaler] = {}
    thresholds: dict[str, dict[str, Any]] = {}
    stats_by_cell: dict[str, dict[str, Any]] = {}
    num_models_trained = 0
    num_fallback_cells = 0

    for cell_id in sorted(cell_ids):
        samples = features_by_cell.get(cell_id, [])
        sample_count = len(samples)
        if sample_count:
            raw_values = np.asarray(samples, dtype=np.float64)
            stats_by_cell[cell_id] = {
                "num_train_samples": sample_count,
                "feature_mean": np.mean(raw_values, axis=0).tolist(),
                "feature_std": np.std(raw_values, axis=0).tolist(),
            }
        else:
            raw_values = np.empty((0, len(config.feature_columns)), dtype=np.float64)
            stats_by_cell[cell_id] = {
                "num_train_samples": 0,
                "feature_mean": [],
                "feature_std": [],
            }

        if sample_count < config.min_samples_per_cell:
            thresholds[cell_id] = _fallback_threshold(cell_id, sample_count, "insufficient_samples")
            num_fallback_cells += 1
            continue

        n_clusters = min(config.clusters_per_cell, sample_count)
        if n_clusters <= 0:
            thresholds[cell_id] = _fallback_threshold(cell_id, sample_count, "insufficient_samples")
            num_fallback_cells += 1
            continue

        scaler = StandardScaler()
        scaled_values = scaler.fit_transform(raw_values)
        model = MiniBatchKMeans(
            n_clusters=n_clusters,
            batch_size=min(config.batch_size, sample_count),
            max_iter=config.max_iter,
            random_state=config.random_state,
            n_init=10,
        )
        model.fit(scaled_values)
        distances_by_cluster = model.transform(scaled_values)
        nearest_clusters = np.argmin(distances_by_cluster, axis=1)
        nearest_distances = distances_by_cluster[np.arange(sample_count), nearest_clusters]
        cluster_sizes = np.bincount(nearest_clusters, minlength=n_clusters).astype(int).tolist()

        threshold_stats = summarize_distances(
            nearest_distances,
            percentile=config.threshold_percentile,
            threshold_floor=config.threshold_floor,
        )
        threshold_stats.update(
            {
                "cell_id": cell_id,
                "model_status": "trained",
                "num_train_samples": sample_count,
                "num_clusters": n_clusters,
                "cluster_sizes": cluster_sizes,
            }
        )
        thresholds[cell_id] = threshold_stats
        scalers[cell_id] = scaler
        models[cell_id] = model
        num_models_trained += 1

    return TrainingResult(
        models=models,
        scalers=scalers,
        thresholds=thresholds,
        feature_stats={
            "feature_columns": config.feature_columns,
            "cells": stats_by_cell,
        },
        num_models_trained=num_models_trained,
        num_fallback_cells=num_fallback_cells,
    )


def _fallback_threshold(cell_id: str, sample_count: int, status: str) -> dict[str, Any]:
    return {
        "cell_id": cell_id,
        "model_status": status,
        "num_train_samples": sample_count,
        "num_clusters": 0,
        "cluster_sizes": [],
        "distance_mean": 0.0,
        "distance_std": 0.0,
        "distance_p95": 0.0,
        "distance_p99": 0.0,
        "threshold": 0.0,
    }
