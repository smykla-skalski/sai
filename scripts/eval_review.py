#!/usr/bin/env python3
"""Review eval runs with Jev, a decision model on OpenRouter.

This replaces the human read-through of eval outputs. It reads the plugin's
evals/review.json:

    {"where": "...", "quality": "...",
     "criteria": {"name": [{"ask": "...", "pass": "...", "fail": "...",
                            "inverted": true}, ...]},
     "cases": {"case": {"medium": "...", "file": "notes.md",
                        "check_quotes": true, "criteria": ["name", ...],
                        "graders": {"name": ["grader", ...]}}}}

Each criterion is asked in at least three phrasings, one of them inverted, so a
reviewer that agrees with everything shows up as inconsistent. A criterion
passes when most phrasings pass. `{where}` and `{medium}` in the text are
replaced with the "where" text and the case's medium. Code computes what Jev
is weak at: whether the file changed and, with check_quotes, which quotes in
the reply's table rows are not verbatim in the original. "graders" maps a
criterion to `claude plugin eval` graders that judge the same thing, so the
summary reports how often Jev and the graders agree.

RESULTS is [LABEL=]PATH[@ARM]: the JSON from `claude plugin eval --json PATH
--keep-temp` (ARM is with or without, default with) or from eval_codex.py
--out. Give older versions or the no-plugin arm as extra labels to see that
Jev catches their known failures. The OpenRouter key comes from
OPENROUTER_API_KEY or AFI_OPENROUTER_API_KEY, in the environment or ~/.env.

Usage:
    scripts/eval_review.py plugins/humanize RESULTS... [--model MODEL]
        [--out raw.json]

Output: one NDJSON "review" record per run, then a "summary" record.
Exit codes: 0 every run of the first label passes, 1 one fails, 2 usage,
input or API error.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from _eval_common import Case, EvalError, evals_dir, load_cases, load_json_object

DEFAULT_MODEL: Final[str] = "~typesafe/jev-latest"
PASS_PROBABILITY: Final[float] = 0.5
KEY_NAMES: Final[tuple[str, ...]] = ("OPENROUTER_API_KEY", "AFI_OPENROUTER_API_KEY")
REQUEST_TIMEOUT_SECONDS: Final[int] = 300
ATTEMPTS: Final[int] = 3
MIN_VARIANTS: Final[int] = 3
MIN_QUOTE_CHARS: Final[int] = 4
QUALITY_LABELS: Final[list[str]] = [
    "Unusable",
    "Poor",
    "Acceptable",
    "Good",
    "Excellent",
]
QUOTE: Final[re.Pattern[str]] = re.compile(rf'"([^"]{{{MIN_QUOTE_CHARS},}})"')
CURLY: Final[dict[int, str]] = str.maketrans(
    {
        "\N{LEFT SINGLE QUOTATION MARK}": "'",
        "\N{RIGHT SINGLE QUOTATION MARK}": "'",
        "\N{LEFT DOUBLE QUOTATION MARK}": '"',
        "\N{RIGHT DOUBLE QUOTATION MARK}": '"',
    },
)
ARMS: Final[frozenset[str]] = frozenset({"with", "without"})


@dataclass(frozen=True)
class Variant:
    """One phrasing of a criterion."""

    ask: str
    pass_text: str
    fail_text: str
    inverted: bool


@dataclass(frozen=True)
class CaseReview:
    """What review.json says about one case."""

    medium: str
    file: str | None
    check_quotes: bool
    criteria: tuple[str, ...]
    graders: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class Rubric:
    """A plugin's review.json."""

    where: str
    quality: str
    criteria: dict[str, tuple[Variant, ...]]
    cases: dict[str, CaseReview]


@dataclass(frozen=True)
class RunInput:
    """One eval run to review."""

    label: str
    case: str
    number: int
    reply: str
    files: dict[str, str] | None
    graders: dict[str, bool]


# -- Rubric ------------------------------------------------------------------


def _variants(name: str, raw: object) -> tuple[Variant, ...]:
    if not isinstance(raw, list) or len(raw) < MIN_VARIANTS:
        msg = f"criterion {name} needs at least {MIN_VARIANTS} phrasings"
        raise EvalError(msg)
    variants = tuple(
        Variant(
            str(item["ask"]),
            str(item["pass"]),
            str(item["fail"]),
            bool(item.get("inverted")),
        )
        for item in raw
        if isinstance(item, dict)
    )
    if len(variants) != len(raw) or not any(v.inverted for v in variants):
        msg = f"criterion {name} needs object phrasings and one inverted phrasing"
        raise EvalError(msg)
    return variants


