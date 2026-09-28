#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["gspread>=6.2.1", "google-auth>=2.58.1", "onepassword-sdk>=0.4.1"]
# ///

import argparse
import asyncio
import csv
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import gspread
import tomllib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from gspread.utils import ValueInputOption, a1_to_rowcol

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]
CONFIG_PATH = Path(
    os.environ.get("KUP_CONFIG")
    or Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "kup" / "config.toml"
)
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "kup"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "kup"
TOKEN_CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "kup" / "google-token.json"
TOKEN_MARGIN = timedelta(minutes=10)
CSV_FIELDS = ["month", "pr_url", "repo", "original_title", "generated_description", "status", "skip_reason", "merged_at"]
MONTH_FORMATS = ("%B %Y", "%b %Y")
SEARCH_CAP = 1000
GH_TIMEOUT = 180
RATE_LIMIT_WAITS = (60, 120, 180, None)
CELL_LIMIT = 50000

BACKPORT_OF = re.compile(r"(?i)\b(?:backport of|bp)\s+#?(\d+)")
CONVENTIONAL_PREFIX = re.compile(r"^\s*\w+(?:\(([^)]*)\))?!?:\s*")
DEPENDENCY_SCOPE = re.compile(r"(?i)^\s*(?:chore|build|fix|revert)\(deps(?:[-/][\w-]+)?\)!?:")
DEPENDENCY_SUBJECT = re.compile(r"(?i)^(?:bump|update|upgrade)\b.*\b(?:to|from)\s+`?v?\d|^update (?:\w+ )?(?:dependencies|dependency|modules?)\b")


class Fail(Exception):
    pass


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def setting(config: dict, key: str) -> str:
    if not CONFIG_PATH.exists():
        raise Fail(f"missing {CONFIG_PATH}, see references/setup.md")
    if not config.get(key):
        raise Fail(f"no {key!r} in {CONFIG_PATH}, see references/setup.md")
    return config[key]


async def read_onepassword_document(op: dict) -> bytes:
    from onepassword.client import Client
    from onepassword.defaults import DesktopAuth

    client = await Client.authenticate(
        auth=DesktopAuth(op["account"]),
        integration_name="kup-skill",
        integration_version="2.0.0",
    )
    item = await client.items.get(op["vault"], op["item"])
    if item.document is None:
        raise Fail(f"1Password item {op['item']} holds no document")
    return await client.items.files.read(op["vault"], op["item"], item.document)


def service_account_info(config: dict) -> dict:
    if raw := os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        return json.loads(raw)
    if path := os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or config.get("service_account_file"):
        return json.loads(Path(path).expanduser().read_text())
    if op := config.get("onepassword"):
        return json.loads(asyncio.run(read_onepassword_document(op)))
    raise Fail(f"no Google service account configured in {CONFIG_PATH}, see references/setup.md")


def cached_token(source: str) -> OAuthCredentials | None:
    try:
        cached = json.loads(TOKEN_CACHE.read_text())
        expiry = datetime.fromisoformat(cached["expiry"])
        if cached["source"] != source or cached["scopes"] != SCOPES or expiry - datetime.now(timezone.utc) < TOKEN_MARGIN:
            return None
        return OAuthCredentials(token=cached["token"], expiry=expiry.replace(tzinfo=None), scopes=SCOPES)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def cache_token(source: str, creds: ServiceAccountCredentials):
    TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(TOKEN_CACHE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"source": source, "scopes": SCOPES, "token": creds.token, "expiry": creds.expiry.replace(tzinfo=timezone.utc).isoformat()}, f)


def google_credentials(config: dict):
    op = config.get("onepassword")
    local = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or config.get("service_account_file")
    if local or not op:
        return ServiceAccountCredentials.from_service_account_info(service_account_info(config), scopes=SCOPES)
    source = f"{op.get('account')}/{op.get('vault')}/{op.get('item')}"
    if creds := cached_token(source):
        return creds
    creds = ServiceAccountCredentials.from_service_account_info(service_account_info(config), scopes=SCOPES)
    creds.refresh(Request())
    cache_token(source, creds)
    return creds


def open_spreadsheet(config: dict, spreadsheet: str | None = None) -> gspread.Spreadsheet:
    target = spreadsheet or setting(config, "spreadsheet")
    gc = gspread.authorize(google_credentials(config))
    return gc.open_by_url(target) if "/" in target else gc.open_by_key(target)


