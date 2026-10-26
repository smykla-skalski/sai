# Simplicity rules

These rules come from two research reports: one on simplifying any system (software, products, work processes, policy) and one on simplicity for new software projects. Their main sources are Brooks (essential and accidental complexity), Ashby (requisite variety), Simon and Parnas (near-decomposability, information hiding), Meadows (leverage points), Sweller (cognitive load), the UK government design principles, Fowler (YAGNI, Monolith First), Google SRE (end-to-end simplicity) and DORA.

## Core definition

A system is simpler when it reaches the required outcomes, under the required constraints and conditions, with less cognitive, structural, coordination, operational and change burden. The goal is the minimum adequate system, not the minimum system. Work can fail in two directions:

- Overbuilt: elements, boundaries, options or steps that no current requirement needs.
- Oversimplified: variety, checks or structure removed or skipped that a requirement, failure mode or real case needs. A system without required authentication, recovery, data integrity or accessibility is incomplete, not simple.

Audit both directions. Simplification is done when any further removal would materially worsen an outcome, a guardrail, adaptability or the ability to handle real variety.

## Applicability

- Groups P, M, N, R, B, I, V, D and E apply to any work.
- Group G applies only to a new software project, a new service or component, or an initial architecture.
- Groups T and K apply to software. For a process or policy, read tests as pilots and outcome checks, and docs as the written procedure.
- Judge each rule against what the work must do now. Skip a rule the work cannot break.

## P - Purpose and constraints

| ID | Rule | Broken when |
| --- | --- | --- |
| P1 | State the outcome before the mechanism: who it is for and what it enables, in one sentence that names no solution | The work starts from a mechanism ("add a workflow engine", "use microservices") and no outcome is stated or plainly implied |
| P2 | Define one or two observable measures of success | Nobody can say what result shows that the work succeeded |
| P3 | Make hard constraints explicit: security, privacy, compliance, safety, accessibility, reliability, latency or throughput, compatibility | Constraints are absent or vague ("must scale"), or exist only as a side effect of the design |
| P4 | Write explicit non-goals | Scope has no edge, and the work tries to handle every future case |
| P5 | Know the users, operators and operating conditions | The design assumes one standard user or ignores who runs it |

## M - Measure the whole system

| ID | Rule | Broken when |
| --- | --- | --- |
| M1 | Record a baseline before a change: steps, decisions, handoffs, interfaces, exceptions, time, errors or rework, cost, workload | A simplification claim has no before-data |
| M2 | Pick the measures before the change and pair each burden measure with an outcome guardrail | Measures are picked after the fact, or a burden measure has no guardrail |
| M3 | No count alone proves simplicity: lines, parts, services, rules, screens and steps can be gamed | The claim rests only on a count ("5 services down to 1", "200 fewer lines") |
| M4 | Measure total burden across all actors: users, operators, other teams, the next maintainer | Work moves to someone else: users must transform data, operators get a manual step, a smaller API pushes interpretation onto every caller |
| M5 | Call a trade-off a trade-off: a clear win needs lower burden and every guardrail still acceptable | One burden falls, another rises, and the work calls it a simplification |
| M6 | Separate the levels of evidence: objects removed, burden plausibly reduced, outcomes shown; forecasts versus results | Projected savings or deleted counts are presented as proven outcomes |
| M7 | Check the result again after people adapt to it | No plan to check the result once users and operators adjust |

## N - Necessity and the admission test

