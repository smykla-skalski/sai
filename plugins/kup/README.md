# kup

Fill the monthly KUP report (Koszty Uzyskania Przychodu, the Polish 50% tax deduction for creative work). The skill collects your merged GitHub pull requests for a month, has the agent write a Polish creative-work description for each, and writes the row to your KUP Google Sheet. It also reads and edits that sheet, or any other Google Sheet shared with the same service account.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex and other compatible agents. It runs on macOS and Linux.

## Installation

Claude Code:

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install kup@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add kup@sai
```

Other agents that read Agent Skills can use `skills/kup/` directly, for example by linking it into `~/.agents/skills/kup`.

## Setup

Setup takes about 15 minutes, once. The agent reads the same steps from [`skills/kup/references/setup.md`](skills/kup/references/setup.md) when a command fails.

### 1. Install the tools and log in to GitHub

```bash
brew install uv gh
gh auth login
```

Log in as the account whose pull requests go into the report. If your organization uses SSO, check that its private PRs show up:

```bash
gh search prs --author @me --owner <org> --merged --limit 5
```

If they are missing, grant GitHub CLI access to the organization under [Settings > Applications](https://github.com/settings/applications).

### 2. Create a Google service account key

The script edits your sheet as a Google service account. Company Google accounts often block key creation, so use a personal Google account here.

1. [Create a project](https://console.cloud.google.com/projectcreate).
2. Enable the [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com) and the [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com).
3. [Create a service account](https://console.cloud.google.com/iam-admin/serviceaccounts). It needs no roles.
4. On its **Keys** tab, choose **Add key > Create new key > JSON**.
5. Save the key as `~/.config/kup/service-account.json` and run `chmod 600` on it.

The same steps with gcloud:

```bash
PROJECT=kup-reports-$RANDOM
gcloud projects create "$PROJECT"
gcloud services enable sheets.googleapis.com drive.googleapis.com --project "$PROJECT"
gcloud iam service-accounts create kup-sheets --project "$PROJECT"
mkdir -p ~/.config/kup
gcloud iam service-accounts keys create ~/.config/kup/service-account.json --iam-account "kup-sheets@$PROJECT.iam.gserviceaccount.com"
chmod 600 ~/.config/kup/service-account.json
```

### 3. Share the sheet

Share your KUP sheet with the service account's email, the `client_email` in the key file, as **Editor**.

The sheet keeps one row per month: the month in column A (`March 2026`), then the descriptions, repository URLs and PR URLs in columns B to D.

### 4. Write the config

Create `~/.config/kup/config.toml`:

```toml
spreadsheet = "<sheet ID or URL>"
sheet = "2022-2025"        # tab with the monthly rows
author = "@me"             # whose merged PRs count
orgs = ["kong", "kumahq"]  # leave out to count every repository
service_account_file = "~/.config/kup/service-account.json"
```

On a tab with no month yet, set `first_row` to the row that takes the first month. It defaults to 6.

To keep the key in 1Password instead, turn on **Settings > Developer > Integrate with other apps** in the 1Password app, then store the key and read its IDs:

```bash
op document create ~/.config/kup/service-account.json --title "kup service account"
op item get "kup service account" --format json | jq -r '.vault.id, .id'
op account list
```

Delete the key file, and replace `service_account_file` with this table at the end of the config:

```toml
[onepassword]
account = "my.1password.com"  # URL column of op account list
vault = "<vault ID>"
item = "<item ID>"
```

1Password then asks once per run. The script reuses a one-hour Google token for the rest of it.

### 5. Check

Ask your agent to "list my KUP sheet tabs". It runs `kup.py sheet list` and shows them.

### Errors

| Error | Fix |
|:------|:----|
| `missing ~/.config/kup/config.toml` | Write the config (step 4) |
| `no Google service account configured` | Set `service_account_file` or `[onepassword]` (step 4) |
| `spreadsheet not found` or `403` | Share the sheet as Editor (step 3) and enable both APIs (step 2) |
| `tab ... not found` | Fix `sheet` in the config, tab names are case-sensitive |
| `1Password ... denied` | Approve the prompt and turn on the app integration (step 4) |
| `gh search prs failed` or private PRs missing | Run `gh auth login` and grant SSO access (step 1) |
| `row N ... already holds other data` | Column A skips or repeats a month near that row, fix it by hand |

## Usage

Ask in plain words, for example "fill my KUP report", "catch up the KUP sheet" or "preview KUP for 2026-03". In Claude Code, `/kup` works too, and in Codex `$kup`. The agent previews every row before it writes.

## How it works

`skills/kup/scripts/kup.py` does the deterministic part: it finds the month and its row in the sheet, searches GitHub, drops backports and dependency bumps, stores the plan, writes the row and keeps a CSV history in `~/.local/share/kup/`. The agent writes the Polish descriptions following `skills/kup/references/kup-rules.md`. The script's own checks run with `uv run --script skills/kup/scripts/test_kup.py`.

## License

MIT