def open_worksheet(config: dict, spreadsheet: str | None = None, tab: str | None = None) -> gspread.Worksheet:
    return open_spreadsheet(config, spreadsheet).worksheet(tab or setting(config, "sheet"))


def sheet_url(ws: gspread.Worksheet) -> str:
    return f"https://docs.google.com/spreadsheets/d/{ws.spreadsheet_id}/edit#gid={ws.id}"


def add_months(month: date, n: int) -> date:
    year, index = divmod(month.year * 12 + month.month - 1 + n, 12)
    return date(year, index + 1, 1)


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def parse_label(value: str) -> date | None:
    for fmt in MONTH_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            pass
    return None


def parse_month(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m").date()
    except ValueError:
        raise Fail(f"month {value!r} is not YYYY-MM") from None


def label(month: date) -> str:
    return month.strftime("%B %Y")


def last_reportable(today: date) -> date:
    first = today.replace(day=1)
    return first if today.day > 20 else add_months(first, -1)


def month_rows(col_a: list[str]) -> dict[date, int]:
    rows = {}
    for row, value in enumerate(col_a, start=1):
        if (month := parse_label(value)) and month not in rows:
            rows[month] = row
    return rows


def missing_months(rows: dict[date, int], today: date) -> list[date]:
    if not rows:
        return []
    month, end, missing = min(rows), last_reportable(today), []
    while month <= end:
        if month not in rows:
            missing.append(month)
        month = add_months(month, 1)
    return missing


def locate(ws, col_a: list[str], month: date, first_row: int) -> tuple[int, bool]:
    rows = month_rows(col_a)
    if month in rows:
        return rows[month], True
    earlier = [m for m in rows if m < month]
    if earlier:
        anchor = max(earlier)
        row = rows[anchor] + months_between(anchor, month)
    elif rows:
        raise Fail(f"{label(month)} is older than every month in the sheet, add its row by hand")
    else:
        row = first_row
    if any(cell.strip() for line in ws.get(f"A{row}:D{row}") for cell in line):
        raise Fail(f"row {row} for {label(month)} already holds other data, the sheet no longer keeps one row per month")
    return row, False


def search_prs(author: str, org: str | None, start: date, end: date) -> list[dict]:
    cmd = [
        "gh", "search", "prs",
        "--author", author,
        "--merged",
        "--merged-at", f"{start.isoformat()}..{end.isoformat()}",
        "--limit", str(SEARCH_CAP),
        "--json", "number,title,url,repository,closedAt",
    ] + (["--owner", org] if org else [])
    for wait in RATE_LIMIT_WAITS:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=GH_TIMEOUT, check=False)
        except FileNotFoundError:
            raise Fail("gh CLI not found, install it from https://cli.github.com and run gh auth login") from None
        except subprocess.TimeoutExpired:
            raise Fail(f"gh search prs gave no answer in {GH_TIMEOUT}s, run it again") from None
        if result.returncode == 0 or "rate limit" not in result.stderr.lower() or wait is None:
            break
        print(json.dumps({"waiting": f"GitHub search rate limit, retrying in {wait}s"}), file=sys.stderr, flush=True)
        time.sleep(wait)
    if result.returncode:
        raise Fail(f"gh search prs failed: {result.stderr.strip()}")
    prs = json.loads(result.stdout)
    if len(prs) >= SEARCH_CAP and start < end:
        middle = start + (end - start) // 2
        return search_prs(author, org, start, middle) + search_prs(author, org, middle + timedelta(days=1), end)
    return prs


def fetch_prs(month: date, author: str, orgs: list[str]) -> list[dict]:
    end = add_months(month, 1) - timedelta(days=1)
    prs = {pr["url"]: pr for org in orgs or [None] for pr in search_prs(author, org, month, end)}
    return list(prs.values())


def is_backport(title: str) -> bool:
    return re.search(r"(?i)\bbackport", title) is not None


def strip_backport(title: str) -> str:
    title = re.sub(r"(?i)\s*[\[(]backport[^\])]*[\])]", "", title)
    title = re.sub(r"(?i)\bbackport(?:ed)?\s+(?:of\s+#\d+\s*)?", "", title)
    title = re.sub(r"(?i)\s+(?:to|for|into)\s+release[-/]\S+", "", title)
    return re.sub(r"\s+", " ", title).strip()


