# KubeCon CFP Eval Cases

Test cases for validating skill output quality.

## Case 1: Strong production story

**Input:** `/kubecon-cfp "migrated 500 services from Istio to Cilium service mesh at fintech company" --track Connectivity`

**Expected:**
- Title includes scale number (500) and specific tech (Cilium)
- Abstract uses third person, ≤1,300 chars
- Benefits section 1,000-1,500 chars, distinct from abstract
- Track: Connectivity confirmed
- Topic trend: Hot (eBPF/Cilium)
- At least 3 title options reference migration/journey pattern

## Case 2: Vague topic rejection

**Input:** `/kubecon-cfp "Kubernetes best practices"`

**Expected:**
- Phase 2 flags: generic topic, high saturation, no production signal
- Phase 3 pushes back hard for specifics
- Does not proceed to title generation without concrete details

## Case 3: Review mode

**Input:** `/kubecon-cfp --review` (with draft abstract using first person "I will present...")

**Expected:**
- Flags first-person language violation
- Scores Content/Originality/Relevance/Speaker dimensions
- Runs pre-submit checklist
- Provides specific rewrite suggestions

## Case 4: Lightning talk format

**Input:** `/kubecon-cfp "DRA for GPU scheduling" --track AI --format lightning`

**Expected:**
- Titles shorter and punchier than session format
- Abstract still ≤1,300 chars but tighter
- Topic trend: Hot (DRA for GPUs)
- Mentions lightning talk as entry point for first-time speakers

## Case 5: Character limit enforcement

**Input:** Abstract draft at 1,450 chars

**Expected:**
- Flags over-limit (1,450 > 1,300)
- Suggests specific cuts: adjectives, hedging, merged sentences
- Rewritten version ≤1,300 chars with preserved meaning
