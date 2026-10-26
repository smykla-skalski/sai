"""Shared helpers for the skill eval tools in scripts/.

The tools read the suite that `claude plugin eval` runs: one directory per case
under plugins/<name>/evals/ with prompt.md, case.yaml, graders/*.md and an
optional scaffold script. Two optional data files sit next to the cases:
triggers.json (eval_triggers.py) and review.json (eval_review.py).
`claude plugin eval` only loads directories with prompt.md or case.yaml, so the
data files never become cases.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

T = TypeVar("T")

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
CODEX_MARKETPLACE: Final[Path] = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
FRONTMATTER_FENCE: Final[str] = "---"
BLOCK_SCALAR: Final[str] = "|"
INDENT: Final[str] = "  "
RETRY_DELAYS_SECONDS: Final[tuple[float, ...]] = (30.0, 120.0)


class EvalError(Exception):
    """An eval suite, data file or agent run that the tools cannot use."""


class RunFailedError(EvalError):
    """An agent run that ended before it finished its turn."""


def run_failure(event: dict[str, Any]) -> str | None:
    """Return the error of an event that ends an agent run in failure, else None."""
    if event.get("type") != "turn.failed":
        return None
    error = event.get("error")
    message = error.get("message") if isinstance(error, dict) else error
    return str(message or "the turn failed")


def with_retries(
    attempt: Callable[[], T],
    label: str,
    delays: tuple[float, ...] | None = None,
) -> T:
    """Return attempt(), running it again after a pause while the run fails.

    Codex ends a rate-limited run with a failed turn. Such a run says nothing
    about the skill, so it must not count as a result: it runs again, and a run
    that keeps failing stops the whole measurement.
    """
    remaining = RETRY_DELAYS_SECONDS if delays is None else delays
    try:
        return attempt()
    except RunFailedError as error:
        if not remaining:
            msg = f"{label}: {error}"
            raise EvalError(msg) from error
    time.sleep(remaining[0])
    return with_retries(attempt, label, remaining[1:])


@dataclass(frozen=True)
class Grader:
    """One graders/*.md file: frontmatter settings and the rubric text."""

    name: str
    meta: dict[str, Any]
    rubric: str


@dataclass(frozen=True)
class Case:
    """One eval case directory."""

    name: str
    path: Path
    prompt: str
    settings: dict[str, Any]
    expected_outcome: str
    graders: tuple[Grader, ...]
    scaffold: Path | None


# -- Parsing -----------------------------------------------------------------


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the YAML subset the eval files use.

    Supports `key: value`, `key: |` block scalars and one level of nested
    `key:` mappings. Flow lists such as `[a, b]` stay plain strings.
    """
    data: dict[str, Any] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(" "):
            msg = f"unexpected indentation: {line!r}"
            raise EvalError(msg)
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        nested: list[str] = []
        while index < len(lines) and (
            lines[index].startswith(INDENT) or not lines[index].strip()
        ):
            nested.append(lines[index])
            index += 1
        if value == BLOCK_SCALAR:
            data[key] = "\n".join(item.removeprefix(INDENT) for item in nested)
            data[key] = data[key].strip("\n") + "\n"
        elif value:
            data[key] = _scalar(value)
        else:
            data[key] = {
                sub_key.strip(): _scalar(sub_value)
                for sub_key, _, sub_value in (
                    item.strip().partition(":") for item in nested if item.strip()
                )
            }
    return data


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return the frontmatter settings and the body of a Markdown file."""
    if not text.startswith(FRONTMATTER_FENCE):
        return {}, text.strip()
    _, head, body = text.split(FRONTMATTER_FENCE, 2)
    return parse_simple_yaml(head), body.strip()


# -- Suites ------------------------------------------------------------------


def evals_dir(plugin: Path) -> Path:
    """Return the eval directory of a plugin, or raise EvalError."""
    path = plugin / "evals"
    if not path.is_dir():
        msg = f"{plugin} has no evals/ directory"
        raise EvalError(msg)
    return path


def load_case(path: Path) -> Case:
    """Load one case directory."""
    settings, prompt = split_frontmatter((path / "prompt.md").read_text())
    case_file = path / "case.yaml"
    meta = parse_simple_yaml(case_file.read_text()) if case_file.exists() else {}
    graders = tuple(
        Grader(grader.stem, *split_frontmatter(grader.read_text()))
        for grader in sorted((path / "graders").glob("*.md"))
    )
    context = meta.get("context")
    script = context.get("scaffold_script") if isinstance(context, dict) else None
    return Case(
        name=path.name,
        path=path,
        prompt=prompt,
        settings=settings,
        expected_outcome=" ".join(str(meta.get("expected_outcome", "")).split()),
        graders=graders,
        scaffold=path / script if script else None,
    )


def load_cases(plugin: Path, pattern: str = "*") -> list[Case]:
    """Load every case of a plugin whose name matches pattern, sorted by name."""
    root = evals_dir(plugin)
    return [
        load_case(path)
        for path in sorted(root.glob(pattern))
        if (path / "prompt.md").is_file()
    ]


def load_json_object(path: Path) -> dict[str, Any]:
    """Read a JSON file that holds an object, or raise EvalError with the path."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        msg = f"cannot read {path}: {error}"
        raise EvalError(msg) from error
    if not isinstance(data, dict):
        msg = f"{path} must hold a JSON object"
        raise EvalError(msg)
    return data


def skill_name(plugin: Path) -> str:
    """Return the name of the plugin's only skill."""
    skills = sorted(p.parent.name for p in (plugin / "skills").glob("*/SKILL.md"))
    if len(skills) != 1:
        msg = f"{plugin} must have exactly one skill, found {skills}"
        raise EvalError(msg)
    return skills[0]


