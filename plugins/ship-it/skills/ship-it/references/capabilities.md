# Portable phase capability contract

The machine-readable contract is [capabilities.json](capabilities.json). It is authoritative for profile names, phase requirements, declared side effects, protected actions and the missing-capability response.

## Phase preflight

Before a phase's first declared side effect:

1. Read its contract entry and select its named profile, applying a matching `profile_overrides` entry when present.
2. Evaluate only requirements whose `when` condition applies.
3. Confirm every `all_of` capability and at least one capability in every `any_of` group.
4. Try the named portable fallback when the preferred mechanism is absent.
5. If a requirement remains unsatisfied, make no phase side effect. Return `STATUS: NEEDS_CAPABILITY` with `phase`, `profile`, `missing_requirement`, `attempted_fallbacks` and `required_user_action`, then stop.

Do not infer permission from a tool being visible. A harness without native profile enforcement must still restrict its own actions to the selected profile. Re-run preflight when a fix returns the workflow to an earlier phase or the harness changes.

Capability availability does not authorize a role route. The role-routing independence policy may reject `inline.review` even though the review profile permits it for an explicitly degraded run.

`filesystem.transient-write` permits ignored build products and isolated test data, never product-source edits. A test that cannot isolate its data needs explicit permission before it runs.

Contract conditions use boolean runtime facts: `github_source`, `jira_source`, `create_issue`, `coordinator`, `inspect_remote_work`, `sail`, `code_changed`, `review_gate_required`, `test_gate_required`, `github_issue_tracking`, and `owns_cleanup`. Gate-required facts come from the selected risk policy; other facts come from resolved task or harness state. Facts default to false, never a guess. An `all` condition requires every nested condition. Re-run preflight whenever a fact changes.

## Portable fallbacks

- `request-ticket-paste`: ask for the Jira summary, description and acceptance criteria as plain text; do not read or mutate another Jira site.
- `portable-review-fallback`: prefer an adversarial-review skill with independent workers, then a fresh generic subagent. Strict independence blocks when neither is available. A repository policy may authorize degraded inline passes outside Sail; Sail always requires a review subagent.
- `portable-test-fallback`: prefer the installed adversarial-test skill, then a fresh generic subagent. Outside Sail only, the active agent may run the mandate inline. Sail requires a test subagent and pauses without one.

A fallback satisfies the same workflow gate. It does not remove, rename or weaken the gate.

## Harness adapters

| Harness | Profile enforcement | Capability mapping |
| :-- | :-- | :-- |
| Claude Code | Select the narrowest tool and permission set before the phase. | `Read`, `Glob` and `Grep` satisfy reads; `Edit` and `Write` satisfy repository writes; `Bash` satisfies process and Git capabilities; `Agent` or installed skills satisfy gate capabilities. |
| Codex | Use the workspace sandbox for local profiles and request escalation only for the active requirement. | Filesystem and command tools satisfy local capabilities; `spawn_agent` satisfies subagent capabilities; authenticated `gh` satisfies GitHub, issue and merge capabilities. |
| OpenCode | Apply the matching permission policy and expose only tools needed by the active profile. | Read, edit, bash and task tools map to filesystem, process, Git and subagent capabilities; authenticated `gh` supplies remote capabilities. |
| Copilot CLI | Select registered tools and agents for the active profile. | Filesystem and shell tools supply local capabilities; registered adversary agents or portable inline fallbacks supply gates; authenticated `gh` supplies remote capabilities. |
| Sail | Select the profile before dispatch and verify the assigned worker and fresh gate workers can launch. | ACP filesystem, terminal and permission primitives supply local capabilities; Sail workers supply subagent capabilities; authenticated `gh` supplies remote capabilities. Missing worker or gate capability pauses the run. |

Provider-specific permission prompts may add restrictions. They never broaden the contract.

## Protected actions

Always ask before a protected action even when its broad capability appears in the active profile. The original shipping request authorizes normal scoped branch, edit, test, push, PR, review-reply, documented merge and issue-close actions; it does not authorize secrets access, production deployment, unrelated destructive changes or unknown operations.
