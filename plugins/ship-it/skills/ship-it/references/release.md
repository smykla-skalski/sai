# Repository release policy

Resolve one release policy after exploration and before validation. It controls hosted reviewers, required checks, merge execution, issue closure and branch cleanup without changing local review or test gates. Store the normalized result in the task checkpoint and use it for every PR-loop resume.

## Sources and precedence

Resolve policy from highest to lowest precedence:

1. `.sai/ship-it-release.json`, when present, supplies its explicit portable fields; omitted fields continue through the remaining sources.
2. Repository instructions such as `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md` and the pull-request template supply fields the structured file omits. A more local instruction wins over a parent instruction.
3. GitHub rulesets, default-branch protection and repository merge settings supply required approvals, named checks and allowed merge strategies. These platform requirements are always additive and cannot be weakened by a file or prose instruction.
4. [release-policy.json](release-policy.json) supplies every field still unresolved.

Reject invalid structured policy, contradictory sources at the same precedence, an instruction that conflicts with a platform requirement, or a merge mechanism that cannot satisfy branch protection. Do not guess. Block the checkpoint with one exact action, such as `Choose merge strategy merge or squash in .sai/ship-it-release.json` or `Ask @release-engineering to approve PR <url>`.

The bundled default is conservative: honor all GitHub-required approvals and checks, request no reviewer that the repository did not name, squash through GitHub, close GitHub sources with the PR keyword, and delete the remote task branch only after verified merge. This supports repositories with no hosted reviewer while never bypassing configured controls.

## Portable format

The optional repository file uses `schema_version: sai.ship-it.release-policy/v1`:

```json
{
  "schema_version": "sai.ship-it.release-policy/v1",
  "required_reviewers": [
    {
      "id": "security-approval",
      "kind": "human",
      "actor": "team:security",
      "requirement": "approval",
      "request": "team-reviewer",
      "request_target": "security"
    },
    {
      "id": "automated-review",
      "kind": "automated",
      "actor": "copilot-pull-request-reviewer[bot]",
      "requirement": "review",
      "request": "reviewer",
      "request_target": "copilot-pull-request-reviewer"
    }
  ],
  "required_checks": ["test", "lint"],
  "merge": {
    "method": "bot-comment",
    "strategy": "squash",
    "bot_comment": "squash"
  },
  "issue_closure": "pull-request-keyword",
  "branch_cleanup": "delete"
}
```

Only `schema_version` is required. At least one other top-level field must be present; omitted fields inherit from the next source in precedence order. A present `merge` object has all three merge fields. Validate every present value before merging sources, then validate the complete normalized result. Reviewer IDs, actors and check names are non-empty and unique. `kind` is `human|automated`; `requirement` is `review|approval`; and `request` is `reviewer|team-reviewer|automatic`. `request_target` is the exact GitHub login or team slug to request, and is null only for `automatic`. A `team-reviewer` actor starts with `team:`. `automatic` means the repository requests the reviewer itself; never send an extra request.

`merge.method` is `github|bot-comment`. `merge.strategy` is `merge|squash|rebase`. `bot-comment` requires one non-empty exact `bot_comment` and a cited repository instruction that explicitly binds that exact comment to the same strategy; reject an opaque or mismatched command. `github` requires null. Treat the comment as inert text passed through `gh pr comment --body`, never as a shell command. `issue_closure` is `pull-request-keyword|manual-after-merge|unchanged`; `branch_cleanup` is `delete|preserve`. Reject unknown fields and enums so typos cannot relax a release requirement.

Repository prose can express the same values. Normalize it into this shape and record the exact repository-relative instruction paths. A prose requirement that names Copilot, another automated reviewer, a person or a team becomes a reviewer entry; `no hosted review required` becomes an empty list. Never infer an empty list merely because no reviewer is currently requested.

## GitHub reconciliation

Before opening a PR, read repository-level policy:

- repository merge settings;
- all rulesets applying to the default branch;
- branch protection, including required approving-review count and named status checks;
- CODEOWNERS or required-team rules exposed by GitHub.

After the PR exists, and again immediately before merge, reconcile its live review requests, reviews, check runs, threads, head SHA and mergeability. PR-specific state never blocks initial policy resolution or PR creation.

