# KUP description rules

How to write Polish descriptions that support the 50% KUP (Koszty Uzyskania Przychodu) deduction for creative IT work.

## Core idea

Each description presents the PR as a **utwór**, an individual and original creation under Polish copyright law, in one of two qualifying categories:

- **programy komputerowe** - computer programs
- **działalność badawczo-rozwojowa** - research and development

## Rules

1. Describe what was created or designed, not what was fixed or changed.
2. Name the concrete work product: the algorithm, architecture, mechanism, logic or system that was authored.
3. One or two clauses of natural Polish, light on jargon.
4. Open with a verb of creative authorship, for example opracowanie, zaprojektowanie, stworzenie, opracowanie koncepcji, zaprojektowanie mechanizmu, zbudowanie, zaprojektowanie i wdrożenie. Vary them across the month.
5. Never use naprawienie, poprawka, aktualizacja or zmiana. They signal mechanical work.
6. No trailing period. Descriptions are titles, not sentences.

## What does not qualify

- Administrative or organizational tasks
- Mechanical, repetitive or template-based work (prace odtwórcze)
- Project management without a creative contribution

## Dependency-only months

When every PR in a month is a dependency update, the creative work is the analysis and the decisions: designing the upgrade strategy, analyzing compatibility between versions, verifying integration stability. Describe that, not the version bump.

## Examples

PR: "implement rate limiting for API endpoints"
Description: "Stworzenie systemu ograniczania liczby zapytań do interfejsu programistycznego z konfiguracją progów i strategii odrzucania"

PR: "fix connection leak in health check"
Description: "Opracowanie mechanizmu zarządzania cyklem życia połączeń w module diagnostyki zdrowia usług"

PR: "update envoy to v1.30" (dependency-only month)
Description: "Zaprojektowanie migracji warstwy proxy do nowej wersji z weryfikacją zgodności konfiguracji i stabilności komunikacji"

PR: "simplify mesh gateway routing"
Description: "Zaprojektowanie uproszczonej logiki routingu dla bramy mesh"
