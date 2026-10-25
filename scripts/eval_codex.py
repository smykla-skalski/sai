#!/usr/bin/env python3
"""Run a plugin's `claude plugin eval` cases on Codex and grade them.

Each case runs through `codex exec --json` in a fresh workspace, scaffolded by
the case's scaffold script, with the plugin installed into an isolated Codex
home. Codex has no Claude tool names, so the graders are mapped onto its event
stream:

    regex                 the last message, or a workspace file (target.path)
    tool_used Read        commands whose text matches input_match; brace
                          groups such as references/{a,b}.md are expanded
    tool_used Skill       commands that read skills/<name>/SKILL.md
    tool_used Edit/Write  1 when any workspace file changed or appeared, else 0
    tool_used Agent       0 unless an event type outside the known set appears
    llm                   three `claude -p` votes on the rubric, majority wins

Other tool_used graders are reported as unsupported and do not count.

Usage:
    scripts/eval_codex.py plugins/humanize [--runs 3] [--case GLOB]
        [--model MODEL] [--judge-model sonnet] [--out results.json]

Output: one NDJSON "run" record per run, then a "summary" record. --out writes
the replies and changed files, which eval_review.py reads.
Exit codes: 0 every run passes, 1 a run fails, 2 usage or setup error.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from _eval_common import (
    Case,
    CodexSandbox,
    EvalError,
    Grader,
    agent_env,
    codex_prompt,
    codex_sandbox,
    load_cases,
    run_command,
    skill_name,
    snapshot,
    stream_json,
)

DEFAULT_RUNS: Final[int] = 3
DEFAULT_TIMEOUT_SECONDS: Final[int] = 900
JUDGE_TIMEOUT_SECONDS: Final[int] = 300
JUDGE_VOTES: Final[int] = 3
JUDGE_ARGV: Final[tuple[str, ...]] = (
    "claude",
    "-p",
    "--output-format",
    "text",
    "--setting-sources",
    "project",
    "--strict-mcp-config",
    "--no-session-persistence",
    "--disable-slash-commands",
)
KNOWN_ITEM_TYPES: Final[frozenset[str]] = frozenset(
    {
        "agent_message",
        "command_execution",
        "file_change",
        "reasoning",
        "todo_list",
        "web_search",
    },
)
BRACE_GROUP: Final[re.Pattern[str]] = re.compile(r"(\S*?)\{([^{}\s]*,[^{}\s]*)\}(\S*)")
VERDICT: Final[re.Pattern[str]] = re.compile(r"VERDICT:\s*\**\s*(PASS|FAIL)")
JUDGE_PROMPT: Final[str] = (
    "You are grading an AI assistant's output against a rubric. Check each "
    "rubric condition against the output step by step, then end with one final "
    "line that is exactly VERDICT: PASS or VERDICT: FAIL."
    "\n\n<rubric>\n{rubric}\n</rubric>\n\n<output>\n{output}\n</output>"
)


@dataclass
class Run:
    """One Codex run of one case."""

    case: Case
    number: int
    reply: str = ""
    commands: list[str] = field(default_factory=list)
    item_types: set[str] = field(default_factory=set)
    before: dict[str, str] = field(default_factory=dict)
    after: dict[str, str] = field(default_factory=dict)

    @property
    def changed_files(self) -> dict[str, str]:
        """Return files that the run created or changed, with their new text."""
        return {
            path: text
            for path, text in self.after.items()
            if self.before.get(path) != text
        }


# -- Grading -----------------------------------------------------------------


def expand_braces(command: str) -> str:
    """Expand shell brace groups, so a{b,c}d reads as abd acd."""
    while match := BRACE_GROUP.search(command):
        head, options, tail = match.groups()
        words = " ".join(f"{head}{option}{tail}" for option in options.split(","))
        command = command[: match.start()] + words + command[match.end() :]
    return command


def tool_count(run: Run, grader: Grader, skill: str) -> int | None:
    """Return how often a Claude tool was used, mapped onto Codex events."""
    tool = grader.meta.get("tool")
    commands = [expand_braces(command) for command in run.commands]
    if tool == "Read":
        pattern = re.compile(str(grader.meta.get("input_match", "")))
        return sum(bool(pattern.search(command)) for command in commands)
    if tool == "Skill":
        return sum(f"skills/{skill}/SKILL.md" in command for command in commands)
    if tool in {"Edit", "Write"}:
        return int(bool(run.changed_files))
    if tool == "Agent":
        return int(bool(run.item_types - KNOWN_ITEM_TYPES))
    return None


def grade_tool_used(run: Run, grader: Grader, skill: str) -> tuple[bool | None, str]:
    """Check a tool_used grader's min and max bounds (default 1 and unbounded)."""
    count = tool_count(run, grader, skill)
    tool = grader.meta.get("tool")
    if count is None:
        return None, f"tool {tool} has no Codex equivalent"
    low = int(grader.meta.get("min", 1))
    high = int(grader.meta["max"]) if "max" in grader.meta else None
    ok = count >= low and (high is None or count <= high)
    return (
        ok,
        f"{tool} used {count}x (expected {low}..{high if high is not None else 'inf'})",
    )


