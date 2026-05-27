# Planning Direction

Date: 2026-05-27

## Current Preference

Future specs should focus directly on the thesis topic:

- spatio-temporal behavior clustering;
- feature/token design for motion, direction, density, brightness, zone, and cluster identity;
- association rule mining with Apriori or FP-Growth;
- anomaly scoring that combines cluster distance with rare token and rule signals;
- explanation text, heatmap/overlay artifacts, and report-ready examples.

## What To Avoid

Do not add new code whose main purpose is to compare variants or prove that one variant is better than another, including:

- tuning leaderboards;
- broad hyperparameter sweeps;
- no-rules vs with-rules comparison workflows;
- ablation runners whose main deliverable is a metric delta;
- best-config selection based on test metrics.

Existing evaluation code can remain available as a sanity check. For future planning, metrics should support the work quietly rather than become the center of the implementation.

## Suggested Next Spec Shape

The next spec should describe a direct research/product step, for example:

- improve per-cell clustering interpretation and centroid summaries;
- mine association rules from richer direction-aware transactions;
- generate alert reasons that connect `cluster=Cx`, motion token, direction token, and rule support;
- create report-ready qualitative cases with frame overlays and concise explanations;
- document the final pipeline from preprocessing to clustering, rules, scoring, and visualization.
