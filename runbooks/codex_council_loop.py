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

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 is unsupported here.
    tomllib = None


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
    "Every spawn or follow-up prompt must start exactly",
    "<subagent_notification>",
    "Never emit bare prefaces",
    "Never use shell/command execution for live-agent state",
    "skill-use announcement is unavoidable",
    "After any `running` close result",
    "Never copy, quote, summarize-by-pasting, or echo",
    "FIRST ACTION: load this SKILL",
    "Empty-query `web_search` is still forbidden",
    "Empty-query `web_search` is still forbidden",
    "Prepare agent capacity before any spawn",
    "inspect native live-agent state",
    "agent state clean: root only; running full selected roster when within limit",
    "coordinator must proactively clean the thread tree",
    "close every visible stale Council reviewer child",
    "Fan out in waves sized by cleaned capacity",
    "Do not spawn into a known full session",
]


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
    plugin = load_json(root / "plugins/council/plugin.json")
    codex = load_json(root / "plugins/council/.codex-plugin/plugin.json")
    versions = {plugin.get("version"), codex.get("version")}
    if len(versions) != 1:
        fail(f"version mismatch: {sorted(str(v) for v in versions)}")
    version = versions.pop()
    if not isinstance(version, str) or not version:
        fail("empty plugin version")
    return version


def cache_versions() -> list[str]:
    cache = Path.home() / ".codex/plugins/cache/sai/council"
    if not cache.exists():
        return []
    return sorted(path.name for path in cache.iterdir() if path.is_dir())


def command_version(args: argparse.Namespace) -> None:
    print(source_version(repo_root()))


def command_baseline(args: argparse.Namespace) -> None:
    root = repo_root()
    subprocess.run(["git", "status", "-sb"], cwd=root, check=True)
    print(f"source version: {source_version(root)}")
    print(f"installed cache versions: {', '.join(cache_versions()) or '<none>'}")


def command_static(args: argparse.Namespace) -> None:
    if tomllib is None:
        fail("python3 must provide tomllib")

    root = repo_root()
    version = source_version(root)

    agents = sorted((root / "codex/agents").glob("*.toml"))
    if not agents:
        fail("no codex/agents/*.toml files found")
    medium_agents = [
        path.name
        for path in agents
        if tomllib.loads(path.read_text()).get("model_reasoning_effort") != "high"
    ]
    if medium_agents:
        fail(f"non-high codex agents: {medium_agents}")

    packaged = sorted((root / "plugins/council/agents").glob("*.agent.md"))
    if len(packaged) != len(agents):
        fail(f"agent count mismatch: packaged={len(packaged)} toml={len(agents)}")
    bad_packaged = [
        path.name
        for path in packaged
        if "model_reasoning_effort: high" not in path.read_text()
        or "tools: Read" not in path.read_text()
    ]
    if bad_packaged:
        fail(f"bad packaged agents: {bad_packaged}")

    skill = (root / "plugins/council/skills/council/SKILL.md").read_text()
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
    cache = Path.home() / ".codex/plugins/cache/sai/council" / version
    manifest = load_json(cache / ".codex-plugin/plugin.json")
    if manifest.get("version") != version:
        fail(f"installed manifest version mismatch: {manifest.get('version')} != {version}")

    agents = sorted((cache / "agents").glob("*.agent.md"))
    if len(agents) != 27:
        fail(f"installed agent count mismatch: {len(agents)}")
    bad_agents = [
        path.name
        for path in agents
        if "model_reasoning_effort: high" not in path.read_text()
        or "tools: Read" not in path.read_text()
    ]
    if bad_agents:
        fail(f"bad installed agents: {bad_agents}")

    skill = (cache / "skills/council/SKILL.md").read_text()
    missing = [needle for needle in SKILL_NEEDLES if needle not in skill]
    if missing:
        fail(f"installed skill missing required text: {missing}")
    if description_length(skill) > 1024:
        fail(f"installed skill frontmatter description exceeds 1024 chars: {description_length(skill)}")

    print(f"installed cache ok: {cache}")


def description_length(skill_text: str) -> int:
    if "description: >-" not in skill_text:
        return 0
    after = skill_text.split("description: >-", 1)[1]
    before_end = after.split("---", 1)[0]
    return len(" ".join(line.strip() for line in before_end.splitlines() if line.strip()))


def resolve_evidence_dir(value: str | None) -> Path:
    root = repo_root()
    evidence = Path(value) if value else root / "tmp/council-validation" / source_version(root)
    if not evidence.is_absolute():
        evidence = root / evidence
    evidence.mkdir(parents=True, exist_ok=True)
    return evidence


