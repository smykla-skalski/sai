# Refactoring catalog, smell taxonomy, and safety discipline

Shared technical reference for the refactor-council orchestrator and personas. Used to name findings precisely (smell -> refactoring) and to enforce the safety discipline in the plan.

## Code-smell taxonomy (five families)

Name the smell, then name the cure. (Fowler/Beck taxonomy, as organized by refactoring.guru / SourceMaking.)

- **Bloaters** — Long Method/Function · Large Class · Primitive Obsession · Long Parameter List · Data Clumps.
- **Object-Orientation Abusers** — Switch Statements / Repeated Switches · Temporary Field · Refused Bequest · Alternative Classes with Different Interfaces.
- **Change Preventers** — Divergent Change (one class changes for many reasons) · Shotgun Surgery (one change touches many classes) · Parallel Inheritance Hierarchies.
- **Dispensables** — Duplicated Code · Lazy Class/Element · Data Class · Dead Code · Speculative Generality · Comments (as deodorant).
- **Couplers** — Feature Envy · Inappropriate Intimacy / Insider Trading · Message Chains · Middle Man.
- Modern additions (Fowler 2nd ed.) — Mysterious Name · Global Data · Mutable Data · Loops.

## Refactoring catalog (by family)

**Composing methods:** Extract/Inline Function · Extract/Inline Variable · Replace Temp with Query · Split Temporary Variable · Replace Method with Method Object · Substitute Algorithm · Split Phase.
**Moving features:** Move Function/Field · Extract/Inline Class · Hide Delegate · Remove Middle Man · Introduce Foreign Method / Local Extension.
**Organizing data:** Encapsulate Variable/Record/Collection · Replace Primitive with Object · Replace Magic Literal with Constant · Replace Type Code with Subclasses/State-Strategy · Change Value/Reference.
**Simplifying conditionals:** Decompose Conditional · Consolidate Conditional · Replace Nested Conditional with Guard Clauses · Replace Conditional with Polymorphism · Introduce Special Case / Null Object · Introduce Assertion.
**Simplifying calls:** Change Function Declaration (rename/reorder params) · Separate Query from Modifier · Parameterize Function · Remove Flag Argument · Preserve Whole Object · Introduce Parameter Object · Replace Constructor with Factory Function · Replace Error Code with Exception.
**Generalization:** Pull Up / Push Down Method/Field · Extract Superclass/Subclass/Interface · Collapse Hierarchy · Form Template Method · Replace Inheritance with Delegation.
**Architectural / big:** Tease Apart Inheritance · Separate Domain from Presentation · Extract Hierarchy · **Strangler Fig** · **Branch by Abstraction**.

## Refactoring to patterns (Kerievsky)

Refactor *to*, *towards*, and *away from* patterns — patterns are destinations you reach when real forces justify them, not up-front design. "Over-engineering: making code more flexible than it needs to be... if you happen to be a psychic." Under-engineering is more common. Key moves: Compose Method (intention-revealing steps at one level of abstraction) · Replace Conditional Logic with Strategy · Move Embellishment to Decorator · Replace State-Altering Conditionals with State · Replace Conditional Dispatcher with Command · Introduce Null Object · **Inline Singleton** (refactoring *away from* a pattern).

## Safety discipline (enforce this in the plan)

1. **Behavior preservation is the definition.** Refactoring changes internal structure without changing observable behavior. Refactoring *preserves bugs*; fixing a bug is not refactoring. A "refactoring" that changes behavior is mislabeled rework (Fowler's Malapropism).
2. **Self-testing code is the precondition.** Comprehensive automated tests are what verify behavior was preserved. No test net -> the first step is to build one, not to refactor.
3. **Characterization / golden-master tests** pin the *actual current* behavior of untested legacy code before you touch it (Feathers). Approve the current output, then refactor against it.
4. **Small steps, system always green.** Tiny change -> run tests -> commit when green -> repeat. Each step too small to be worth doing alone; that smallness is the safety.
5. **Two hats.** Never mix a structural change with a behavioral change in one commit/PR (Beck/Fowler). Reviewers must be able to verify "structure only, behavior unchanged" at a glance.
6. **Strangler Fig / Branch by Abstraction** for large-scale change — keep the system shippable on mainline throughout; avoid the big-bang rewrite and long-lived broken branches.
7. **Mikado Method** for tangled prerequisite changes — attempt naively, record prerequisites, revert to green, execute leaves first.
8. **Automated (IDE) refactorings** (Rename, Extract Function) are semantics-preserving and need less test validation than manual edits; prefer them where available.

## The DRY / abstraction tension (hold both sides)

- **DRY** (Hunt & Thomas): "Every piece of *knowledge* must have a single, unambiguous, authoritative representation." DRY is about knowledge, not text — two identical-looking blocks encoding *different* knowledge are not a violation.
- **Rule of Three** (Don Roberts): don't abstract on the second occurrence; "three strikes and you refactor."
- **"Duplication is far cheaper than the wrong abstraction"** (Metz): premature DRY breeds an abstraction that drowns in parameters and conditionals; the fix is to re-inline and re-extract.
- **AHA — Avoid Hasty Abstractions** (Kent C. Dodds): "optimize for change first"; don't abstract on first sight of duplication, don't refuse forever — wait for the pattern to emerge.

## Anti-patterns (the adversary watches for these)

- Refactoring without tests · big-bang rewrite mislabeled as "refactoring" · structure + behavior mixed in one commit · scope creep / gold-plating (a refactoring spreading across dozens of files) · speculative generality (flexibility for needs that may never arrive) · refactoring cold code the history shows no one touches.

## Where to refactor (Tornhill)

Prioritize **hotspots** (complexity x change frequency) over prettiness; surface **change/temporal coupling** (files that change together); don't spend effort on cold code. "A software design is good if it supports the kind of changes we do to the code."
