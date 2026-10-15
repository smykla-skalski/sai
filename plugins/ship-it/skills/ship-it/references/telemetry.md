# Portable workflow telemetry

Telemetry defaults on for normal runs; raw events stay entirely local. A repository may disable it with `.sai/ship-it-bookkeeping.json`; then create no run state or event file. When enabled, record privacy-safe start and completion observations for each phase, observed waits and user interruptions, and the final outcome. Telemetry failures never block or change the workflow outcome; report the diagnostic and continue.

## Recorder

Locate `scripts/telemetry.py` relative to this reference's parent skill directory. Run it directly with Python 3.11 or newer.

After task resolution and checkpoint reconciliation, use the portable checkpoint ID as the telemetry task ID. This gives every harness the same privacy-safe SHA-256 task identity without recording its source. A caller outside ship-it must supply an equivalent opaque task ID that contains no prompt, URL, path or source content. Start the run before repository changes:

```bash
python3 <skill-dir>/scripts/telemetry.py begin --task-id <id> --harness <harness> --provider <provider> --model <model> --role primary
```

`begin` is idempotent by task ID. On resume it returns the existing `run_id` and does not append a second start event. Keep that ID in the workflow. Use one safe observation ID for both boundaries of each phase:

```bash
python3 <skill-dir>/scripts/telemetry.py observe --run-id <id> --event phase_started --phase implement --observation-id implement-1
python3 <skill-dir>/scripts/telemetry.py observe --run-id <id> --event phase_completed --phase implement --observation-id implement-1 --turns 8 --tool-calls 21
```

Record only waits observed directly. The supported kinds are `approval`, `hosted_service` and `resource_queue`. Pair start and completion with the same safe observation ID:

```bash
python3 <skill-dir>/scripts/telemetry.py observe --run-id <id> --event wait_started --phase publish --observation-id approval-1 --wait-kind approval
python3 <skill-dir>/scripts/telemetry.py observe --run-id <id> --event wait_completed --phase publish --observation-id approval-1 --wait-kind approval
```

Record a user interruption with `--event user_interruption` and a unique observation ID. Add `--worker-id <safe-id>` to worker phase boundaries. Worker durations remain separate in the report and are never added to primary active work or delivery elapsed time. Override `--provider`, `--model` or `--role` when a worker differs from the primary agent.

Use `null` by omitting an unavailable counter. Never estimate a duration, wait or counter. Finish after success or a hard stop:

```bash
python3 <skill-dir>/scripts/telemetry.py finish --run-id <id> --outcome accepted
```

Outcomes are `accepted`, `rejected`, `blocked`, `cancelled` and `failed`. Accepted means the task reached its repository-defined delivery state, normally a merged PR.

Generate a local JSON report by run or task ID:

```bash
python3 <skill-dir>/scripts/telemetry.py report --run-id <id>
python3 <skill-dir>/scripts/telemetry.py report --task-id <checkpoint-id>
```

The report derives delivery elapsed time from run boundaries. It computes primary active work from the union of completed primary phase intervals minus the union of observed waits, so overlaps are never double-counted. It reports each worker independently, keeps absent durations and waits as `null`, and marks incomplete observation pairs. Repeated review, test and quality-gate counts come from cumulative `review_cycles`, `test_runs` and `full_quality_gate_runs` counters after subtracting the first run. User interruptions come from interruption observations or the cumulative `user_interruptions` counter.

## Stable vocabulary

- Roles: `primary`, `subagent`, `validator`, `guardian`, `synthetic`, `probe`
- Phases: `resolve`, `orchestrate`, `explore`, `branch`, `implement`, `publish`, `review`, `test`, `pr`, `wait`, `fix`, `merge`, `complete`
- Harness, provider and model are safe identifiers. Use the literal `unknown` when a value is unavailable
- Events: `run_started`, `phase_started`, `phase_completed`, `wait_started`, `wait_completed`, `user_interruption`, `run_finished`
- Wait kinds: `approval`, `hosted_service`, `resource_queue`
- Counters: `turns`, `tool_calls`, `permission_decisions`, `compactions`, `input_tokens`, `output_tokens`, `elapsed_ms`, `retries`, `findings`, `checks`, `human_interventions`, `failed_commands`, `approval_wait_ms`, `ci_failures`, `ci_recurrences`, `ci_resolutions`, `review_cycles`, `test_runs`, `full_quality_gate_runs`, `user_interruptions`

CI triage counters are cumulative and privacy-safe. `ci_failures` counts unique failure IDs in the checkpoint, `ci_recurrences` counts observations linked to an earlier recurrence key, and `ci_resolutions` counts failures that became resolved. Recompute them from durable checkpoint records for each event; consumers use the latest value per run and never sum cumulative snapshots. A repeated observation of the same revision/workflow/job/attempt changes none of them. Derive `retries` from durable `rerunsUsed` values so only successful provider rerun requests authorized by repository policy or explicit approval count.