def load_rubric(plugin: Path, cases: dict[str, Case]) -> Rubric:
    """Read and check review.json against the plugin's eval cases."""
    data = load_json_object(evals_dir(plugin) / "review.json")
    criteria = {
        str(name): _variants(str(name), raw)
        for name, raw in dict(data.get("criteria", {})).items()
    }
    reviews: dict[str, CaseReview] = {}
    for name, raw in dict(data.get("cases", {})).items():
        if name not in cases:
            msg = f"review.json names case {name}, which has no prompt.md"
            raise EvalError(msg)
        review = CaseReview(
            medium=str(raw["medium"]),
            file=str(raw["file"]) if raw.get("file") else None,
            check_quotes=bool(raw.get("check_quotes")),
            criteria=tuple(raw["criteria"]),
            graders={k: tuple(v) for k, v in dict(raw.get("graders", {})).items()},
        )
        grader_names = {grader.name for grader in cases[name].graders}
        unknown = [
            *(c for c in review.criteria if c not in criteria),
            *(c for c in review.graders if c not in review.criteria),
            *(g for gs in review.graders.values() for g in gs if g not in grader_names),
        ]
        if unknown:
            msg = (
                f"review.json case {name} names unknown criteria or graders: {unknown}"
            )
            raise EvalError(msg)
        if review.file and not (cases[name].path / "files" / review.file).is_file():
            msg = f"review.json case {name}: files/{review.file} does not exist"
            raise EvalError(msg)
        reviews[name] = review
    return Rubric(str(data.get("where", "")), str(data["quality"]), criteria, reviews)


# -- Results -----------------------------------------------------------------


def _unseal(run_dir: Path) -> None:
    # claude plugin eval leaves kept run directories unreadable to the owner.
    for path in (run_dir, run_dir / "sealed"):
        if path.exists():
            path.chmod(0o700)


def _claude_run(label: str, case: str, number: int, run: dict[str, Any]) -> RunInput:
    trace = Path(str(run.get("tracePath", "")))
    if not trace.is_file():
        msg = f"{label} {case} run {number}: trace {trace} is gone"
        raise EvalError(msg)
    reply = json.loads(trace.read_text().splitlines()[-1]).get("result") or ""
    run_dir = trace.parent.parent
    _unseal(run_dir)
    workspace = run_dir / "sealed" / "home" / "cwd"
    files = None
    if workspace.is_dir():
        files = {
            str(path.relative_to(workspace)): path.read_text(errors="replace")
            for path in workspace.rglob("*")
            if path.is_file()
        }
    graders = {str(g["name"]): bool(g["passed"]) for g in run.get("graders", [])}
    return RunInput(label, case, number, str(reply), files, graders)


def load_results(spec: str) -> list[RunInput]:
    """Load the runs named by [LABEL=]PATH[@ARM]."""
    label, _, rest = spec.rpartition("=")
    path_text, _, arm = rest.partition("@")
    path, arm = Path(path_text), arm or "with"
    label = label or path.stem
    if arm not in ARMS:
        msg = f"{spec}: arm must be one of {sorted(ARMS)}"
        raise EvalError(msg)
    data = load_json_object(path)
    if data.get("agent") == "codex":
        return [
            RunInput(
                label,
                str(run["case"]),
                int(run["run"]),
                str(run["reply"]),
                {**dict(run.get("files", {}))},
                {
                    k: bool(v["pass"])
                    for k, v in run["graders"].items()
                    if v["pass"] is not None
                },
            )
            for run in data["runs"]
        ]
    return [
        _claude_run(label, str(case["name"]), number, run)
        for case in data.get("cases", [])
        for number, run in enumerate(case.get("arms", {}).get(arm, []), 1)
    ]


# -- Review ------------------------------------------------------------------


def quote_check(reply: str, original: str) -> dict[str, object]:
    """List quotes in the reply's table rows that are not verbatim in the original."""
    table = "\n".join(
        line
        for line in reply.translate(CURLY).splitlines()
        if line.lstrip().startswith("|")
    )
    quotes = QUOTE.findall(table)
    source = original.translate(CURLY).lower()
    nested = {
        q
        for q in quotes
        if quotes.count(q) > 1 or any(q != o and q in o for o in quotes)
    }
    return {
        "quotes_found": len(quotes),
        "quotes_not_verbatim_in_original": [
            q for q in quotes if q.lower() not in source
        ],
        "quotes_repeated_or_nested": sorted(nested),
    }


