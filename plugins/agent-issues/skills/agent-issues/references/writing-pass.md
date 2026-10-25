# Writing pass

Apply to every title and body before showing anything. The goal is text a maintainer reads easily and an agent reads unambiguously. Humanizing helps human reviewers; it has no measured effect on agent success. It runs after the cold-read review and keeps meaning unchanged, so the review findings still hold for the text that ships. If the pass touches an outcome, check or stop trigger beyond wording, treat the text as changed and re-run the self-check.

## Format rules

- One physical line per paragraph and per bullet. Never hard-wrap prose to a column width.
- Keep the template's headings and keep lists as lists.
- Backticks for commands, paths, symbols and identifiers.
- No decorative emoji, no bold-as-header, no horizontal rules.
- Present tense and active voice in the Problem. Imperative in titles.

## Use the sibling skills when present

- If the `humanize` skill is available, run it on the draft as the final pass, preserving every command, path and identifier exactly.
- Otherwise apply the checklist below. It is the fallback and the verification.

## Checklist

- Cut filler: "in order to", "it is important to note", "needs to be able to", "leverage", "utilize", "facilitate".
- Cut significance inflation and promotion: "crucial", "robust", "seamless", "comprehensive".
- Cut hedges that carry no information: "might potentially", "may possibly". If the doubt is real, say what is unknown and how to find out.
- Cut chatbot artifacts: "Here is", "I hope this helps", "Let me", closing summaries.
- Prefer concrete nouns and verbs to abstractions. "Returns 401" beats "handles the error appropriately".
- State the thing once. Delete the second section that restates the first.
- Replace vague quantifiers with numbers or remove them.
- Keep exact strings (error messages, flags, command output) exactly as they appear.

## Verification

After the pass, re-read the draft once and confirm:

- No outcome lost its check.
- No identifier, path or command changed.
- No unverified fact became a fact during rewriting.
- Meaning is unchanged. If a rewrite is unsure, keep the original wording.