def codex_prompt(prompt: str, skill: str) -> str:
    """Rewrite a leading /skill invocation into Codex's $skill form."""
    command = f"/{skill}"
    if prompt == command or prompt.startswith((f"{command} ", f"{command}\n")):
        return f"${skill}{prompt[len(command) :]}"
    return prompt


def write_files(root: Path, files: Mapping[str, str]) -> None:
    """Write fixture files, given as relative path to content, under root."""
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def snapshot(root: Path) -> dict[str, str]:
    """Return the text of every file under root, keyed by relative path."""
    return {
        str(path.relative_to(root)): path.read_text(errors="replace")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# -- Processes ---------------------------------------------------------------


def agent_env(**overrides: str) -> dict[str, str]:
    """Return the environment for a child agent CLI.

    CLAUDECODE is dropped so a nested `claude -p` does not refuse to start.
    """
    env = {key: value for key, value in os.environ.items() if key != "CLAUDECODE"}
    env.update(overrides)
    return env


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout: float,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run an agent CLI to completion and capture its output."""
    # S603: argv is a list with no shell. Callers build it from a CLI the
    # operator chose (claude, codex) plus eval data, which is the point here.
    return subprocess.run(  # noqa: S603
        argv,
        cwd=cwd,
        env=dict(env),
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def stream_json(
    argv: list[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout: float,
) -> Iterator[dict[str, Any]]:
    """Yield each JSON object an agent CLI prints, one per line.

    The process is killed when the caller stops reading or the timeout passes,
    so a trigger check can stop as soon as it has its answer.
    """
    # S603: argv is a list with no shell. Callers build it from a CLI the
    # operator chose (claude, codex) plus eval data, which is the point here.
    process = subprocess.Popen(  # noqa: S603
        argv,
        cwd=cwd,
        env=dict(env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    timer = threading.Timer(timeout, process.kill)
    timer.start()
    try:
        if process.stdout is None:
            return
        for line in process.stdout:
            with contextlib.suppress(json.JSONDecodeError):
                event = json.loads(line)
                if isinstance(event, dict):
                    yield event
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
        process.wait()


# -- Codex -------------------------------------------------------------------


@dataclass(frozen=True)
class CodexSandbox:
    """A Codex install that sees only the plugin under test."""

    codex: str
    home: Path
    codex_home: Path

    def env(self) -> dict[str, str]:
        """Return the environment that points Codex at the sandbox.

        HOME is a fresh directory too, so skills in ~/.agents/skills stay out.
        """
        return agent_env(HOME=str(self.home), CODEX_HOME=str(self.codex_home))

    def exec_argv(self, workspace: Path, prompt: str, model: str | None) -> list[str]:
        """Return the argv of one non-interactive Codex run with JSON events."""
        argv = [self.codex, "exec", "--skip-git-repo-check", "--ephemeral"]
        argv += ["-s", "workspace-write", "-C", str(workspace), "--json"]
        if model:
            argv += ["-m", model]
        return [*argv, prompt]


def _codex_auth() -> Path:
    base = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    auth = Path(base) / "auth.json"
    if not auth.is_file():
        msg = f"no Codex login at {auth}; run `codex login` first"
        raise EvalError(msg)
    return auth


def plugin_marketplace(plugin: Path, root: Path) -> tuple[Path, str]:
    """Write a Codex marketplace that serves only a copy of plugin.

    Return the marketplace directory and its name. The copy is what Codex
    installs, so a plugin outside the repo, such as an old snapshot or one with
    a candidate description, gets tested as given. The entry keeps the repo
    marketplace's settings for that plugin.
    """
    repo = load_json_object(CODEX_MARKETPLACE)
    entries = [e for e in repo.get("plugins", []) if e.get("name") == plugin.name]
    entry = dict(entries[0]) if entries else {"name": plugin.name}
    entry["source"] = {"source": "local", "path": f"./plugins/{plugin.name}"}
    market = root / "marketplace"
    shutil.copytree(
        plugin,
        market / "plugins" / plugin.name,
        ignore=shutil.ignore_patterns("evals"),
    )
    manifest = {"name": repo["name"], "plugins": [entry]}
    write_files(market, {".agents/plugins/marketplace.json": json.dumps(manifest)})
    return market, str(repo["name"])


def codex_sandbox(codex: str, plugin: Path, root: Path) -> CodexSandbox:
    """Install a copy of one plugin directory into a fresh Codex home.

    Codex copies plugins into its cache, so call this again after every edit.
    The codex binary must honor CODEX_HOME; some wrapper scripts do not.
    """
    sandbox = CodexSandbox(codex, root / "home", root / "codex-home")
    sandbox.home.mkdir(parents=True, exist_ok=True)
    sandbox.codex_home.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_codex_auth(), sandbox.codex_home / "auth.json")
    market, name = plugin_marketplace(plugin, root)
    for argv in (
        [codex, "plugin", "marketplace", "add", str(market)],
        [codex, "plugin", "add", f"{plugin.name}@{name}"],
    ):
        result = run_command(argv, cwd=root, env=sandbox.env(), timeout=120)
        if result.returncode != 0:
            msg = f"`{' '.join(argv[1:])}` failed: {result.stderr.strip()[:300]}"
            raise EvalError(msg)
    return sandbox
