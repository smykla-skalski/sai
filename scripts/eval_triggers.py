#!/usr/bin/env python3
"""Measure whether a plugin's skill triggers on the queries it should.

Reads plugins/<name>/evals/triggers.json:

    {"files": {"path": "content", ...},
     "queries": [{"query": "...", "should_trigger": true}, ...]}

Each query runs in a fresh workspace that holds the files, so a query can name
a file. A run counts as triggered when the agent loads the skill: on Claude a
Skill tool call (`claude -p --plugin-dir`), on Codex a read of
skills/<name>/SKILL.md (the plugin goes into an isolated Codex home). The run
stops as soon as the answer is known. A query passes when at least half of its
runs match should_trigger.

skill-creator's description loop cannot measure plugin skills: it tests a
command stand-in and stops at the first tool call, so queries that name a file
always miss. Use --description to score a candidate description instead.

Usage:
    scripts/eval_triggers.py plugins/humanize [--agent claude|codex] [--runs 3]
        [--model MODEL] [--description TEXT | --description-file FILE]

Output: one NDJSON "query" record per query, then a "summary" record.
Exit codes: 0 every query passes, 1 a query misses, 2 usage or setup error.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from _eval_common import (
    CodexSandbox,
    EvalError,
    agent_env,
    codex_sandbox,
    evals_dir,
    load_json_object,
    skill_name,
    stream_json,
    write_files,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

DEFAULT_RUNS: Final[int] = 3
DEFAULT_TIMEOUT_SECONDS: Final[int] = 240
# Drafting queries read a diff or files first and load the skill only before writing.
CLAUDE_MAX_TURNS: Final[str] = "16"
DESCRIPTION_LINE: Final[re.Pattern[str]] = re.compile(
    r"^description:.*\n(?:[ \t]+.*\n)*",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Query:
    """One trigger query and whether the skill should load for it."""

    text: str
    should_trigger: bool


@dataclass(frozen=True)
class Outcome:
    """The runs of one query."""

    query: Query
    hits: int
    runs: int

    @property
    def triggered(self) -> bool:
        """Return whether at least half of the runs loaded the skill."""
        return self.hits * 2 >= self.runs

    @property
    def passed(self) -> bool:
        """Return whether the majority result matches should_trigger."""
        return self.triggered == self.query.should_trigger


# -- Detection ---------------------------------------------------------------


def claude_loaded_skill(event: dict[str, Any], skill: str) -> bool:
    """Return whether a Claude stream-json event calls the Skill tool for skill."""
    if event.get("type") != "assistant":
        return False
    for block in event.get("message", {}).get("content", []):
        if block.get("type") != "tool_use" or block.get("name") != "Skill":
            continue
        name = str(block.get("input", {}).get("skill", ""))
        if name.rsplit(":", 1)[-1] == skill:
            return True
    return False


def codex_loaded_skill(event: dict[str, Any], skill: str) -> bool:
    """Return whether a Codex JSON event reads the skill's SKILL.md."""
    item = event.get("item")
    if not isinstance(item, dict) or item.get("type") != "command_execution":
        return False
    return f"skills/{skill}/SKILL.md" in str(item.get("command", ""))


def run_ended(event: dict[str, Any]) -> bool:
    """Return whether an event is the last one of a Claude or Codex run."""
    return event.get("type") in {"result", "turn.completed"}


# -- Runs --------------------------------------------------------------------


@dataclass(frozen=True)
class Runner:
    """Everything one trigger run needs."""

    agent: str
    plugin: Path
    skill: str
    files: dict[str, str]
    model: str | None
    timeout: float
    scratch: Path
    sandbox: CodexSandbox | None

    def argv(self, query: str, workspace: Path) -> list[str]:
        """Return the agent command for one query."""
        if self.sandbox is not None:
            return self.sandbox.exec_argv(workspace, query, self.model)
        argv = ["claude", "-p", query, "--plugin-dir", str(self.plugin)]
        argv += ["--output-format", "stream-json", "--verbose"]
        argv += ["--setting-sources", "project", "--strict-mcp-config"]
        argv += ["--no-session-persistence", "--max-turns", CLAUDE_MAX_TURNS]
        if self.model:
            argv += ["--model", self.model]
        return argv

    def triggered(self, query: str) -> bool:
        """Run one query in a fresh workspace and report whether the skill loaded."""
        workspace = Path(tempfile.mkdtemp(prefix="trigger-", dir=self.scratch))
        try:
            # An empty .claude/ makes the workspace its own project root.
            (workspace / ".claude").mkdir()
            write_files(workspace, self.files)
            env = self.sandbox.env() if self.sandbox else agent_env()
            loaded = (
                codex_loaded_skill if self.sandbox is not None else claude_loaded_skill
            )
            events = stream_json(
                self.argv(query, workspace),
                cwd=workspace,
                env=env,
                timeout=self.timeout,
            )
            for event in events:
                if loaded(event, self.skill):
                    return True
                if run_ended(event):
                    return False
            return False
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


