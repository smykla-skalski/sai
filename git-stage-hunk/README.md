# git-stage-hunk

A Claude Code plugin for non-interactive hunk staging. Selectively stage parts of files for git commit without a TTY, replacing `git add -p` in scripted and multi-agent environments.

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
claude --plugin-dir /path/to/sai/git-stage-hunk/
```

## Skills

### stage-hunk

Non-interactive hunk staging for selective `git add`. Lists hunks with stable IDs, then stages by ID, pattern, file, or line range.

```
/stage-hunk --list
/stage-hunk --hunk H1,H3
/stage-hunk --hunk H2 --dry-run
/stage-hunk --pattern 'handleAuth'
/stage-hunk --file src/auth.ts
/stage-hunk --range src/auth.ts:45-60
/stage-hunk --verify
```

| Flag               | Purpose                                       |
|:-------------------|:----------------------------------------------|
| `--list`           | List all unstaged hunks with IDs and previews |
| `--hunk H1,H2`    | Stage specific hunks by global ID             |
| `--pattern REGEX`  | Stage hunks matching regex (needs patchutils) |
| `--file PATH`      | Stage all hunks for file(s)                   |
| `--range FILE:S-E` | Stage hunks in line range (needs patchutils)  |
| `--dry-run`        | Preview without applying                      |
| `--verify`         | Show staged vs unstaged summary               |

## Dependencies

- git, python3 (required)
- patchutils (optional, enables `--pattern` and `--range` modes)

Install patchutils: `brew install patchutils` (macOS) or `apt install patchutils` (Debian/Ubuntu). The plugin works without it using a pure-bash fallback for `--list`, `--hunk`, and `--file` modes.

## License

MIT
