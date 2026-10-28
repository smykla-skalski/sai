#!/usr/bin/env python3
"""Run whole simulated interviews and session sequences with a plugin's skill.

`claude plugin eval` and eval_codex.py check one turn per case. A skill that
interviews the user can pass every such case and still ask too many questions,
or invent an answer, over a whole interview. This tool plays the whole chat: a
simulated user (`claude -p` with no tools) answers each turn only from a hidden
brief, and a judge model then reads the chat and the file the skill wrote.

Reads plugins/<name>/evals/interviews.json:

    {"setting": "an assistant helps a user turn a rough idea into a plan",
     "baseline": "the request that stands in for the skill in --arm without",
     "judge_notes": "plugin rules the judge applies",
     "checks": {"done_when_checkable": "true if ...", ...},
     "question_slack": 2,
     "scenarios": [{"name": "...", "prompt": "...", "file": "ideas/x.md",
                    "brief": ["a fact the user knows", ...],
                    "questions": [6, 8]}],
     "sequences": [{"name": "...", "requests": ["...", ...],
                    "expect": [{"after": 1, "glob": "{data}/x/*.md", "min": 1},
                               {"after": 2, "file": "{data}/x/setting",
                                "equals": "{workspace}/notes"}]}]}

A sequence checks state that a skill keeps between sessions. Each request runs
as a fresh session, one after another, in one workspace, with XDG_DATA_HOME set
to the workspace's .data folder. After request n, each expectation with
"after": n checks the files: a glob must match at least "min" (default 1) and
at most "max" files, or a file must hold "equals" (surrounding whitespace
ignored). {workspace} and {data} stand for the two folders. A clickable
question in a sequence gets the answer that the user stops there. Sequences
run only in --arm with, and --scenario selects them by name too.

Agents:
    claude      `claude -p` and `--resume`, plugin through --plugin-dir; the
                skill asks in plain text and may run Bash only for python3
    claude-ask  the Claude Agent SDK with AskUserQuestion on, answered through
                can_use_tool; each call must hold one question, 2-4 options,
                labels of 1-5 words and a header of at most 12 characters.
                Run it with `uv run --no-project --with claude-agent-sdk`
    codex       `codex exec` and `codex exec resume`, plugin in an isolated
                Codex home, a fresh HOME per session
    kimi        `kimi -p -S`, skill through --skills-dir, the user's Kimi
                config without its hooks
    opencode    `opencode run --session`, skill in .opencode/skills, only the
                model and its provider from the user's opencode config

A run passes when the judge finds the interview finished, with no turn that
asks more than one question, no needless question, no vague answer kept as
precise and no invented fact, every check in "checks" true, and a question
count inside the scenario's range widened by question_slack on each side.
`--arm without` runs the claude agent without the plugin, with the baseline
request, for comparison. Its runs never fail the exit code.

Usage:
    scripts/eval_interview.py plugins/smallsteps [--agent claude]
        [--arm with|without] [--scenario GLOB] [--runs 1] [--cli PATH]
        [--model MODEL] [--user-model sonnet] [--judge-model opus]
        [--concurrency 2] [--out results.json]

Output: one NDJSON "interview" or "sequence" record per run, then a "summary"
record. --out also writes each chat, the judge's answer and the file the skill
wrote, or each reply of a sequence.
Exit codes: 0 every run passes, 1 a run fails, 2 usage or setup error.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import asyncio
import fnmatch
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Protocol, TypeVar

from _eval_common import (
    CodexSandbox,
    EvalError,
    RunFailedError,
    agent_env,
    codex_prompt,
    codex_sandbox,
    evals_dir,
    load_json_object,
    run_command,
    run_failure,
    skill_name,
    with_retries,
    write_files,
)

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")

AGENTS: Final[tuple[str, ...]] = ("claude", "claude-ask", "codex", "kimi", "opencode")
DEFAULT_RUNS: Final[int] = 1
MAX_TURNS: Final[int] = 30
TURN_TIMEOUT_SECONDS: Final[int] = 900
MODEL_TIMEOUT_SECONDS: Final[int] = 300
DONE: Final[str] = "DONE"
CLAUDE_TOOLS: Final[tuple[str, ...]] = (
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Skill",
    "ToolSearch",
)
# Portable skills run their scripts as `python3 <skill folder>/scripts/x.py`.
SCRIPT_BASH: Final[str] = "Bash(python3:*)"
DATA_FOLDER: Final[str] = ".data"
STOP_ANSWER: Final[str] = "Let us stop here for now."
ISOLATED: Final[tuple[str, ...]] = (
    "--setting-sources",
    "project",
    "--strict-mcp-config",
)
MODEL_ARGV: Final[tuple[str, ...]] = (
    "claude",
    "-p",
    "--output-format",
    "text",
    "--tools",
    "",
    "--no-session-persistence",
    "--disable-slash-commands",
    *ISOLATED,
)
MAX_HEADER_CHARS: Final[int] = 12
MIN_OPTIONS: Final[int] = 2
MAX_OPTIONS: Final[int] = 4
MAX_LABEL_WORDS: Final[int] = 5
RANGE_BOUNDS: Final[int] = 2
JSON_OBJECT: Final[re.Pattern[str]] = re.compile(r"\{[\s\S]*\}")
JSONC_COMMENT: Final[re.Pattern[str]] = re.compile(r"^\s*//.*$", re.MULTILINE)
OPENCODE_SCHEMA: Final[str] = "https://opencode.ai/config.json"

USER_PROMPT: Final[str] = (
    "You are the user in a chat in which {setting}.\n"
    "You know only these facts:\n{brief}\n"
    "The chat so far:\n{chat}\n\n"
    "Write your next message to the assistant as this user. Rules:\n"
    "- Answer only what the assistant's last message asks. Keep it short and "
    "plain.\n"
    "- Use only the facts above. If they do not cover the question, say you do "
    "not know.\n"
    "- If it offers numbered options, pick the one that fits your facts, or "
    "write your own answer.\n"
    "- If it plays back a summary that matches your facts, say yes. If something "
    "is wrong, say what.\n"
    "- Never volunteer facts it did not ask for.\n"
    "- If the assistant's last message asks you nothing and the work looks "
    f"finished, reply with exactly: {DONE}\n"
    "Output only the message text."
)

PICK_PROMPT: Final[str] = (
    "You are the user in a chat in which {setting}.\n"
    "You know only these facts:\n{brief}\n"
    "The chat so far:\n{chat}\n\n"
    "The assistant now shows you this clickable question:\n{question}\n\n"
    "Answer as this user. Rules:\n"
    "- If one option matches your facts, reply with its label exactly.\n"
    "- Otherwise reply with your own short answer, using only your facts, or "
    '"I do not know".\n'
    "Output only the answer."
)

JUDGE_PROMPT: Final[str] = (
    "You judge a chat in which {setting}.\n"
    "The user knew only these facts, which the assistant did not see:\n"
    "{brief}\n\n"
    'The full chat (a turn marked "assistant (clickable)" is a question with '
    "clickable options):\n{chat}\n\n"
    "The file the assistant wrote ({file}):\n<file>\n{file_text}\n</file>\n\n"
    "Return only JSON with these keys:\n"
    '- "questions": the total number of distinct questions the assistant asked '
    "the user (count each question sentence; a set of numbered answer options is "
    "part of one question).\n"
    '- "turns_with_more_than_one_question": the number of assistant turns that '
    "asked more than one question.\n"
    '- "needless": a list of {{"turn": n, "question": "...", "why": "..."}} for '
    "each question that asked for something the user had already stated clearly "
    "earlier in the chat, or whose answer could not change the file. A single "
    "playback question that confirms items, and a follow-up after a vague "
    "answer, are NOT needless.\n"
    '- "missed_precision": a list of vague user answers (such as "faster", '
    '"better", "users") that the file still holds as if precise, with no '
    "follow-up.\n"
    '- "invented": a list of facts, numbers, targets, dates or decisions in the '
    "file that the user's own words do not support. Judge each item the "
    "assistant drafted as if the user had never confirmed it: a yes to a "
    "summary or playback does not give its content.\n"
    '- "finished": true if the chat reached the finished result the user asked '
    "for.\n"
    "{checks}\n"
    '- "verdict": one sentence.\n\n'
    "{judge_notes}"
)


# -- Suite -------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """One interview: what the user asks, what they know, how long it may be."""

    name: str
    prompt: str
    file: str
    brief: str
    questions: tuple[int, int]


@dataclass(frozen=True)
class Suite:
    """A plugin's interviews.json."""

    skill: str
    setting: str
    baseline: str
    judge_notes: str
    checks: dict[str, str]
    slack: int
    scenarios: tuple[Scenario, ...]
    sequences: tuple[SessionSequence, ...] = ()