def with_description(plugin: Path, skill: str, description: str, root: Path) -> Path:
    """Copy the plugin with the skill description replaced, and return the copy."""
    target = root / plugin.name
    shutil.copytree(plugin, target, ignore=shutil.ignore_patterns("evals"))
    skill_md = target / "skills" / skill / "SKILL.md"
    text = skill_md.read_text()
    line = f"description: {json.dumps(' '.join(description.split()))}\n"
    replaced, count = DESCRIPTION_LINE.subn(lambda _: line, text, count=1)
    if count != 1:
        msg = f"{skill_md} has no description line"
        raise EvalError(msg)
    skill_md.write_text(replaced)
    return target


def load_queries(plugin: Path) -> tuple[dict[str, str], list[Query]]:
    """Read triggers.json, or raise EvalError when it is missing or malformed."""
    data = load_json_object(evals_dir(plugin) / "triggers.json")
    files = data.get("files", {})
    raw = data.get("queries")
    if not isinstance(files, dict) or not isinstance(raw, list) or not raw:
        msg = "triggers.json needs a files object and a non-empty queries list"
        raise EvalError(msg)
    queries = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(
            item.get("should_trigger"),
            bool,
        ):
            msg = f"bad trigger query: {item!r}"
            raise EvalError(msg)
        queries.append(Query(str(item["query"]), item["should_trigger"]))
    return {str(k): str(v) for k, v in files.items()}, queries


def measure(
    runner: Runner,
    queries: list[Query],
    runs: int,
    concurrency: int,
) -> list[Outcome]:
    """Run every query runs times and return the outcomes in query order."""
    jobs = [index for index in range(len(queries)) for _ in range(runs)]
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        hits = list(pool.map(lambda i: runner.triggered(queries[i].text), jobs))
    counts = [0] * len(queries)
    for index, hit in zip(jobs, hits, strict=True):
        counts[index] += hit
    return [Outcome(query, counts[i], runs) for i, query in enumerate(queries)]


def summary(outcomes: Iterable[Outcome]) -> dict[str, object]:
    """Return the summary record: pass counts, recall and precision."""
    outcomes = list(outcomes)
    positives = [o for o in outcomes if o.query.should_trigger]
    true_hits = sum(o.triggered for o in positives)
    all_hits = sum(o.triggered for o in outcomes)
    passed = sum(o.passed for o in outcomes)
    return {
        "kind": "summary",
        "total": len(outcomes),
        "passed": passed,
        "failed": len(outcomes) - passed,
        "precision": f"{true_hits}/{all_hits}",
        "recall": f"{true_hits}/{len(positives)}",
    }


# -- CLI ---------------------------------------------------------------------


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        description="Measure skill triggering on Claude or Codex",
    )
    parser.add_argument("plugin", type=Path, help="plugin directory")
    parser.add_argument("--agent", choices=("claude", "codex"), default="claude")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--model", help="model for the agent (default: its own)")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--codex",
        default="codex",
        help="codex binary; it must honor CODEX_HOME",
    )
    candidate = parser.add_mutually_exclusive_group()
    candidate.add_argument("--description", help="candidate description to score")
    candidate.add_argument("--description-file", type=Path)
    args = parser.parse_args(argv)
    if args.runs < 1 or args.concurrency < 1:
        parser.error("--runs and --concurrency must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    """Run the trigger check and return the exit code."""
    args = parse_args(argv)
    plugin = args.plugin.resolve()
    with tempfile.TemporaryDirectory(prefix="eval-triggers-") as scratch_dir:
        scratch = Path(scratch_dir)
        try:
            skill = skill_name(plugin)
            files, queries = load_queries(plugin)
            if args.description_file:
                args.description = args.description_file.read_text()
            if args.description:
                plugin = with_description(plugin, skill, args.description, scratch)
            sandbox = (
                codex_sandbox(args.codex, plugin, scratch / "codex")
                if args.agent == "codex"
                else None
            )
        except (EvalError, OSError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        runner = Runner(
            args.agent,
            plugin,
            skill,
            files,
            args.model,
            args.timeout,
            scratch,
            sandbox,
        )
        outcomes = measure(runner, queries, args.runs, args.concurrency)
    for outcome in outcomes:
        record = {
            "kind": "query",
            "query": outcome.query.text,
            "should_trigger": outcome.query.should_trigger,
            "hits": outcome.hits,
            "runs": outcome.runs,
            "pass": outcome.passed,
        }
        print(json.dumps(record, ensure_ascii=False))
    print(json.dumps(summary(outcomes)))
    return 0 if all(o.passed for o in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