| ID | Rule | Broken when |
| --- | --- | --- |
| N1 | Each element names what fails if it is removed: a requirement, disturbance, failure mode or user outcome | The only reason for an element is blank, "might be useful", "for flexibility" or "best practice" |
| N2 | Admit new complexity only for a current reason: (a) a validated current requirement, (b) an invariant such as correctness, security, privacy or compliance, (c) a measurement that shows the current design misses a defined reliability, latency, throughput or capacity objective, (d) a stable ownership or deployment boundary that solves a demonstrated coordination problem, (e) an external compatibility contract | A cache, queue, service, framework, datastore, abstraction or option rests on "we will need it", "big companies do it", "it must scale infinitely", "the framework makes it easy" or a pattern name |
| N3 | Try the current design and a smaller change first | No sign that the current system or a smaller change (an index, a query fix, a direct call) was considered |
| N4 | Give each admitted addition an owner, an operational cost, a rollback path and a review or removal trigger: one row in a complexity ledger | A new component has none of these |
| N5 | Defer speculative complexity and record the trigger that would make it real, unless a later retrofit is demonstrably prohibitive | Extension points, plugin systems, generic frameworks, config for values that never change, or multi-tenant or multi-region support with no requirement |
| N6 | A new abstraction needs two real beneficiaries or repeated real variants | An interface with one implementation, a factory for one product, a generic base class, a reusable layer before the second case exists |
| N7 | For an uncertain need, instrument or experiment instead of charging every user the cost | A hypothetical need ships to everyone as permanent structure |

## R - Reduce in a strong order

| ID | Rule | Broken when |
| --- | --- | --- |
| R1 | Reduce in this order: eliminate, combine, default, standardize, encapsulate, automate, optimize | Automation, caching, tuning or new tooling is applied to work that could be deleted or merged |
| R2 | Keep one authority for each datum, rule or decision, unless the redundancy is deliberate and its consistency mechanism is understood | The same data or rule lives in two places, is entered twice by hand, or needs manual reconciliation; new code repeats a helper, type or pattern that already exists in the codebase |
| R3 | Turn repeated safe decisions into defaults: one standard default per concern, and a choice only when two real use cases need materially different behavior | People must choose among options every time; several frameworks or modes serve one concern |
| R4 | Fix the rule that generates exceptions before you add a branch, unless the exception is irreducible real-world variety | Special cases pile up to compensate for another broken rule |
| R5 | Question a process before you automate it: would you keep this process if automation were not available? | A 14-step manual flow becomes a 14-step automated flow |
| R6 | Optimize only after a measurement and after simpler fixes | A performance mechanism exists with no measured problem |

## B - Boundaries and structure

| ID | Rule | Broken when |
| --- | --- | --- |
| B1 | Divide by what can change independently, and hide change-prone decisions behind stable interfaces, not by processing step, category or org chart | Modules mirror workflow stages or type-named layers, and one change touches many of them |
| B2 | Each boundary (module, service, team, queue, process stage) must buy isolation, ownership, security or independent scaling worth its interface cost | A boundary exists for history, fashion or symmetry |
| B3 | A distributed boundary must earn its cost: network calls, serialization, partial failure, versioning, data movement | Network services, a message broker or an event bus do work that one process can do; services always deploy together |
| B4 | Keep interactions narrow and hierarchical: total complexity includes the interactions, not only the parts | Everything can call everything; cycles, shared mutable state, chatty cross-component calls |
| B5 | Pass the change test: a part can change internally without forcing unrelated parts to understand the change | Callers depend on internal details; abstractions leak |
| B6 | One deployable can still be modular, with clear internal modules and one-directional dependencies | One unit with no internal boundaries, or a split into separate units only to get boundaries that modules would give |
| B7 | Prefer incremental simplification to a big rewrite, unless the rewrite wins on the total transition cost: migration, coexistence, feature parity | A rewrite is chosen "to start clean" with no comparison |

## I - Interfaces and surface

| ID | Rule | Broken when |
| --- | --- | --- |
| I1 | Keep the public surface minimal: endpoints, events, schemas, flags, CLI options, environment variables, plugin hooks and deployables are all compatibility commitments | New public options, endpoints or exports that no current consumer needs |
| I2 | Simplify interfaces more than internals, and put complexity where people or components can absorb it most cheaply and safely, with its new cost stated | Internal complexity is exposed to every user, or complexity moves inward with its cost hidden |
| I3 | Use structured interfaces with real semantics | Key-value bags, a `doEverything()` call, or parameter explosion: many flags or modes that hide several concepts |
| I4 | Use standard semantics instead of home-grown ones: HTTP (RFC 9110), problem details (RFC 9457), OpenAPI, Semantic Versioning for library APIs | A custom error format, status convention or versioning scheme where a standard fits |
| I5 | Make the common path obvious; put rare complexity behind progressive disclosure, but keep an explicit path to less common needs and show what a user must see to decide | Rare cases force every user through extra steps, or a needed function is removed or hidden with no path to it |
| I6 | A minimal appearance must not cost discoverability | Controls are removed so that users must memorize gestures or search through menus |

