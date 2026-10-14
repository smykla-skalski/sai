# Validation result validity

Read this contract before reserving validation or reconciling a changed revision. Use the bookkeeping helper's observable decisions; do not infer validity from unchanged HEAD, an operation name, or an agent summary.

## Relevant input manifest

Write one JSON manifest per review, test or local quality gate outside the worktree, then pass its path through `--inputs-json`. Include every acceptance path and transitive dependency the gate covers. Use `source: ["."]` when a narrower scope cannot establish independence. A directory includes new and deleted committed files, modes and Git object identities. Dependencies include locks, shared code, fixtures and executable test helpers. Policy paths include bundled policy references and applicable repository instructions; `policyFacts` retains live release requirements, gate selectors and external policy. Runtime facts include tool versions, container images, services and other inputs that Git cannot observe.

```json
{
  "repository": "/absolute/worktree",
  "source": ["plugins/ship-it", "tests"],
  "dependencies": ["ruff.toml"],
  "policy": ["CLAUDE.md", "plugins/ship-it/skills/ship-it/references"],
  "command": ["mise", "exec", "--", "python", "-m", "unittest", "discover", "-s", "tests"],
  "environment": {"variables": ["PATH"], "facts": {"python": "3.14.8"}},
  "policyFacts": {"requiredChecks": [], "requiredApprovals": 1}
}
```

The helper captures committed contents from a clean worktree at the checkpoint revision, hashes declared environment variable values without retaining secrets, and binds the task's acceptance criteria. It does not execute `command`. Symlink scopes fail closed because the committed link cannot prove its target contents. External inputs require explicit content or version facts; an inaccessible, mutable or unknown dependency makes the result unverifiable. Never omit an input merely to obtain a cache hit.

## Assess, reserve, finish

```text
bookkeeping.py assess --checkpoint FILE --kind review|test|quality --revision HEAD --inputs-json MANIFEST
bookkeeping.py reserve --checkpoint FILE --id OPERATION --kind review|test|quality --revision HEAD --inputs-json MANIFEST
bookkeeping.py finish --checkpoint FILE --id OPERATION --result-json OBJECT
```

Run `assess` after each source, dependency, command, environment or policy change, before requesting a reservation. It persists `convergence.validityDecisions` even when another broad run has no remaining allowance. Each decision names the current revision, prior operation/revision and precise changed dimensions or unverifiable/incomplete evidence. Invalid results mark corresponding checkpoint gate verdicts stale. Keep these decisions and all consumed counters across resume. With evidence enabled, apply that invalidation to the selected revision record before advancing; checkpoint attestations alone never satisfy enabled evidence.

`reserve` recomputes validity under the checkpoint lock. With identical relevant inputs and a verified completed output, it returns `dispatch: false`, the original receipt/result and the validity decision, even when the caller has a new operation ID or the branch has an unrelated integration commit. No counter or explicit allowance is consumed. Refused dispatch persists detected invalidations while rolling back attempted spending. A failed or blocked result remains failed or blocked; it never attests a passing gate. A pending receipt remains consumed and cannot authorize another attempt. Legacy opaque `--inputs` receipts retain retry behavior but lack verifiable input/output provenance and cannot carry results to another revision.

Execute only on `dispatch: true`. Structured completion requires a non-empty persistent output artifact's absolute path in `result.output`; the helper records its SHA-256 and rechecks the reserved inputs at completion. A review also retains `findings`. Missing, modified or unreadable output is unverifiable. Preserve artifacts for the task's delivery lifetime, including across compaction and worktree integration.

A verified passing review/test/quality result records an exact-current-revision gate attestation with original operation, original revision, input fingerprint and output artifact digest. With evidence enabled, copy only that attestation and its original route provenance into the current revision's record; preserve the original execution identity rather than inventing a fresh worker. Test reservation rechecks reusable review inputs and output provenance at its prerequisite boundary, including artifact corruption after completion. Reuse never spends a new review cycle or counts as a new tester dispatch.

## Changed behavior and focused recovery

Changed inputs invalidate the affected gate; they do not grant another broad pass. Apply the retained convergence policy and scoped authorization. Focused recovery records each affected acceptance criterion, correction and executed reproduction separately in `convergence.acceptanceRecovery`. Carry unaffected criterion results only with their input/output provenance. A missing, failed or unverifiable criterion remains unsatisfied; focused success does not fill missing broad evidence or promote an unrelated failed result. Keep the original counters and receipt immutable.

After default-branch integration, assess every affected review/test/quality manifest. Unchanged source plus unchanged dependencies, invocation, runtime and policy carries the verified result to the current PR head with explicit provenance. Changed scope or inputs require focused verification or a permitted gate; unchanged branch filenames alone cannot prove runtime independence.

Repository-required CI, approval and merge checks remain live forge requirements on the revision required by repository policy. They are outside this helper's reusable kinds. Local quality reuse does not satisfy hosted CI, and historical approvals do not satisfy current-head review requirements.