def original_text(case: Case, review: CaseReview) -> str:
    """Return the text under edit: the case file, else the prompt's pasted text."""
    if review.file:
        return (case.path / "files" / review.file).read_text()
    return case.prompt.split("\n\n", 1)[-1]


def build_state(run: RunInput, case: Case, review: CaseReview) -> dict[str, object]:
    """Return the facts Jev judges for one run."""
    original = original_text(case, review)
    state: dict[str, object] = {
        "user_request": case.prompt,
        "medium": review.medium,
        "expected_outcome": case.expected_outcome,
        "assistant_reply": run.reply,
        "original_text": original,
        "file_changed": False,
    }
    if review.file:
        if run.files is None:
            msg = f"{run.label} {run.case}: no workspace; rerun with --keep-temp"
            raise EvalError(msg)
        after = run.files.get(review.file, original)
        state.update(file_after=after, file_changed=after != original)
    if review.check_quotes:
        state["report_quote_check"] = quote_check(run.reply, original)
    return state


def build_questions(
    rubric: Rubric, review: CaseReview
) -> tuple[dict[str, object], dict[str, bool]]:
    """Return Jev questions for one case and which question IDs are inverted."""

    def fill(text: str) -> str:
        return text.replace("{where}", rubric.where).replace("{medium}", review.medium)

    questions: dict[str, object] = {}
    inverted: dict[str, bool] = {}
    for name in review.criteria:
        for number, variant in enumerate(rubric.criteria[name], 1):
            qid = f"{name}__v{number}"
            true, false = variant.pass_text, variant.fail_text
            if variant.inverted:
                true, false = false, true
            questions[qid] = {
                "type": "noul",
                "instructions": fill(variant.ask),
                "criteria": {"true": true, "false": false},
            }
            inverted[qid] = variant.inverted
    questions["quality"] = {
        "type": "score",
        "instructions": fill(rubric.quality),
        "criteria": QUALITY_LABELS,
    }
    return questions, inverted


def criterion_verdicts(
    answers: dict[str, Any],
    inverted: dict[str, bool],
) -> dict[str, dict[str, object]]:
    """Turn Jev's answers into one verdict per criterion.

    Each answer is the probability that its "true" text holds, so an inverted
    phrasing passes with probability 1 - p.
    """
    passes: dict[str, list[float]] = {}
    for qid, is_inverted in inverted.items():
        probability = float(answers[qid]["noul"])
        name = qid.rsplit("__", 1)[0]
        passes.setdefault(name, []).append(
            1 - probability if is_inverted else probability
        )
    return {
        name: {
            "pass": sum(p >= PASS_PROBABILITY for p in ps) * 2 > len(ps),
            "unanimous": len({p >= PASS_PROBABILITY for p in ps}) == 1,
            "p": [round(p, 2) for p in ps],
        }
        for name, ps in passes.items()
    }


def api_key() -> str:
    """Return the OpenRouter key from the environment or ~/.env."""
    for name in KEY_NAMES:
        if value := os.environ.get(name):
            return value
    env_file = Path.home() / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            key, _, value = line.removeprefix("export ").partition("=")
            if key.strip() in KEY_NAMES and value.strip():
                return value.strip().strip("'\"")
    msg = f"no OpenRouter key: set one of {', '.join(KEY_NAMES)}"
    raise EvalError(msg)


