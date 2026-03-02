# SAI - Skills for Agentic Intelligence

A collection of independent Claude Code plugins for development workflows, automation, and productivity.

## Overview

This monorepo contains independent plugins, each providing specialized capabilities:

| Plugin                  | Description                                                                             | Installation Path      |
|:------------------------|:----------------------------------------------------------------------------------------|:-----------------------|
| **ai-daily-digest**     | Daily AI news digest covering technical advances, business news, and engineering impact | `ai-daily-digest/`     |
| **browser-controller**  | Programmatic control of Chrome/Firefox via CDP/Marionette                               | `browser-controller/`  |
| **gh-review-comments**  | List, reply to, resolve, and create GitHub PR review comment threads                    | `gh-review-comments/`  |
| **git**                 | Git workflow automation: worktree creation, branch cleanup, and reset utilities         | `git/`                 |
| **git-stage-hunk**      | Non-interactive hunk staging for selective git add without TTY                          | `git-stage-hunk/`      |
| **humanize**            | Make text sound natural by removing AI writing patterns                                 | `humanize/`            |
| **manage-agent**        | Create, modify, or transform subagent definitions with quality validation               | `manage-agent/`        |
| **manage-plan**         | Investigate codebases and produce implementation plans                                  | `manage-plan/`         |
| **ocr-finder**          | Find text in images using EasyOCR and return click coordinates                          | `ocr-finder/`          |
| **promptgen**           | Turn rough instructions into optimized, evidence-based AI prompts                       | `promptgen/`           |
| **review-agent**        | Audit subagent definitions for quality compliance                                       | `review-agent/`        |
| **review-claude-md**    | Audit and fix CLAUDE.md files using tiered binary checklist                             | `review-claude-md/`    |
| **review-plan**         | Review implementation plans for executor-readiness                                      | `review-plan/`         |
| **review-skill**        | Review and fix Claude Code skill definitions using tiered binary checklist              | `review-skill/`        |
| **screen-recorder**     | Record macOS screen with verification and format conversion                             | `screen-recorder/`     |
| **session**             | Capture session context for continuity between Claude Code sessions                     | `session/`             |
| **space-finder**        | Find and switch macOS Spaces by application name                                        | `space-finder/`        |
| **ui-inspector**        | Inspect live macOS UI elements via Accessibility API                                    | `ui-inspector/`        |
| **verified-screenshot** | Capture screenshots with verification and retry logic                                   | `verified-screenshot/` |
| **web-automation**      | Investigate and implement web browser automation workflows                              | `web-automation/`      |
| **window-controller**   | Find, activate, and screenshot macOS windows across Spaces                              | `window-controller/`   |

## Installation

### Via marketplace

Add the SAI marketplace, then install individual plugins:

```bash
# Add the SAI marketplace
/plugin marketplace add git@github.com:smykla-skalski/sai.git

# Install individual plugins
/plugin install sai/ai-daily-digest
/plugin install sai/browser-controller
/plugin install sai/gh-review-comments
/plugin install sai/git
/plugin install sai/git-stage-hunk
/plugin install sai/humanize
/plugin install sai/manage-agent
/plugin install sai/manage-plan
/plugin install sai/ocr-finder
/plugin install sai/promptgen
/plugin install sai/review-agent
/plugin install sai/review-claude-md
/plugin install sai/review-plan
/plugin install sai/review-skill
/plugin install sai/screen-recorder
/plugin install sai/session
/plugin install sai/space-finder
/plugin install sai/ui-inspector
/plugin install sai/verified-screenshot
/plugin install sai/web-automation
/plugin install sai/window-controller
```

Each plugin is independent - install only what you need.

### Local development

Clone the repository and point directly to plugin directories:

