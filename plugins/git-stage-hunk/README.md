# git-stage-hunk

Non-interactive hunk staging. Stage only your changes when a file has edits from multiple sessions or agents. Commit part of a file without `git add -p`. Works without a TTY.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install git-stage-hunk@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add git-stage-hunk@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/git-stage-hunk/` directly:

```bash
ln -s /path/to/sai/plugins/git-stage-hunk/skills/git-stage-hunk ~/.config/opencode/skills/git-stage-hunk
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/git-stage-hunk/`

## Usage

In Claude Code and Copilot CLI use `/git-stage-hunk`, in Codex `$git-stage-hunk`. Codex only runs it when you name it, because it writes the git index. The script runs from the skill's `scripts/` directory against the repository in your current working directory.

## Skills

### git-stage-hunk

Non-interactive hunk staging for selective `git add`. Lists hunks with stable IDs, then stages by ID, pattern, file, or line range. Supports splitting large hunks into sub-hunks when multiple changes got merged by git's default context.

```
/git-stage-hunk --list --table
/git-stage-hunk --list --file src/auth.ts --table
/git-stage-hunk --list --split --table
/git-stage-hunk --split H3
/git-stage-hunk --hunk H1,H3 --table
/git-stage-hunk --hunk H3.1,H3.2 --table
/git-stage-hunk --hunk H3:5-10 --table
/git-stage-hunk --hunk H1,H3.2,H5:10-15 --table
/git-stage-hunk --hunk H2 --dry-run --table
/git-stage-hunk --pattern 'handleAuth' --table
/git-stage-hunk --file src/auth.ts --table
/git-stage-hunk --range src/auth.ts:45-60 --table
/git-stage-hunk --verify --table
```

| Flag                  | Purpose                                          |
|:----------------------|:-------------------------------------------------|
| `--list`              | List all unstaged hunks with IDs and previews    |
| `--list --file PATH`  | List hunks filtered to file(s)                   |
| `--list --split`      | List all hunks with sub-hunk breakdown           |
| `--split H3`          | Show sub-hunks for one specific hunk             |
| `--hunk H1,H2`        | Stage specific hunks by global ID                |
| `--hunk H3.1`         | Stage sub-hunks by dot-notation ID               |
| `--hunk H3:5-10`      | Stage hunk-relative lines within a hunk          |
| `--pattern REGEX`     | Stage hunks matching regex (needs patchutils)    |
| `--file PATH`         | Stage all hunks for file(s)                      |
| `--range FILE:S-E`    | Stage hunks in line range (needs patchutils)     |
| `--table`             | Output as markdown table (default is NDJSON)     |
| `--dry-run`           | Preview without applying                         |
| `--verify`            | Show staged vs unstaged summary                  |

`--file` has dual behavior: with `--list` it filters the listing, without `--list` it stages all hunks for that file.

## Dependencies

- git, python3 (required)
- patchutils (optional, enables `--pattern` and `--range` modes)

Install patchutils: `brew install patchutils` (macOS) or `apt install patchutils` (Debian/Ubuntu). The plugin works without it using a pure-Python fallback for `--list`, `--hunk`, and `--file` modes.

## License

MIT
