# Council Persona Registry

Twenty-seven personas. Six core (bias-correction default), ten extended-domain (type/test/DDD/spec/IaC/perf/AI/CICD lenses), and eleven extended UX/platform (SwiftUI/Cocoa/macOS-craft/UX/a11y/motion/critic/density). Each built from primary public sources of the named thinker. Full deep dossiers (with sourced quotes and URLs) sit alongside this file.

## Core (6) - bias correction lens

| Subagent | Person | Lens | Deep dossier |
|----------|--------|------|--------------|
| `antirez-simplicity-reviewer` | Salvatore Sanfilippo (antirez) - Redis creator | Design sacrifices, code as artifact, comments-pro, fitness-for-purpose, anti-bloat, hack value | [antirez-deep.md](antirez-deep.md) |
| `tef-deletability-reviewer` | Thomas Edward Figg (tef) - programmingisterrible.com | Easy to delete > easy to extend, anti-naive-DRY, protocol over topology, Devil's Dictionary | [tef-deep.md](tef-deep.md) |
| `muratori-perf-reviewer` | Casey Muratori - Handmade Hero, Computer Enhance | Semantic compression, performance from day one, operation-primal, anti-Clean-Code-orthodoxy | [muratori-deep.md](muratori-deep.md) |
| `hebert-resilience-reviewer` | Fred Hebert (ferd) - ferd.ca, Honeycomb SRE | Operability, supervision trees, controlled-burn, complexity-has-to-live-somewhere, sociotechnical resilience | [hebert-deep.md](hebert-deep.md) |
| `meadows-systems-advisor` | Donella Meadows - *Thinking in Systems* | 12 leverage points, stocks/flows/loops, paradigm transcendence, dancing with systems | [meadows-deep.md](meadows-deep.md) |
| `chin-strategy-advisor` | Cedric Chin - commoncog.com | Tacit knowledge, NDM (Klein), close-the-loop, anti-framework-cult, calibration cases | [chin-deep.md](chin-deep.md) |

## Extended Domain (10) - domain-specific lenses

