# AGENTS.md — Engineering Rules of Engagement

## Operating mode
- Do a quick repo recon before coding: identify build/test/lint/typecheck commands and main entrypoints.
- Keep changes minimal and aligned with existing patterns. No drive-by refactors.
- Break work into small, reviewable steps. If scope is large, propose a plan and implement step 1 first.

## Definition of done (must satisfy before final answer)
- Code builds/runs.
- Lint/format passes (or explain exact failures).
- Tests pass (or add tests; if impossible, document manual verification steps).
- Any behavior change is documented (README/docs/changelog/comments as appropriate).
- Final response includes:
  - What changed + why
  - Files changed
  - Commands run + results
  - How to verify manually

## Change safety
- Ask before:
  - adding production dependencies
  - changing public APIs/contracts
  - modifying auth/security-sensitive logic
  - large refactors or file moves

## Testing rules
- Prefer adding/adjusting tests for new behavior.
- If tests are missing in the repo, add at least minimal coverage where practical.
- Tests should be deterministic and not rely on external networks unless the repo already does.

## Security rules
- Never print or commit secrets.
- Validate untrusted input at boundaries.
- Avoid injection risks (shell, SQL, template, command args). Use safe APIs/parameterization.
- Prefer least-privilege and fail-closed behavior on auth/permissions.

## Style and maintainability
- Clear names, small functions, straightforward control flow.
- Separate pure logic from I/O; keep side-effects contained.
- Handle errors explicitly; no silent catches.

## Dependencies
- Reuse existing libraries. If a new dependency is needed, justify and request approval.

## Concurrency
- If multiple threads/agents are used, do not edit the same files in parallel.
