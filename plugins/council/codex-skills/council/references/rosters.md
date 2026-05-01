# Council Rosters

Use this file only to choose native Codex reviewer-agent slugs.

## Mode Rosters

- `core-eng`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `muratori-perf-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, `chin-strategy-advisor`
- `core-ux`: `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `krug-usability-reviewer`, `watson-a11y-reviewer`, `tognazzini-fpid-reviewer`, `tufte-density-reviewer`
- `core-mix`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `hebert-resilience-reviewer`, `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `watson-a11y-reviewer`

## Selection Hints

- Bias correction/default: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `muratori-perf-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, `chin-strategy-advisor`
- Type/test/domain/spec/functional/IaC/perf/AI/CI: `king-type-reviewer`, `hughes-pbt-advisor`, `evans-ddd-reviewer`, `fp-structure-reviewer`, `wayne-spec-advisor`, `iac-craft-reviewer`, `test-architect`, `gregg-perf-reviewer`, `ai-quality-advisor`, `cicd-build-advisor`
- UX/platform/a11y/motion/data/macOS: `eidhof-swiftui-reviewer`, `ash-cocoa-runtime-reviewer`, `simmons-mac-craft-reviewer`, `norman-affordance-reviewer`, `tognazzini-fpid-reviewer`, `krug-usability-reviewer`, `nielsen-heuristics-reviewer`, `watson-a11y-reviewer`, `head-motion-reviewer`, `siracusa-mac-critic`, `tufte-density-reviewer`

## Shortcut Map

- Over-engineering/deletability/perf: antirez, tef, muratori.
- Failure modes/ops/systems/process: hebert, meadows, chin, cicd-build.
- Testing/properties/boundaries: test-architect, hughes, king.
- Domain modeling/functional structure/spec: evans, fp-structure, wayne.
- Infra/deploy/fleet performance: iac-craft, gregg, hebert, cicd-build.
- LLM/prompt/eval/sandboxing: ai-quality, chin, hebert.
- SwiftUI/Cocoa/macOS craft: eidhof, ash, simmons, siracusa, tognazzini.
- Interaction/usability/a11y: norman, krug, nielsen, watson, tognazzini.
- Motion/dashboard density: head, tufte, muratori, antirez, tef.

For `auto`, select exactly 6 reviewers most likely to change the recommendation and include at least one bias-correction reviewer unless the task is narrowly specialist.