def _decide(body: bytes, key: str) -> tuple[dict[str, Any] | None, str]:
    """Send one decision request and return the answer or the error text."""
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        with urllib.request.urlopen(
            urllib.request.Request(
                "https://openrouter.ai/api/alpha/decisions",
                data=body,
                headers=headers,
            ),
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        return None, f"HTTP {error.code}: {error.read().decode(errors='replace')[:300]}"
    except OSError as error:
        return None, str(error)
    if isinstance(data, dict) and isinstance(data.get("answers"), dict):
        return data, ""
    return None, f"unexpected response: {str(data)[:300]}"


def ask_jev(
    state: dict[str, object],
    questions: dict[str, object],
    model: str,
    key: str,
) -> dict[str, Any]:
    """Send one decision request, retrying transient failures."""
    body = json.dumps({"model": model, "state": state, "questions": questions}).encode()
    error_text = ""
    for _ in range(ATTEMPTS):
        data, error_text = _decide(body, key)
        if data is not None:
            return data
    raise EvalError(error_text)


# -- CLI ---------------------------------------------------------------------


def review_runs(
    runs: list[RunInput],
    rubric: Rubric,
    cases: dict[str, Case],
    model: str,
    concurrency: int,
) -> list[dict[str, Any]]:
    """Ask Jev about every run and return one result per run, in order."""
    key = api_key()
    jobs = []
    for run in runs:
        review = rubric.cases.get(run.case)
        if review is None:
            print(f"skip {run.label} {run.case}: not in review.json", file=sys.stderr)
            continue
        state = build_state(run, cases[run.case], review)
        questions, inverted = build_questions(rubric, review)
        jobs.append((run, review, state, questions, inverted))
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        responses = list(
            pool.map(lambda job: ask_jev(job[2], job[3], model, key), jobs)
        )
    results = []
    for (run, review, state, _, inverted), response in zip(
        jobs, responses, strict=True
    ):
        verdicts = criterion_verdicts(response["answers"], inverted)
        disagree = [
            name
            for name, graders in review.graders.items()
            if all(g in run.graders for g in graders)
            and all(run.graders[g] for g in graders) != verdicts[name]["pass"]
        ]
        results.append(
            {
                "run": run,
                "verdicts": verdicts,
                "quality": float(response["answers"]["quality"]["score"]),
                "compared": sum(
                    all(g in run.graders for g in gs) for gs in review.graders.values()
                ),
                "disagree": disagree,
                "cost": float(response.get("usage", {}).get("cost", 0)),
                "state": state,
                "response": response,
            },
        )
    return results


def summary(results: list[dict[str, Any]], labels: list[str]) -> dict[str, object]:
    """Return the summary record: pass counts per label, consistency, agreement."""
    verdicts = [v for r in results for v in r["verdicts"].values()]
    compared = sum(r["compared"] for r in results)
    disagreed = sum(len(r["disagree"]) for r in results)
    per_label = {}
    for label in labels:
        rows = [r for r in results if r["run"].label == label]
        per_label[label] = {
            "runs": len(rows),
            "passed": sum(all(v["pass"] for v in r["verdicts"].values()) for r in rows),
            "quality": round(statistics.mean(r["quality"] for r in rows), 2)
            if rows
            else None,
        }
    passed = sum(all(v["pass"] for v in r["verdicts"].values()) for r in results)
    return {
        "kind": "summary",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "agreement": f"{compared - disagreed}/{compared}",
        "consistency": f"{sum(bool(v['unanimous']) for v in verdicts)}/{len(verdicts)}",
        "cost_usd": round(sum(r["cost"] for r in results), 4),
        "labels": per_label,
    }


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(description="Review eval runs with Jev")
    parser.add_argument("plugin", type=Path, help="plugin directory")
    parser.add_argument("results", nargs="+", help="[LABEL=]PATH[@ARM]")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--out", type=Path, help="write states and raw answers")
    args = parser.parse_args(argv)
    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    """Review the given results and return the exit code."""
    args = parse_args(argv)
    plugin = args.plugin.resolve()
    try:
        cases = {case.name: case for case in load_cases(plugin)}
        rubric = load_rubric(plugin, cases)
        runs = [run for spec in args.results for run in load_results(spec)]
        results = review_runs(runs, rubric, cases, args.model, args.concurrency)
    except (EvalError, OSError, KeyError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    labels = list(dict.fromkeys(run.label for run in runs))
    for result in results:
        run = result["run"]
        record = {
            "kind": "review",
            "label": run.label,
            "case": run.case,
            "run": run.number,
            "pass": all(v["pass"] for v in result["verdicts"].values()),
            "quality": result["quality"],
            "failed": [n for n, v in result["verdicts"].items() if not v["pass"]],
            "split": [n for n, v in result["verdicts"].items() if not v["unanimous"]],
            "disagree_with_graders": result["disagree"],
        }
        print(json.dumps(record, ensure_ascii=False))
    print(json.dumps(summary(results, labels)))
    if args.out:
        raw = [
            {
                "label": r["run"].label,
                "case": r["run"].case,
                "run": r["run"].number,
                "verdicts": r["verdicts"],
                "state": r["state"],
                "response": r["response"],
            }
            for r in results
        ]
        args.out.write_text(json.dumps(raw, indent=1, ensure_ascii=False))
    first = [r for r in results if r["run"].label == labels[0]] if labels else []
    return (
        0 if all(all(v["pass"] for v in r["verdicts"].values()) for r in first) else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
