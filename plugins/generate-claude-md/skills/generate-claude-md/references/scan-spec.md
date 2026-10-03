# Codebase Scan Specification

Instructions for the `Explore` agent that gathers the facts a CLAUDE.md is built
from. The agent reads, never writes. It returns a compact structured summary —
not file dumps. Keep the summary tight; the synthesis step turns it into a lean
file, so raw volume here just gets discarded.

## What to read

- **Package / build manifests**: `package.json`, `pyproject.toml`, `go.mod`,
  `Cargo.toml`, `pom.xml`, `build.gradle`, `Gemfile`, `composer.json`.
- **Task runners**: `Makefile`, `Taskfile.yml`, `justfile`, `mise.toml`,
  `package.json` scripts, `pyproject.toml` `[tool.*]` script tables.
- **CI**: `.github/workflows/*`, `.gitlab-ci.yml`, `.circleci/config.yml` — the
  real build/test/lint commands the project runs live here.
- **Lint/format config**: `.eslintrc*`, `biome.json`, `.prettierrc*`, `ruff.toml`,
  `.golangci.yml`, `rustfmt.toml`, `.editorconfig`.
- **Test config**: `jest.config.*`, `vitest.config.*`, `pytest.ini`,
  `pyproject.toml` `[tool.pytest]`, `go` test layout, `conftest.py`.
- **Pre-commit / hooks**: `.pre-commit-config.yaml`, `.husky/`, `lefthook.yml`.
- **Existing context files**: `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*`,
  `AGENTS.md`, `.cursorrules`, `.windsurfrules` — preserve and reconcile, don't
  discard.
- **README.md**: read it to know what NOT to duplicate.
- **Top-level layout + entry points**: enough to describe component relationships
  (where handlers/services/data-access/domain logic live), not to enumerate files.
- **`git log --oneline -20`**: infer the commit-message convention.

## What to return

A structured summary with exactly these fields. Use "none found" when a field is
empty — do not invent.

- **project_name** and a one-line purpose (only if not obvious from the name).
- **commands**: build, test (full), test (single — infer the framework's syntax),
  lint, format, run/dev, and any pre-commit gate. Give exact invocations with flags.
- **architecture**: 3–6 bullet points on component relationships and enforced
  boundaries, each with a `file:line` anchor where one exists. Name the one or two
  entry points that matter (main, router, webhook handler, CLI root).
- **style_deltas**: conventions that differ from the language default, each with
  the config file that owns the rule. Empty if style is just formatter defaults.
- **testing**: framework, single-test command, mock strategy, fixture/teardown or
  integration prerequisites (Docker, env vars, live services).
- **repo_etiquette**: commit convention (from git log), branch/PR rules (from CI
  or CONTRIBUTING).
- **gotcha_candidates**: non-obvious traps detectable from code — custom test
  setup/teardown, migration ordering, env vars required at import time, generated
  directories, eventual-consistency comments, `// HACK`/`// NOTE` markers. Each
  with `file:line`.
- **boundaries**: generated/vendored paths, secret handling, off-limits dirs.
- **readme_headings**: the section headings present in README.md, so synthesis can
  avoid duplicating them.
- **existing_context**: contents/topics of any existing CLAUDE.md, `.claude/rules/`,
  or AGENTS.md, and whether an AGENTS.md exists (drives cross-tool bridging).
- **commit_convention**: the observed format (e.g. conventional commits, scope
  required) inferred from recent history.

## Rules for the agent

- Verify commands exist where cheap: a command named in CI or a Makefile target is
  trustworthy; flag anything inferred/guessed as `(unverified)`.
- Prefer the command form CI uses over the one in the README — CI is ground truth.
- Do not return file contents or long excerpts; return facts and `file:line` anchors.
- If the repo is multi-language or a monorepo, note the sub-projects and where each
  one's commands live (this drives whether to split into nested CLAUDE.md / rules).