| Subagent | Person | Lens | Deep dossier |
|----------|--------|------|--------------|
| `king-type-reviewer` | Alexis King (lexi-lambda) - Haskell, Hackett | Parse-don't-validate, totality, make illegal states unrepresentable, types as axioms, names are not type safety | [king-deep.md](king-deep.md) |
| `hughes-pbt-advisor` | John Hughes - Chalmers, QuickCheck co-creator, QuviQ | Property-based testing, generators not examples, shrinking is the value, stateful PBT, find the bugs your tests can't reach | [hughes-deep.md](hughes-deep.md) |
| `evans-ddd-reviewer` | Eric Evans - Domain Language Inc, DDD blue book | Ubiquitous language, bounded contexts, strategic before tactical, distill the core domain, context maps before microservices | [evans-deep.md](evans-deep.md) |
| `fp-structure-reviewer` | Mark Seemann (blog.ploeh.dk) with Scott Wlaschin (fsharpforfunandprofit.com) | Impureim sandwich, dependency rejection, railway-oriented programming, code that fits in your head, functional architecture for boring people | [fp-structure-deep.md](fp-structure-deep.md) |
| `wayne-spec-advisor` | Hillel Wayne - hillelwayne.com, *Practical TLA+* | Formal methods, TLA+, model-check the protocol, the spec is the design, safety vs liveness, are we really engineers | [wayne-deep.md](wayne-deep.md) |
| `iac-craft-reviewer` | Kief Morris (*Infrastructure as Code* O'Reilly, ThoughtWorks) with Yevgeniy Brikman (*Terraform Up & Running*) | Immutable infrastructure, drift detection, pipeline IS the change-management process, phoenix not snowflake, infrastructure as software | [iac-craft-deep.md](iac-craft-deep.md) |
| `test-architect` | Gary Bernhardt (Destroy All Software) with Kent Beck and Martin Fowler | Functional core/imperative shell, values not objects, boundaries, tests as design pressure, test pyramid, mocks aren't stubs | [test-architect-deep.md](test-architect-deep.md) |
| `gregg-perf-reviewer` | Brendan Gregg - ex-Netflix/Intel, *Systems Performance*, *BPF Performance Tools* | USE method, methodology over tools, profile in production, off-CPU analysis, BPF observability, workload characterization | [gregg-deep.md](gregg-deep.md) |
| `ai-quality-advisor` | Simon Willison - simonwillison.net, Datasette, llm CLI, Django co-creator | Prompt injection, eval-driven LLM development, lethal trifecta, dual LLM pattern, sandboxed tool use, open weights for resilience | [ai-quality-deep.md](ai-quality-deep.md) |
| `cicd-build-advisor` | Charity Majors - charity.wtf, Honeycomb co-founder | Test in production, observability over monitoring, deploy small deploy often, CI as feedback loop, oncall as cultural force, sociotechnical fixes | [cicd-build-deep.md](cicd-build-deep.md) |

## Extended UX/Platform (11) - UI craft, accessibility, motion, macOS conventions, dashboard density

| Subagent | Person | Lens | Deep dossier |
|----------|--------|------|--------------|
| `eidhof-swiftui-reviewer` | Chris Eidhof (objc.io, *Thinking in SwiftUI*, Swift Talk) with Florian Kugler | SwiftUI declarative discipline, view identity, state ownership, environment over singletons, value semantics, body as a function of state | [eidhof-deep.md](eidhof-deep.md) |
| `ash-cocoa-runtime-reviewer` | Mike Ash - mikeash.com, Friday Q&A | Cocoa runtime mechanics, ARC retain/release, GCD edge cases, NSRunLoop, blocks, locks/dispatch correctness, Swift bridging cost | [ash-deep.md](ash-deep.md) |
| `simmons-mac-craft-reviewer` | Brent Simmons - inessential.com, NetNewsWire creator | Mac app craft, "feels like a real Mac app", lifecycle finesse, multi-window, sandbox vs HIG, threading model as architecture, ship-it-small | [simmons-deep.md](simmons-deep.md) |
| `norman-affordance-reviewer` | Don Norman - jnd.org, *The Design of Everyday Things*, ex-Apple "User Experience Architect", NN/g co-founder | Affordances vs signifiers, mappings, mental models, conceptual models, seven stages of action, error mode design, "blame the design, not the user" | [norman-deep.md](norman-deep.md) |
| `tognazzini-fpid-reviewer` | Bruce "Tog" Tognazzini - asktog.com, Apple Human Interface Engineer #66, NN/g co-founder | First Principles of Interaction Design, Fitts's law, anticipation, latency reduction, autonomy, protect user's work, modeless preferred | [tognazzini-deep.md](tognazzini-deep.md) |
| `krug-usability-reviewer` | Steve Krug - sensible.com, *Don't Make Me Think*, *Rocket Surgery Made Easy* | Three laws (don't make me think / mindless clicks / cut half the words), muddling through, trunk test, reservoir of goodwill, three-users-a-month testing | [krug-deep.md](krug-deep.md) |
| `nielsen-heuristics-reviewer` | Jakob Nielsen - nngroup.com Alertbox, *Usability Engineering* 1993, NN/g co-founder | 10 Usability Heuristics (1994), severity rating 0-4, discount usability, 5-users finding, thinking-aloud protocol, F-pattern reading | [nielsen-deep.md](nielsen-deep.md) |
| `watson-a11y-reviewer` | Léonie Watson - tink.uk, TetraLogical, W3C invited expert | Lived screen-reader experience, semantic HTML over ARIA, accessible-name computation, focus order, four rules of ARIA, accessibility as craft not checklist | [watson-deep.md](watson-deep.md) |
| `head-motion-reviewer` | Val Head - valhead.com, *Designing Interface Animation*, "Motion and Meaning" podcast | Motion has purpose, easing curves, timing budgets 200-500ms, vestibular safety, prefers-reduced-motion, choreography, Disney's 12 Principles for UI | [head-deep.md](head-deep.md) |
| `siracusa-mac-critic` | John Siracusa - hypercritical.co, Ars Technica Mac OS X reviews 1999-2014, ATP podcast | Mac platform critique, AppKit/Cocoa appreciation, filesystem rants, backwards compatibility as craft, "this is not how a Mac app does X", annoyance-driven development | [siracusa-deep.md](siracusa-deep.md) |
| `tufte-density-reviewer` | Edward Tufte - edwardtufte.com, *Visual Display of Quantitative Information* (1983), *Envisioning Information* (1990), *Visual Explanations* (1997), *Beautiful Evidence* (2006) | Data-ink ratio, chartjunk, sparklines (his coinage), small multiples, "above all else show the data", lie factor, integration of text and image | [tufte-deep.md](tufte-deep.md) |

