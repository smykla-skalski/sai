#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["gspread>=6.2.1", "google-auth>=2.58.1", "onepassword-sdk>=0.4.1"]
# ///

import csv
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import kup


class Sheet:
    def __init__(self, rows):
        self.rows = rows

    def get(self, a1):
        row = int(a1.split(":")[0][1:])
        return [self.rows[row - 1]] if row <= len(self.rows) else []


def pr(number, title, repo="acme/app", merged="2026-03-10T10:00:00Z"):
    return {
        "number": number,
        "title": title,
        "url": f"https://github.com/{repo}/pull/{number}",
        "repository": {"nameWithOwner": repo},
        "closedAt": merged,
    }


def test_months():
    assert kup.add_months(date(2025, 12, 1), 1) == date(2026, 1, 1)
    assert kup.add_months(date(2026, 1, 1), -1) == date(2025, 12, 1)
    assert kup.last_reportable(date(2026, 9, 28)) == date(2026, 9, 1)
    assert kup.last_reportable(date(2026, 1, 20)) == date(2025, 12, 1)
    assert kup.parse_label("Aug 2025") == date(2025, 8, 1)
    assert kup.parse_label(" February 2026 ") == date(2026, 2, 1)
    assert kup.parse_label("Employee Name / Imię Pracownika:") is None


def test_missing_and_locate():
    col_a = ["Employee", "Job", "Dept", "", "", "January 2026", "Feb 2026", "", "April 2026"]
    rows = kup.month_rows(col_a)
    assert kup.missing_months(rows, date(2026, 6, 10)) == [date(2026, 3, 1), date(2026, 5, 1)]
    sheet = Sheet([[c, "", "", ""] for c in col_a])
    assert kup.locate(sheet, col_a, date(2026, 2, 1), 6) == (7, True)
    assert kup.locate(sheet, col_a, date(2026, 3, 1), 6) == (8, False)
    assert kup.locate(sheet, col_a, date(2026, 7, 1), 6) == (12, False)
    assert kup.locate(Sheet([["Employee"]]), ["Employee"], date(2026, 3, 1), 6) == (6, False)
    stray = Sheet([[c, "", "", ""] for c in col_a])
    stray.rows[7] = ["", "stray"]
    for s, month in ((stray, date(2026, 3, 1)), (sheet, date(2025, 12, 1))):
        try:
            kup.locate(s, col_a, month, 6)
        except kup.Fail:
            continue
        raise AssertionError(f"locate accepted {month}")


def test_triage():
    result = kup.triage([
        pr(14814, "ci(version.sh): correct v-prefix removal [backport release-2.7]"),
        pr(14810, "ci(version.sh): correct v-prefix removal"),
        pr(14800, "ci(workflows): fix SBOM upload to GitHub releases"),
        pr(14797, "ci(workflows): fix SBOM upload to GitHub releases"),
        pr(15007, "fix(tools): backport AddGoComments symlink fix to release-2.11"),
        pr(8772, "ci(workflows): fix SBOM upload to GitHub releases", repo="acme/mesh"),
        pr(14667, "chore(deps): bump go to 1.25.2"),
        pr(14616, "chore(tooling): bump Helm to 3.18.1 to include upstream bugfix"),
        pr(14694, "ci(k3d): add CNI selector, switch Calico to Helm, bump MetalLB"),
        pr(2157, "ci(version-bump): improve auto-bump logic", repo="acme/charts"),
        pr(8720, "feat(deps)!: migrate module path to example.com/acme/mesh/v2", repo="acme/mesh"),
        pr(495, "refactor(release-issue): improve code quality", repo="acme/tools"),
        pr(473, "refactor(github): improve code quality", repo="acme/tools"),
        pr(16589, "fix(helm): verify packaged chart has real version"),
        pr(16591, "fix(helm): catch placeholder (backport of #16589)"),
        pr(16686, "feat(xds): delta xDS Helm + injection (bp 16392)"),
    ])
    included = {e["number"]: e["title"] for e in result["included"]}
    skipped = {e["number"]: e["skip_reason"] for e in result["skipped"]}
    assert not result["dependency_only"]
    assert included == {
        14810: "correct v-prefix removal",
        14797: "fix SBOM upload to GitHub releases",
        15007: "AddGoComments symlink fix",
        8772: "fix SBOM upload to GitHub releases",
        14694: "add CNI selector, switch Calico to Helm, bump MetalLB",
        2157: "improve auto-bump logic",
        8720: "migrate module path to example.com/acme/mesh/v2",
        495: "improve code quality",
        473: "improve code quality",
        16589: "verify packaged chart has real version",
        16686: "delta xDS Helm + injection (bp 16392)",
    }, included
    assert skipped == {
        16591: "backport_duplicate",
        14814: "backport_duplicate",
        14800: "backport_duplicate",
        14667: "dependency_filtered",
        14616: "dependency_filtered",
    }, skipped

    assert kup.is_dependency("chore(deps/dev): security fixes") and kup.is_dependency("chore(deps-dev): refresh lockfile")
    only_deps = kup.triage([pr(1, "chore(deps): bump go to 1.25.2"), pr(2, "build(deps): update protobuf to v1.34.0")])
    assert only_deps["dependency_only"] and len(only_deps["included"]) == 2 and not only_deps["skipped"]


