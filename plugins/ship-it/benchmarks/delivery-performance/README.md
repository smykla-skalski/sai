# Ship-it delivery performance benchmark

This benchmark compares two ship-it contracts against five public synthetic cases: documentation-only work, an ordinary fix, a confirmed security defect, a moving default branch, and a native fixture failure.

The runner sends the same case text, acceptance criteria, result schema, model, reasoning effort, sandbox, adapter, and host environment to both contracts. Only the contract directory and recorded source revision differ. The ordinary-fix and moving-default cases exercise resumption. The ordinary-fix case also starts review and test workers concurrently before a user interruption.

Codex runs each case in a read-only simulation and returns a strict normalized result. The persisted report contains counters, decisions, digests, timings, and tool metadata. It excludes prompts, model transcripts, tool output, paths, repository source, credentials, and environment variables.

## Run

Extract the immutable baseline tar into an empty scratch directory, then run:

```sh
python3 plugins/ship-it/skills/ship-it/scripts/delivery_benchmark.py run \
  --cases plugins/ship-it/benchmarks/delivery-performance/cases.json \
  --result-schema plugins/ship-it/benchmarks/delivery-performance/result.schema.json \
  --baseline-dir "$BASELINE_ROOT/plugins/ship-it/skills/ship-it" \
  --candidate-dir "$PWD/plugins/ship-it/skills/ship-it" \
  --baseline-revision 913312e7b3580ae7ad3bc4f9a484072585deed87 \
  --candidate-revision 41133043ec6fbde4da57bab57d5b77bb47e601ed \
  --baseline-artifact-sha256 34e5cea99f80bb8529f6ce0dbb0ea5470c67aaee480c8c49c0945e73ea1c7c8d \
  --baseline-harness-revision 226a561bd260eeb75102d0632855a139c0519154 \
  --candidate-harness-revision ba97832ee25138cc4295806f522b6a96fa02b2c0 \
  --model gpt-5.6-sol \
  --reasoning-effort high \
  --samples 1 \
  --output benchmark-report.json
```

Validate a saved report with:

```sh
python3 plugins/ship-it/skills/ship-it/scripts/delivery_benchmark.py validate \
  --cases plugins/ship-it/benchmarks/delivery-performance/cases.json \
  --report plugins/ship-it/benchmarks/delivery-performance/report.json
```

The measured report uses one sample for each case and variant. Run with a larger `--samples` value before making timing claims.

## Metric definitions

- `elapsed_ms` measures the complete Codex subprocess from prompt submission to validated output
- `active_ms` equals elapsed time because the read-only simulation executes no external approval, hosted-service, or resource-queue waits
- `waits` records workflow waits selected by the contract; duration stays `null` when the synthetic case supplies no measured duration
- `duplicate_gate_executions` counts a gate dispatched again with unchanged relevant inputs
- `approval_requests` counts requests made in the measured continuation and excludes previously granted approval history
- `redundant_approval_requests` counts a request for permission already recorded in the scenario
- `user_interruptions` comes from the scenario, including interruptions before resumption
- `confirmed_defect_detected`, `required_delivery_blocker_present`, and `untested_criteria` protect required validation from speed optimizations

The runner returns exit code 1 when either variant loses a required blocker or explicit untested criterion. Candidate replay and unchanged-input cases also fail when they request approval again or repeat a gate.
