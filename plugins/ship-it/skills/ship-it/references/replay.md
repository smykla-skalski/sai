# Workflow failure replay

Use `scripts/replay_failures.py` to run the shared public failure corpus against the harness adapters available in the evaluation environment. The canonical corpus lives in [`Automaat/environment-as-code/evals/agent-workflows`](https://github.com/Automaat/environment-as-code/tree/main/evals/agent-workflows); pass its `cases.json` with `--corpus`.

The runner validates the corpus's version 1 fields and approved `synthetic-redaction` privacy marker before launching an adapter. It rejects unknown corpus fields, duplicate IDs, private or unreviewed cases, and cases marked as containing source content.

## Adapter protocol

Register each available adapter with `--adapter HARNESS=/absolute/executable`. Harness names are `claude-code`, `codex`, `opencode`, `copilot-cli`, and `sail`. An omitted adapter produces explicit `skipped` results for its applicable cases; a skipped case never counts as a pass.

The runner starts the executable once per applicable case. [`replay-trace.schema.json`](replay-trace.schema.json) defines the machine-readable trace contract. The runner writes this JSON envelope to stdin:

```json
{"schema_version":1,"harness":"codex","case":{"id":"synthetic-case","privacy":{"classification":"public","provenance":"synthetic-redaction","reviewed":true,"contains_source_content":false}}}
```

The real `case` value contains the complete validated synthetic case. The adapter must isolate its run from user repositories and credentials, drive its harness contract, and emit exactly one normalized JSON trace on stdout:

```json
{
  "schema_version": 1,
  "case_id": "synthetic-case",
  "harness": "codex",
  "outcome": "accepted",
  "events": [
    {"sequence": 1, "phase": "resolve", "observation": "ownership_checked"},
    {"sequence": 2, "phase": "complete", "observation": "no_repository_mutation"}
  ],
  "cost": {
    "turns": 2,
    "tool_calls": 3,
    "permission_decisions": 0,
    "input_tokens": null,
    "output_tokens": null,
    "elapsed_ms": 1200,
    "retries": 0
  }
}
```

Events normalize harness-specific activity into the ship-it phase vocabulary and the case's declared grading observation tokens. An undeclared observation fails the case and is reduced to a count so arbitrary adapter text cannot enter the report. Sequence numbers start at one and remain contiguous. A `complete` event is final, an `accepted` trace ends in `complete`, and a `waiting` trace ends in `wait`. Outcomes are `accepted`, `rejected`, `blocked`, `cancelled`, `failed`, or `waiting`. Every cost field is a non-negative integer or `null`; adapters never estimate unavailable counters.

Adapter stderr is never copied into the report. The report stores only case and harness IDs, normalized phases and observation tokens, status, stable error codes, and numeric cost. It excludes task text, initial state, expected behavior, prompts, tool arguments, tool output, paths, URLs, credentials, and source content.

## Grading and release gate

A case passes only when the trace contains every `required_observations` token, contains no `failure_observations` token, follows terminal phase rules, and reaches the expected final outcome for its failure mode. Duplicate work and persistent tool failures end `blocked`; permission-loop, stale-validation, and compaction-resume cases end `accepted`; incomplete delivery remains `waiting`. Invalid traces, timeouts, nonzero adapter exits, and grading regressions fail the run. The process exits `1` when any available supported harness fails, so the command can gate a portable plugin release.

The report aggregates cost only for passing traces whose outcome is `accepted`. It reports per-harness accepted-task counts and mean counters, leaving unavailable counters as `null`.

```sh
python3 plugins/ship-it/skills/ship-it/scripts/replay_failures.py \
  --corpus /path/to/environment-as-code/evals/agent-workflows/cases.json \
  --adapter claude-code=/absolute/path/to/claude-adapter \
  --adapter codex=/absolute/path/to/codex-adapter \
  --adapter opencode=/absolute/path/to/opencode-adapter \
  --adapter copilot-cli=/absolute/path/to/copilot-adapter \
  --adapter sail=/absolute/path/to/sail-adapter \
  --output /tmp/ship-it-replay.json
```
