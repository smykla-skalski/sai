#!/usr/bin/env python3
"""Helpers for the Codex Council improvement-loop runbook."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

FEATURE_FLAGS = [
    "--enable",
    "multi_agent_v2",
    "--enable",
    "enable_fanout",
    "--enable",
    "child_agents_md",
    "--enable",
    "runtime_metrics",
]

MANDATORY_HEADINGS = [
    "# Council review:",
    "## Convergence (high-confidence signals)",
    "## Disagreement (real tradeoffs the user must decide)",
    "## Per-reviewer top-3",
    "## What to do next",
    "## What we did not address",
]

SKILL_NEEDLES = [
    'reasoning_effort: "high"',
    "same as other reviewers",
    "Council progress:",
    "Council not run: broad council approval not granted.",
    "Council not run: skill unavailable.",
    "Every spawn or follow-up prompt, on every agent, starts exactly with",
    "Your first line must be exactly: ## <display name> review",
    "<subagent_notification>",
    "Never emit bare prefaces",
    "Never use shell/command execution for live-agent state",
    "After any `running` close result",
    "Never copy, quote, summarize-by-pasting, or echo",
    "A direct read is allowed only when the path",
    "Empty-query `web_search` is still forbidden",
    "Prepare agent capacity before any spawn",
    "inspect native live-agent state",
    "agent state clean: root only; running selected roster one reviewer at a time",
    "coordinator must proactively clean the thread tree",
    "close every visible stale Council reviewer child",
    "Run reviewers sequentially by default",
    "<persona-mandate>",
    "Do not spawn into a known full session",
]

PLUGIN_DIR = "plugins/council"
PERSONA_COUNT = 27
MAX_CONCURRENT_REVIEWERS = 1
CODEX_CACHE = Path.home() / ".codex/plugins/cache/sai/council"

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        fail(f"missing file: {path}")


def source_version(root: Path) -> str:
    plugin = load_json(root / PLUGIN_DIR / "plugin.json")
    claude = load_json(root / PLUGIN_DIR / ".claude-plugin/plugin.json")
    versions = {plugin.get("version"), claude.get("version")}
    if len(versions) != 1:
        fail(f"version mismatch: {sorted(str(v) for v in versions)}")
    version = versions.pop()
    if not isinstance(version, str) or not version:
        fail("empty plugin version")
    return version


def cache_versions() -> list[str]:
    if not CODEX_CACHE.exists():
        return []
    return sorted(path.name for path in CODEX_CACHE.iterdir() if path.is_dir())


def command_version(args: argparse.Namespace) -> None:
    print(source_version(repo_root()))


def command_baseline(args: argparse.Namespace) -> None:
    root = repo_root()
    subprocess.run(["git", "status", "-sb"], cwd=root, check=True)
    print(f"source version: {source_version(root)}")
    print(f"installed cache versions: {', '.join(cache_versions()) or '<none>'}")


def command_static(args: argparse.Namespace) -> None:
    root = repo_root()
    version = source_version(root)
    plugin = root / PLUGIN_DIR

    agents = check_agents(plugin)
    mandates = sorted((plugin / "skills/council/references/agents").glob("*.md"))
    if [path.name for path in mandates] != [path.name for path in agents]:
        fail("skills/council/references/agents/ mandates do not match agents/")
    if "$schema" in load_json(plugin / "plugin.json"):
        fail("root plugin.json must not set $schema: Copilot CLI then skips agents/")

    skill = (plugin / "skills/council/SKILL.md").read_text()
    missing = [needle for needle in SKILL_NEEDLES if needle not in skill]
    if missing:
        fail(f"skill missing required text: {missing}")
    if description_length(skill) > 1024:
        fail(f"skill frontmatter description exceeds 1024 chars: {description_length(skill)}")

    subprocess.run(["git", "diff", "--check"], cwd=root, check=True)
    print(f"static council surface ok: version={version} agents={len(agents)}")


def command_installed(args: argparse.Namespace) -> None:
    root = repo_root()
    version = args.version or source_version(root)
    cache = CODEX_CACHE / version
    manifest = load_json(cache / "plugin.json")
    if manifest.get("version") != version:
        fail(f"installed manifest version mismatch: {manifest.get('version')} != {version}")

    check_agents(cache)
    mandates = sorted((cache / "skills/council/references/agents").glob("*.md"))
    if len(mandates) != PERSONA_COUNT:
        fail(f"installed mandate count mismatch: {len(mandates)}")

    skill = (cache / "skills/council/SKILL.md").read_text()
    missing = [needle for needle in SKILL_NEEDLES if needle not in skill]
    if missing:
        fail(f"installed skill missing required text: {missing}")
    if description_length(skill) > 1024:
        fail(f"installed skill frontmatter description exceeds 1024 chars: {description_length(skill)}")

    print(f"installed cache ok: {cache}")


def check_agents(plugin: Path) -> list[Path]:
    """Fail unless the plugin ships every persona agent at high effort."""
    agents = sorted((plugin / "agents").glob("*.md"))
    if len(agents) != PERSONA_COUNT:
        fail(f"agent count mismatch in {plugin}: {len(agents)} != {PERSONA_COUNT}")
    bad_agents = [
        path.name
        for path in agents
        if "model_reasoning_effort: high" not in path.read_text()
        or "tools: Read" not in path.read_text()
    ]
    if bad_agents:
        fail(f"bad persona agents: {bad_agents}")
    return agents


def description_length(skill_text: str) -> int:
    if "description: >-" not in skill_text:
        return 0
    after = skill_text.split("description: >-", 1)[1].split("\n---", 1)[0]
    folded: list[str] = []
    for line in after.splitlines()[1:]:
        if line and not line.startswith(" "):
            break
        if line.strip():
            folded.append(line.strip())
    return len(" ".join(folded))


def resolve_evidence_dir(value: str | None) -> Path:
    root = repo_root()
    evidence = Path(value) if value else root / "tmp/council-validation" / source_version(root)
    if not evidence.is_absolute():
        evidence = root / evidence
    evidence.mkdir(parents=True, exist_ok=True)
    return evidence


def is_runtime_child_transport(text: str) -> bool:
    """Codex JSONL can surface child notifications as transcript transport."""
    return (
        "<subagent_notification>" in text
        and '"author":"/root' in text
        and '"trigger_turn":false' in text
    )


def authored_agent_messages(events: list[dict]) -> list[str]:
    messages: list[str] = []
    for event in events:
        item = event.get("item", {})
        if item.get("type") != "agent_message":
            continue
        text = item.get("text") or ""
        if is_runtime_child_transport(text):
            continue
        messages.append(text)
    return messages


def prompt_texts(events: list[dict]) -> list[str]:
    prompts: list[str] = []
    for event in events:
        item = event.get("item", {})
        if item.get("type") == "collab_tool_call":
            prompt = item.get("prompt")
            if isinstance(prompt, str):
                prompts.append(prompt)
    return prompts


def first_streaming_violation(event: dict) -> str | None:
    item = event.get("item", {})
    if item.get("type") != "agent_message":
        return None
    text = item.get("text") or ""
    if is_runtime_child_transport(text):
        return None
    if "<subagent_notification>" in text or '"author":"/root' in text or '"recipient":"/root' in text:
        return "raw child transport leaked into visible message"
    return None


def run_to_file(command: list[str], output: Path, cwd: Path, input_text: str | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    print("+ " + shlex.join(command))
    stdin = subprocess.PIPE if input_text is not None else subprocess.DEVNULL
    process = subprocess.Popen(command, cwd=cwd, stdin=stdin, stdout=subprocess.PIPE)
    if input_text is not None and process.stdin is not None:
        process.stdin.write(input_text.encode())
        process.stdin.close()
    assert process.stdout is not None
    with output.open("wb") as stdout:
        for line in process.stdout:
            stdout.write(line)
            stdout.flush()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            violation = first_streaming_violation(event)
            if violation:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                fail(violation)
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)


def session_id_from_jsonl(path: Path) -> str:
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            thread_id = event.get("thread_id")
            if isinstance(thread_id, str) and thread_id:
                return thread_id
        if event.get("type") == "session_meta":
            session_id = event.get("payload", {}).get("id")
            if isinstance(session_id, str) and session_id:
                return session_id
    fail(f"could not find session_meta payload.id in {path}")


def command_smoke(args: argparse.Namespace) -> None:
    root = repo_root()
    target_repo = Path(args.target_repo).expanduser().resolve()
    if not target_repo.is_dir():
        fail(f"target repo is not a directory: {target_repo}")

    evidence = resolve_evidence_dir(args.evidence_dir)
    for name in [
        "normal.jsonl",
        "normal-final.txt",
        "prefixed.jsonl",
        "prefixed-final.txt",
        "broad.jsonl",
        "broad-final.txt",
        "followup.jsonl",
        "followup-final.txt",
    ]:
        (evidence / name).unlink(missing_ok=True)
    env_model = os.environ.get("COUNCIL_SMOKE_MODEL", "gpt-5.4-mini")

    base = [
        "codex",
        "exec",
        "--json",
        "--cd",
        str(target_repo),
        "--model",
        env_model,
        *FEATURE_FLAGS,
    ]
    runs = [
        (
            "normal",
            '$council core-mix Council validation smoke. Inline material only: review the rule "always run all selected reviewers with complete bounded material" and report only material blockers. Use the regular fixed reviewer flow. Clean stale council agents first; if state is clean/root-only, run the reviewers one at a time.',
        ),
        (
            "prefixed",
            "$council:council core-mix Council validation smoke. Inline material only: verify the plugin-prefixed alias follows the same bounded-review behavior. Use the regular fixed reviewer flow. Clean stale council agents first; if state is clean/root-only, run the reviewers one at a time.",
        ),
        (
            "broad",
            "$council all Council validation smoke. Inline material only: this broad run has no same-turn approval and must stop.",
        ),
    ]

    for name, prompt in runs:
        run_to_file(
            [
                *base,
                "--output-last-message",
                str(evidence / f"{name}-final.txt"),
                "-",
            ],
            evidence / f"{name}.jsonl",
            root,
            input_text=prompt,
        )
        if name == "broad":
            check_broad(evidence / "broad-final.txt")
        else:
            check_review_run(evidence, name)

    normal_session_id = session_id_from_jsonl(evidence / "normal.jsonl")
    followup_prompt = (
        "$council follow-up challenge: using the prior council smoke result, "
        "verify the same accepted reviewer roster is preserved or explicitly reported missing."
    )
    run_to_file(
        [
            "codex",
            "exec",
            "resume",
            "--json",
            "--model",
            env_model,
            *FEATURE_FLAGS,
            "--output-last-message",
            str(evidence / "followup-final.txt"),
            normal_session_id,
            "-",
        ],
        evidence / "followup.jsonl",
        root,
        input_text=followup_prompt,
    )
    check_review_run(evidence, "followup")
    print(f"smoke evidence: {evidence}")


def check_broad(path: Path) -> None:
    expected = "Council not run: broad council approval not granted."
    actual = path.read_text().strip()
    if actual != expected:
        fail(f"broad stop mismatch in {path}: {actual!r}")


def command_check_broad(args: argparse.Namespace) -> None:
    check_broad(Path(args.path))
    print("broad stop ok")


def running_agents_from_close(item: dict) -> list[str]:
    agents_states = item.get("agents_states") or {}
    return [
        agent_id
        for agent_id, state in agents_states.items()
        if isinstance(state, dict) and state.get("status") == "running"
    ]


def has_close_recovery(events: list[dict], start_index: int) -> bool:
    recovery_tools = {"wait", "wait_agent", "send_input", "followup_task", "close_agent", "list_agents"}
    for event in events[start_index + 1 :]:
        item = event.get("item", {})
        item_type = item.get("type")
        if item_type == "collab_tool_call" and item.get("tool") in recovery_tools:
            return True
        if item_type == "agent_message" and (item.get("text") or "").startswith("# Council review:"):
            return False
    return False


def has_persona_mandate(prompt: str) -> bool:
    """Codex reviewers are generic agents; the mandate block carries the persona."""
    after_assignment = prompt.split("</council-review-assignment>", 1)[-1]
    return "<persona-mandate>" in after_assignment


def ensure_capacity_safe_spawns(events: list[dict], name: str) -> None:
    active_agents: set[str] = set()
    pending_close: set[str] = set()
    max_active = 0

    for event in events:
        item = event.get("item", {})
        if item.get("type") != "collab_tool_call":
            continue

        tool = item.get("tool")
        if tool == "spawn_agent":
            for agent_id in item.get("receiver_thread_ids") or []:
                if isinstance(agent_id, str):
                    active_agents.add(agent_id)
            max_active = max(max_active, len(active_agents))
            continue
        still_running = set(running_agents_from_close(item))
        if tool == "close_agent":
            for agent_id in item.get("receiver_thread_ids") or []:
                if isinstance(agent_id, str) and agent_id not in still_running:
                    active_agents.discard(agent_id)
            pending_close.update(still_running)
        resolved = {
            agent_id
            for agent_id, state in (item.get("agents_states") or {}).items()
            if agent_id in pending_close and isinstance(state, dict)
            and state.get("status") != "running"
        }
        active_agents.difference_update(resolved)
        pending_close.difference_update(resolved)

    if max_active > MAX_CONCURRENT_REVIEWERS:
        limit = MAX_CONCURRENT_REVIEWERS
        fail(f"{name} spawned {max_active} concurrent reviewers; limit is {limit}")


def load_jsonl(path: Path) -> list[dict]:
    events: list[dict] = []
    for line in path.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            fail(f"{path.name} contains invalid JSONL line: {line[:120]}")
    return events


def reviewer_payload_text(events: list[dict]) -> str:
    chunks: list[str] = []
    for event in events:
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            chunks.append(item.get("text") or "")
        if item.get("type") == "collab_tool_call":
            agents_states = item.get("agents_states") or {}
            for state in agents_states.values():
                if isinstance(state, dict):
                    message = state.get("message")
                    if isinstance(message, str):
                        chunks.append(message)
    return "\n".join(chunks)


def check_review_run(evidence: Path, name: str) -> None:
    final_path = evidence / f"{name}-final.txt"
    jsonl_path = evidence / f"{name}.jsonl"
    if not final_path.exists() or not jsonl_path.exists():
        fail(f"{name} evidence missing")

    final_text = final_path.read_text()

    events = load_jsonl(jsonl_path)
    jsonl_text = jsonl_path.read_text()
    visible_text = "\n".join(authored_agent_messages(events))
    forbidden_raw = ["<subagent_notification>", '"author":"/root', '"recipient":"/root']
    leaked = [needle for needle in forbidden_raw if needle in f"{final_text}\n{visible_text}"]
    if leaked:
        fail(f"raw child transport leaked into authored/final messages: {leaked}")
    alias_headings = ["## antirez review", "## tef review", "## hebert review", "## nielsen review"]
    payload_text = reviewer_payload_text(events)
    bad_heading = [heading for heading in alias_headings if heading in payload_text]
    if bad_heading:
        fail(f"reviewer alias heading accepted or leaked: {bad_heading}")
    prompt_text = "\n".join(prompt_texts(events))
    if "same as other reviewers" in prompt_text or "same as assignment" in prompt_text:
        fail("shorthand reviewer material leaked into reviewer prompt")

    exact_fanout_failure = final_text.strip() == "Council not run: reviewer fan-out failed."
    accepted_review_count = payload_text.count("## ")
    if exact_fanout_failure:
        if accepted_review_count:
            fail("fan-out failure returned despite accepted reviewer bodies")
    else:
        missing_headings = [heading for heading in MANDATORY_HEADINGS if heading not in final_text]
        if missing_headings:
            fail(f"{final_path.name} missing headings: {missing_headings}")
    ensure_capacity_safe_spawns(events, jsonl_path.name)

    bad_prompts: list[str] = []
    running_close_without_tool: list[str] = []
    for index, event in enumerate(events):
        item = event.get("item", {})
        if item.get("type") != "collab_tool_call":
            continue
        tool = item.get("tool")
        if tool == "close_agent" and item.get("status") == "completed":
            running_agents = running_agents_from_close(item)
            if running_agents and not has_close_recovery(events, index):
                running_close_without_tool.extend(running_agents)
        if tool not in {"spawn_agent", "send_input", "followup_task"}:
            continue
        prompt = item.get("prompt") or ""
        if not prompt.startswith("You are "):
            bad_prompts.append(f"{tool} prompt does not start with 'You are ': {prompt[:80]!r}")
            continue
        if "Your first line must be exactly: ## " not in prompt[:260]:
            bad_prompts.append(f"{tool} prompt missing exact first-line heading requirement: {prompt[:160]!r}")
            continue
        if "\n\n<council-review-assignment>" not in prompt[:320]:
            bad_prompts.append(f"{tool} prompt missing blank-line assignment boundary: {prompt[:160]!r}")
            continue
        if "<council-review-assignment>" in prompt:
            before_assignment = prompt.split("<council-review-assignment>", 1)[0]
            if "\n## " in before_assignment:
                bad_prompts.append(
                    f"{tool} prompt has reviewer heading before assignment: {before_assignment[:120]!r}"
                )
        if tool == "spawn_agent" and not has_persona_mandate(prompt):
            bad_prompts.append(
                f"spawn_agent prompt lacks <persona-mandate>: {prompt[:120]!r}",
            )
    if bad_prompts:
        fail("; ".join(bad_prompts[:5]))
    if running_close_without_tool:
        fail(f"running close result without recovery tool call: {running_close_without_tool[:5]}")
    if jsonl_text.count("spawn_agent") == 0:
        fail("evidence does not mention spawn_agent")
    if jsonl_text.count("wait_agent") + jsonl_text.count('"tool":"wait"') == 0:
        fail("evidence does not mention wait_agent")


def command_evidence(args: argparse.Namespace) -> None:
    evidence = resolve_evidence_dir(args.evidence_dir)
    required_files = [
        "normal.jsonl",
        "normal-final.txt",
        "prefixed.jsonl",
        "prefixed-final.txt",
        "broad.jsonl",
        "broad-final.txt",
        "followup.jsonl",
        "followup-final.txt",
    ]
    missing = [name for name in required_files if not (evidence / name).exists()]
    if missing:
        fail(f"missing evidence files: {missing}")

    check_broad(evidence / "broad-final.txt")

    for name in ["normal-final.txt", "prefixed-final.txt", "followup-final.txt"]:
        text = (evidence / name).read_text()
        missing_headings = [heading for heading in MANDATORY_HEADINGS if heading not in text]
        if missing_headings:
            fail(f"{name} missing headings: {missing_headings}")

    jsonl_names = ["normal.jsonl", "prefixed.jsonl", "followup.jsonl"]
    events: list[dict] = []
    events_by_file: dict[str, list[dict]] = {}
    jsonl_chunks: list[str] = []
    for name in jsonl_names:
        text = (evidence / name).read_text()
        jsonl_chunks.append(text)
        file_events = load_jsonl(evidence / name)
        events.extend(file_events)
        events_by_file[name] = file_events
    jsonl_text = "\n".join(jsonl_chunks)
    visible_text = "\n".join(authored_agent_messages(events))
    forbidden_raw = ["<subagent_notification>", '"author":"/root', '"recipient":"/root']
    final_text = "\n".join((evidence / name).read_text() for name in required_files if name.endswith("-final.txt"))
    leaked = [needle for needle in forbidden_raw if needle in f"{final_text}\n{visible_text}"]
    if leaked:
        fail(f"raw child transport leaked into authored/final messages: {leaked}")
    alias_headings = ["## antirez review", "## tef review", "## hebert review", "## nielsen review"]
    payload_text = reviewer_payload_text(events)
    bad_heading = [heading for heading in alias_headings if heading in f"{final_text}\n{payload_text}"]
    if bad_heading:
        fail(f"reviewer alias heading accepted or leaked: {bad_heading}")
    prompt_text = "\n".join(prompt_texts(events))
    if "same as other reviewers" in prompt_text or "same as assignment" in prompt_text:
        fail("shorthand reviewer material leaked into reviewer prompt")
    for name, file_events in events_by_file.items():
        ensure_capacity_safe_spawns(file_events, name)

    bad_prompts: list[str] = []
    running_close_without_tool: list[str] = []
    for index, event in enumerate(events):
        item = event.get("item", {})
        if item.get("type") != "collab_tool_call":
            continue
        tool = item.get("tool")
        if tool == "close_agent" and item.get("status") == "completed":
            running_agents = running_agents_from_close(item)
            if running_agents and not has_close_recovery(events, index):
                running_close_without_tool.extend(running_agents)
        if tool not in {"spawn_agent", "send_input", "followup_task"}:
            continue
        prompt = item.get("prompt") or ""
        if not prompt.startswith("You are "):
            bad_prompts.append(f"{tool} prompt does not start with 'You are ': {prompt[:80]!r}")
            continue
        if "Your first line must be exactly: ## " not in prompt[:260]:
            bad_prompts.append(f"{tool} prompt missing exact first-line heading requirement: {prompt[:160]!r}")
            continue
        if "\n\n<council-review-assignment>" not in prompt[:320]:
            bad_prompts.append(f"{tool} prompt missing blank-line assignment boundary: {prompt[:160]!r}")
            continue
        if "<council-review-assignment>" in prompt:
            before_assignment = prompt.split("<council-review-assignment>", 1)[0]
            if "\n## " in before_assignment:
                bad_prompts.append(
                    f"{tool} prompt has reviewer heading before assignment: {before_assignment[:120]!r}"
                )
        if tool == "spawn_agent" and not has_persona_mandate(prompt):
            bad_prompts.append(
                f"spawn_agent prompt lacks <persona-mandate>: {prompt[:120]!r}",
            )
    if bad_prompts:
        fail("; ".join(bad_prompts[:5]))
    if running_close_without_tool:
        fail(f"running close result without recovery tool call: {running_close_without_tool[:5]}")

    counts = {
        "spawn_agent": jsonl_text.count("spawn_agent"),
        "wait_agent": jsonl_text.count("wait_agent") + jsonl_text.count('"tool":"wait"'),
        "followup_or_send_input": jsonl_text.count("followup_task") + jsonl_text.count('"tool":"send_input"'),
        "Council progress:": jsonl_text.count("Council progress:"),
    }
    if counts["spawn_agent"] == 0:
        fail("evidence does not mention spawn_agent")
    if counts["wait_agent"] == 0:
        fail("evidence does not mention wait_agent")

    print(f"evidence ok: {evidence}")
    for key, count in counts.items():
        print(f"{key}: {count}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("version", help="Print aligned source plugin version").set_defaults(
        func=command_version
    )
    subcommands.add_parser("baseline", help="Print git status, source version, and cache versions").set_defaults(
        func=command_baseline
    )
    subcommands.add_parser("static", help="Validate source Council surface").set_defaults(
        func=command_static
    )

    installed = subcommands.add_parser("installed", help="Validate installed cache")
    installed.add_argument("version", nargs="?")
    installed.set_defaults(func=command_installed)

    smoke = subcommands.add_parser("smoke", help="Run live Codex Council smoke checks")
    smoke.add_argument("target_repo")
    smoke.add_argument("evidence_dir", nargs="?")
    smoke.set_defaults(func=command_smoke)

    broad = subcommands.add_parser("check-broad", help="Validate broad-stop final output")
    broad.add_argument("path")
    broad.set_defaults(func=command_check_broad)

    evidence = subcommands.add_parser("evidence", help="Validate saved smoke evidence")
    evidence.add_argument("evidence_dir", nargs="?")
    evidence.set_defaults(func=command_evidence)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
