# KUP setup

One-time setup, about 15 minutes. You need a GitHub login, a Google service account key that can edit the KUP sheet, and one config file.

## 1. Install the tools

```bash
brew install uv gh
```

Without Homebrew: `curl -LsSf https://astral.sh/uv/install.sh | sh` for [uv](https://docs.astral.sh/uv/) and the packages from [cli.github.com](https://cli.github.com) for gh. uv installs the Python dependencies on the first run by itself.

## 2. Log in to GitHub

```bash
gh auth login
```

Pick GitHub.com, then "Login with a web browser", as the account whose PRs go into the report. The default scopes include `repo`, which private repositories need.

Organizations with SAML SSO (Kong, for example) only return private PRs once the token is authorized for them. Check with:

```bash
gh search prs --author @me --owner kong --merged --limit 5
```

If private repositories are missing, open [GitHub > Settings > Applications > Authorized OAuth Apps](https://github.com/settings/applications), pick **GitHub CLI** and grant access to the organization, or sign in to the organization's SSO in the browser and run `gh auth login` again.

## 3. Create a Google service account key

The script edits the sheet as a Google service account, a robot account with its own email address that sees only the sheets shared with it. Its key is a JSON file.

Company Google organizations often forbid service account keys through the `iam.disableServiceAccountKeyCreation` policy. The key step then fails with "key creation is not allowed" or "disabled by an organization policy". Create the project while signed in to a personal Google account instead, which has no such policy. The company sheet can still be shared with the service account, as long as the company allows sharing outside the organization.

### In the Google Cloud console

1. Open [console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate), name the project (for example `kup-reports`) and click **Create**. Keep the project selected in the top bar for the next steps.
2. Open [the Google Sheets API page](https://console.cloud.google.com/apis/library/sheets.googleapis.com) and click **Enable**. Do the same on [the Google Drive API page](https://console.cloud.google.com/apis/library/drive.googleapis.com).
3. Open [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts) and click **Create service account**. Name it (for example `kup-sheets`), click **Create and continue**, skip the optional role and user access steps, and click **Done**. It needs no IAM roles, because access comes from sharing the sheet.
4. Click the new service account, open the **Keys** tab and choose **Add key > Create new key > JSON > Create**. The browser downloads the key file. Google keeps no copy, so a lost key means creating a new one.
5. Note the service account email, `kup-sheets@<project-id>.iam.gserviceaccount.com`. It is also the `client_email` field of the key file.

### With gcloud instead

```bash
PROJECT=kup-reports-$RANDOM
gcloud projects create "$PROJECT"
gcloud services enable sheets.googleapis.com drive.googleapis.com --project "$PROJECT"
gcloud iam service-accounts create kup-sheets --display-name "KUP sheets" --project "$PROJECT"
mkdir -p ~/.config/kup
gcloud iam service-accounts keys create ~/.config/kup/service-account.json \
  --iam-account "kup-sheets@$PROJECT.iam.gserviceaccount.com"
chmod 600 ~/.config/kup/service-account.json
```

Project IDs are global, so the random suffix avoids a clash. `gcloud projects create` needs a logged-in `gcloud auth login` session with the account that should own the project.

## 4. Share the KUP sheet with the service account

1. Open the KUP spreadsheet in Google Sheets and click **Share**.
2. Paste the service account email, set the role to **Editor**, turn off **Notify people**, and click **Share**. Confirm the "outside your organization" warning if it shows.

Every other sheet `kup.py sheet` should reach needs the same share, as **Editor** to write or **Viewer** to read only.

## 5. Store the key

Pick one.

### As a file

Move the downloaded key to `~/.config/kup/service-account.json`, run `chmod 600` on it, and set `service_account_file` in the config (step 6). Keep it out of every git repository.

### In 1Password

The script reads the key through the 1Password desktop app, so no key file stays on disk.

1. In the 1Password app, turn on **Settings > Developer > Integrate with other apps**.
2. Store the key as a Document item and read back its IDs:

   ```bash
   op document create ~/Downloads/<key file>.json --title "kup service account" --vault Private
   op item get "kup service account" --vault Private --format json | jq -r '.id, .vault.id'
   op account list
   ```

   The first line is the item ID and the second the vault ID. `op account list` shows the account's sign-in address in the URL column, for example `my.1password.com`.
3. Delete the downloaded key file.

The first sheet command of a run makes 1Password ask for access. Approve it. The script then keeps a Google access token (not the key) in `~/.cache/kup/google-token.json`, readable only by you, and reuses it for up to an hour, so later commands ask nothing. Deleting that file forces a new prompt.

## 6. Write the config

Create `~/.config/kup/config.toml` (or `$XDG_CONFIG_HOME/kup/config.toml`, or any path in `KUP_CONFIG`):

```toml
# Spreadsheet ID or full URL, the ID is the part between /d/ and /edit in the sheet's URL
spreadsheet = "1AbC...xyz"
# Tab with the monthly rows
sheet = "2022-2025"
# GitHub author, @me is the gh login
author = "@me"
# Only PRs in repositories owned by these users or organizations, omit to take every repository
orgs = ["kong", "kumahq"]
# Row of the first month, used only while the tab has no month yet
first_row = 6

# Key as a file:
service_account_file = "~/.config/kup/service-account.json"

# Or key in 1Password, instead of service_account_file:
# [onepassword]
# account = "my.1password.com"
# vault = "<vault ID>"
# item = "<item ID>"
```

TOML puts every key below `[onepassword]` into that table, so keep it last.

`GOOGLE_SERVICE_ACCOUNT_JSON` (the key itself) or `GOOGLE_SERVICE_ACCOUNT_FILE` (a path) in the environment take precedence over the config, but a config file works in every agent, while environment variables depend on what each agent passes to its shell.

`kup.py sheet` against another spreadsheet only needs the key settings from this file.

## 7. Check

```bash
uv run --quiet --script scripts/kup.py sheet list
```

A JSON list of tabs means the key, the sharing and the config work. It only reads.

## Sheet layout

The script expects the layout of the KUP template:

- Header rows at the top, the month rows below them, one row per month.
- Column A holds the month label, `March 2026` (`Mar 2026` also parses).
- Columns B, C and D hold the descriptions, the repository URLs and the PR URLs.

It never writes to a row that holds anything other than the month it is writing.

## Errors

| Error | Fix |
|:------|:----|
| `missing ~/.config/kup/config.toml` | Write the config from step 6 |
| `no 'spreadsheet' in ...` | Add `spreadsheet` and `sheet` above `[onepassword]` |
| `no Google service account configured` | Add `service_account_file` or `[onepassword]` to the config |
| `No such file or directory` | Fix the `service_account_file` path |
| `1Password ... denied` or `authorization` | Approve the 1Password prompt, turn on the app integration from step 5, and don't start two sheet commands at once |
| `Google rejected the cached access token` | Run the command again, it fetches a fresh token |
| `spreadsheet not found` | Share the sheet with the service account email from step 4 |
| `403` or `PERMISSION_DENIED` | Enable both APIs in the key's project (step 3), or share the sheet as Editor |
| `tab ... not found` | Fix `sheet` in the config or `--tab`, tab names are case-sensitive |
| `gh search prs failed` | Run `gh auth login` |
| PRs from private repositories missing | Authorize GitHub CLI for the SSO organization (step 2) |
| `row N ... already holds other data` | Column A no longer has one row per month around that date, fix the sheet by hand |