## V - Requisite variety (do not oversimplify)

| ID | Rule | Broken when |
| --- | --- | --- |
| V1 | Keep the distinctions and responses that materially different cases need; merge two rules only when their cases are equivalent for outcome and risk | Two different situations are collapsed into one path, script or rule |
| V2 | Do not remove checks, redundancy, recovery paths, validation, authentication, audit or data-integrity controls only to reduce a count | A safeguard is deleted "to simplify" with no evidence that it is unnecessary |
| V3 | Standardization keeps a working route for legitimate edge cases, including accessibility and uncommon circumstances | One standard user; disabled users or rare valid cases have no route |
| V4 | An abstraction compresses a stable pattern; it does not hide distinctions that callers must later find again | The abstraction leaks through flags, exceptions or undocumented behavior |
| V5 | Challenge essential complexity only by changing the requirement | Real domain rules, failure modes or compatibility duties are abstracted away or ignored |
| V6 | Fit the time horizon: a long-lived or safety-critical system can justify docs, redundancy and diagnostics that a prototype does not need | Prototype-level rigor on a long-lived critical system, or platform-level process on a throwaway prototype |

## D - Delivery in small steps

| ID | Rule | Broken when |
| --- | --- | --- |
| D1 | Build the smallest coherent version first: one real end-to-end path with an entry point, a business rule, persistence if needed, a deployment path, telemetry and one realistic test | Horizontal layers come first, infrastructure exists before any working path, or many features exist before one works end to end |
| D2 | Change in small steps with a return path; an irreversible simplification needs stronger evidence or a pilot | A large irreversible change has no rollback or pilot |
| D3 | Add one complexity increment at a time and check that it pays | A cache, a queue and a search cluster arrive together |
| D4 | Remove the old path once the new one meets its requirements | Old and new paths coexist with no removal plan |
| D5 | Stress-test the simplification: peak load, bad input, partial failure, novice users, accessibility, conflicting cases, regulatory exceptions | Only the happy path was considered |

## G - New software projects

| ID | Rule | Broken when |
| --- | --- | --- |
| G1 | Start from a one-page brief: outcome, evidence of success, what is required now, constraints and invariants, non-goals, the simplest first release as one user journey, and triggers to revisit the architecture | Architecture or scaffolding is chosen before any brief |
| G2 | Default to a boring topology: one repository, one deployable modular monolith, one primary transactional datastore, synchronous in-process module calls, a small public API, tests, structured logs and a simple deployment pipeline | The work exceeds the default budget below without an N2 reason |
| G3 | Advance the architecture one stage at a time, and only on a trigger: prototype; modular monolith with one datastore; stronger automation, tests and SLOs; one selective addition; extraction of one stable boundary; advanced distribution | Stages are skipped: microservices, multi-region or a platform before real use and data |
| G4 | Once the application deploys, follow the Twelve-Factor basics: explicit dependencies, config outside the code, separate build, release and run, dev/prod parity | Hidden system dependencies, config compiled into the code, environments that differ |
| G5 | Choose a conventional stack, and size governance to the real risk and team size | Architecture or process copied from a large company, or heavy branch rules and review gates on a one-person prototype |
| G6 | Keep the request path direct: parse and validate, use case, domain rule, repository or integration, explicit result | A mediator, command bus, event bus, generic repository, plugin engine or several mapping layers with no demonstrated problem |

Default budget at inception. Exceed it only for an N2 reason:

| Item | Default | Evidence that justifies more |
| --- | --- | --- |
| Deployables | 1 | Independent scaling, isolation, availability or ownership has become demonstrably valuable |
| Primary transactional datastores | 1 | A workload needs storage semantics that the current store cannot reasonably give |
| Internal network calls | 0 | A justified service boundary |
| Message brokers | 0 | A real asynchronous workflow, buffering, fan-out or failure-decoupling need |
| Application caches | 0 | A measured latency or load problem remains after database and query fixes |
| Search infrastructure | 0 | Required retrieval exceeds what the primary store can do |
| Feature flags | Only with an owner and a lifecycle | A real rollout, experiment or operational need; remove the flag when it is done |
| Frameworks per concern | 1 | A second one solves a materially different, demonstrated need |
| Multi-region active/active | 0 | An explicit continuity, latency, availability or regulatory requirement |