```bash
git clone git@github.com:smykla-skalski/sai.git

claude --plugin-dir /path/to/sai/ai-daily-digest
claude --plugin-dir /path/to/sai/browser-controller
claude --plugin-dir /path/to/sai/gh-review-comments
claude --plugin-dir /path/to/sai/git
claude --plugin-dir /path/to/sai/git-stage-hunk
claude --plugin-dir /path/to/sai/humanize
claude --plugin-dir /path/to/sai/manage-agent
claude --plugin-dir /path/to/sai/manage-plan
claude --plugin-dir /path/to/sai/ocr-finder
claude --plugin-dir /path/to/sai/promptgen
claude --plugin-dir /path/to/sai/review-agent
claude --plugin-dir /path/to/sai/review-claude-md
claude --plugin-dir /path/to/sai/review-plan
claude --plugin-dir /path/to/sai/review-skill
claude --plugin-dir /path/to/sai/screen-recorder
claude --plugin-dir /path/to/sai/session
claude --plugin-dir /path/to/sai/space-finder
claude --plugin-dir /path/to/sai/ui-inspector
claude --plugin-dir /path/to/sai/verified-screenshot
claude --plugin-dir /path/to/sai/web-automation
claude --plugin-dir /path/to/sai/window-controller
```

## Plugins

### ai-daily-digest

Daily AI news digest covering technical advances, business news, and engineering impact. Aggregates from research papers, tech blogs, HN, newsletters.

**Usage**: `/ai-daily-digest [--focus technical|business|engineering|leadership] [--notion-page-id ID] [--no-notion]`

[Full documentation →](./ai-daily-digest/README.md)

### browser-controller

Programmatic control of Chrome and Firefox browsers via Chrome DevTools Protocol and Firefox Marionette. Features tab management, navigation, DOM interaction, form filling, JavaScript execution, and screenshot capture.

**Usage**: `/browser-controller [command] [args]`

[Full documentation →](./browser-controller/README.md)

### gh-review-comments

List, reply to, resolve, and create GitHub PR review comment threads using gh CLI scripts. Manage code review feedback, reply to reviewer remarks, resolve conversations.

**Usage**: `/gh-review-comments owner/repo 42 [--reply "message"] [--resolve] [--author login]`

[Full documentation →](./gh-review-comments/README.md)

### git

Git workflow automation: worktree creation with context transfer, branch cleanup, and reset utilities. Includes 4 skills: worktree creation, branch reset, stale branch cleanup, and worktree validation.

**Usage**: `/worktree <task>`, `/reset-main`, `/clean-gone`, `/worktree-review`

[Full documentation →](./git/README.md)

### git-stage-hunk

Non-interactive hunk staging for selective `git add` without a TTY. Lists hunks with stable IDs, then stages by ID, pattern, file, or line range. Works in scripted and multi-agent environments where `git add -p` is unavailable.

**Usage**: `/stage-hunk [--list] [--hunk H1,H2] [--pattern REGEX] [--file PATH] [--range FILE:S-E] [--dry-run]`

[Full documentation →](./git-stage-hunk/README.md)

### humanize

Make text sound natural by removing AI writing patterns. Based on Wikipedia's Signs of AI Writing guide — detects 24 patterns across content, language, style, communication, and filler categories.

**Usage**: `/humanize path/to/file.md [--score-only] [--inline]`

[Full documentation →](./humanize/README.md)

### manage-agent

Create, modify, or transform Claude Code subagent definitions with built-in quality validation. Converts prompt templates into production-quality agent definitions with automatic quality checks.

**Usage**: `/manage-agent [file-path|description] [--create|--modify|--transform]`

[Full documentation →](./manage-agent/README.md)

### manage-plan

Investigate codebases and produce self-contained implementation plans with built-in quality validation. Supports creating plans from descriptions, modifying existing plans, and transforming specs or RFCs.

**Usage**: `/manage-plan [task-description|plan-path|doc-path] [--create|--modify|--transform]`

[Full documentation →](./manage-plan/README.md)

### ocr-finder

Find text in images using EasyOCR and return click coordinates. Works on screenshots and UI captures without accessibility permissions for UI automation workflows.

**Usage**: `/ocr-finder [command] [args]`

[Full documentation →](./ocr-finder/README.md)