def test_descriptions_and_history():
    plan = {"included": [{"url": "u1", "title": "t1"}, {"url": "u2", "title": "t2"}], "descriptions": {}}
    plan = kup.merge_descriptions(plan, {"u1": " Opracowanie mechanizmu. "})
    assert plan["descriptions"] == {"u1": "Opracowanie mechanizmu"}
    assert kup.remaining(plan) == [{"url": "u2", "title": "t2"}]
    plan = kup.merge_descriptions(plan, {"u2": "Zaprojektowanie"})
    assert kup.remaining(plan) == [] and len(plan["descriptions"]) == 2
    for bad in ({"u3": "b"}, {"u1": "a\nb"}, {"u1": " "}):
        try:
            kup.merge_descriptions(plan, bad)
        except kup.Fail:
            continue
        raise AssertionError(f"accepted {bad}")
    assert kup.description_budget(600) == 82 and kup.description_budget(10) == 250

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "history.csv"
        entry = {"url": "https://github.com/acme/app/pull/1", "repo": "acme/app", "original_title": 'a "quoted", title', "merged_at": "m", "description": "Opis"}
        skipped = {**entry, "url": "https://github.com/acme/app/pull/2", "skip_reason": "backport_duplicate"}
        assert kup.record_history(path, "2026-02", [entry], []) == 1
        assert kup.record_history(path, "2026-03", [entry], [skipped]) == 3
        assert kup.record_history(path, "2026-03", [entry], []) == 2
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))
        assert [(r["month"], r["pr_url"], r["status"]) for r in rows] == [
            ("2026-02", "acme/app/pull/1", "included"),
            ("2026-03", "acme/app/pull/1", "included"),
        ]
        assert rows[0]["original_title"] == 'a "quoted", title'
        assert path.read_text().startswith('"month","pr_url"')


def test_token_cache():
    class Creds:
        token = "ya29.token"
        expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=50)

    with tempfile.TemporaryDirectory() as tmp:
        kup.TOKEN_CACHE = Path(tmp) / "kup" / "google-token.json"
        assert kup.cached_token("acct/vault/item") is None
        kup.cache_token("acct/vault/item", Creds())
        assert kup.TOKEN_CACHE.stat().st_mode & 0o777 == 0o600
        assert "private_key" not in kup.TOKEN_CACHE.read_text()
        creds = kup.cached_token("acct/vault/item")
        assert creds.token == "ya29.token" and creds.valid
        assert kup.cached_token("acct/vault/other") is None
        Creds.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
        kup.cache_token("acct/vault/item", Creds())
        assert kup.cached_token("acct/vault/item") is None
        kup.TOKEN_CACHE.write_text("{not json")
        assert kup.cached_token("acct/vault/item") is None


def test_row_values():
    included = [
        {"url": "https://github.com/b/x/pull/2", "repo": "b/x", "description": "Drugi"},
        {"url": "https://github.com/a/y/pull/1", "repo": "a/y", "description": "Pierwszy"},
    ]
    assert kup.row_values(date(2026, 3, 1), included) == [
        "March 2026",
        "Drugi\nPierwszy",
        "https://github.com/a/y\nhttps://github.com/b/x",
        "https://github.com/b/x/pull/2\nhttps://github.com/a/y/pull/1",
    ]
    try:
        kup.row_values(date(2026, 3, 1), [{**included[0], "description": "x" * kup.CELL_LIMIT}] * 2)
    except kup.Fail:
        return
    raise AssertionError("accepted an oversized cell")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
