# SPEC 8 Processed - Skipped metric-driven tuning

Original spec path: `src/doc/spec_8.md`

Date/time processed: 2026-05-27 19:19:47 +07:00

## Summary

SPEC 8 is intentionally skipped. The requested direction is to stop adding code whose main purpose is metric-driven comparison, leaderboard tuning, or proving that one variant is better than another. Future planning should focus directly on the core project topic: spatio-temporal behavior clustering, tokenization, association rule mining, anomaly explanation, and usable pipeline artifacts.

## Checklist

- [Done] Read PRD and root `repomix-output.xml`.
- [Done] Read `src/doc/spec_8.md`.
- [Skipped] Implement metric-driven threshold, smoothing, and score-weight tuning.
- [Skipped] Add `src/tune.py`, tuning leaderboard, best-config export, or additional comparison workflow.
- [Done] Record the updated planning direction for future specs.

## Files Changed

- `src/doc/spec_8_processed.md`
- `src/doc/planning_direction.md`
- `src/doc/prd.md`
- `src/doc/spec_5.md`

## Verification Evidence

- [Done] Documentation-only change; no product code was added.
- [Done] `git diff --check -- src/doc/prd.md src/doc/spec_5.md src/doc/spec_8_processed.md src/doc/planning_direction.md`
  - Result: no whitespace errors; Git reported only LF-to-CRLF warnings for existing docs.
- [Done] `repomix.cmd`
  - Result: Repomix v1.14.0 packed `80` files successfully and wrote `repomix-output.xml`.

## Future Planning Rule

New specs should be direct implementation plans for clustering, token/rule mining, explanation, visualization, or report-ready artifacts. Metrics may be used as lightweight sanity checks when already available, but they should not drive new comparison/tuning code unless the user explicitly asks for it.

## Remaining Risks

- Older specs and outputs still mention SPEC 6 comparison work because that work already exists. Treat those references as historical context, not as a request to keep expanding comparison code.
