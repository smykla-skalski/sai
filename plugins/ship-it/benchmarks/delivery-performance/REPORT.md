# Ship-it delivery performance report

## Result

The controlled comparison passed all five cases for both contracts. The candidate made zero redundant approval requests and executed zero duplicate gates in the replayed-approval and unchanged-input cases. Both contracts detected the confirmed security defect, kept it blocking, and left the failed security criterion explicit. Both also blocked on the native fixture failure and named its untested criterion.

This run does not support a speedup claim. Each case has one sample per variant, candidate aggregate elapsed time was 30.5% higher, and the case-level timing moved in both directions.

## Controlled inputs

| Input | Baseline | Candidate |
| :-- | :-- | :-- |
| SAI revision | `913312e7b3580ae7ad3bc4f9a484072585deed87` | `41133043ec6fbde4da57bab57d5b77bb47e601ed` |
| Sail context revision | `226a561bd260eeb75102d0632855a139c0519154` | `ba97832ee25138cc4295806f522b6a96fa02b2c0` (through Sail issue #677) |
| Model | `gpt-5.6-sol` | `gpt-5.6-sol` |
| Reasoning effort | high | high |
| Adapter | Codex CLI 0.162.1, read-only | Codex CLI 0.162.1, read-only |
| Host | Darwin arm64, Python 3.12.14 | Darwin arm64, Python 3.12.14 |
| Samples | 1 per case | 1 per case |

The immutable baseline tar has SHA-256 `34e5cea99f80bb8529f6ce0dbb0ea5470c67aaee480c8c49c0945e73ea1c7c8d`. Both variants used the same five case definitions, acceptance criteria, output schema, prompt template, model settings, sandbox, and host. The contract path and source revision identify the variant under test.

## Timing

| Case | Baseline elapsed/active | Candidate elapsed/active | Change |
| :-- | --: | --: | --: |
| Documentation-only work | 40.332 s | 31.605 s | -21.6% |
| Ordinary fix with resumption | 33.703 s | 90.242 s | +167.8% |
| Confirmed security defect | 44.812 s | 53.243 s | +18.8% |
| Moving default branch | 44.541 s | 55.009 s | +23.5% |
| Native fixture failure | 35.265 s | 29.196 s | -17.2% |
| Aggregate | 198.653 s | 259.295 s | +30.5% |

Active time equals elapsed time because the simulation did not execute external waits. Workflow wait decisions have unknown duration and stay `null` in the machine report.

## Workflow measures

| Case | Wait count baseline/candidate | Repeated gates baseline/candidate | Redundant approvals baseline/candidate | User interruptions baseline/candidate | Peak workers baseline/candidate | Defect detected | Required blocker |
| :-- | --: | --: | --: | --: | --: | :-- | :-- |
| Documentation-only work | 2 / 2 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 2 | no / no | no / no |
| Ordinary fix with resumption | 2 / 2 | 0 / 0 | 0 / 0 | 1 / 1 | 2 / 2 | no / no | no / no |
| Confirmed security defect | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | yes / yes | yes / yes |
| Moving default branch | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 1 | 1 / 1 | no / no | no / no |
| Native fixture failure | 1 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | no / no | yes / yes |

The candidate reduced one reported workflow wait decision in the native-fixture case and reported one additional user interruption in the moving-default case. All required validation counters stayed at the baseline floor. The report does not convert wait decisions into time saved because no wait duration was measured.

## Measured improvements

- Documentation-only evaluation finished 8.727 seconds faster
- Native-fixture evaluation finished 6.069 seconds faster and removed one resource-queue wait decision while keeping the test blocked

## Measured regressions

- Ordinary-fix evaluation took 56.539 seconds longer
- Security-defect evaluation took 8.431 seconds longer while retaining detection and the delivery blocker
- Moving-default evaluation took 10.468 seconds longer and reported one additional user interruption
- Aggregate candidate elapsed time increased by 60.642 seconds
- Candidate input plus output tokens increased from 387,486 to 717,596 in these samples

The sample count is too small to separate contract effects from model variance. No speedup is claimed.

## Historical context

The four-day audit ending 2026-10-14 08:32 Europe/Warsaw observed 2,371 transcript files, 21 ship-it conversation trees, and 76 matched pull requests. The 49 task-to-merge samples had a 2h16 median and 24h29 p90; 58 pull-request-open-to-merge samples had a 1h49 median and 24h13 p90; draft creation had a 12-minute median. The audit also counted 12,739 agent waits, 8,325 inter-agent messages, 9,411 skill reads, 409 compactions, 16,602 guardian review completions, 11.1 guardian hours, 45 guardian denials, and 32 nonterminal checkpoints linked to merged pull requests.

Those observations are not controlled benchmark timings. Central ship-it telemetry recorded zero baseline events because collection was disabled, so this report does not use telemetry to reconstruct a baseline.

## Privacy

The committed cases are synthetic. The machine report contains stable case IDs, normalized decisions, counters, timings, digests, revisions, and tool versions. It contains no private transcript, prompt, source content, credential, raw tool output, local path, or environment variable.
