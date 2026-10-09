# Portable workflow telemetry

Use this contract only when checkpoint bookkeeping policy enables telemetry. Telemetry defaults off; then create no run state or event file. When enabled, record one privacy-safe event when a run starts, after each completed phase, and when it finishes. Telemetry failures never block or change the workflow outcome; report the diagnostic and continue.

## Recorder

Locate `scripts/telemetry.py` relative to this reference's parent skill directory. Run it directly with Python 3.11 or newer.

After task resolution and checkpoint reconciliation, use the portable checkpoint ID as the telemetry task ID. This gives every harness the same privacy-safe SHA-256 task identity without recording its source. A caller outside ship-it must supply an equivalent opaque task ID that contains no prompt, URL, path or source content. Start the run before repository changes:

```bash
python3 <skill-dir>/scripts/telemetry.py begin --task-id <id> --harness <harness> --provider <provider> --model <model> --role primary
```

Keep the returned `run_id` for the workflow. After each phase, record the cumulative metrics the harness exposes:

```bash
python3 <skill-dir>/scripts/telemetry.py record --run-id <id> --phase implement --turns 8 --tool-calls 21 --elapsed-ms 92000
```

Use `null` by omitting any unavailable counter. Never estimate a counter. Override `--provider`, `--model` or `--role` on an event when a worker differs from the primary agent. Finish after success or a hard stop:

```bash
python3 <skill-dir>/scripts/telemetry.py finish --run-id <id> --outcome accepted
```

Outcomes are `accepted`, `rejected`, `blocked`, `cancelled` and `failed`. Accepted means the task reached its repository-defined delivery state, normally a merged PR.

## Stable vocabulary

- Roles: `primary`, `subagent`, `validator`, `guardian`, `synthetic`, `probe`
- Phases: `resolve`, `orchestrate`, `explore`, `branch`, `implement`, `publish`, `review`, `test`, `pr`, `wait`, `fix`, `merge`, `complete`
- Harness, provider and model are safe identifiers. Use the literal `unknown` when a value is unavailable
- Counters: `turns`, `tool_calls`, `permission_decisions`, `compactions`, `input_tokens`, `output_tokens`, `elapsed_ms`, `retries`, `findings`, `checks`, `human_interventions`, `failed_commands`, `approval_wait_ms`, `ci_failures`, `ci_recurrences`, `ci_resolutions`

CI triage counters are cumulative and privacy-safe. `ci_failures` counts unique failure IDs in the checkpoint, `ci_recurrences` counts observations linked to an earlier recurrence key, and `ci_resolutions` counts failures that became resolved. Recompute them from durable checkpoint records for each event; consumers use the latest value per run and never sum cumulative snapshots. A repeated observation of the same revision/workflow/job/attempt changes none of them. Derive `retries` from durable `rerunsUsed` values so only successful provider rerun requests authorized by repository policy or explicit approval count.

## Event contract

The recorder appends NDJSON to `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/telemetry/events.ndjson` and stores private run identity under the adjacent `runs/` directory. Directories use mode `0700`; files use `0600`.

Every event contains `schema_version`, `event_id`, `emitted_at`, `run_id`, `task_id`, `event`, `harness`, `provider`, `model`, `role`, `phase`, `metrics` and `outcome`. [telemetry.schema.json](telemetry.schema.json) is the current version-2 contract; [telemetry-v1.schema.json](telemetry-v1.schema.json) preserves the historical contract. Version 2 adds the required CI counters. Consumers dispatch each NDJSON event by version, accept both bundled versions, and reject unsupported future versions. Unavailable counters and non-final outcomes are JSON `null`.

The schema has no field for prompt text, task descriptions, tool arguments, tool-output bodies, credentials, file content, source code, repository paths or URLs. Do not add these values to identifiers. A telemetry event is operational metadata, never an execution transcript.
