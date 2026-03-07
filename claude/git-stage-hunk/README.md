# git-stage-hunk

A Claude Code plugin for non-interactive hunk staging. Stage only your changes when a file has edits from multiple sessions or agents. Commit part of a file without `git add -p`. Works without a TTY.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install git-stage-hunk@smykla-skalski-sai
```

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/claude/git-stage-hunk/
```

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

Install patchutils: `brew install patchutils` (macOS) or `apt install patchutils` (Debian/Ubuntu). The plugin works without it using a pure-bash fallback for `--list`, `--hunk`, and `--file` modes.

## License

MIT