def is_dependency(title: str) -> bool:
    return bool(DEPENDENCY_SCOPE.match(title) or DEPENDENCY_SUBJECT.search(CONVENTIONAL_PREFIX.sub("", title, count=1)))


def by_merge(entry: dict) -> tuple[str, str]:
    return entry["merged_at"], entry["url"]


def triage(prs: list[dict]) -> dict:
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for pr in prs:
        repo = pr["repository"]["nameWithOwner"]
        stripped = strip_backport(pr["title"])
        prefix = CONVENTIONAL_PREFIX.match(stripped)
        scope = ((prefix and prefix.group(1)) or "").lower()
        title = stripped[prefix.end():] if prefix else stripped
        entry = {
            "url": pr["url"],
            "repo": repo,
            "number": pr["number"],
            "title": title,
            "original_title": pr["title"],
            "merged_at": pr["closedAt"],
        }
        groups.setdefault((repo.lower(), scope, title.lower()), []).append(entry)

    kept, skipped = [], []
    for group in groups.values():
        original = min(group, key=lambda e: (is_backport(e["original_title"]), e["number"]))
        kept.append(original)
        skipped += [{**e, "skip_reason": "backport_duplicate"} for e in group if e is not original]

    numbers = {(e["repo"].lower(), e["number"]) for e in kept}
    backports = [e for e in kept if (ref := BACKPORT_OF.search(e["original_title"])) and (e["repo"].lower(), int(ref.group(1))) in numbers]
    kept = [e for e in kept if e not in backports]
    skipped += [{**e, "skip_reason": "backport_duplicate"} for e in backports]

    dependencies = [e for e in kept if is_dependency(e["original_title"])]
    dependency_only = bool(kept) and len(dependencies) == len(kept)
    if not dependency_only:
        kept = [e for e in kept if e not in dependencies]
        skipped += [{**e, "skip_reason": "dependency_filtered"} for e in dependencies]

    return {"dependency_only": dependency_only, "included": sorted(kept, key=by_merge), "skipped": sorted(skipped, key=by_merge)}


def plan_path(month: date) -> Path:
    return STATE_DIR / f"{month:%Y-%m}.json"


def cmd_plan(args, config: dict) -> dict:
    ws = open_worksheet(config)
    col_a = ws.col_values(1)
    rows = month_rows(col_a)
    missing = missing_months(rows, date.today())
    if args.month:
        month = parse_month(args.month)
    elif missing:
        month = missing[0]
    elif rows:
        return {"up_to_date": True, "last_month": f"{max(rows):%Y-%m}", "sheet_url": sheet_url(ws)}
    else:
        month = last_reportable(date.today())

    row, existing = locate(ws, col_a, month, config.get("first_row", 6))
    prs = fetch_prs(month, config.get("author", "@me"), config.get("orgs", []))
    plan = {
        "month": f"{month:%Y-%m}",
        "label": label(month),
        "row": row,
        "existing": existing,
        "missing": [f"{m:%Y-%m}" for m in missing],
        "sheet_url": sheet_url(ws),
        "fetched": len(prs),
        **triage(prs),
    }
    included = {e["url"] for e in plan["included"]}
    plan["descriptions"] = {u: d for u, d in load_plan(month, required=False).get("descriptions", {}).items() if u in included}
    save_plan(month, plan)
    return {
        **{k: v for k, v in plan.items() if k not in ("included", "skipped", "descriptions")},
        "skipped": dict(Counter(e["skip_reason"] for e in plan["skipped"])),
        "max_description_chars": description_budget(len(included)),
        "to_describe": remaining(plan),
    }


def load_plan(month: date, required: bool = True) -> dict:
    if plan_path(month).exists():
        return json.loads(plan_path(month).read_text())
    if required:
        raise Fail(f"no plan for {month:%Y-%m}, run: kup.py plan --month {month:%Y-%m}")
    return {}