def first_streaming_violation(event: dict) -> str | None:
    item = event.get("item", {})
    item_type = item.get("type")
    if item_type == "agent_message":
        text = item.get("text") or ""
        if text.startswith("# Council review:") or text.startswith("Council not run:"):
            return None
        if "<subagent_notification>" in text or '"author":"/root' in text or '"recipient":"/root' in text:
            return "raw child transport leaked into visible message"
        if not text.startswith("Council progress:"):
            return f"non-Council progress status line: {text[:120]}"
        return None
    if item_type == "command_execution":
        command = item.get("command") or ""
        forbidden_bits = ["&&", ";", " pwd", "pwd ", " find ", " rg ", " ls "]
        if any(bit in command for bit in forbidden_bits):
            return f"forbidden chained/discovery command: {command[:160]}"
        return None
    if item_type in {"web_search", "browser"}:
        return f"forbidden tool used: {item_type}"
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
            '$council core-mix Council validation smoke. Inline material only: review the rule "always run all selected reviewers with complete bounded material" and report only material blockers. Use the regular fixed reviewer flow. Clean stale council agents first; if state is clean/root-only, run the largest safe wave.',
        ),
        (
            "prefixed",
            "$council:council core-mix Council validation smoke. Inline material only: verify the plugin-prefixed alias follows the same bounded-review behavior. Use the regular fixed reviewer flow. Clean stale council agents first; if state is clean/root-only, run the largest safe wave.",
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


def ensure_progress_claims_have_tools(events: list[dict], name: str) -> None:
    claim_tools = {
        "checking": {"list_agents", "wait", "wait_agent"},
        "verifying": {"list_agents", "wait", "wait_agent"},
        "retrying": {"close_agent", "followup_task", "send_input", "wait", "wait_agent", "list_agents"},
        "closing": {"close_agent"},
        "waiting": {"wait", "wait_agent"},
    }
    violations: list[str] = []
    for index, event in enumerate(events):
        item = event.get("item", {})
        if item.get("type") != "agent_message":
            continue
        text = item.get("text") or ""
        if not text.startswith("Council progress:"):
            continue
        lowered = text.lower()
        required: set[str] = set()
        for word, tools in claim_tools.items():
            if word in lowered:
                required |= tools
        if not required:
            continue
        next_tool = None
        for later in events[index + 1 :]:
            later_item = later.get("item", {})
            later_type = later_item.get("type")
            if later_type == "collab_tool_call":
                next_tool = later_item.get("tool")
                break
            if later_type == "agent_message" or later_type == "command_execution":
                break
        if next_tool not in required:
            violations.append(text[:120])
    if violations:
        fail(f"{name} progress claimed a tool action without matching next tool call: {violations[:5]}")


def ensure_capacity_safe_spawns(events: list[dict], name: str) -> None:
    first_spawn_index: int | None = None
    capacity_checked_before_spawn = False
    active_agents: set[str] = set()
    max_active = 0

    for index, event in enumerate(events):
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            text = item.get("text") or ""
            if text == "Council progress: agent state clean: root only; running full selected roster when within limit.":
                if first_spawn_index is None:
                    capacity_checked_before_spawn = True
            continue
        if item.get("type") != "collab_tool_call":
            continue

        tool = item.get("tool")
        if tool == "list_agents" and first_spawn_index is None:
            capacity_checked_before_spawn = True
            continue
        if tool == "spawn_agent":
            if first_spawn_index is None:
                first_spawn_index = index
            for agent_id in item.get("receiver_thread_ids") or []:
                if isinstance(agent_id, str):
                    active_agents.add(agent_id)
            max_active = max(max_active, len(active_agents))
            continue
        if tool == "close_agent":
            for agent_id in item.get("receiver_thread_ids") or []:
                if isinstance(agent_id, str):
                    active_agents.discard(agent_id)

    if first_spawn_index is None:
        return
    if not capacity_checked_before_spawn:
        fail(f"{name} spawned reviewers before agent-state cleanup/check")
    if max_active > 6:
        fail(f"{name} spawned {max_active} concurrent reviewers; subagent limit is 6")


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
    missing_headings = [heading for heading in MANDATORY_HEADINGS if heading not in final_text]
    if missing_headings:
        fail(f"{final_path.name} missing headings: {missing_headings}")

    events = load_jsonl(jsonl_path)
    jsonl_text = jsonl_path.read_text()
    visible_text = "\n".join(
        item.get("text") or ""
        for event in events
        for item in [event.get("item", {})]
        if item.get("type") == "agent_message"
    )
    forbidden_raw = ["<subagent_notification>", '"author":"/root', '"recipient":"/root']
    leaked = [needle for needle in forbidden_raw if needle in visible_text]
    if leaked:
        fail(f"raw child transport leaked into visible messages: {leaked}")
    alias_headings = ["## antirez review", "## tef review", "## hebert review", "## nielsen review"]
    payload_text = reviewer_payload_text(events)
    bad_heading = [heading for heading in alias_headings if heading in payload_text]
    if bad_heading:
        fail(f"reviewer alias heading accepted or leaked: {bad_heading}")
    if "same as other reviewers" in jsonl_text or "same as assignment" in jsonl_text:
        fail("shorthand reviewer material leaked into evidence stream")
    ensure_capacity_safe_spawns(events, jsonl_path.name)
    ensure_progress_claims_have_tools(events, jsonl_path.name)

    bad_prompts: list[str] = []
    bad_status: list[str] = []
    bad_commands: list[str] = []
    forbidden_tools: list[str] = []
    running_close_without_tool: list[str] = []
    for index, event in enumerate(events):
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            text = item.get("text") or ""
            if text.startswith("# Council review:") or text.startswith("Council not run:"):
                continue
            if not text.startswith("Council progress:"):
                bad_status.append(text[:120])
            continue
        if item.get("type") == "command_execution":
            command = item.get("command") or ""
            forbidden_command_bits = ["ls_agents", "list_agents", " pgrep", " ps ", " find ", " rg ", "pwd &&"]
            if any(bit in command for bit in forbidden_command_bits):
                bad_commands.append(command[:160])
            continue
        if item.get("type") in {"web_search", "browser"}:
            forbidden_tools.append(item.get("type"))
            continue
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
        if "setup.\n\n<council-review-assignment>" not in prompt[:240]:
            bad_prompts.append(f"{tool} prompt missing blank-line assignment boundary: {prompt[:120]!r}")
            continue
        if "<council-review-assignment>" in prompt:
            before_assignment = prompt.split("<council-review-assignment>", 1)[0]
            if "\n## " in before_assignment:
                bad_prompts.append(
                    f"{tool} prompt has reviewer heading before assignment: {before_assignment[:120]!r}"
                )
    if bad_status:
        fail(f"non-Council progress status lines: {bad_status[:5]}")
    if bad_commands:
        fail(f"shell-based agent probing/orchestration commands: {bad_commands[:5]}")
    if forbidden_tools:
        fail(f"forbidden search/browser tools used: {forbidden_tools[:5]}")
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
    visible_text = "\n".join(
        item.get("text") or ""
        for event in events
        for item in [event.get("item", {})]
        if item.get("type") == "agent_message"
    )
    forbidden_raw = ["<subagent_notification>", '"author":"/root', '"recipient":"/root']
    leaked = [needle for needle in forbidden_raw if needle in visible_text]
    if leaked:
        fail(f"raw child transport leaked into visible messages: {leaked}")
    alias_headings = ["## antirez review", "## tef review", "## hebert review", "## nielsen review"]
    bad_heading = [heading for heading in alias_headings if heading in jsonl_text]
    if bad_heading:
        fail(f"reviewer alias heading accepted or leaked: {bad_heading}")
    if "same as other reviewers" in jsonl_text or "same as assignment" in jsonl_text:
        fail("shorthand reviewer material leaked into evidence stream")
    for name, file_events in events_by_file.items():
        ensure_capacity_safe_spawns(file_events, name)
        ensure_progress_claims_have_tools(file_events, name)

    bad_prompts: list[str] = []
    bad_status: list[str] = []
    bad_commands: list[str] = []
    forbidden_tools: list[str] = []
    running_close_without_tool: list[str] = []
    first_agent_message_seen = False
    for index, event in enumerate(events):
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            text = item.get("text") or ""
            if not first_agent_message_seen:
                first_agent_message_seen = True
                continue
            if text.startswith("# Council review:") or text.startswith("Council not run:"):
                continue
            if not text.startswith("Council progress:"):
                bad_status.append(text[:120])
            continue
        if item.get("type") == "command_execution":
            command = item.get("command") or ""
            forbidden_command_bits = ["ls_agents", "list_agents", " pgrep", " ps ", " find ", " rg "]
            if any(bit in command for bit in forbidden_command_bits):
                bad_commands.append(command[:160])
            continue
        if item.get("type") in {"web_search", "browser"}:
            forbidden_tools.append(item.get("type"))
            continue
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
        if "setup.\n\n<council-review-assignment>" not in prompt[:240]:
            bad_prompts.append(f"{tool} prompt missing blank-line assignment boundary: {prompt[:120]!r}")
            continue
        if "<council-review-assignment>" in prompt:
            before_assignment = prompt.split("<council-review-assignment>", 1)[0]
            if "\n## " in before_assignment:
                bad_prompts.append(
                    f"{tool} prompt has reviewer heading before assignment: {before_assignment[:120]!r}"
                )
    if bad_status:
        fail(f"non-Council progress status lines: {bad_status[:5]}")
    if bad_commands:
        fail(f"shell-based agent probing/orchestration commands: {bad_commands[:5]}")
    if forbidden_tools:
        fail(f"forbidden search/browser tools used: {forbidden_tools[:5]}")
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
