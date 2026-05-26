---
name: Dev
description: Enforce a repository workflow where Codex must read the PRD first, then read repomix-output.xml for project context, implement user requests from spec files, maintain *_processed.md progress files for completed spec work, run tests, and only then refresh repomix-output.xml with repomix.
---

# PRD + Repomix Spec Workflow

Follow this workflow for any request in this repository, especially when the user asks to implement, update, fix, or complete a spec.

## Required Startup

1. Read the PRD first.
   - Prefer a PRD path named by the user.
   - Otherwise look for common PRD files such as `PRD.md`, `prd.md`, `docs/PRD.md`, `docs/prd.md`, or files matching `*prd*.md`.
   - Do not start implementation before reading the PRD. If no PRD can be found, report that and ask for the PRD path.

2. Read `repomix-output.xml` after the PRD.
   - Prefer the repository-root `repomix-output.xml`.
   - Use it to understand project structure, architecture, existing conventions, and relevant files.
   - Treat `repomix-output.xml` as context, not as a substitute for checking live files. Before editing, inspect the current source files directly.
   - If `repomix-output.xml` is missing, report that and continue only after collecting equivalent context from the repository files.

3. Read the requested spec after the PRD and repomix context.
   - If the user names a spec file, read that file.
   - If the request implies a spec but does not name one, search for likely spec files and choose the most relevant one, or ask when the choice is ambiguous.

## Processed Spec File

For every spec file being implemented, create or update a sibling processed file named like the original spec with `_processed` added before the extension.

Examples:

- `spec_1.md` -> `spec_1_processed.md`
- `docs/spec-login.md` -> `docs/spec-login_processed.md`

Use the processed file to record implementation progress. Keep it concise but auditable:

- Original spec path
- Date/time processed
- Checklist of spec items
- Status for each item: `Done`, `Skipped`, or `Blocked`
- Files changed for each completed item when useful
- Test or verification evidence
- Remaining risks or follow-up notes, if any

Update the processed file as work progresses. Do not modify the original spec just to mark progress unless the user explicitly asks.

## Implementation Rules

- Let the PRD define product intent and constraints.
- Let `repomix-output.xml` define broad project context.
- Let the live repository files define the source of truth for code edits.
- Follow existing architecture, naming, style, and test patterns.
- Keep changes scoped to the requested spec.
- Do not overwrite unrelated user changes.
- If a spec conflicts with the PRD, pause and explain the conflict before implementing that part.

## Verification

Before considering the work complete:

1. Run the relevant tests, lint, type checks, build, or validation commands for the changed area.
2. If no obvious command exists, inspect project scripts and choose the closest meaningful verification.
3. Fix failures caused by the implementation.
4. Record the final verification result in the processed spec file.

Do not run the final repomix update until the implementation is complete and the verification commands pass. If verification cannot be run, explain why and do not claim the work is fully complete.

## Final Repomix Update

After all requested work is complete and tests pass, update `repomix-output.xml`.

Preferred order:

1. Run the repository's configured repomix script if one exists.
2. Otherwise run `repomix` from the repository root.
3. If `repomix` is unavailable, report the exact failure and leave `repomix-output.xml` unchanged.

After updating, confirm that `repomix-output.xml` changed as expected.

## Final Response

In the final response, summarize:

- The spec implemented
- The processed spec file created or updated
- Key files changed
- Verification commands and results
- Whether `repomix-output.xml` was refreshed
