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
    "Do not emit prefaces",
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

    print(f"installed cache ok: {cache}")


def resolve_evidence_dir(value: str | None) -> Path:
    root = repo_root()
    evidence = Path(value) if value else root / "tmp/council-validation" / source_version(root)
    if not evidence.is_absolute():
        evidence = root / evidence
    evidence.mkdir(parents=True, exist_ok=True)
    return evidence


def run_to_file(command: list[str], output: Path, cwd: Path, input_text: str | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    print("+ " + shlex.join(command))
    with output.open("wb") as stdout:
        run_kwargs = {"cwd": cwd, "stdout": stdout, "check": True}
        if input_text is None:
            run_kwargs["stdin"] = subprocess.DEVNULL
        else:
            run_kwargs["input"] = input_text.encode()
        subprocess.run(command, **run_kwargs)


def session_id_from_jsonl(path: Path) -> str:
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
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
            '$council core-mix Council validation smoke. Inline material only: review the rule "always run all selected reviewers with complete bounded material" and report only material blockers.',
        ),
        (
            "prefixed",
            "$council:council core-mix Council validation smoke. Inline material only: verify the plugin-prefixed alias follows the same bounded-review behavior.",
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

    check_broad(evidence / "broad-final.txt")
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
    print(f"smoke evidence: {evidence}")


def check_broad(path: Path) -> None:
    expected = "Council not run: broad council approval not granted."
    actual = path.read_text().strip()
    if actual != expected:
        fail(f"broad stop mismatch in {path}: {actual!r}")


def command_check_broad(args: argparse.Namespace) -> None:
    check_broad(Path(args.path))
    print("broad stop ok")


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
    jsonl_chunks: list[str] = []
    for name in jsonl_names:
        text = (evidence / name).read_text()
        jsonl_chunks.append(text)
        for line in text.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                fail(f"{name} contains invalid JSONL line: {line[:120]}")
    jsonl_text = "\n".join(jsonl_chunks)
    forbidden_raw = ["<subagent_notification>", '"author":"/root', '"recipient":"/root']
    leaked = [needle for needle in forbidden_raw if needle in jsonl_text]
    if leaked:
        fail(f"raw child transport leaked into evidence stream: {leaked}")
    if "same as other reviewers" in jsonl_text or "same as assignment" in jsonl_text:
        fail("shorthand reviewer material leaked into evidence stream")

    bad_prompts: list[str] = []
    bad_status: list[str] = []
    for event in events:
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            text = item.get("text") or ""
            if text.startswith("# Council review:") or text.startswith("Council not run:"):
                continue
            if not text.startswith("Council progress:"):
                bad_status.append(text[:120])
            continue
        if item.get("type") != "collab_tool_call":
            continue
        tool = item.get("tool")
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
    if bad_prompts:
        fail("; ".join(bad_prompts[:5]))

    counts = {
        "spawn_agent": jsonl_text.count("spawn_agent"),
        "wait_agent": jsonl_text.count("wait_agent"),
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