### promptgen

Turn rough instructions into optimized, evidence-based AI prompts. Built on 35+ academic papers, Anthropic/OpenAI vendor docs, and Mollick/Wharton Prompting Science Reports. Copies to clipboard.

**Usage**: `/promptgen <instructions> [--for claude|gpt|generic] [--verbose] [--no-copy] [--with-examples]`

[Full documentation ->](./promptgen/README.md)

### review-agent

Audit Claude Code subagent definitions for quality compliance against template standards. Checks frontmatter, section order, constraints, anti-patterns, and completeness with graded quality reports.

**Usage**: `/review-agent <file-path> [--fix]`

[Full documentation →](./review-agent/README.md)

### review-claude-md

Audit and fix CLAUDE.md files using tiered binary checklist based on Anthropic best practices and community guidelines.

**Usage**: `/review-claude-md [path/to/CLAUDE.md]`

[Full documentation →](./review-claude-md/README.md)

### review-plan

Review implementation plans for completeness, quality, and executor-readiness. Checks mandatory sections, workflow commands, git configuration, execution phases, and self-containment.

**Usage**: `/review-plan <file-path> [--fix]`

[Full documentation →](./review-plan/README.md)

### review-skill

Review and fix Claude Code skill definitions (SKILL.md) using tiered binary checklist based on Agent Skills specification.

**Usage**: `/review-skill [path/to/SKILL.md]`

[Full documentation →](./review-skill/README.md)

### screen-recorder

Record macOS screen with verification, retry logic, and format conversion for Discord, GitHub, and JetBrains. Captures screen recordings of windows or regions with automatic verification.

**Usage**: `/screen-recorder [command] [args]`

[Full documentation →](./screen-recorder/README.md)

### session

Capture session context for continuity between Claude Code sessions. Generates handover documents with failed approaches, architectural decisions, and next steps.

**Usage**: `/session [session-focus]`

[Full documentation →](./session/README.md)

### space-finder

Find and switch to macOS Spaces by application name. Locates which macOS Space contains a specific app and enables navigation to it.

**Usage**: `/space-finder <app-name> [--list] [--current] [--go] [--json]`

[Full documentation →](./space-finder/README.md)

### ui-inspector

Inspect live macOS UI elements via Accessibility API and get click coordinates for automation. Finds buttons, text fields, and other UI elements in running macOS applications.

**Usage**: `/ui-inspector <command> --app <app> [--role <role>] [--title <title>] [--json]`

[Full documentation →](./ui-inspector/README.md)

### verified-screenshot

Capture macOS window screenshots with automatic verification and retry logic. Provides reliable screenshot capture with verification strategies and configurable retry mechanisms.

**Usage**: `/verified-screenshot <command> <app> [--verify <strategy>] [--retries N] [--json]`

[Full documentation →](./verified-screenshot/README.md)

### web-automation

Investigate and implement web browser automation for testing, scraping, and interaction workflows. Provides investigation and implementation support with guidance on Playwright, Selenium, and Puppeteer.

**Usage**: `/web-automation <url-or-task> [--tool playwright|selenium|puppeteer]`

[Full documentation →](./web-automation/README.md)

### window-controller

Find, activate, and screenshot macOS windows across Spaces. Supports filtering by app name, title, process path, or command line arguments.

**Usage**: `/window-controller <command> <app> [--title <pattern>] [--args-contains <str>] [--json]`

[Full documentation →](./window-controller/README.md)

## Development

See [CLAUDE.md](./CLAUDE.md) for detailed documentation on:

- Plugin architecture
- Creating new plugins
- Skill definition format
- Workflow patterns
- State management
- Testing and contribution guidelines

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution workflow.

To contribute:

1. Fork the repository
2. Create a feature branch
3. Add/modify plugin in its directory
4. Test locally with `claude --plugin-dir {plugin-name}/`
5. Submit a pull request

## License

MIT - See [LICENSE](./LICENSE)

## Repository

- **GitHub**: https://github.com/smykla-skalski/sai