def grader_subject(run: Run, grader: Grader, key: str) -> str:
    """Return the text a grader looks at: a workspace file or the last message."""
    target = grader.meta.get(key)
    if isinstance(target, dict) and target.get("source") == "file":
        path = str(target.get("path", ""))
        return run.after.get(path, run.before.get(path, ""))
    return run.reply


def grade_regex(run: Run, grader: Grader) -> tuple[bool, str]:
    """Check a regex grader, honoring match: not_contains and flags: i."""
    flags = re.IGNORECASE if grader.meta.get("flags") == "i" else 0
    found = re.search(
        str(grader.meta["pattern"]), grader_subject(run, grader, "target"), flags
    )
    if grader.meta.get("match") == "not_contains":
        return found is None, "pattern absent" if found is None else "pattern found"
    return found is not None, "pattern found" if found else "pattern absent"


def judge_vote(rubric: str, output: str, model: str, cwd: Path) -> bool:
    """Ask `claude -p` for one PASS or FAIL verdict on a rubric."""
    result = run_command(
        [*JUDGE_ARGV, "--model", model],
        cwd=cwd,
        env=agent_env(),
        timeout=JUDGE_TIMEOUT_SECONDS,
        input_text=JUDGE_PROMPT.format(rubric=rubric, output=output),
    )
    verdicts = VERDICT.findall(result.stdout.upper())
    return bool(verdicts) and verdicts[-1] == "PASS"


def grade_llm(run: Run, grader: Grader, model: str, cwd: Path) -> tuple[bool, str]:
    """Check an llm grader by majority over JUDGE_VOTES judge runs."""
    subject = grader_subject(run, grader, "focus")
    votes = [judge_vote(grader.rubric, subject, model, cwd) for _ in range(JUDGE_VOTES)]
    return sum(votes) * 2 > len(votes), f"{sum(votes)}/{len(votes)} judge votes pass"


def grade(
    run: Run, skill: str, judge_model: str, cwd: Path
) -> dict[str, dict[str, object]]:
    """Grade one run against every grader of its case."""
    results: dict[str, dict[str, object]] = {}
    for grader in run.case.graders:
        kind = grader.meta.get("type")
        verdict: tuple[bool | None, str]
        if kind == "regex":
            verdict = grade_regex(run, grader)
        elif kind == "tool_used":
            verdict = grade_tool_used(run, grader, skill)
        elif kind == "llm":
            verdict = grade_llm(run, grader, judge_model, cwd)
        else:
            verdict = (None, f"grader type {kind} is not supported")
        results[grader.name] = {"pass": verdict[0], "detail": verdict[1]}
    return results


# -- Runs --------------------------------------------------------------------


