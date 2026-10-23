# Repository templates and issue forms

The repo's template is the container. The quality bar is the content. Fill every field the template defines and apply [issue-rules.md](issue-rules.md) inside the fields.

No study compares form-shaped issues with free text for agent implementers. This policy is judgment. One related result favors keeping structure: in a small-model ablation, removing section headers or flattening lists reduced solve rates even when no content changed. See [evidence.md](evidence.md).

## Detect

```bash
gh repo view --json issueTemplates
```

Also look under `.github/ISSUE_TEMPLATE/` for `*.md`, `*.yml` and `config.yml` (check `blank_issues_enabled`), and for a `.github/ISSUE_TEMPLATE.md` or `docs/` template. The `issueTemplates` field finds markdown templates regardless of where they live. Read the files; they are authoritative for every aspect they cover.

Pick the closest template to the user's intent. If none fits and blank issues are allowed, use the default shape from the issue rules. If blank issues are disabled, ask which template to use.

## Fill

1. **Keep the skeleton.** Keep every field, its label and its order. Never rename, delete or reorder fields; maintainers' triage and automation depend on them.
2. **Map the bar's elements onto the closest field.**

   | Element | Goes in |
   | :-- | :-- |
   | Problem, expected behavior | The description or "what happened / expected" field |
   | Runnable done-checks | The acceptance or expected field, as a list |
   | Non-goals, Do-not lines | "Additional context", or the field closest to scope |
   | Verified starting points | "Additional context" |
   | Stop-and-flag triggers | "Additional context" |

   If the template has no free-text field for an element, add one trailing `## Agent notes` section. Do not split one element across fields.
3. **Keep lists as lists** and keep the template's headings.
4. **Required fields and dropdowns.** Choose only from the offered options and never invent a label or an option. If you cannot fill a required field truthfully (a version, an environment), ask the user, or write `Unknown: <reason>` and list it in Open items. Do not fabricate, and do not leave it silently blank. A form with required fields is a hard contract; hold filing until each is resolved or visibly marked.
5. **Hunch fields.** A field that invites a guess ("Possible fix", "Suggested solution") gets the verified-or-omit rule: fill it only with a checked cause or a labelled hypothesis.
6. **Conflicts.** If a template demands something the rules forbid, such as a step-by-step plan, the template stays and the content is kept minimal. Tell the user in one line.
7. **Labels, types, assignees.** Set what the template's front matter or form sets. Otherwise leave them alone.

## Creating the issue

- Markdown templates: the issue body is the filled template. `gh issue create --template "<name>"` uses a template as starting text; passing your own `--body-file` is equivalent and keeps the exact text.
- YAML issue forms: GitHub's documentation says form responses are converted to markdown and added to the body, and does not give the heading format. Do not assume one. Find a recent issue in the repo that was created from the same form (`gh issue list --state all --limit 30 --json number,title,body`) and copy its body structure, including the heading style, for each field. If none exists, use `### <label>` headings in form order and say so in Open items.
- Created through `gh` or the API, an issue bypasses the web form's validation, so the skill itself must supply every required field.
