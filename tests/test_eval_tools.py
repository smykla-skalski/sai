"""Check the offline logic of the skill eval tools and every plugin's eval data.

The tools themselves run paid agent and model calls, so these tests cover what
decides a verdict: how Codex events map onto `claude plugin eval` graders, how
trigger runs are detected and scored, and how Jev answers become criterion
verdicts. They also load each plugin's triggers.json, review.json and
interviews.json.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
common = importlib.import_module("_eval_common")
codex = importlib.import_module("eval_codex")
review = importlib.import_module("eval_review")
triggers = importlib.import_module("eval_triggers")
interviews = importlib.import_module("eval_interview")

HUMANIZE = REPO_ROOT / "plugins" / "humanize"


def grader(**meta: object) -> object:
    return common.Grader("g", dict(meta), "rubric")


def codex_run(**fields: object) -> object:
    case = common.load_cases(HUMANIZE, "scores-without-editing")[0]
    return codex.Run(case, 1, **fields)


class SuiteLoadingTest(unittest.TestCase):
    def test_humanize_cases_load_with_settings_and_nested_targets(self) -> None:
        cases = {case.name: case for case in common.load_cases(HUMANIZE)}
        self.assertEqual(len(cases), 13)
        notes = cases["rewrites-release-notes-in-place"]
        self.assertFalse(notes.prompt.startswith("---"))
        self.assertEqual(notes.settings["timeout_seconds"], "600")
        self.assertIsNotNone(notes.scaffold)
        targets = [g.meta.get("target") for g in notes.graders]
        self.assertIn({"source": "file", "path": "release-notes.md"}, targets)
        self.assertNotIn("\n", cases["scores-without-editing"].expected_outcome)

    def test_codex_marketplace_serves_a_copy_of_the_given_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            plugin = Path(root) / "snapshot" / "humanize"
            (plugin / "evals").mkdir(parents=True)
            (plugin / "plugin.json").write_text("{}")
            market, name = common.plugin_marketplace(plugin, Path(root) / "cx")
            manifest = json.loads(
                (market / ".agents/plugins/marketplace.json").read_text()
            )
            self.assertEqual(name, manifest["name"])
            [entry] = manifest["plugins"]
            self.assertEqual(entry["source"]["path"], "./plugins/humanize")
            self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
            served = market / "plugins" / "humanize"
            self.assertTrue((served / "plugin.json").is_file())
            self.assertFalse((served / "evals").exists())

    def test_codex_prompt_rewrites_only_the_exact_slash_command(self) -> None:
        self.assertEqual(
            common.codex_prompt("/humanize --score-only a.md", "humanize"),
            "$humanize --score-only a.md",
        )
        self.assertEqual(
            common.codex_prompt("/humanizer x", "humanize"), "/humanizer x"
        )
        self.assertEqual(
            common.codex_prompt("humanize this", "humanize"), "humanize this"
        )


class CodexGradingTest(unittest.TestCase):
    def test_judge_failure_is_not_reported_as_a_failed_vote(self) -> None:
        result = subprocess.CompletedProcess([], 1, "", "Not logged in")
        with mock.patch.object(codex, "run_command", return_value=result):
            passed, detail = codex.grade_llm(
                codex_run(), grader(type="llm"), "s", Path()
            )
        self.assertFalse(passed)
        self.assertIn("judge error", detail)
        self.assertIn("Not logged in", detail)

    def test_judge_must_return_an_explicit_verdict(self) -> None:
        result = subprocess.CompletedProcess([], 0, "No verdict", "")
        with (
            mock.patch.object(codex, "run_command", return_value=result),
            self.assertRaisesRegex(common.EvalError, "no verdict"),
        ):
            codex.judge_vote("rubric", "output", "s", Path())

    def test_read_grader_sees_files_inside_brace_groups(self) -> None:
        run = codex_run(
            commands=["/bin/zsh -lc 'cat skills/x/references/{voice,patterns}.md'"],
        )
        verdict, _ = codex.grade_tool_used(
            run,
            grader(tool="Read", input_match=r"references/patterns\.md"),
            "humanize",
        )
        self.assertTrue(verdict)

    def test_edit_bounds_follow_workspace_changes(self) -> None:
        no_edits = grader(tool="Edit", min="0", max="0")
        changed = codex_run(before={"a.md": "old"}, after={"a.md": "new"})
        created = codex_run(before={}, after={"b.md": "new"})
        untouched = codex_run(before={"a.md": "old"}, after={"a.md": "old"})
        self.assertFalse(codex.grade_tool_used(changed, no_edits, "humanize")[0])
        self.assertFalse(codex.grade_tool_used(created, no_edits, "humanize")[0])
        self.assertTrue(codex.grade_tool_used(untouched, no_edits, "humanize")[0])

    def test_unknown_event_types_count_as_a_subagent(self) -> None:
        no_agents = grader(tool="Agent", min="0", max="0")
        spawned = codex_run(item_types={"agent_message", "collab_tool_call"})
        plain = codex_run(item_types={"agent_message", "command_execution"})
        self.assertFalse(codex.grade_tool_used(spawned, no_agents, "humanize")[0])
        self.assertTrue(codex.grade_tool_used(plain, no_agents, "humanize")[0])
        self.assertIsNone(codex.grade_tool_used(plain, grader(tool="Bash"), "x")[0])

    def test_codex_runs_record_whether_their_turn_finished(self) -> None:
        run = codex.Run(common.load_cases(HUMANIZE, "scores-without-editing")[0], 1)
        rate_limited = {"type": "turn.failed", "error": {"message": "429 Too Many"}}
        codex.record_event(run, rate_limited)
        self.assertEqual((run.completed, run.failure), (False, "429 Too Many"))
        codex.record_event(run, {"type": "turn.completed"})
        self.assertTrue(run.completed)

    def test_each_run_gets_its_own_home_shared_by_scaffold_and_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scaffold = root / "place-files.sh"
            # Fails when a previous run's file is already in this HOME.
            scaffold.write_text(
                '#!/bin/sh\ntest ! -e "$HOME/setting" && echo x > "$HOME/setting"\n'
            )
            scaffold.chmod(0o755)
            case = common.Case("c", root, "p", {}, "", (), scaffold)
            sandbox = common.CodexSandbox("codex", root / "home", root / "codex-home")
            suite = codex.Suite(sandbox, "s", None, root)
            homes = []

            def finished(*_args: object, **kwargs: object) -> object:
                env = kwargs["env"]
                assert isinstance(env, dict)
                homes.append(Path(env["HOME"]))
                return iter([{"type": "turn.completed"}])

            with mock.patch.object(codex, "stream_json", side_effect=finished):
                codex.execute_once(case, 1, suite)
                codex.execute_once(case, 2, suite)
            self.assertNotEqual(homes[0], homes[1])
            self.assertTrue(all((home / "setting").is_file() for home in homes))
            self.assertFalse((root / "home" / "setting").exists())

    def test_regex_grader_reads_the_target_file_after_the_run(self) -> None:
        dashes = grader(
            pattern="—[\\s\\S]*—",
            match="not_contains",
            target={"source": "file", "path": "notes.md"},
        )
        kept = codex_run(before={"notes.md": "a — b — c"}, after={})
        fixed = codex_run(
            before={"notes.md": "a — b — c"}, after={"notes.md": "a, b — c"}
        )
        self.assertFalse(codex.grade_regex(kept, dashes)[0])
        self.assertTrue(codex.grade_regex(fixed, dashes)[0])
        self.assertTrue(
            codex.grade_regex(
                codex_run(reply="Done."), grader(pattern="done", flags="i")
            )[0]
        )


class TriggerTest(unittest.TestCase):
    def test_skill_loads_are_detected_by_exact_skill_name(self) -> None:
        def skill_call(name: str) -> dict[str, object]:
            block = {"type": "tool_use", "name": "Skill", "input": {"skill": name}}
            return {"type": "assistant", "message": {"content": [block]}}

        self.assertTrue(
            triggers.claude_loaded_skill(skill_call("humanize:humanize"), "humanize")
        )
        self.assertTrue(
            triggers.claude_loaded_skill(skill_call("humanize"), "humanize")
        )
        self.assertFalse(
            triggers.claude_loaded_skill(skill_call("humanizer"), "humanize")
        )
        read = {
            "item": {
                "type": "command_execution",
                "command": "cat skills/humanize/SKILL.md",
            }
        }
        self.assertTrue(triggers.codex_loaded_skill(read, "humanize"))
        self.assertFalse(triggers.codex_loaded_skill(read, "humanizer"))

    def test_a_failed_run_is_run_again_and_never_counted_as_a_miss(self) -> None:
        block = {"type": "tool_use", "name": "Skill", "input": {"skill": "humanize"}}
        load: dict[str, object] = {"type": "assistant", "message": {"content": [block]}}
        failed: dict[str, object] = {"type": "turn.failed", "error": {"message": "429"}}

        def runs(*streams: list[dict[str, object]]) -> object:
            pending = iter(streams)
            return lambda *_args, **_kwargs: iter(next(pending))

        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(common, "RETRY_DELAYS_SECONDS", (0.0,)),
        ):
            runner = triggers.Runner(
                "claude", Path(tmp), "humanize", {}, None, 1.0, Path(tmp), None
            )
            with mock.patch.object(triggers, "stream_json", runs([failed], [load])):
                self.assertTrue(runner.triggered("make it plain"))
            # A failed turn, then a run cut off before its turn ended.
            with (
                mock.patch.object(triggers, "stream_json", runs([failed], [])),
                self.assertRaises(common.EvalError),
            ):
                runner.triggered("make it plain")

    def test_a_query_passes_on_the_majority_of_its_runs(self) -> None:
        positive = triggers.Query("make it plain", should_trigger=True)
        negative = triggers.Query("translate it", should_trigger=False)
        self.assertTrue(triggers.Outcome(positive, 2, 3).passed)
        self.assertFalse(triggers.Outcome(positive, 1, 3).passed)
        self.assertTrue(triggers.Outcome(positive, 1, 2).passed)
        self.assertTrue(triggers.Outcome(negative, 0, 3).passed)
        outcomes = [
            triggers.Outcome(positive, 3, 3),
            triggers.Outcome(positive, 0, 3),
            triggers.Outcome(negative, 3, 3),
        ]
        record = triggers.summary(outcomes)
        self.assertEqual((record["passed"], record["failed"]), (1, 2))
        self.assertEqual((record["recall"], record["precision"]), ("1/2", "1/2"))

    def test_candidate_description_replaces_a_folded_description(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            plugin = Path(root) / "src" / "demo"
            skill = plugin / "skills" / "demo" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "---\nname: demo\ndescription: >\n  old text\n  more: old\nallowed-tools: Read\n---\nBody\n"
            )
            copy = triggers.with_description(
                plugin, "demo", 'Use for "plain"\n text: now', Path(root)
            )
            text = (copy / "skills/demo/SKILL.md").read_text()
        lines = text.splitlines()
        self.assertEqual(lines[2], 'description: "Use for \\"plain\\" text: now"')
        self.assertEqual(
            json.loads(lines[2].removeprefix("description: ")),
            'Use for "plain" text: now',
        )
        self.assertEqual(lines[3:], ["allowed-tools: Read", "---", "Body"])


class ReviewTest(unittest.TestCase):
    def test_inverted_phrasings_count_the_opposite_answer(self) -> None:
        inverted = {"facts__v1": False, "facts__v2": False, "facts__v3": True}
        agree = {
            "facts__v1": {"noul": 0.9},
            "facts__v2": {"noul": 0.8},
            "facts__v3": {"noul": 0.1},
        }
        verdict = review.criterion_verdicts(agree, inverted)["facts"]
        self.assertTrue(verdict["pass"])
        self.assertTrue(verdict["unanimous"])
        yes_to_all = {
            "facts__v1": {"noul": 0.9},
            "facts__v2": {"noul": 0.2},
            "facts__v3": {"noul": 0.9},
        }
        verdict = review.criterion_verdicts(yes_to_all, inverted)["facts"]
        self.assertFalse(verdict["pass"])
        self.assertFalse(verdict["unanimous"])

    def test_questions_fill_placeholders_and_swap_inverted_criteria(self) -> None:
        variant = review.Variant("{where} For {medium}?", "good", "bad", inverted=True)
        rubric = review.Rubric(
            "Judge the rewrite.", "Rate {medium}.", {"c": (variant,)}, {}
        )
        case = review.CaseReview("a commit message", None, False, False, ("c",), {})
        questions, inverted = review.build_questions(rubric, case)
        self.assertEqual(
            questions["c__v1"]["instructions"],
            "Judge the rewrite. For a commit message?",
        )
        self.assertEqual(
            questions["c__v1"]["criteria"], {"true": "bad", "false": "good"}
        )
        self.assertEqual(inverted, {"c__v1": True})
        self.assertEqual(questions["quality"]["instructions"], "Rate a commit message.")

    def test_lossless_check_finds_dropped_details_in_the_result_only(self) -> None:
        original = (
            "Run `make migrate` before 30 June (see #482 and https://x.io/a). "
            "Cold start drops to 0.9s."
        )
        case = review.CaseReview("a doc", None, False, True, ("c",), {})
        reply = (
            "Run make migrate before June, see https://x.io/a.\n\n"
            "| # | Pattern | Instance | Fix |\n"
            '| 1 | Filler | "before 30 June (see #482" | cut |\n'
        )
        run = review.RunInput("final", "c", 1, reply, None, {})
        result = review.result_text(run, case, original)
        check = review.lossless_check(original, result)
        self.assertEqual(check["missing_details"], ["30", "#482", "0.9"])
        dry_run = review.RunInput("final", "c", 1, reply, {"a.md": original}, {})
        file_case = review.CaseReview("a doc", "a.md", False, True, ("c",), {})
        self.assertEqual(review.result_text(dry_run, file_case, original), result)
        self.assertEqual((check["original_words"], check["result_words"]), (15, 7))

    def test_a_file_the_run_creates_starts_empty_and_counts_as_changed(self) -> None:
        case = common.load_cases(HUMANIZE, "scores-without-editing")[0]
        file_case = review.CaseReview(
            "a design doc", "docs/new.md", False, True, (), {}
        )
        run = review.RunInput(
            "final", case.name, 1, "Wrote it.", {"docs/new.md": "# New"}, {}
        )
        state = review.build_state(run, case, file_case)
        self.assertEqual(state["original_text"], "")
        self.assertEqual(state["file_after"], "# New")
        self.assertTrue(state["file_changed"])

    def test_word_budget_comes_from_the_reference_and_skips_fences(self) -> None:
        case = review.CaseReview(
            "a doc", None, False, True, ("c",), {}, reference="one two three four five"
        )
        budget = review.word_budget(case)
        self.assertEqual(budget, 6)
        fenced = "```\none two three four five six\n```"
        check = review.lossless_check("x", fenced, budget)
        self.assertEqual((check["result_words"], check["within_budget"]), (6, True))
        over = review.lossless_check("x", fenced.replace("six", "six seven"), budget)
        self.assertFalse(over["within_budget"])
        explicit = review.CaseReview("a", None, False, True, (), {}, max_words=9)
        self.assertEqual(review.word_budget(explicit), 9)

    def test_claude_models_are_refused_as_openrouter_judges(self) -> None:
        for model in ("anthropic/claude-opus-5.5", "claude-sonnet-5-5"):
            with self.subTest(model=model), self.assertRaises(SystemExit):
                review.parse_args(["plugins/humanize", "a.json", "--model", model])
        self.assertEqual(review.parse_args(["p", "a.json"]).model, review.DEFAULT_MODEL)

    def test_quote_check_flags_invented_and_nested_quotes(self) -> None:
        reply = (
            "| # | Pattern | Instance | Fix |\n"
            "| 1 | Puffery | “a groundbreaking update” | cut |\n"
            '| 2 | Puffery | "groundbreaking update" | cut |\n'
            '| 3 | Filler | "it is worth noting" | cut |\n'
            'Outside the table: "never checked here"\n'
        )
        result = review.quote_check(reply, "We ship a Groundbreaking update today.")
        self.assertEqual(result["quotes_found"], 3)
        self.assertEqual(
            result["quotes_not_verbatim_in_original"], ["it is worth noting"]
        )
        self.assertEqual(result["quotes_repeated_or_nested"], ["groundbreaking update"])


class EvalDataTest(unittest.TestCase):
    def test_every_trigger_set_has_both_classes_and_unique_queries(self) -> None:
        for path in sorted(REPO_ROOT.glob("plugins/*/evals/triggers.json")):
            with self.subTest(plugin=path.parts[-3]):
                _, queries = triggers.load_queries(path.parent.parent)
                texts = [query.text for query in queries]
                self.assertEqual(len(texts), len(set(texts)))
                self.assertEqual({q.should_trigger for q in queries}, {True, False})

    def test_every_review_rubric_matches_its_cases(self) -> None:
        for path in sorted(REPO_ROOT.glob("plugins/*/evals/review.json")):
            plugin = path.parent.parent
            with self.subTest(plugin=plugin.name):
                cases = {case.name: case for case in common.load_cases(plugin)}
                rubric = review.load_rubric(plugin, cases)
                self.assertTrue(rubric.cases)

    def test_every_interview_suite_loads(self) -> None:
        for path in sorted(REPO_ROOT.glob("plugins/*/evals/interviews.json")):
            with self.subTest(plugin=path.parts[-3]):
                suite = interviews.load_suite(path.parent.parent)
                self.assertTrue(suite.scenarios)

    def test_rubric_naming_a_missing_grader_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            case = Path(root) / "evals" / "demo"
            (case / "graders").mkdir(parents=True)
            (case / "prompt.md").write_text("do it\n")
            (case / "graders" / "01-ok.md").write_text(
                "---\ntype: llm\n---\nPASS if done\n"
            )
            variants: list[dict[str, object]] = [
                {"ask": "a", "pass": "p", "fail": "f"}
            ] * 2
            variants.append({"ask": "a", "pass": "p", "fail": "f", "inverted": True})
            data = {
                "quality": "q",
                "criteria": {"done": variants},
                "cases": {
                    "demo": {
                        "medium": "m",
                        "criteria": ["done"],
                        "graders": {"done": ["02-gone"]},
                    }
                },
            }
            (Path(root) / "evals" / "review.json").write_text(json.dumps(data))
            cases = {c.name: c for c in common.load_cases(Path(root))}
            with self.assertRaisesRegex(common.EvalError, "02-gone"):
                review.load_rubric(Path(root), cases)


def scenario(questions: tuple[int, int] = (6, 8)) -> object:
    return interviews.Scenario("demo", "do it", "out.md", "- a fact", questions)


def suite(**fields: object) -> object:
    values: dict[str, object] = {
        "skill": "demo",
        "setting": "s",
        "baseline": "Ask me questions.",
        "judge_notes": "",
        "checks": {"done_when_checkable": "true if ..."},
        "slack": 2,
        "scenarios": (scenario(),),
        "sequences": (),
    }
    return interviews.Suite(**(values | fields))


def agent(name: str = "claude", root: Path = Path()) -> object:
    return interviews.Agent(name, name, None, Path("skill"), None, root)


def context(name: str = "claude", arm: str = "with", root: Path = Path()) -> object:
    return interviews.Context(suite(), agent(name, root), arm, "sonnet", "opus", root)


def clean_judge(**fields: object) -> dict[str, object]:
    judge: dict[str, object] = {
        "questions": 7,
        "turns_with_more_than_one_question": 0,
        "needless": [],
        "missed_precision": [],
        "invented": [],
        "finished": True,
        "done_when_checkable": True,
    }
    return judge | fields


class InterviewTest(unittest.TestCase):
    def test_choice_without_question_mark_does_not_end_interview(self) -> None:
        session = mock.Mock()
        session.send.side_effect = [
            "Choose one: 1. One evening 2. A weekend",
            "Plan ready.",
        ]
        session.problems.return_value = []
        replies = ["One evening", interviews.DONE, json.dumps(clean_judge())]
        with (
            tempfile.TemporaryDirectory() as root,
            mock.patch.object(interviews, "start_session", return_value=session),
            mock.patch.object(interviews, "ask_model", side_effect=replies),
        ):
            result = interviews.interview(context(root=Path(root)), scenario(), 1)
        self.assertTrue(result["pass"], result["problems"])
        self.assertEqual(session.send.call_count, 2)
        self.assertEqual(session.send.call_args_list[1].args, ("One evening",))
        session.close.assert_called_once()

    def test_question_count_passes_within_range_and_slack(self) -> None:
        for count, passes in ((4, True), (3, False), (10, True), (11, False)):
            with self.subTest(questions=count):
                problems = interviews.assess(
                    clean_judge(questions=count), scenario(), suite()
                )
                self.assertEqual(not problems, passes, problems)

    def test_judge_findings_fail_the_interview(self) -> None:
        findings: dict[str, dict[str, object]] = {
            "multi-question turn": {"turns_with_more_than_one_question": 1},
            "needless question": {"needless": [{"turn": 3}]},
            "invented fact": {"invented": ["a 45-minute test"]},
            "plugin check": {"done_when_checkable": False},
            "unfinished": {"finished": False},
            "no count": {"questions": None},
        }
        for name, fields in findings.items():
            with self.subTest(name):
                judge = clean_judge(**fields)
                self.assertTrue(interviews.assess(judge, scenario(), suite()))
        self.assertTrue(interviews.assess(None, scenario(), suite()))

    def test_judge_json_is_found_in_prose_or_fences(self) -> None:
        reply = 'Here it is:\n```json\n{"questions": 7, "needless": []}\n```'
        self.assertEqual(
            interviews.parse_judge(reply), {"questions": 7, "needless": []}
        )
        self.assertIsNone(interviews.parse_judge("no verdict"))

    def test_scenario_needs_an_ordered_question_range(self) -> None:
        raw = {"name": "x", "prompt": "p", "file": "f.md", "brief": ["fact"]}
        interviews.load_scenario(raw | {"questions": [6, 8]}, "test")
        for bad in ([8, 6], [0, 4], [6], ["6", "8"]):
            with self.subTest(questions=bad), self.assertRaises(common.EvalError):
                interviews.load_scenario(raw | {"questions": bad}, "test")

    def test_ask_call_must_hold_one_short_question(self) -> None:
        good = {
            "question": "What problem does it solve?",
            "header": "Step 1 of 4",
            "options": [{"label": "Lost links"}, {"label": "I do not know"}],
        }
        self.assertEqual(interviews.ask_call_problems([good]), [])
        broken = {
            "two questions": [good, good],
            "long header": [good | {"header": "Step 1 of 4: Problem"}],
            "one option": [good | {"options": [{"label": "Yes"}]}],
            "long label": [
                good
                | {
                    "options": [
                        {"label": "one two three four five six"},
                        {"label": "No"},
                    ]
                }
            ],
        }
        for name, questions in broken.items():
            with self.subTest(name):
                self.assertTrue(interviews.ask_call_problems(questions))

    def test_agent_replies_give_the_last_message_and_session(self) -> None:
        codex_events = [
            {"type": "thread.started", "thread_id": "t1"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "a"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "b"}},
        ]
        self.assertEqual(interviews.codex_reply(codex_events), ("b", "t1"))
        kimi_events = [
            {"role": "assistant", "content": "a"},
            {"type": "session.resume_hint", "session_id": "k1"},
        ]
        self.assertEqual(interviews.kimi_reply(kimi_events), ("a", "k1"))
        opencode_events = [{"type": "text", "part": {"text": "o"}}, {"type": "step"}]
        self.assertEqual(interviews.opencode_reply(opencode_events), "o")
        claude_out = json.dumps({"result": "c", "session_id": "s1"})
        self.assertEqual(interviews.claude_reply(claude_out), ("c", "s1"))

    def test_failed_codex_turn_is_retried_not_judged(self) -> None:
        events = [{"type": "turn.failed", "error": {"message": "rate limited"}}]
        with self.assertRaisesRegex(common.RunFailedError, "rate limited"):
            interviews.codex_reply(events)

    def test_claude_turns_after_the_first_resume_its_session(self) -> None:
        replies = [
            json.dumps({"result": "Who has it?", "session_id": "s1"}),
            json.dumps({"result": "Done.", "session_id": "s1"}),
            "",
        ]
        calls: list[list[str]] = []

        def run(argv: list[str], **_kwargs: object) -> object:
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, replies[len(calls) - 1], "")

        with (
            tempfile.TemporaryDirectory() as root,
            mock.patch.object(interviews, "run_command", side_effect=run),
        ):
            session = interviews.ClaudeSession(Path(root), agent(), {})
            self.assertEqual(session.send("first"), "Who has it?")
            self.assertEqual(session.send("me"), "Done.")
            with self.assertRaises(common.RunFailedError):
                session.send("again")
        self.assertNotIn("--resume", calls[0])
        self.assertEqual(calls[1][-2:], ["--resume", "s1"])
        allowed = calls[0][calls[0].index("--allowedTools") : calls[0].index("--tools")]
        available = calls[0][calls[0].index("--tools") :]
        for tool in ("WebSearch", "WebFetch"):
            self.assertIn(tool, allowed)
            self.assertIn(tool, available)

    def test_first_message_invokes_the_skill_on_each_agent(self) -> None:
        expected = {
            ("claude", "with"): "/demo do it",
            ("claude-ask", "with"): "/demo do it",
            ("codex", "with"): "$demo do it",
            ("kimi", "with"): "Use the demo skill. do it",
            ("claude", "without"): "Ask me questions.\n\ndo it",
        }
        for (name, arm), message in expected.items():
            with self.subTest(agent=name, arm=arm):
                ctx = context(name, arm)
                self.assertEqual(interviews.first_message(ctx, "do it"), message)

    def test_expectations_count_files_or_compare_one(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            places = {"workspace": root, "data": f"{root}/.data"}
            common.write_files(Path(root), {".data/ideas/a.md": "", "setting": "x\n"})
            met = [
                interviews.Expectation(1, glob="{data}/ideas/*.md"),
                interviews.Expectation(1, glob="{workspace}/*.md", least=0, most=0),
                interviews.Expectation(1, file="{workspace}/setting", equals="x"),
            ]
            broken = [
                interviews.Expectation(1, glob="{workspace}/ideas/*.md"),
                interviews.Expectation(1, glob="{data}/**/*.md", least=0, most=0),
                interviews.Expectation(1, file="{workspace}/setting", equals="y"),
                interviews.Expectation(1, file="{workspace}/gone", equals="x"),
            ]
            for expect in met:
                self.assertIsNone(interviews.check_expectation(expect, places))
            for expect in broken:
                self.assertIsNotNone(interviews.check_expectation(expect, places))

    def test_sequence_entries_must_name_a_request_and_one_check(self) -> None:
        raw = {"name": "s", "requests": ["a", "b"]}
        interviews.load_sequence(raw | {"expect": [{"after": 2, "glob": "x"}]}, "t")
        for bad in (
            {"after": 3, "glob": "x"},
            {"after": 1, "glob": "x", "file": "y", "equals": "z"},
            {"after": 1, "file": "y"},
            {"after": 1, "glob": "x", "min": 2, "max": 1},
        ):
            with self.subTest(bad), self.assertRaises(common.EvalError):
                interviews.load_sequence(raw | {"expect": [bad]}, "t")

    def test_sessions_start_again_in_the_same_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root) / "ws"
            skill = Path(root) / "skill"
            workspace.mkdir()
            common.write_files(skill, {"SKILL.md": "x"})
            claude = interviews.Agent("claude", "claude", None, skill, None, Path(root))
            opencode = interviews.Agent(
                "opencode",
                "opencode",
                None,
                skill,
                None,
                Path(root),
                opencode_config=Path(root) / "config",
            )
            for _ in range(2):
                interviews.ClaudeSession(workspace, claude, {})
                interviews.OpenCodeSession(workspace, opencode, {})
            self.assertTrue((workspace / ".opencode/skills/skill/SKILL.md").is_file())

    def test_sequence_runs_each_request_as_a_fresh_session(self) -> None:
        sessions: list[dict[str, str]] = []

        class Fake:
            def __init__(self, extra: dict[str, str]) -> None:
                self.extra = extra

            def send(self, message: str) -> str:
                data = Path(self.extra["XDG_DATA_HOME"])
                if "first" in message:
                    common.write_files(data, {"ideas/a.md": "note"})
                return "Saved."

            def problems(self) -> list[str]:
                return []

            def close(self) -> None:
                pass

        def start(
            _agent: object, _ws: Path, _pick: object, extra: dict[str, str]
        ) -> object:
            sessions.append(extra)
            return Fake(extra)

        sequence = interviews.SessionSequence(
            "seq",
            ("first idea", "second idea"),
            (
                interviews.Expectation(1, glob="{data}/ideas/*.md"),
                interviews.Expectation(2, glob="{workspace}/vault/*.md"),
            ),
        )
        with (
            tempfile.TemporaryDirectory() as root,
            mock.patch.object(interviews, "start_session", side_effect=start),
        ):
            record = interviews.run_sequence(context(root=Path(root)), sequence, 1)
        self.assertEqual(len(sessions), 2)
        self.assertTrue(sessions[0]["XDG_DATA_HOME"].endswith("/.data"))
        self.assertEqual(sessions[0], sessions[1])
        self.assertEqual(len(record["problems"]), 1)
        self.assertTrue(record["problems"][0].startswith("after request 2: "))
        self.assertEqual(record["replies"], ["Saved.", "Saved."])

    def test_kimi_config_drops_only_hook_tables(self) -> None:
        config = (
            'default_model = "k"\n[[hooks]]\nevent = "Stop"\n'
            '[models."k"]\neffort = "high"\n[[hooks]]\nevent = "Start"\n'
        )
        self.assertEqual(
            interviews.drop_toml_tables(config, "[[hooks]]"),
            'default_model = "k"\n[models."k"]\neffort = "high"\n',
        )

    def test_opencode_config_keeps_only_the_chosen_provider(self) -> None:
        user = {
            "model": "a/one",
            "agent": {"build": {}},
            "provider": {
                "a": {"options": {"apiKey": "x"}, "models": {"one": {"limit": 1}}},
                "b": {},
            },
        }
        config = interviews.isolated_opencode_config(user, "a/two")
        self.assertEqual(config["model"], "a/two")
        self.assertEqual(list(config["provider"]), ["a"])
        self.assertEqual(
            config["provider"]["a"]["models"], {"two": {}, "one": {"limit": 1}}
        )
        self.assertNotIn("agent", config)
        self.assertEqual(
            interviews.isolated_opencode_config(user, None)["provider"]["a"]["models"],
            {"one": {"limit": 1}},
        )
        with self.assertRaisesRegex(common.EvalError, "'c'"):
            interviews.isolated_opencode_config(user, "c/three")


if __name__ == "__main__":
    unittest.main()
