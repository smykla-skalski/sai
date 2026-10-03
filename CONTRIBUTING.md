# Contributing to Smykla Skalski Projects

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to Smykla Skalski projects.

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

Check the project's README for specific prerequisites. Common requirements include:

- [mise](https://mise.jdx.dev/) for tool version management
- Project-specific tools managed by mise

### SAI Monorepo Structure

For the SAI project specifically:

- New plugins, and plugins migrated off the old split, use the portable layout below. Legacy Claude plugins still live under `claude/{plugin-name}/` and legacy Codex skills under `codex/{skill-name}/`
- Test individual plugins: `claude --plugin-dir plugins/{plugin-name}/` (legacy: `claude/{plugin-name}/`)
- Plugin-specific changes modify files in the plugin's own directory
- Monorepo-wide changes modify root files (README.md, CLAUDE.md, etc.)
- Plugin versions are bumped by a pre-commit hook. Enable it once per clone with `git config core.hooksPath .githooks`
- On each commit the hook bumps the patch version of every plugin with staged changes (`claude/{plugin-name}/`, `plugins/{plugin-name}/`, and any `codex/{skill-name}/` a manifest points to), keeps all manifests of one plugin on the same version, and stages them. README-only changes skip the bump
- For a minor or major bump, set the version yourself in the same commit; the hook leaves it alone
- Stage with `git add` and run `git commit` without paths; `git commit <paths>` is rejected when a bump is needed
- Hook tests: `python3 -m unittest discover -s tests`

#### Portable plugin layout

One directory serves Claude Code, Codex, Copilot CLI and opencode. Copy `plugins/humanize/` (skill without scripts) or `plugins/kup/` (skill with scripts):

```text
plugins/{name}/
├── plugin.json                 # Agent Plugins manifest: $schema, extensions."com.openai".interface (Codex UI)
├── .claude-plugin/plugin.json  # Claude Code and Copilot CLI manifest: same name, version, description
├── README.md
└── skills/{skill}/
    ├── SKILL.md                # name = directory name, description up to 1024 chars
    ├── agents/openai.yaml      # optional Codex skill UI metadata
    ├── references/
    └── scripts/                # called by paths relative to the skill directory
```

- List the plugin in both marketplaces, each pointing at `./plugins/{name}`: `.claude-plugin/marketplace.json` (`source`) and `.agents/plugins/marketplace.json` (`source.path`). Do not add `.codex-plugin/`; Codex reads the root `plugin.json`
- SKILL.md frontmatter uses the [Agent Skills](https://agentskills.io/specification) fields (`name`, `description`, `license`, `compatibility`, `metadata`, space-separated `allowed-tools`). Claude-only keys (`argument-hint`, `user-invocable`, `context`, `agent`, `disable-model-invocation`) may stay: other agents ignore them, and they are the only errors `skills-ref validate` may report
- Every Claude-only feature the workflow uses (`$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`, AskUserQuestion, subagents, `context: fork`) needs a fallback written in SKILL.md, like the "Agent compatibility" table in `plugins/humanize/skills/humanize/SKILL.md`
- Migrating a plugin: `git mv` `claude/{name}/.claude-plugin/`, `skills/` and `README.md` into `plugins/{name}/`, add the root `plugin.json` with the Claude version, fold any Codex-only guidance from `codex/{name}/SKILL.md` into SKILL.md, move `codex/{name}/agents/openai.yaml` to `skills/{skill}/agents/`, delete `codex/{name}/` and `plugins/{name}/.codex-plugin/`, then fix every link to the old paths (`grep -rn "claude/{name}\|codex/{name}"`). The hook bumps past the old Claude and Codex versions
- Validate: `claude plugin validate .` and `claude plugin validate plugins/{name}`; `uvx --from skills-ref agentskills validate plugins/{name}/skills/{skill}`; install from the local marketplace with throwaway `CLAUDE_CONFIG_DIR`, `CODEX_HOME` and `COPILOT_HOME` directories (`codex debug prompt-input` shows whether Codex loaded the skill)

### Setup

1. Fork the repository on GitHub
2. Clone your fork:

   ```bash
   git clone https://github.com/YOUR_USERNAME/REPO_NAME.git
   cd REPO_NAME
   ```

3. Add upstream remote:

   ```bash
   git remote add upstream https://github.com/smykla-skalski/REPO_NAME.git
   ```

4. Install dependencies (if applicable):

   ```bash
   mise install
   ```

## Development Workflow

### Branch Naming

Create descriptive, kebab-case branches with a type prefix:

```bash
git checkout -b feat/add-feature
git checkout -b fix/bug-description
git checkout -b docs/update-readme
```

Valid branch types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`

### Making Changes

1. **Create a feature branch** from `main`:

   ```bash
   git fetch upstream
   git checkout -b feat/my-feature upstream/main
   ```

2. **Make your changes**:
   - Follow project-specific coding standards
   - Keep changes focused and minimal
   - Add comments where logic isn't self-evident
   - Update documentation if needed

3. **Run quality checks** (if applicable):

   ```bash
   make check  # or task check
   ```

4. **Commit your changes** (see [Commit Guidelines](#commit-guidelines))

5. **Push to your fork**:

   ```bash
   git push origin feat/my-feature
   ```

## Commit Guidelines

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```text
type(scope): description

Optional body with more details.
Lines should be ≤72 characters.
```

### Commit Message Rules

- **Title**: ≤50 characters
- **Body lines**: ≤72 characters
- **Type**: Use appropriate type for the change
- **Scope**: Use lowercase, descriptive scope
- **Description**: Clear, concise summary in imperative mood

### Commit Types

**User-facing changes**:

- `feat`: New feature for users
- `fix`: Bug fix for users

**Infrastructure changes** (use specific type, NOT `feat` or `fix`):

- `ci`: CI/CD changes
- `test`: Test changes
- `docs`: Documentation changes
- `build`: Build system changes
- `chore`: Maintenance tasks
- `refactor`: Code refactoring
- `style`: Code style changes
- `perf`: Performance improvements

### Examples

✅ **Good**:

```text
feat(api): add user authentication endpoint

ci(workflows): update release workflow

test(parser): add edge case tests
```

❌ **Bad**:

```text
fix(ci): update workflow  # Use ci(...) instead
feat(test): add helper    # Use test(...) instead
update code              # Missing type/scope
```

## Pull Request Process

### Creating a Pull Request

1. **Ensure your branch is up to date**:

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run quality checks** (if applicable)

3. **Push your changes**:

   ```bash
   git push origin feat/my-feature
   ```

4. **Create PR** using semantic title:

   ```bash
   gh pr create --title "feat(scope): description" --body "..."
   ```

### PR Title Format

Use same format as commit messages:

```text
type(scope): description
```

### PR Guidelines

- Keep PRs focused on a single concern
- Link related issues using `Fixes #123` or `Relates to #456`
- Respond to review comments promptly
- Update PR based on feedback
- Ensure all CI checks pass

## Getting Help

- **Issues**: Open an issue in the relevant repository
- **Discussions**: Use GitHub Discussions if available

## License

By contributing, you agree that your contributions will be licensed under the project's license.
