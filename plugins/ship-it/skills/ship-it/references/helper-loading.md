# Running helpers delivered as individual files

Use Python 3.11 or newer. Installed plugin directories already provide these files; no download or copying is needed there. On file-by-file hosts, use the host's file-read/download facility to materialize the required bundle into a local cache before running it. Fetch every file from the same skill package revision, retain bytes unchanged and preserve the paths below relative to one skill directory. Never mix versions or import a globally installed sibling module.

| Entry point | Required files in addition to that entry point |
| :-- | :-- |
| `scripts/bookkeeping.py` | `scripts/checkpoint_state.py`, `scripts/convergence.py`, `scripts/validation_reuse.py`, `references/convergence-policy.json` |
| `scripts/checkpoint_state.py` (importable library) | `scripts/convergence.py`, `scripts/validation_reuse.py`, `references/convergence-policy.json` |
| `scripts/convergence.py` (importable library) | `scripts/validation_reuse.py`, `references/convergence-policy.json` |
| `scripts/validation_reuse.py` (importable library) | None |
| `scripts/telemetry.py` | None |
| `scripts/ci_triage.py` | None |
| `scripts/replay_failures.py` | The caller-selected corpus JSON and its case input files; adapter executables are supplied separately |
| `scripts/delivery_benchmark.py` | The caller-selected manifest JSON; executable adapters are supplied separately |

1. Resolve the entry point's row and retrieve every listed dependency before execution. Fetch normal phase references and schemas on demand; they are not Python imports.
2. Save `scripts/` and `references/` as siblings under the same materialized skill directory. Execute an absolute script path, for example `python3 /cache/ship-it/scripts/bookkeeping.py policy --repository /work/repo`. Python then finds sibling imports independently of the current working directory.
3. For an import-only library, validate loading with `python3 -c 'import checkpoint_state'` from the materialized `scripts/` directory; it has no CLI output. CLI helpers accept `--help` for a smoke check.
4. If a file is unavailable, stop before the helper operation and name the missing package path and revision. Retrieve it through the host's package mechanism; do not fabricate a replacement, remove imports or bypass checkpoint checks.

Checkpoints, output artifacts and telemetry remain in their configured persistent data directories, outside this materialized package. A cache directory is disposable code delivery, never durable run state.