@dataclass(frozen=True)
class Expectation:
    """A file check after one request of a sequence."""

    after: int
    glob: str = ""
    least: int = 1
    most: int | None = None
    file: str = ""
    equals: str = ""


@dataclass(frozen=True)
class SessionSequence:
    """Requests that run as fresh sessions in one workspace, with file checks."""

    name: str
    requests: tuple[str, ...]
    expect: tuple[Expectation, ...]


def _text(data: dict[str, Any], key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"{where}: {key!r} must be a non-empty string"
        raise EvalError(msg)
    return value


def load_scenario(raw: object, where: str) -> Scenario:
    """Check one scenario of interviews.json and return it."""
    if not isinstance(raw, dict):
        msg = f"{where}: each scenario must be an object"
        raise EvalError(msg)
    name = _text(raw, "name", where)
    where = f"{where} scenario {name}"
    brief = raw.get("brief")
    if not (
        isinstance(brief, list)
        and brief
        and all(isinstance(fact, str) and fact for fact in brief)
    ):
        msg = f"{where}: 'brief' must be a non-empty list of strings"
        raise EvalError(msg)
    questions = raw.get("questions")
    if not (
        isinstance(questions, list)
        and len(questions) == RANGE_BOUNDS
        and all(type(n) is int for n in questions)
        and 0 < questions[0] <= questions[1]
    ):
        msg = f"{where}: 'questions' must be [low, high] with 0 < low <= high"
        raise EvalError(msg)
    return Scenario(
        name=name,
        prompt=_text(raw, "prompt", where),
        file=_text(raw, "file", where),
        brief="\n".join(f"- {fact}" for fact in brief),
        questions=(questions[0], questions[1]),
    )


def _count(
    raw: dict[str, Any], key: str, default: int | None, where: str
) -> int | None:
    value = raw.get(key, default)
    if value is not None and (type(value) is not int or value < 0):
        msg = f"{where}: {key!r} must be a whole number of at least 0"
        raise EvalError(msg)
    return value


def load_expectation(raw: object, requests: int, where: str) -> Expectation:
    """Check one expectation of a sequence and return it."""
    if not isinstance(raw, dict):
        msg = f"{where}: each expectation must be an object"
        raise EvalError(msg)
    after = raw.get("after")
    if type(after) is not int or not 1 <= after <= requests:
        msg = f"{where}: 'after' must name a request from 1 to {requests}"
        raise EvalError(msg)
    if ("glob" in raw) == ("file" in raw):
        msg = f"{where}: an expectation needs either 'glob' or 'file'"
        raise EvalError(msg)
    if "file" in raw:
        return Expectation(
            after=after,
            file=_text(raw, "file", where),
            equals=_text(raw, "equals", where),
        )
    least = _count(raw, "min", 1, where)
    most = _count(raw, "max", None, where)
    if least is None or (most is not None and most < least):
        msg = f"{where}: 'max' must not be below 'min'"
        raise EvalError(msg)
    return Expectation(after, _text(raw, "glob", where), least, most)


def load_sequence(raw: object, where: str) -> SessionSequence:
    """Check one sequence of interviews.json and return it."""
    if not isinstance(raw, dict):
        msg = f"{where}: each sequence must be an object"
        raise EvalError(msg)
    name = _text(raw, "name", where)
    where = f"{where} sequence {name}"
    requests = raw.get("requests")
    if not (
        isinstance(requests, list)
        and requests
        and all(isinstance(text, str) and text for text in requests)
    ):
        msg = f"{where}: 'requests' must be a non-empty list of strings"
        raise EvalError(msg)
    expect = raw.get("expect")
    if not isinstance(expect, list) or not expect:
        msg = f"{where}: 'expect' must be a non-empty list"
        raise EvalError(msg)
    return SessionSequence(
        name=name,
        requests=tuple(requests),
        expect=tuple(load_expectation(e, len(requests), where) for e in expect),
    )


def load_suite(plugin: Path) -> Suite:
    """Load and check plugins/<name>/evals/interviews.json."""
    path = evals_dir(plugin) / "interviews.json"
    data = load_json_object(path)
    where = str(path)
    checks = data.get("checks", {})
    if not isinstance(checks, dict) or not all(
        isinstance(text, str) and text for text in checks.values()
    ):
        msg = f"{where}: 'checks' must map each key to a non-empty string"
        raise EvalError(msg)
    slack = data.get("question_slack", 0)
    if type(slack) is not int or slack < 0:
        msg = f"{where}: 'question_slack' must be a whole number of at least 0"
        raise EvalError(msg)
    raw_scenarios = data.get("scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        msg = f"{where}: 'scenarios' must be a non-empty list"
        raise EvalError(msg)
    scenarios = tuple(load_scenario(raw, where) for raw in raw_scenarios)
    raw_sequences = data.get("sequences", [])
    if not isinstance(raw_sequences, list):
        msg = f"{where}: 'sequences' must be a list"
        raise EvalError(msg)
    sequences = tuple(load_sequence(raw, where) for raw in raw_sequences)
    names = [s.name for s in scenarios] + [q.name for q in sequences]
    if len(set(names)) != len(names):
        msg = f"{where}: scenario and sequence names must be unique"
        raise EvalError(msg)
    return Suite(
        skill=skill_name(plugin),
        setting=_text(data, "setting", where),
        baseline=_text(data, "baseline", where),
        judge_notes=str(data.get("judge_notes", "")),
        checks=checks,
        slack=slack,
        scenarios=scenarios,
        sequences=sequences,
    )


def select_runs(
    suite: Suite,
    pattern: str,
    arm: str,
) -> list[Scenario | SessionSequence]:
    """Return what matches pattern, or raise EvalError when nothing does.

    Sequences check what the skill keeps, so they run only with the plugin.
    """
    items: list[Scenario | SessionSequence] = [*suite.scenarios]
    if arm == "with":
        items += suite.sequences
    chosen = [item for item in items if fnmatch.fnmatchcase(item.name, pattern)]
    if not chosen:
        msg = f"no scenario or sequence matches {pattern!r}"
        raise EvalError(msg)
    return chosen


# -- Verdicts ----------------------------------------------------------------


def parse_judge(text: str) -> dict[str, Any] | None:
    """Return the JSON object in a judge reply, or None when it has none."""
    match = JSON_OBJECT.search(text)
    if match is None:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def assess(judge: dict[str, Any] | None, scenario: Scenario, suite: Suite) -> list[str]:
    """Return what makes an interview fail, or an empty list when it passes."""
    if judge is None:
        return ["the judge gave no JSON verdict"]
    problems = []
    if judge.get("finished") is not True:
        problems.append("the interview did not finish")
    multi = judge.get("turns_with_more_than_one_question")
    if multi != 0:
        problems.append(f"turns with more than one question: {multi}")
    problems.extend(
        f"{key}: {json.dumps(judge[key], ensure_ascii=False)}"
        for key in ("needless", "missed_precision", "invented")
        if judge.get(key)
    )
    problems.extend(
        f"{check} is not true" for check in suite.checks if judge.get(check) is not True
    )
    count = judge.get("questions")
    low, high = scenario.questions
    if type(count) is not int or not low - suite.slack <= count <= high + suite.slack:
        problems.append(f"{count} questions, the scenario wants about {low} to {high}")
    return problems


def fill(text: str, places: dict[str, str]) -> str:
    """Replace each {name} placeholder in text with its folder."""
    for name, value in places.items():
        text = text.replace(f"{{{name}}}", value)
    return text


def check_expectation(expect: Expectation, places: dict[str, str]) -> str | None:
    """Return why the files break expect, or None when they meet it."""
    if expect.file:
        path = Path(fill(expect.file, places))
        found = path.read_text().strip() if path.is_file() else None
        want = fill(expect.equals, places).strip()
        return None if found == want else f"{path} holds {found!r}, want {want!r}"
    pattern = fill(expect.glob, places)
    anchor = Path(Path(pattern).anchor)
    count = len(list(anchor.glob(str(Path(pattern).relative_to(anchor)))))
    if count < expect.least or (expect.most is not None and count > expect.most):
        most = "any" if expect.most is None else expect.most
        return f"{pattern} matches {count} files, want {expect.least} to {most}"
    return None


def ask_call_problems(questions: list[dict[str, Any]]) -> list[str]:
    """Return how one AskUserQuestion call breaks the one-question form."""
    problems = []
    if len(questions) != 1:
        problems.append(f"{len(questions)} questions in one call")
    for question in questions:
        options = question.get("options") or []
        if not MIN_OPTIONS <= len(options) <= MAX_OPTIONS:
            problems.append(f"{len(options)} options")
        header = str(question.get("header", ""))
        if len(header) > MAX_HEADER_CHARS:
            problems.append(f"header of {len(header)} characters: {header!r}")
        for option in options:
            label = str(option.get("label", ""))
            if not 1 <= len(label.split()) <= MAX_LABEL_WORDS:
                problems.append(f"label of {len(label.split())} words: {label!r}")
        if str(question.get("question", "")).count("?") > 1:
            problems.append(f"more than one question: {question.get('question')!r}")
    return problems


# -- Agent replies -----------------------------------------------------------


def json_lines(text: str) -> list[dict[str, Any]]:
    """Return every JSON object printed on its own line."""
    events = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def claude_reply(stdout: str) -> tuple[str, str | None]:
    """Return the reply and session of a `claude -p --output-format json` run."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return "", None
    if not isinstance(data, dict):
        return "", None
    session = data.get("session_id")
    return str(data.get("result") or ""), str(session) if session else None


def codex_reply(events: list[dict[str, Any]]) -> tuple[str, str | None]:
    """Return the last message and thread of a `codex exec --json` run."""
    session, texts = None, []
    for event in events:
        failure = run_failure(event)
        if failure:
            raise RunFailedError(failure)
        if event.get("type") == "thread.started":
            session = event.get("thread_id")
        item = event.get("item") or {}
        if (
            event.get("type") == "item.completed"
            and item.get("type") == "agent_message"
        ):
            texts.append(str(item.get("text", "")))
    return (texts[-1] if texts else ""), session


def kimi_reply(events: list[dict[str, Any]]) -> tuple[str, str | None]:
    """Return the last message and session of a `kimi -p` stream-json run."""
    session, texts = None, []
    for event in events:
        if event.get("type") == "session.resume_hint":
            session = event.get("session_id")
        if event.get("role") == "assistant" and isinstance(event.get("content"), str):
            texts.append(event["content"])
    return (texts[-1] if texts else ""), session


def opencode_reply(events: list[dict[str, Any]]) -> str:
    """Return the last text part of an `opencode run --format json` run."""
    texts = [
        str(event["part"]["text"])
        for event in events
        if event.get("type") == "text"
        and isinstance(event.get("part"), dict)
        and event["part"].get("text")
    ]
    return texts[-1] if texts else ""


# -- Agent sessions ----------------------------------------------------------


class Session(Protocol):
    """One interview with one agent."""

    def send(self, message: str) -> str:
        """Send one user message and return the agent's reply."""
        ...

    def problems(self) -> list[str]:
        """Return what the agent did wrong outside its replies."""
        ...

    def close(self) -> None:
        """Release what the session holds."""
        ...


class CliSession:
    """An agent CLI that runs once per turn and resumes a saved session."""

    def __init__(self, workspace: Path, env: dict[str, str]) -> None:
        """Run every turn in workspace with env."""
        self.workspace = workspace
        # opencode reads the project folder from $PWD, not the process folder.
        self.env = {**env, "PWD": str(workspace)}
        self.session: str | None = None

    def argv(self, message: str) -> list[str]:
        """Return the command line of one turn."""
        raise NotImplementedError

    def parse(self, stdout: str) -> tuple[str, str | None]:
        """Return the reply and the session id in the CLI's output."""
        raise NotImplementedError

    def send(self, message: str) -> str:
        """Run one turn, or raise RunFailedError when it gives no reply."""
        result = run_command(
            self.argv(message),
            cwd=self.workspace,
            env=self.env,
            timeout=TURN_TIMEOUT_SECONDS,
        )
        reply, session = self.parse(result.stdout)
        self.session = session or self.session
        if not reply.strip() or self.session is None:
            detail = (result.stderr or result.stdout).strip()[-300:]
            msg = f"no reply (exit {result.returncode}): {detail}"
            raise RunFailedError(msg)
        return reply.strip()

    def problems(self) -> list[str]:
        """Return nothing: a CLI turn shows all it does in its reply."""
        return []

    def close(self) -> None:
        """Do nothing: the CLI exits after every turn."""


@dataclass(frozen=True)
class Agent:
    """The chosen agent, set up once for every session of a measurement."""

    name: str
    cli: str
    plugin: Path | None
    skill: Path
    model: str | None
    scratch: Path
    codex: CodexSandbox | None = None
    kimi_home: Path | None = None
    opencode_config: Path | None = None


def _needs(value: T | None, what: str) -> T:
    if value is None:
        msg = f"the agent was set up without {what}"
        raise EvalError(msg)
    return value


class ClaudeSession(CliSession):
    """Claude Code through `claude -p`, plain-text questions only."""

    def __init__(self, workspace: Path, agent: Agent, extra: dict[str, str]) -> None:
        """Make workspace the project folder that --setting-sources reads."""
        super().__init__(workspace, agent_env(**extra))
        (workspace / ".claude").mkdir(exist_ok=True)
        self.agent = agent

    def argv(self, message: str) -> list[str]:
        """Return the command line of one turn."""
        agent = self.agent
        argv = [agent.cli, "-p", message, "--output-format", "json", *ISOLATED]
        if agent.plugin is not None:
            argv += ["--plugin-dir", str(agent.plugin)]
        if agent.model:
            argv += ["--model", agent.model]
        argv += ["--permission-mode", "acceptEdits", "--allowedTools", SCRIPT_BASH]
        argv += ["--tools", *CLAUDE_TOOLS, "Bash"]
        return [*argv, "--resume", self.session] if self.session else argv

    def parse(self, stdout: str) -> tuple[str, str | None]:
        """Return the reply and the session id."""
        return claude_reply(stdout)


class CodexSession(CliSession):
    """Codex through `codex exec` and `codex exec resume`."""

    def __init__(self, workspace: Path, agent: Agent, extra: dict[str, str]) -> None:
        """Give the session its own HOME, so nothing it writes there leaks."""
        sandbox = _needs(agent.codex, "a Codex sandbox")
        home = tempfile.mkdtemp(prefix="home-", dir=agent.scratch)
        super().__init__(workspace, {**sandbox.env(), "HOME": home, **extra})
        self.codex, self.model = sandbox.codex, agent.model

    def argv(self, message: str) -> list[str]:
        """Return the command line of one turn.

        No --ephemeral: the next turn resumes this session.
        """
        model = ["-m", self.model] if self.model else []
        if self.session is None:
            return [
                *(self.codex, "exec", "--skip-git-repo-check", "--json"),
                *("-s", "workspace-write", "-C", str(self.workspace)),
                *model,
                message,
            ]
        return [
            *(self.codex, "exec", "resume", self.session, "--skip-git-repo-check"),
            *("--json", "-c", 'sandbox_mode="workspace-write"'),
            *model,
            message,
        ]

    def parse(self, stdout: str) -> tuple[str, str | None]:
        """Return the reply and the thread id."""
        return codex_reply(json_lines(stdout))


class KimiSession(CliSession):
    """Kimi Code through `kimi -p`, resumed with -S."""

    def __init__(self, workspace: Path, agent: Agent, extra: dict[str, str]) -> None:
        """Point Kimi at the isolated home and the plugin's skills folder."""
        home = _needs(agent.kimi_home, "a Kimi home")
        super().__init__(workspace, agent_env(KIMI_CODE_HOME=str(home), **extra))
        self.agent = agent

    def argv(self, message: str) -> list[str]:
        """Return the command line of one turn."""
        argv = [self.agent.cli, "-p", message, "--output-format", "stream-json"]
        argv += ["--skills-dir", str(self.agent.skill.parent)]
        if self.agent.model:
            argv += ["-m", self.agent.model]
        return [*argv, "-S", self.session] if self.session else argv

    def parse(self, stdout: str) -> tuple[str, str | None]:
        """Return the reply and the session id."""
        return kimi_reply(json_lines(stdout))


class OpenCodeSession(CliSession):
    """opencode through `opencode run`, with a session id chosen up front."""

    def __init__(self, workspace: Path, agent: Agent, extra: dict[str, str]) -> None:
        """Install the skill as a project skill of workspace."""
        config = _needs(agent.opencode_config, "an opencode config")
        super().__init__(workspace, agent_env(XDG_CONFIG_HOME=str(config), **extra))
        skill = agent.skill
        shutil.copytree(
            skill,
            workspace / ".opencode" / "skills" / skill.name,
            dirs_exist_ok=True,
        )
        if "XDG_DATA_HOME" in extra:
            # opencode keeps its login under $XDG_DATA_HOME/opencode.
            own = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
            link = Path(extra["XDG_DATA_HOME"]) / "opencode"
            link.parent.mkdir(parents=True, exist_ok=True)
            if not link.exists():
                link.symlink_to(own / "opencode")
        self.cli = agent.cli
        self.session = f"ses_{uuid.uuid4().hex[:24]}"

    def argv(self, message: str) -> list[str]:
        """Return the command line of one turn."""
        argv = [self.cli, "run", "--standalone", "--format", "json", "--auto"]
        return [*argv, "--session", str(self.session), message]

    def parse(self, stdout: str) -> tuple[str, str | None]:
        """Return the reply and the session id chosen up front."""
        return opencode_reply(json_lines(stdout)), self.session


async def _keep_stream_open(*_args: object) -> dict[str, bool]:
    return {"continue_": True}


class AskSession:
    """Claude Code through the Agent SDK, with AskUserQuestion answered."""

    def __init__(
        self,
        workspace: Path,
        agent: Agent,
        pick: Callable[[str], str],
        extra: dict[str, str],
    ) -> None:
        """Start one SDK client on its own event loop for the session."""
        try:
            self.sdk = importlib.import_module("claude_agent_sdk")
        except ImportError as error:
            msg = "claude-ask needs `uv run --no-project --with claude-agent-sdk`"
            raise EvalError(msg) from error
        (workspace / ".claude").mkdir(exist_ok=True)
        self.pick = pick
        self.calls: list[list[str]] = []
        self.loop = asyncio.new_event_loop()
        plugin = _needs(agent.plugin, "the plugin")
        options = self.sdk.ClaudeAgentOptions(
            cwd=str(workspace),
            cli_path=shutil.which(agent.cli) or agent.cli,
            model=agent.model,
            env=extra,
            plugins=[{"type": "local", "path": str(plugin)}],
            setting_sources=["project"],
            tools=[*CLAUDE_TOOLS, "Bash", "AskUserQuestion"],
            # Left out of allowed_tools, so every AskUserQuestion call reaches
            # can_use_tool, which answers it as the simulated user.
            allowed_tools=[*CLAUDE_TOOLS, SCRIPT_BASH],
            can_use_tool=self._can_use_tool,
            # The Python SDK closes the stream before can_use_tool runs unless
            # a PreToolUse hook keeps it open.
            hooks={
                "PreToolUse": [
                    self.sdk.HookMatcher(matcher=None, hooks=[_keep_stream_open]),
                ],
            },
            extra_args={"strict-mcp-config": None},
            max_turns=200,
        )
        self.client = self.sdk.ClaudeSDKClient(options=options)
        self.loop.run_until_complete(self.client.connect())

    async def _can_use_tool(
        self,
        tool: str,
        tool_input: dict[str, Any],
        _context: object,
    ) -> object:
        if tool != "AskUserQuestion":
            # The same tools as the claude agent: Bash only for python3.
            return self.sdk.PermissionResultDeny(message=f"{tool} is not allowed")
        questions = list(tool_input.get("questions") or [])
        self.calls.append(ask_call_problems(questions))
        answers = {}
        for question in questions:
            options = "\n".join(
                f"- {option.get('label')}: {option.get('description', '')}"
                for option in question.get("options") or []
            )
            block = f"[{question.get('header')}] {question.get('question')}\n{options}"
            answers[str(question.get("question", ""))] = await asyncio.to_thread(
                self.pick,
                block,
            )
        return self.sdk.PermissionResultAllow(
            updated_input={**tool_input, "answers": answers},
        )

    async def _turn(self, message: str) -> str:
        await self.client.query(message)
        texts = []
        async for event in self.client.receive_response():
            if isinstance(event, self.sdk.AssistantMessage):
                texts += [
                    block.text
                    for block in event.content
                    if isinstance(block, self.sdk.TextBlock)
                ]
        return texts[-1].strip() if texts else ""

    def send(self, message: str) -> str:
        """Run one turn, or raise RunFailedError when it gives no reply."""
        reply = self.loop.run_until_complete(self._turn(message))
        if not reply:
            msg = "no reply from the Agent SDK"
            raise RunFailedError(msg)
        return reply

    def problems(self) -> list[str]:
        """Return each break of the one-question form in AskUserQuestion calls."""
        return [
            f"AskUserQuestion call {number}: {problem}"
            for number, problems in enumerate(self.calls, start=1)
            for problem in problems
        ]

    def close(self) -> None:
        """Stop the SDK client and its event loop."""
        self.loop.run_until_complete(self.client.disconnect())
        self.loop.close()


# -- Agent setup -------------------------------------------------------------


def drop_toml_tables(text: str, header: str) -> str:
    """Return TOML text without the tables that start with header."""
    kept, dropping = [], False
    for line in text.splitlines():
        if line.startswith("["):
            dropping = line.strip() == header
        if not dropping:
            kept.append(line)
    return "\n".join(kept) + "\n"


def kimi_home(root: Path) -> Path:
    """Copy the user's Kimi home without hooks, which would run in every turn.

    The config keeps the user's model and its effort, and the login is linked.
    """
    source = Path(os.environ.get("KIMI_CODE_HOME") or Path.home() / ".kimi-code")
    config = source / "config.toml"
    if not config.is_file():
        msg = f"no Kimi config at {config}; run `kimi login` first"
        raise EvalError(msg)
    root.mkdir(parents=True)
    (root / "config.toml").write_text(drop_toml_tables(config.read_text(), "[[hooks]]"))
    (root / "credentials").symlink_to(source / "credentials")
    if (source / "device_id").is_file():
        shutil.copy2(source / "device_id", root / "device_id")
    return root


def isolated_opencode_config(user: dict[str, Any], model: str | None) -> dict[str, Any]:
    """Return an opencode config with only the model and its provider.

    The user's agents, plugins, skills and MCP servers stay out of the run.
    """
    chosen = model or user.get("model")
    if not isinstance(chosen, str) or "/" not in chosen:
        msg = "pass --model provider/model, the opencode config sets no model"
        raise EvalError(msg)
    provider, name = chosen.split("/", 1)
    providers = user.get("provider") or {}
    if provider not in providers:
        msg = f"provider {provider!r} is not in the opencode config"
        raise EvalError(msg)
    entry = dict(providers[provider])
    entry["models"] = {name: {}, **(entry.get("models") or {})}
    return {"$schema": OPENCODE_SCHEMA, "model": chosen, "provider": {provider: entry}}


def opencode_config(root: Path, model: str | None) -> Path:
    """Write the isolated opencode config and return its XDG_CONFIG_HOME."""
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    source = base / "opencode" / "opencode.json"
    try:
        user = json.loads(JSONC_COMMENT.sub("", source.read_text()))
    except (OSError, json.JSONDecodeError) as error:
        msg = f"cannot read {source}: {error}"
        raise EvalError(msg) from error
    config = isolated_opencode_config(user, model)
    write_files(root, {"opencode/opencode.json": json.dumps(config, indent=2)})
    return root


def setup_agent(
    args: argparse.Namespace,
    plugin: Path,
    suite: Suite,
    scratch: Path,
) -> Agent:
    """Set up the chosen agent once for every session of the measurement."""
    cli = args.cli or ("claude" if args.agent.startswith("claude") else args.agent)
    agent = Agent(
        name=args.agent,
        cli=cli,
        plugin=plugin if args.arm == "with" else None,
        skill=plugin / "skills" / suite.skill,
        model=args.model,
        scratch=scratch,
    )
    if agent.name == "codex":
        return replace(agent, codex=codex_sandbox(cli, plugin, scratch / "codex"))
    if agent.name == "kimi":
        return replace(agent, kimi_home=kimi_home(scratch / "kimi-home"))
    if agent.name == "opencode":
        config = opencode_config(scratch / "opencode-config", args.model)
        return replace(agent, opencode_config=config)
    return agent


def start_session(
    agent: Agent,
    workspace: Path,
    pick: Callable[[str], str],
    extra: dict[str, str],
) -> Session:
    """Start one session in workspace; pick answers a clickable question."""
    if agent.name == "claude-ask":
        return AskSession(workspace, agent, pick, extra)
    if agent.name == "codex":
        return CodexSession(workspace, agent, extra)
    if agent.name == "kimi":
        return KimiSession(workspace, agent, extra)
    if agent.name == "opencode":
        return OpenCodeSession(workspace, agent, extra)
    return ClaudeSession(workspace, agent, extra)


# -- Interviews --------------------------------------------------------------


@dataclass
class Chat:
    """The turns of one interview, in order."""

    turns: list[tuple[str, str]] = field(default_factory=list)

    def add(self, who: str, text: str) -> None:
        """Append one turn."""
        self.turns.append((who, text))

    def text(self) -> str:
        """Return the chat as the simulated user and the judge read it."""
        return "\n\n".join(f"[{who}]\n{text}" for who, text in self.turns)


@dataclass(frozen=True)
class Context:
    """What every interview of one measurement shares."""

    suite: Suite
    agent: Agent
    arm: str
    user_model: str
    judge_model: str
    scratch: Path


def ask_model(prompt: str, model: str, cwd: Path) -> str:
    """Return the reply of `claude -p` with no tools, or raise EvalError."""
    result = run_command(
        [*MODEL_ARGV, "--model", model],
        cwd=cwd,
        env=agent_env(),
        timeout=MODEL_TIMEOUT_SECONDS,
        input_text=prompt,
    )
    if result.returncode != 0 or not result.stdout.strip():
        msg = f"`claude -p --model {model}` failed: {result.stderr.strip()[:300]}"
        raise EvalError(msg)
    return result.stdout.strip()


def first_message(ctx: Context, request: str) -> str:
    """Return request as the message that starts a session on the agent."""
    skill = ctx.suite.skill
    if ctx.arm == "without":
        return f"{ctx.suite.baseline}\n\n{request}"
    command = f"/{skill} {request}"
    if ctx.agent.name in {"claude", "claude-ask"}:
        return command
    if ctx.agent.name == "codex":
        return codex_prompt(command, skill)
    return f"Use the {skill} skill. {request}"


def interview(ctx: Context, scenario: Scenario, number: int) -> dict[str, Any]:
    """Run one whole interview, judge it and return its record."""
    suite = ctx.suite
    workspace = Path(
        tempfile.mkdtemp(prefix=f"{scenario.name}-{number}-", dir=ctx.scratch),
    )
    chat = Chat()

    def pick(question: str) -> str:
        prompt = PICK_PROMPT.format(
            setting=suite.setting,
            brief=scenario.brief,
            chat=chat.text(),
            question=question,
        )
        answer = ask_model(prompt, ctx.user_model, ctx.scratch)
        chat.add("assistant (clickable)", question)
        chat.add("user", answer)
        return answer

    session = start_session(ctx.agent, workspace, pick, {})
    message = first_message(ctx, scenario.prompt)
    label = f"{scenario.name} run {number}"
    try:
        for _ in range(MAX_TURNS):
            chat.add("user", message)
            reply = with_retries(partial(session.send, message), label)
            chat.add("assistant", reply)
            if "?" not in reply:
                break
            message = ask_model(
                USER_PROMPT.format(
                    setting=suite.setting,
                    brief=scenario.brief,
                    chat=chat.text(),
                ),
                ctx.user_model,
                ctx.scratch,
            )
            if message.strip() == DONE:
                break
    finally:
        session.close()
    path = workspace / scenario.file
    file_text = path.read_text() if path.is_file() else None
    checks = "\n".join(f'- "{key}": {text}' for key, text in suite.checks.items())
    judge_reply = ask_model(
        JUDGE_PROMPT.format(
            setting=suite.setting,
            brief=scenario.brief,
            chat=chat.text(),
            file=scenario.file,
            file_text=file_text if file_text is not None else "(no file)",
            checks=checks,
            judge_notes=suite.judge_notes,
        ),
        ctx.judge_model,
        ctx.scratch,
    )
    judge = parse_judge(judge_reply)
    problems = assess(judge, scenario, suite) + session.problems()
    return {
        "kind": "interview",
        "agent": ctx.agent.name,
        "arm": ctx.arm,
        "scenario": scenario.name,
        "run": number,
        "pass": not problems,
        "questions": (judge or {}).get("questions"),
        "problems": problems,
        "verdict": (judge or {}).get("verdict", judge_reply[:300]),
        "chat": chat.turns,
        "file": file_text,
        "judge": judge,
    }


def run_sequence(
    ctx: Context, sequence: SessionSequence, number: int
) -> dict[str, Any]:
    """Run each request of a sequence as a fresh session and check the files."""
    workspace = Path(
        tempfile.mkdtemp(prefix=f"{sequence.name}-{number}-", dir=ctx.scratch),
    )
    data = workspace / DATA_FOLDER
    places = {"workspace": str(workspace), "data": str(data)}
    problems, replies = [], []
    for index, request in enumerate(sequence.requests, start=1):
        session = start_session(
            ctx.agent,
            workspace,
            lambda _question: STOP_ANSWER,
            {"XDG_DATA_HOME": str(data)},
        )
        message = first_message(ctx, fill(request, places))
        label = f"{sequence.name} run {number} request {index}"
        try:
            replies.append(with_retries(partial(session.send, message), label))
        finally:
            session.close()
        problems += session.problems()
        problems += [
            f"after request {index}: {problem}"
            for expect in sequence.expect
            if expect.after == index
            and (problem := check_expectation(expect, places)) is not None
        ]
    return {
        "kind": "sequence",
        "agent": ctx.agent.name,
        "arm": ctx.arm,
        "scenario": sequence.name,
        "run": number,
        "pass": not problems,
        "problems": problems,
        "replies": replies,
    }


# -- CLI ---------------------------------------------------------------------


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(description="Run whole simulated interviews")
    parser.add_argument("plugin", type=Path, help="plugin directory")
    parser.add_argument("--agent", choices=AGENTS, default="claude")
    parser.add_argument("--arm", choices=("with", "without"), default="with")
    parser.add_argument("--scenario", default="*", help="scenario or sequence glob")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--cli", help="agent binary (default: the agent's name)")
    parser.add_argument("--model", help="agent model (default: the agent's own)")
    parser.add_argument("--user-model", default="sonnet")
    parser.add_argument("--judge-model", default="opus")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--out", type=Path, help="write chats, files and verdicts")
    args = parser.parse_args(argv)
    if args.runs < 1 or args.concurrency < 1:
        parser.error("--runs and --concurrency must be at least 1")
    if args.arm == "without" and args.agent != "claude":
        parser.error("--arm without runs only on --agent claude")
    return args


def run_item(
    ctx: Context,
    item: Scenario | SessionSequence,
    number: int,
) -> dict[str, Any]:
    """Run one scenario as an interview, or one sequence of sessions."""
    if isinstance(item, SessionSequence):
        return run_sequence(ctx, item, number)
    return interview(ctx, item, number)


def main(argv: list[str] | None = None) -> int:
    """Run the interviews and return the exit code."""
    args = parse_args(argv)
    plugin = args.plugin.resolve()
    detail_keys = ("chat", "file", "judge", "replies")
    records = []
    with tempfile.TemporaryDirectory(prefix="eval-interview-") as scratch_dir:
        # Resolved, so a folder a skill writes down matches the expected one.
        scratch = Path(scratch_dir).resolve()
        try:
            suite = load_suite(plugin)
            items = select_runs(suite, args.scenario, args.arm)
            ctx = Context(
                suite=suite,
                agent=setup_agent(args, plugin, suite, scratch),
                arm=args.arm,
                user_model=args.user_model,
                judge_model=args.judge_model,
                scratch=scratch,
            )
            jobs = [(item, n) for item in items for n in range(1, args.runs + 1)]
            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                for record in pool.map(lambda job: run_item(ctx, *job), jobs):
                    line = {k: v for k, v in record.items() if k not in detail_keys}
                    print(json.dumps(line, ensure_ascii=False), flush=True)
                    records.append(record)
        except (EvalError, OSError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    if args.out:
        args.out.write_text(json.dumps({"runs": records}, indent=1))
    passed = sum(bool(record["pass"]) for record in records)
    summary = {
        "kind": "summary",
        "total": len(records),
        "passed": passed,
        "failed": len(records) - passed,
    }
    print(json.dumps(summary))
    return 0 if args.arm == "without" or passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
