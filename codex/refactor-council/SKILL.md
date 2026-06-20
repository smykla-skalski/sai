---
name: refactor-council
description: Refactoring review through seven sourced refactoring personas (Fowler, Uncle Bob, Feathers, Beck, Metz, Ousterhout, Tornhill) plus an adversarial pass, by reusing the source workflow under `claude/refactor-council`. Use when the user wants a refactoring review of code, a module, an app, or a diff.
metadata:
  short-description: Refactoring review through opposed persona lenses
---

# Refactor Council

Use this skill when the user wants a refactoring review of a file, module, directory, app, or diff. It scans the target for code smells and git hotspots, reviews it through seven opposed refactoring lenses, synthesizes a safety-first sequenced refactoring plan, then adversarially stress-tests that plan before returning it.

This is a Codex wrapper around `claude/refactor-council/skills/refactor-council/SKILL.md`. Reuse the source workflow, persona dossiers, and scripts from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- The user asks to "refactor this", "how should I refactor X", for a "refactoring review", "what should I clean up here", or "is this worth refactoring".
- The user shares a path, file, directory, or diff and wants structured, prioritized, safety-checked refactoring guidance.

## Do Not Use This Skill

- For a quick syntax check or lightweight lint pass.
- For a correctness/security/performance audit on its own - this council preserves behavior by definition. Use a staff-level or language-specific review for those (the adversary pass only partially covers them).

## Source Material

- Source skill: `claude/refactor-council/skills/refactor-council/SKILL.md`
- Persona dossiers: `claude/refactor-council/skills/refactor-council/references/` (one `*-deep.md` per persona, plus `personas.md` and `refactoring-catalog.md`)
- Persona definitions: `claude/refactor-council/agents/` (one `*.md` per persona, plus `refactor-adversary.md`)
- Scan scripts: `claude/refactor-council/skills/refactor-council/scripts/` (`smell_scan.py`, `hotspots.py`)
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Read each persona's dossier before speaking in that persona's voice.

## Workflow

1. **Setup.** Resolve the target (path, `@file`, directory, or `diff`). Read `refactoring-catalog.md` so you name smells and refactorings precisely and enforce the safety discipline.
2. **Scan.** Run the shared scanners and check the test net:
   - `python3 claude/refactor-council/skills/refactor-council/scripts/smell_scan.py <target> --human`
   - `python3 claude/refactor-council/skills/refactor-council/scripts/hotspots.py <target> --since 12.month --human` (git repos only)
   - Detect tests near the target (test/, tests/, `*_test.*`, `*.test.*`, `*.spec.*`, `__tests__/`).
   Assemble a compact evidence bundle: top smells (located), top hotspots + coupling pairs, test-net status.
3. **Persona review (see Codex execution notes for HOW).** Produce one review per persona, each speaking strictly in that persona's voice from their dossier, returning the Persona output contract from the source SKILL.
4. **Synthesize.** Write one integrated review using the source SKILL's Synthesis output shape: Convergence, Disagreement, Per-persona top-3, Safety net status, a sequenced smallest-first refactoring plan (characterization-tests-first when untested; structural vs behavioral separated), and an explicit "Do NOT refactor" list. Surface disagreement; do not flatten it.
5. **Adversarial pass.** Red-team the synthesized findings and plan against the `refactor-adversary` checklist: behavior preservation, safety net, wrong-abstraction risk, over-decomposition, cold-code/ROI, scope creep, sequencing, and latent correctness/security/concurrency/perf. Return SHIP / SHIP WITH CHANGES / HOLD and fold the verdict into the plan before presenting it.

## Codex execution notes - subagent spawning

Codex subagent fan-out is fragile at this council's size. As of mid-2026: the default `agents.max_threads` is **6** (seven personas plus an adversary exceed it), completed subagents do not free their slot unless explicitly closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)), and subagents can finish without returning their payload ([#16051](https://github.com/openai/codex/issues/16051)). Therefore:

- **Default: sequential / inline.** Do NOT fan out to one subagent per persona by default. Adopt each persona's lens in turn yourself - read the dossier, produce that persona's review in their voice, move to the next - then synthesize, then run the adversarial pass inline. This sidesteps the thread cap and the quota-leak and handoff bugs entirely, and is the reliable Codex path.
- **Optional parallel mode (only if the user asks and has raised `agents.max_threads`).** Cap concurrency at **<= 5** so the manager thread is not starved; run the personas in batches (e.g. two waves), **`close_agent` each reviewer as soon as it returns** (completion alone does not free the slot), and **verify each reviewer actually returned a payload** before synthesizing - re-run any missing one inline. Never assume all spawned reviewers reported.
- Keep the adversarial pass as a final step regardless of mode; run it inline if spawning is unreliable.

## Codex Notes

- Ignore Claude-only frontmatter and runtime wiring such as `allowed-tools`, `user-invocable`, `argument-hint`, `$ARGUMENTS`, and `CLAUDE_SKILL_DIR`.
- Parse flags from the user request: `--no-scan`, `--no-adversary`, `--since`, `--personas`.
- Infer the target from the user request and local context before asking follow-up questions; if no target can be resolved, ask which file/dir/diff to review rather than inventing one.
- Persona dossiers are private review aids derived from public writing - keep persona framing internal; if the review leaves the team, restate the argument in your own voice.