## Event contract

The recorder appends NDJSON to `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/telemetry/events.ndjson`, stores each idempotent event under the adjacent `events/` directory, and stores private run identity under `runs/`. Event files make duplicate checks constant-time and recover an append interrupted after the event became durable. Directories use mode `0700`; files use `0600`.

Every event contains `schema_version`, `event_id`, `emitted_at`, `run_id`, `task_id`, `event`, `harness`, `provider`, `model`, `role`, `phase`, `observation_id`, `worker_id`, `wait_kind`, `metrics` and `outcome`. Repeating an event with the same run, event, phase and observation ID returns the original identity without appending another record; worker phase identity also includes the worker ID, and final-event identity includes the outcome so a blocked run can resume and later finish accepted. [telemetry.schema.json](telemetry.schema.json) is the current version-4 contract; [telemetry-v2.schema.json](telemetry-v2.schema.json) [telemetry-v3.schema.json](telemetry-v3.schema.json) and [telemetry-v1.schema.json](telemetry-v1.schema.json) preserve historical contracts. Version 2 added CI counters. Version 3 adds timing observations and report counters. Consumers dispatch each NDJSON event by version, accept every bundled version, and reject unsupported future versions. Unavailable counters, missing observations and non-final outcomes are JSON `null`.

The schema has no field for prompt text, task descriptions, tool arguments, tool-output bodies, credentials, file content, source code, repository paths or URLs. Do not add these values to identifiers. The recorder reads and writes only the local telemetry directory and performs no remote transmission. The completion workflow publishes only the aggregate described below. A telemetry event is operational metadata, never an execution transcript.

## Weighted token cost

When telemetry is enabled, record one `usage` observation for each disjoint request or phase delta exposed by the host. Use the actual worker role and ID for worker usage. Record unavailable phases with omitted counts; never invent usage from context size or treat missing figures as zero. Do not record overlapping parent and worker totals. `input` means uncached input, exclusive of cache reads and writes; subtract cache tokens from inclusive host input totals before recording. When a host exposes only a run total, attribute it to `complete` and leave unavailable phase attribution unknown.

```bash
python3 <skill-dir>/scripts/telemetry.py usage --run-id <id> --phase implement --observation-id request-1 --input-tokens 1000 --cache-write-tokens 0 --cache-read-tokens 500 --output-tokens 200 --input-price 2 --cache-read-price 0.2 --output-price 8
```

Prices are explicit USD per million tokens for the observed provider/model and billing tier, including the actual cache-write duration. The example prices illustrate the interface; they are not a pricing catalogue. Read prices from verified host billing metadata or current provider pricing; omit unavailable prices. Supply explicit zero only for a host-confirmed zero count. A zero count needs no price. Preserve one stable observation ID per usage delta across retries. Events retain only numeric token counts, decimal prices and existing safe execution identifiers. Record no raw host transcript, billing account, tool arguments or credentials.

- Claude Code: use exposed `usage` counters, including cache creation/read tokens; choose the price for the reported cache lifetime. Keep cache writes and reads separate from uncached input.
- Codex: use host-exposed usage when available, subtract cached input from inclusive input tokens, and retain unavailable cache writes as unknown. This skill has no access to hidden session counters.
- Copilot CLI and opencode: use provider usage exposed by the host under the same normalization contract. Missing counters or unavailable billing prices stay unknown.
- Every host: if no usage interface is exposed, emit an observation without token/price flags for the affected phase and role. Never substitute a different host's figures.

`report` includes `token_cost.total`, `by_phase` and `by_role`. Each group exposes `estimated_usd` (null when any observation is unknown), `known_estimated_usd` (a partial subtotal), `unknown_observations` and `usage_observations`. All values are estimates, not a provider invoice. With no usage observations the total remains null. Cost uses disjoint usage events, never the existing cumulative diagnostic counters. Historical v1-v3 completed phases remain unknown even when a resumed run adds priced usage. A completed v4 phase without any usage delta also contributes unknown coverage; repeated snapshots of the same phase, role and worker count once.

After a confirmed merge, finish the run and generate `report --run-id <id> --markdown`. The Markdown renderer includes only the plugin version, opaque run ID, `token_cost.total` and phase/role cost groups. Save that rendered output to a scratch body file and post it with `gh pr comment --body-file` after confirming the merge. Label null amounts **unknown** and partial subtotals **known subtotal**, never a complete total. Check the PR for the same run ID before posting to avoid duplicate comments after resume. No raw events, local paths or identity metadata belong in the comment. When telemetry is disabled, perform none of the usage recording, report generation or PR cost publication steps.