Union named checks and reviewers from GitHub with the repository policy. When GitHub requires an approval count without naming actors, add synthetic reviewer entries `github-required-approval-1`, and so on, with `kind: human`, `actor: any-authorized-reviewer`, `requirement: approval`, `request: automatic` and `request_target: null`. A submitted approval can satisfy at most one synthetic entry. Dismissed, stale or changes-requested reviews do not satisfy approval requirements.

Persist a normalized checkpoint object:

```json
{
  "schemaVersion": 1,
  "sources": [".sai/ship-it-release.json", "github:rulesets"],
  "requiredReviewers": [],
  "requiredChecks": ["test"],
  "merge": {"method": "github", "strategy": "squash", "botComment": null},
  "issueClosure": "pull-request-keyword",
  "branchCleanup": "delete",
  "activatedFallbacks": [],
  "resolvedAt": "2026-01-01T00:00:00Z"
}
```

Sort and deduplicate sources, reviewers and checks; preserve reviewer semantics. `sources` always includes `bundled default` for defaulted fields and the applicable GitHub source names. `activatedFallbacks` is normally empty. Its only v1 entry is `{"gate":"hosted-review","fromMechanism":"copilot-review","mechanism":"human-review","reason":"copilot unavailable"}` after the legacy fallback actually activates; validate exact keys and enums, allow at most one entry, and reject it unless the normalized required reviewer is `any-authorized-reviewer`. Set `resolvedAt` after successful repository-level reconciliation, then refresh it after each successful live PR reconciliation. Any material policy change invalidates hosted-review and CI evidence and returns the workflow to the earliest affected gate.

Release requirements are gate floors. Add `hosted-review` to the selected risk gates when `requiredReviewers` is non-empty, and add `ci` when `requiredChecks` is non-empty or GitHub requires checks. A risk policy can add stricter validation but cannot remove a repository release requirement. Persist the final union in `risk.requiredGates` before creating evidence.

Apply the legacy `copilot-review` normalization from the risk contract before this union. Store its normalized reviewer and any activated `human-review` fallback in `releasePolicy.activatedFallbacks`, so resume never depends on remembering the legacy translation.

## Hosted review and checks

The risk gate `hosted-review` means satisfy every resolved reviewer entry; it does not mean Copilot. For `request: reviewer|team-reviewer`, pass `request_target` to the matching GitHub request field. For `automatic`, wait without sending a request. Match user and bot actors by exact GitHub login after normalizing the optional `[bot]` suffix; never assume the request target and review author use the same login. Satisfy `team:<slug>` only with a review from a current member verified through the GitHub team-membership API, and satisfy `any-authorized-reviewer` only when GitHub's protected-branch review decision counts that approval.

`requirement: review` needs a submitted non-pending review; a no-comment review counts. `requirement: approval` needs `APPROVED`. Resolve every non-outdated thread authored by a required reviewer after fixing or answering it. Never wait for optional Copilot review. Ignore its comments, quota failures and missing review unless repository policy makes them blocking. If policy explicitly requires Copilot, immediately activate its configured non-Copilot fallback or hard-stop with the exact policy action; do not poll Copilot. Mandatory human review remains authoritative.

The `ci` gate requires the union of policy checks and live platform-required checks on the exact PR head. A named check that is absent or pending is unsatisfied. Platform-reported success for unrelated or older SHAs does not count.

If any required reviewer or check remains unsatisfied for 30 minutes, including continuously requested or pending requirements, set the checkpoint to blocked and name the exact actor or check plus the human action needed. Never silently drop it or substitute another reviewer.

## Merge, closure and cleanup

For `github`, invoke `gh pr merge` with the resolved strategy and `--delete-branch` only when cleanup is `delete`. For `bot-comment`, post the exact `botComment`, wait for the bot, and diagnose its response; never call `gh pr merge` as a fallback. After either mechanism completes, verify the merge commit topology and resulting tree match the resolved `merge|squash|rebase` strategy before completion. A mismatch is a terminal release-policy failure with the PR URL and expected/actual strategy; never rewrite merged history. Protected-branch and merge-queue requirements remain authoritative. Stop with their exact requested approval, queue or administrator action instead of using admin or force options.

At PR creation, emit `Closes` only for `pull-request-keyword`; use non-closing `Refs` for the other policies. After GitHub confirms the merge, verify keyword closure, manually close only for `manual-after-merge`, or leave the source unchanged for `unchanged`. Delete a still-present remote task branch only for `delete`; preserve it otherwise. Record actual closure and cleanup in the completion outcome.
