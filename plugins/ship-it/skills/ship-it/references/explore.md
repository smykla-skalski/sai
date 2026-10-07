# Exploring the target repository

Build the implementation map before editing anything.

- Read root `CLAUDE.md`, `AGENTS.md` and `CONTRIBUTING.md` when present. Follow nested instructions for files in their scope.
- Identify the default branch and repository-specific review, release and merge conventions.
- Identify the primary stack from manifests and lockfiles.
- Find the formatter, linter, type checker, test and build commands that cover the change.
- Locate the affected code, callers and existing behavior tests.
- Inspect recent related changes and open work when they can reveal ownership or duplication.

Do not turn exploration into implementation. Finish with a concise map of files, behavior, gates and unresolved product questions.
