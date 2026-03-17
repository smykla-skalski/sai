---
name: slug
description: Generate a semantic slug for the current session's work and copy the `/rename type/slug` command to clipboard. Use when the user asks what to call this session, wants a branch-style name for the work done, or asks to rename the conversation.
argument-hint: ""
allowed-tools: Bash
user-invocable: true
model: haiku
---

<!-- justify: CF-side-effect Bash is used only for pbcopy to fill clipboard at user request - intentional, not infrastructure-modifying -->

Review the **entire conversation from start to finish** and generate a semantic slug that captures all the meaningful work done across the session - not just the last task.

## Slug format

`<type>/<slug>` where:

- **Type**: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, or `perf`
- **Slug**: 2-4 words in kebab-case, specific to the work done

## Steps

1. Scan the full conversation from the first message to the last - identify the core work across all tasks (what was built, fixed, changed, or researched). If the session covered multiple things, pick the dominant theme or the one that best characterizes the session as a whole.
2. Pick the type that best fits. When in doubt: `feat` for new things, `fix` for bugs, `chore` for maintenance/config, `docs` for documentation, `refactor` for restructuring, `test` for test work.
3. Write a short kebab-case slug (2-4 words, no filler like "update" or "changes").
4. Run: `printf '/rename <type>/<slug>' | pbcopy`
5. Reply with exactly one line: `Copied: /rename <type>/<slug>`

Copy and confirm on one line. Nothing else.

## When not to use

Skip this skill when the session has no meaningful work (e.g., just questions and answers with no code changes, config edits, or decisions made). If the session covered two completely unrelated topics with no dominant theme, pick the one with the most substantive work.

## Error handling

If `pbcopy` is unavailable (non-macOS), fall back to `xclip -selection clipboard` on Linux. If neither is available, output the rename command directly in chat instead of copying.

## Examples

<example>
Session: added JWT-based login and refresh token handling
Slug: `feat/jwt-auth`
Copied: `/rename feat/jwt-auth`
</example>

<example>
Session: debugged nil pointer panic in user service under concurrent load
Slug: `fix/user-nil-pointer`
Copied: `/rename fix/user-nil-pointer`
</example>

<example>
Session: extracted shared parsing helpers out of three checker scripts into a common library
Slug: `refactor/shared-checker-helpers`
Copied: `/rename refactor/shared-checker-helpers`
</example>
