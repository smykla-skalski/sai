# Contents

1. [The problem](#the-problem)
2. [Signs of flat writing](#signs-of-flat-writing)
3. [Keep the author's voice](#keep-the-authors-voice)
4. [Match the medium](#match-the-medium)
5. [What voice is not](#what-voice-is-not)
6. [Before and after](#before-and-after)

---

## The problem

Removing AI patterns can leave text that is clean but flat: every sentence the same shape, every document in the same polished corporate register. Voice fixes that. Voice is the author's own way of writing and the shape the medium expects. It is not personality you add.

## Signs of flat writing

- Every sentence has the same length and structure
- Every paragraph or bullet follows the same mould ("First... Second... Third...")
- One neutral register everywhere, so a Slack reply sounds like a press release
- Stiff phrasing where the medium uses contractions ("We are unable to proceed at this time")
- Vague claims while the useful facts (owner, date, ticket, number) sit buried later in the text

## Keep the author's voice

**Keep what is already theirs.** Contractions, first person, humor, opinions, idioms and a team's usual phrasing stay. Do not sand them into neutral prose, and do not delete normal contractions.

**Use the medium's normal register.** Contractions are fine wherever the medium allows them. "We can't ship this yet" is better than "We are unable to proceed at this time" in Slack, a PR or a commit body.

**Vary rhythm by meaning.** A short sentence for the verdict, a longer one when the reasoning needs it. Do not enforce a length or a quota.

**Bring the useful facts forward.** If the source names an owner, a date, a ticket or a number, put it where the reader sees it first.

**Say uncertainty the way the source does, precisely.** "Untested above 20k RPS" beats "this should be robust". Never invent the uncertainty or the evidence.

**Keep the jargon the audience uses.** "Redis" beats "a data storage intermediary".

## Match the medium

| Medium | Shape | Example |
| :-- | :-- | :-- |
| Commit message | imperative subject that says what changed, then why | "fix(pool): stop Acquire deadlock under load" |
| PR description | problem, then what changed and why | "Release could block forever. It now times out after 30s." |
| Slack reply | answer, then reason or blocker, then next action | "Yes. CI is green, merging after stand-up." |
| Announcement | change, who it affects, when, what they must do | "VPN login moves to SSO on 3 Nov. Contractors must enroll by Friday." |
| Changelog or release notes | one line per change, user-visible effect first | "Cold start drops from 1.8s to 0.9s." |
| Technical doc | claim, evidence, implication | "Retries cause duplicate writes. Keep them off for this endpoint." |
| RFC | problem, constraints, proposal, evidence, alternatives | "Proposal: cache signing keys for 5 min to remove one network hop." |
| ADR | context, decision, consequences | "Decision: Postgres advisory locks. Reason: locks must span workers." |

## What voice is not

- **Not added content.** Never add opinions, feelings, first person, humor, asides or tangents the source does not have. They change what the author says.
- **Not fake mistakes.** Never add typos, broken grammar, odd spacing or look-alike characters to seem human. Fix real mistakes instead.
- **Not a detector score.** The goal is text that works for its reader. Writing to fool an AI detector is the wrong target and does not work reliably.

## Before and after

**Before (pattern-free but flat, for a team Slack channel):**
> We are pleased to inform you that the migration to the new authentication service has been completed successfully. All users will be required to log in again. Legacy tokens will no longer be accepted going forward. Should you have any questions, please do not hesitate to reach out.

**After (same facts, Slack register, generic sign-off dropped):**
> The auth migration is done. Everyone has to log in again, and old tokens no longer work.