## What each persona is good at catching

| Symptom | Personas to summon |
|---------|--------------------|
| Over-engineering / premature abstraction | antirez, tef, muratori |
| Wrong abstraction, hard-to-delete code | tef, antirez |
| Performance built into architecture too late (single-process hot path) | muratori |
| Performance unmeasured at fleet scale (Linux / JVM / production) | gregg, muratori |
| Failure modes ignored, blast radius unclear | hebert |
| Concurrency invariant unspecified / model-check gap | wayne, hebert |
| Wrong leverage point intervention | meadows |
| Plan that codifies frameworks instead of building skill | chin |
| Operational blindness | hebert, meadows, cicd-build |
| Sociotechnical mismatch (org/system disconnect) | meadows, hebert, chin, cicd-build |
| Lacks evidence / measurement | muratori, chin, gregg |
| Solves the symptom not the structure | meadows, hebert |
| Type lies about its preconditions / shotgun parsing | king, antirez |
| No properties, only example tests / generative coverage gap | hughes, test-architect |
| Domain language slipping / bounded context confusion | evans, meadows |
| Functional core polluted with effects / DI container ceremony | fp-structure, test-architect |
| Snowflake infra / drift unmeasured / IaC missing | iac-craft, hebert |
| Test pyramid inverted / mocks where values should be | test-architect, hughes |
| LLM output trusted without evals / prompt injection / lethal trifecta | ai-quality, hebert |
| CI is gate not feedback / deploy frequency low / oncall punishing | cicd-build, hebert, tef |
| SwiftUI render-pipeline cliffs / view-identity bugs / state placement | eidhof, ash, king |
| Cocoa runtime hot paths / ARC subtleties / GCD contention / NSRunLoop stalls | ash, muratori, gregg |
| "This doesn't feel like a Mac app" / lifecycle finesse / multi-window restoration | simmons, siracusa, tognazzini |
| Wrong affordance / missing signifier / discoverability gap / mental-model mismatch | norman, tognazzini, krug |
| Heuristic violation needs severity scoring / 5-user test gap / thinking-aloud absent | nielsen, krug, norman |
| Accessible name missing / focus order broken / WCAG criterion violated / screen-reader unfriendly | watson, norman, nielsen |
| Animation too long / wrong easing / vestibular hostile / no prefers-reduced-motion fallback | head, muratori, simmons |
| Dashboard chartjunk / data-ink ratio low / lie factor non-1.0 / small-multiples opportunity | tufte, antirez, tef |
| macOS HIG violation / non-Mac convention / breaks AppKit expectation | siracusa, tognazzini, simmons |
| Recording-first triage / muddler-test gap / user-perspective issue invisible to detector | krug, chin, watson |

## What no persona in this council is good at catching

Twenty-seven personas leave residual gaps. Out of scope today: relational-database internals (query planning, index design, lock escalation), ML model training and data engineering, security threat modeling and red-team work, hardware / electrical-engineering / firmware constraints, embedded real-time scheduling. If your problem lives squarely in one of those, route to direct review rather than `/council`.