def save_plan(month: date, plan: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    plan_path(month).write_text(json.dumps(plan, indent=2, ensure_ascii=False))


def description_budget(count: int) -> int:
    return min(250, CELL_LIMIT // max(count, 1) - 1)


def remaining(plan: dict) -> list[dict]:
    return [{"url": e["url"], "title": e["title"]} for e in plan["included"] if e["url"] not in plan["descriptions"]]


def read_descriptions(source: str) -> dict[str, str]:
    raw = sys.stdin.read() if source == "-" else Path(source).read_text()
    descriptions = json.loads(raw)
    if not isinstance(descriptions, dict) or not all(isinstance(v, str) for v in descriptions.values()):
        raise Fail('descriptions must be a JSON object: {"<pr url>": "<description>"}')
    return descriptions


def merge_descriptions(plan: dict, descriptions: dict[str, str]) -> dict:
    urls = {e["url"] for e in plan["included"]}
    problems = {
        "unknown_urls": sorted(set(descriptions) - urls),
        "empty": sorted(u for u, d in descriptions.items() if not d.strip()),
        "multiline": sorted(u for u, d in descriptions.items() if "\n" in d.strip()),
    }
    if any(problems.values()):
        raise Fail(json.dumps({k: v for k, v in problems.items() if v}))
    cleaned = {u: d.strip().rstrip(".").strip() for u, d in descriptions.items()}
    return {**plan, "descriptions": {**plan["descriptions"], **cleaned}}


def row_values(month: date, included: list[dict]) -> list[str]:
    values = [
        label(month),
        "\n".join(e["description"] for e in included),
        "\n".join(sorted({f"https://github.com/{e['repo']}" for e in included})),
        "\n".join(e["url"] for e in included),
    ]
    if oversized := {col: len(v) for col, v in zip("ABCD", values, strict=True) if len(v) > CELL_LIMIT}:
        raise Fail(f"cells over the {CELL_LIMIT} character limit of Google Sheets: {oversized}, shorten the descriptions")
    return values


def cmd_describe(args, config: dict) -> dict:
    month = parse_month(args.month)
    descriptions = read_descriptions(args.input) if args.input else None
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with plan_path(month).with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        plan = load_plan(month)
        if descriptions is not None:
            plan = merge_descriptions(plan, descriptions)
            save_plan(month, plan)
    return {"described": len(plan["descriptions"]), "remaining": remaining(plan)}


def record_history(path: Path, month: str, included: list[dict], skipped: list[dict]) -> int:
    rows = []
    if path.exists():
        with path.open(newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["month"] != month]
    for status, entries in (("included", included), ("skipped", skipped)):
        for e in entries:
            rows.append({
                "month": month,
                "pr_url": e["url"].removeprefix("https://github.com/"),
                "repo": e["repo"],
                "original_title": e["original_title"],
                "generated_description": e.get("description", ""),
                "status": status,
                "skip_reason": e.get("skip_reason", ""),
                "merged_at": e["merged_at"],
            })
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def cmd_write(args, config: dict) -> dict:
    month = parse_month(args.month)
    plan = load_plan(month)
    if todo := remaining(plan):
        raise Fail(f"{len(todo)} PRs still need a description, list them with: kup.py describe --month {plan['month']}")
    included = [{**e, "description": plan["descriptions"][e["url"]]} for e in plan["included"]]
    values = row_values(month, included)

    ws = open_worksheet(config)
    row, existing = locate(ws, ws.col_values(1), month, config.get("first_row", 6))
    if existing and not args.force and not args.dry_run:
        raise Fail(f"{label(month)} already fills row {row}, pass --force to replace it")

    if not args.dry_run:
        ws.update([values], f"A{row}:D{row}", value_input_option=ValueInputOption.raw)

    history = DATA_DIR / "pr-history.csv"
    total = record_history(history, plan["month"], included, plan["skipped"])
    if not args.dry_run:
        plan_path(month).unlink()
        plan_path(month).with_suffix(".lock").unlink(missing_ok=True)
    result = {
        "dry_run": args.dry_run,
        "month": plan["month"],
        "row": row,
        "replaces_existing": existing,
        "included": len(included),
        "skipped": len(plan["skipped"]),
        "sheet_url": sheet_url(ws),
        "history_csv": str(history),
        "history_rows": total,
    }
    return {**result, "values": dict(zip("ABCD", values, strict=True))} if args.dry_run else result


def input_option(args) -> ValueInputOption:
    return ValueInputOption.user_entered if args.user_entered else ValueInputOption.raw


def cmd_sheet_list(args, config: dict):
    ss = open_spreadsheet(config, args.spreadsheet)
    return [{"title": ws.title, "id": ws.id, "rows": ws.row_count, "cols": ws.col_count} for ws in ss.worksheets()]


def cmd_sheet_read(args, config: dict):
    ws = open_worksheet(config, args.spreadsheet, args.tab)
    return ws.get(args.range) if args.range else ws.get_all_values()


def cmd_sheet_write(args, config: dict):
    open_worksheet(config, args.spreadsheet, args.tab).update([[args.value]], args.cell, value_input_option=input_option(args))
    return {"ok": True, "cell": args.cell, "value": args.value}


def cmd_sheet_append(args, config: dict):
    row = json.loads(args.row)
    if not isinstance(row, list):
        raise Fail("--row must be a JSON array")
    ws = open_worksheet(config, args.spreadsheet, args.tab)
    if not args.after_col:
        ws.append_row(row, value_input_option=input_option(args))
        return {"ok": True, "appended": row}
    target = len(ws.col_values(a1_to_rowcol(f"{args.after_col.upper()}1")[1])) + 1
    ws.update([row], f"A{target}", value_input_option=input_option(args))
    return {"ok": True, "appended": row, "row": target}


def cmd_sheet_clear(args, config: dict):
    ws = open_worksheet(config, args.spreadsheet, args.tab)
    if args.range:
        ws.batch_clear([args.range])
    else:
        ws.clear()
    return {"ok": True}


def add_sheet_commands(sub):
    sheet = sub.add_parser("sheet", help="read or edit the KUP sheet, or another sheet shared with the service account").add_subparsers(dest="op", required=True)

    def command(name, help, fn, tab=True):
        p = sheet.add_parser(name, help=help)
        p.add_argument("--spreadsheet", metavar="ID_OR_URL", help="default: spreadsheet from the config")
        if tab:
            p.add_argument("--tab", help="tab name, case-sensitive (default: sheet from the config)")
        p.set_defaults(fn=fn)
        return p

    command("list", "list tabs", cmd_sheet_list, tab=False)
    command("read", "read a tab or range", cmd_sheet_read).add_argument("--range", help="A1 range, e.g. A1:D10 (default: whole tab)")
    p = command("write", "write one cell", cmd_sheet_write)
    p.add_argument("--cell", required=True, help="A1 cell, e.g. B3")
    p.add_argument("--value", required=True)
    p.add_argument("--user-entered", action="store_true", help="parse like typed in the UI (formulas, numbers, dates)")
    p = command("append", "append a row", cmd_sheet_append)
    p.add_argument("--row", required=True, help='JSON array, e.g. \'["Alice","done"]\'')
    p.add_argument("--after-col", metavar="COL", help="place the row after the last filled cell of this column instead of the last row with any data")
    p.add_argument("--user-entered", action="store_true", help="parse like typed in the UI (formulas, numbers, dates)")
    command("clear", "clear a tab or range", cmd_sheet_clear).add_argument("--range", help="A1 range (default: whole tab)")


def parse_args():
    parser = argparse.ArgumentParser(description="KUP monthly report: plan a month, then write it")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="pick the month, fetch and triage its merged PRs, save the plan")
    p.add_argument("--month", metavar="YYYY-MM", help="default: oldest month missing from the sheet")
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("describe", help="add Polish descriptions to the plan, or list PRs still missing one")
    p.add_argument("--month", metavar="YYYY-MM", required=True)
    p.add_argument("--input", metavar="FILE", help='JSON {"<pr url>": "<description>"}, - for stdin')
    p.set_defaults(fn=cmd_describe)
    p = sub.add_parser("write", help="write a fully described month to the sheet")
    p.add_argument("--month", metavar="YYYY-MM", required=True)
    p.add_argument("--dry-run", action="store_true", help="preview the row without touching the sheet")
    p.add_argument("--force", action="store_true", help="replace the month if the sheet already has it")
    p.set_defaults(fn=cmd_write)
    add_sheet_commands(sub)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        print(json.dumps(args.fn(args, load_config()), indent=2, ensure_ascii=False))
    except gspread.exceptions.SpreadsheetNotFound:
        fail("spreadsheet not found: share it with the service account email as Editor")
    except gspread.exceptions.APIError as e:
        if e.response.status_code == 401:
            TOKEN_CACHE.unlink(missing_ok=True)
            fail(f"Google rejected the cached access token, it is dropped now, run the command again: {e}")
        fail(str(e))
    except gspread.exceptions.WorksheetNotFound as e:
        fail(f"tab {str(e)!r} not found, tab names are case-sensitive, check --tab or 'sheet' in {CONFIG_PATH}")
    except Exception as e:
        fail(str(e) or type(e).__name__)


def fail(message: str):
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