def record_event(run: Run, event: dict[str, Any]) -> None:
    """Collect the parts of a Codex event that the graders need."""
    item = event.get("item")
    if event.get("type") != "item.completed" or not isinstance(item, dict):
        return
    kind = str(item.get("type", ""))
    run.item_types.add(kind)
    if kind == "command_execution":
        run.commands.append(str(item.get("command", "")))
    elif kind == "agent_message":
        run.reply = str(item.get("text", ""))


@dataclass(frozen=True)
class Suite:
    """What every run of the suite shares."""

    sandbox: CodexSandbox
    skill: str
    model: str | None
    scratch: Path


def select_cases(plugin: Path, pattern: str) -> list[Case]:
    """Load the cases that match pattern, or raise EvalError when none do."""
    cases = load_cases(plugin, pattern)
    if not cases:
        msg = f"no case matches {pattern!r}"
        raise EvalError(msg)
    return cases


def execute(case: Case, number: int, suite: Suite) -> Run:
    """Scaffold a workspace, run the case once on Codex and collect its events."""
    workspace = Path(
        tempfile.mkdtemp(prefix=f"{case.name}-{number}-", dir=suite.scratch)
    )
    if case.scaffold is not None:
        result = run_command(
            [str(case.scaffold)],
            cwd=workspace,
            env=agent_env(),
            timeout=60,
        )
        if result.returncode != 0:
            msg = f"{case.name}: scaffold failed: {result.stderr.strip()[:300]}"
            raise EvalError(msg)
    run = Run(case, number, before=snapshot(workspace))
    timeout = float(case.settings.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
    prompt = codex_prompt(case.prompt, suite.skill)
    for event in stream_json(
        suite.sandbox.exec_argv(workspace, prompt, suite.model),
        cwd=workspace,
        env=suite.sandbox.env(),
        timeout=timeout,
    ):
        record_event(run, event)
    run.after = snapshot(workspace)
    return run


# -- CLI ---------------------------------------------------------------------


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(description="Run a plugin's evals on Codex")
    parser.add_argument("plugin", type=Path, help="plugin directory")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--case", default="*", help="case name glob")
    parser.add_argument("--model", help="Codex model (default: Codex's own)")
    parser.add_argument("--judge-model", default="sonnet")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument(
        "--codex",
        default="codex",
        help="codex binary; it must honor CODEX_HOME",
    )
    parser.add_argument("--out", type=Path, help="write replies for eval_review.py")
    args = parser.parse_args(argv)
    if args.runs < 1 or args.concurrency < 1:
        parser.error("--runs and --concurrency must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    """Run the suite on Codex and return the exit code."""
    args = parse_args(argv)
    plugin = args.plugin.resolve()
    with tempfile.TemporaryDirectory(prefix="eval-codex-") as scratch_dir:
        scratch = Path(scratch_dir)
        try:
            skill = skill_name(plugin)
            cases = select_cases(plugin, args.case)
            sandbox = codex_sandbox(args.codex, plugin, scratch / "codex")
            suite = Suite(sandbox, skill, args.model, scratch)
            jobs = [(case, n) for case in cases for n in range(1, args.runs + 1)]
            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                runs = list(pool.map(lambda job: execute(job[0], job[1], suite), jobs))
                grades = list(
                    pool.map(
                        lambda run: grade(run, skill, args.judge_model, scratch),
                        runs,
                    ),
                )
        except (EvalError, OSError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    records = []
    for run, graders in zip(runs, grades, strict=True):
        counted = [g["pass"] for g in graders.values() if g["pass"] is not None]
        record = {
            "kind": "run",
            "case": run.case.name,
            "run": run.number,
            "pass": all(counted),
            "graders": graders,
        }
        print(json.dumps(record, ensure_ascii=False))
        records.append({**record, "reply": run.reply, "files": run.changed_files})
    if args.out:
        args.out.write_text(json.dumps({"agent": "codex", "runs": records}, indent=1))
    passed = sum(bool(r["pass"]) for r in records)
    print(
        json.dumps(
            {
                "kind": "summary",
                "total": len(records),
                "passed": passed,
                "failed": len(records) - passed,
            },
        ),
    )
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