## T - Tests and telemetry

| ID | Rule | Broken when |
| --- | --- | --- |
| T1 | Keep the system safe to change: automated tests protect behavior so refactoring stays cheap (deferring design without that ability makes the system brittle) | Business rules have no tests, so every change is risky |
| T2 | Fit the test portfolio: focused tests for business rules, integration tests with real components at consequential boundaries, a few end-to-end tests for critical journeys, high-signal static checks | Every case runs through the browser, or only unit tests exist where a real boundary is the risk |
| T3 | Test behavior, not implementation interactions; do not mock the component that you need confidence in | Mock-heavy tests break on refactors, or pass against a fake that differs from the real dependency |
| T4 | Value confidence per unit of maintenance, not test count | Tests of trivial framework behavior, large redundant suites, huge custom lint rule sets |
| T5 | Keep CI simple: format and lint, type check, small tests, integration tests, build, smoke test, deploy | A large compatibility matrix, a staging topology or many gates with no risk that needs them |
| T6 | Start observability small but early: structured logs with the deployed version; request volume, error rate, latency and saturation; one to a few SLOs; page only on user impact; add traces when requests cross process boundaries | No signals at all, or alerts on every metric, or a tracing estate for one process |
| T7 | Before production use, have a rollback path, backups and recovery where state matters, and a runbook | A stateful service has no backup or restore path, or no way to roll back |

## K - Knowledge and docs

| ID | Rule | Broken when |
| --- | --- | --- |
| K1 | Keep a few living docs: a README (what, why, how to run and test), an architecture page with one current diagram, decisions with reasons and reconsider triggers, a runbook, a contribution path | No docs for the common path, or an encyclopedia that goes stale |
| K2 | Record each consequential decision, its reason and what would cause you to reconsider it; give provisional choices a review trigger | Important choices have no recorded reason; an experiment became infrastructure by inertia |
| K3 | A new engineer can build an accurate mental model and do routine work without tribal knowledge; the architecture can be explained in minutes | Specialist-only operations, or steps that live only in one person's head |
| K4 | Keep project instructions short and remove obsolete options | Instructions list dead options or grow without pruning |

## E - Eliminate and govern

| ID | Rule | Broken when |
| --- | --- | --- |
| E1 | Delete obsolete code, flags, dependencies, config, layers and services; source control makes deletion reversible, and sunk cost is not a reason to keep anything | Dead code kept "just in case", unused dependencies, commented-out blocks, a subsystem kept because "we spent weeks on it" |
| E2 | Each temporary flag has an owner and a removal trigger | Long-lived flags preserve obsolete paths |
| E3 | Run a recurring simplicity review that asks what can now disappear | No mechanism to prune |
| E4 | Keep governance small: the complexity ledger lists complexity additions only, not every decision | The governance process is itself accidental complexity |
| E5 | Review each change for concepts, config or public surface beyond what its requirement needs | A change adds more than its requirement asks for |
| E6 | Watch trends, not hard limits: system surface, decision surface, dependency structure, time to explain, and the DORA delivery metrics (lead time, deployment frequency, change failure rate, recovery time, rework rate). The warning sign is more surface with slower change, more instability and worse understandability | A universal limit ("no more than N services") is treated as science, or there is no signal at all |

## Severity

- High: breaks a hard constraint or safeguard (for example V2 or V3), or adds a burden that dominates the work, such as a distributed boundary with no N2 reason.
- Medium: a real recurring burden or risk with a clear smaller alternative.
- Low: a local improvement that is cheap to fix or safe to defer.

## Boundary questions

For a boundary under question (B2, B5, I1), check its purpose (why it exists), its contract (the smallest information that must cross it), its owner, the internal details that callers rely on, its behavior when the other side fails, and whether either side can change internally without forcing a change on the other.
