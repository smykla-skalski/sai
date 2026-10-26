# AI writing patterns

Each pattern is an editing smell: it makes text vaguer, longer or less specific. None of them proves that a model wrote the text, because people write every one of them too. Never present a hit as evidence of AI authorship.

A word or mark on a list is a hit only when it does that harm in context. "Key" in "API key", or one em dash where the author would naturally use one, is not a hit. Do not replace words or punctuation just because they appear on a list, and never fix a hit by adding typos or broken grammar.

Every "After" below uses only facts from its "Before". A fix deletes decoration and states the remaining facts plainly. It never adds a source, number, cause or detail, however much better the text would read.

## Contents

1. [Content patterns](#content-patterns)
   - [1. Significance inflation](#1-significance-inflation)
   - [2. Notability and media coverage claims](#2-notability-and-media-coverage-claims)
   - [3. Superficial -ing analyses](#3-superficial--ing-analyses)
   - [4. Promotional language](#4-promotional-language)
   - [5. Vague attributions and weasel words](#5-vague-attributions-and-weasel-words)
   - [6. Formulaic challenges sections](#6-formulaic-challenges-sections)
2. [Language and grammar patterns](#language-and-grammar-patterns)
   - [7. AI vocabulary words](#7-ai-vocabulary-words)
   - [8. Copula avoidance](#8-copula-avoidance)
   - [9. Negative parallelisms](#9-negative-parallelisms)
   - [10. Rule of three overuse](#10-rule-of-three-overuse)
   - [11. Synonym cycling](#11-synonym-cycling)
   - [12. False ranges](#12-false-ranges)
3. [Style patterns](#style-patterns)
   - [13. Em dash overuse](#13-em-dash-overuse)
   - [14. Boldface overuse](#14-boldface-overuse)
   - [15. Inline-header vertical lists](#15-inline-header-vertical-lists)
   - [16. Title case in headings](#16-title-case-in-headings)
   - [17. Emoji decoration](#17-emoji-decoration)
   - [18. Curly quotation marks](#18-curly-quotation-marks)
4. [Communication patterns](#communication-patterns)
   - [19. Chatbot correspondence artifacts](#19-chatbot-correspondence-artifacts)
   - [20. Knowledge-cutoff disclaimers](#20-knowledge-cutoff-disclaimers)
   - [21. Sycophantic tone](#21-sycophantic-tone)
5. [Filler and hedging](#filler-and-hedging)
   - [22. Filler phrases](#22-filler-phrases)
   - [23. Excessive hedging](#23-excessive-hedging)
   - [24. Generic positive conclusions](#24-generic-positive-conclusions)
6. [Structure patterns](#structure-patterns)
   - [25. Buried point](#25-buried-point)
   - [26. Over-completing](#26-over-completing)
   - [27. Excessive balance](#27-excessive-balance)
   - [28. Generic headings](#28-generic-headings)
   - [29. Unsupported confidence](#29-unsupported-confidence)
   - [30. Needless connectors](#30-needless-connectors)

---

## Content patterns

### 1. Significance inflation

**Words to watch:** stands/serves as, is a testament/reminder, a vital/significant/crucial/pivotal/key role/moment, underscores/highlights its importance/significance, reflects broader, symbolizing its ongoing/enduring/lasting, contributing to the, setting the stage for, marking/shaping the, represents/marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted

LLM writing puffs up importance by adding statements about how arbitrary aspects represent or contribute to a broader topic.

> **Before:** The Statistical Institute of Catalonia was officially established in 1989, marking a pivotal moment in the evolution of regional statistics in Spain. This initiative was part of a broader movement across Spain to decentralize administrative functions and enhance regional governance.

> **After:** The Statistical Institute of Catalonia was established in 1989, as part of a movement across Spain to decentralize administration and strengthen regional government.

### 2. Notability and media coverage claims

**Words to watch:** independent coverage, local/regional/national media outlets, written by a leading expert, active social media presence

LLMs hit readers over the head with claims of notability, often listing sources without context. Keep the facts and drop the boasting frame. Only the author can add what the sources said.

> **Before:** Her views have been cited in The New York Times, BBC, Financial Times, and The Hindu. She maintains an active social media presence with over 500,000 followers.

> **After:** The New York Times, the BBC, the Financial Times and The Hindu have cited her views. She has over 500,000 followers on social media.

### 3. Superficial -ing analyses

**Words to watch:** highlighting/underscoring/emphasizing..., ensuring..., reflecting/symbolizing..., contributing to..., cultivating/fostering..., encompassing..., showcasing...

AI chatbots tack present participle ("-ing") phrases onto sentences to add fake depth. Cut a phrase that only asserts significance. Keep one that states a checkable fact, as its own clause.

> **Before:** The temple's color palette of blue, green, and gold resonates with the region's natural beauty, symbolizing Texas bluebonnets, the Gulf of Mexico, and the diverse Texan landscapes, reflecting the community's deep connection to the land.

> **After:** The temple's blue, green, and gold symbolize Texas bluebonnets, the Gulf of Mexico, and the Texan landscape.

### 4. Promotional language

**Words to watch:** boasts a, vibrant, rich (figurative), profound, enhancing its, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking (figurative), renowned, breathtaking, must-visit, stunning, and adjective stacks such as "robust, seamless, scalable" or "cutting-edge"

LLMs have serious problems keeping a neutral tone, especially for "cultural heritage" topics.

> **Before:** Nestled within the breathtaking region of Gonder in Ethiopia, Alamata Raya Kobo stands as a vibrant town with a rich cultural heritage and stunning natural beauty.

> **After:** Alamata Raya Kobo is a town in the Gonder region of Ethiopia.

### 5. Vague attributions and weasel words

**Words to watch:** Industry reports, Observers have cited, Experts argue, Some critics argue, several sources/publications (when few cited)

AI chatbots attribute opinions to vague authorities without specific sources. Name the source when the text names it elsewhere. Never invent one. If the text names none, keep the claim with its attribution as vague as it was, and list it under `Claims without evidence:` in the report.

> **Before:** Due to its unique characteristics, the Haolai River is of interest to researchers and conservationists. Experts believe it plays a crucial role in the regional ecosystem.

> **After:** The Haolai River interests researchers and conservationists. Experts believe it plays a major role in the regional ecosystem.

### 6. Formulaic challenges sections

**Words to watch:** Despite its... faces several challenges..., Despite these challenges, Challenges and Legacy, Future Outlook

Many LLM-generated articles include formulaic "Challenges" sections.

> **Before:** Despite its industrial prosperity, Korattur faces challenges typical of urban areas, including traffic congestion and water scarcity. Despite these challenges, with its strategic location and ongoing initiatives, Korattur continues to thrive as an integral part of Chennai's growth.

> **After:** Korattur, an industrially prosperous part of Chennai, has traffic congestion and water scarcity.

---

## Language and grammar patterns

### 7. AI vocabulary words

**High-frequency AI words:** Additionally, align with, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (verb), interplay, intricate/intricacies, key (adjective), landscape (abstract noun), pivotal, showcase, tapestry (abstract noun), testament, underscore (verb), valuable, vibrant

These words appear far more frequently in post-2023 text. They often co-occur. Replace one only when a plainer or more specific word says the same thing. Keep it when it is the precise term.

> **Before:** Additionally, a distinctive feature of Somali cuisine is the incorporation of camel meat. An enduring testament to Italian colonial influence is the widespread adoption of pasta in the local culinary landscape, showcasing how these dishes have integrated into the traditional diet.

> **After:** Camel meat is a distinctive part of Somali cuisine. Pasta, a result of Italian colonial influence, is widely eaten and now part of the traditional diet.

### 8. Copula avoidance

**Words to watch:** serves as/stands as/marks/represents [a], boasts/features/offers [a]

LLMs substitute elaborate constructions for simple copulas.

> **Before:** Gallery 825 serves as LAAA's exhibition space for contemporary art. The gallery features four separate spaces and boasts over 3,000 square feet.

> **After:** Gallery 825 is LAAA's exhibition space for contemporary art. It has four separate spaces and over 3,000 square feet.

"Over 3,000" stays "over 3,000": a range is a protected detail, and "totaling 3,000" would change it.

### 9. Negative parallelisms

Constructions like "Not only...but..." or "It's not just about..., it's..." are overused by LLMs.

> **Before:** It's not just about the beat riding under the vocals; it's part of the aggression and atmosphere. It's not merely a song, it's a statement.

> **After:** The beat under the vocals adds to the aggression and atmosphere. The song is a statement.

### 10. Rule of three overuse

LLMs force ideas into groups of three to appear comprehensive. A real list of three things stays.

> **Before:** The event features keynote sessions, panel discussions, and networking opportunities. Attendees can expect innovation, inspiration, and industry insights.

> **After:** The event has keynote sessions, panel discussions, and time for networking.

The first triad lists three real parts of the event, so it stays. The second is decoration.

### 11. Synonym cycling

AI has repetition-penalty code causing excessive synonym substitution for the same referent.

> **Before:** The protagonist faces many challenges. The main character must overcome obstacles. The central figure eventually triumphs. The hero returns home.

> **After:** The protagonist faces many challenges but eventually triumphs and returns home.

### 12. False ranges

LLMs use "from X to Y" constructions where X and Y are not on a meaningful scale. A real scale is not a false range: "from startups to Fortune 500 companies" (company size) or "from 1.8s to 0.9s" are fine.

> **Before:** Our journey through the universe has taken us from the singularity of the Big Bang to the grand cosmic web, from the birth and death of stars to the enigmatic dance of dark matter.

> **After:** We covered the Big Bang, the cosmic web, the birth and death of stars, and dark matter.

---

## Style patterns

### 13. Em dash overuse

LLMs use em dashes more than humans, mimicking "punchy" sales writing: several dashes in a short text, or a dash for a reveal ("X—not Y"). Replace the extra ones with commas, periods, colons, or parentheses. One dash where the author would naturally use one is fine. Do not strip every dash by rule. A style guide or user instruction that bans em dashes wins.

> **Before:** The term is primarily promoted by Dutch institutions---not by the people themselves. You don't say "Netherlands, Europe" as an address---yet this mislabeling continues---even in official documents.

> **After:** The term is primarily promoted by Dutch institutions, not by the people themselves. You don't say "Netherlands, Europe" as an address, yet this mislabeling continues in official documents.

### 14. Boldface overuse

AI chatbots emphasize phrases in boldface mechanically, especially for acronyms and proper nouns.

> **Before:** It blends **OKRs (Objectives and Key Results)**, **KPIs (Key Performance Indicators)**, and visual strategy tools such as the **Business Model Canvas (BMC)** and **Balanced Scorecard (BSC)**.

> **After:** It blends OKRs (objectives and key results), KPIs (key performance indicators), and visual strategy tools such as the Business Model Canvas and the Balanced Scorecard.

The expansions stay for readers who need them. Each acronym used only once goes.

### 15. Inline-header vertical lists

AI outputs lists where items start with bolded headers followed by colons. Collapse into prose when possible.

> **Before:**
> - **User Experience:** The user experience has been significantly improved with a new interface.
> - **Performance:** Performance has been enhanced through optimized algorithms.
> - **Security:** Security has been strengthened with end-to-end encryption.

> **After:** The update adds a new interface that significantly improves the user experience, optimized algorithms that improve performance, and end-to-end encryption.

"Significantly improved" has no evidence in the source, so it stays at its strength and goes on the report's `Claims without evidence:` list.

### 16. Title case in headings

AI chatbots capitalize all main words in headings. Use sentence case instead, unless the project's style guide asks for title case.

> **Before:** Strategic Negotiations And Global Partnerships

> **After:** Strategic negotiations and global partnerships

### 17. Emoji decoration

AI chatbots decorate headings or bullet points with emojis. Remove them.

> **Before:** 🚀 Launch Phase: The product launches in Q3. 💡 Key Insight: Users prefer simplicity. ✅ Next Steps: Schedule follow-up meeting.

> **After:** The product launches in Q3. Users prefer simplicity. Next step: schedule a follow-up meeting.

### 18. Curly quotation marks

ChatGPT carries curly quotes into Markdown, commit messages, code comments, and plain-text files, where the surrounding text uses straight quotes. Straighten them there. In typeset prose that uses curly quotes throughout, keep them.

Curly: \u201c \u201d \u2018 \u2019. Straight: " " ' '.

> **Before:** He said \u201cthe project is on track\u201d but others disagreed.

> **After:** He said "the project is on track" but others disagreed.

---

## Communication patterns

### 19. Chatbot correspondence artifacts

**Words to watch:** I hope this helps, Of course!, Certainly!, Sure!, You're absolutely right!, Would you like..., let me know, here is a..., below is a...

Text meant as chatbot correspondence gets pasted as content: openers that echo the request, and follow-up offers at the end. Strip these entirely.

> **Before:** Here is an overview of the French Revolution. The revolution began in 1789 amid a financial crisis and food shortages. I hope this helps! Let me know if you'd like me to expand on any section.

> **After:** The French Revolution began in 1789 amid a financial crisis and food shortages.

### 20. Knowledge-cutoff disclaimers

**Words to watch:** as of [date], Up to my last training update, While specific details are limited/scarce..., based on available information...

AI disclaimers about incomplete information get left in text.

> **Before:** While specific details about the company's founding are not extensively documented in readily available sources, it appears to have been established sometime in the 1990s.

> **After:** The company was probably founded in the 1990s.

"Probably" keeps the uncertainty that the disclaimer expressed. Removing the disclaimer must not make the claim more certain.

### 21. Sycophantic tone

Overly positive, people-pleasing language. Cut it.

> **Before:** Great question! You're absolutely right that this is a complex topic. That's an excellent point about the economic factors.

> **After:** You're right that this topic is complex, and your point about the economic factors holds.

The agreement is content, so it stays. The flattery goes.

---

## Filler and hedging

### 22. Filler phrases

Common substitutions:

| Filler | Replacement |
| :-- | :-- |
| In order to achieve this goal | To achieve this |
| Due to the fact that | Because |
| At this point in time | Now |
| In the event that | If |
| has the ability to | can |
| It is important to note that X | X |
| It is worth noting that X | X |
| When it comes to X, ... | Start with X |
| In today's fast-paced world, ... | Cut it |
| utilize, leverage | use |
| facilitate | help |
| perform an evaluation of | evaluate |

### 23. Excessive hedging

Over-qualifying statements. Collapse stacked hedges into one hedge of the same strength. Never remove the uncertainty itself: "may" must not become "will".

> **Before:** It could potentially possibly be argued that the policy might have some effect on outcomes.

> **After:** The policy may affect outcomes.

### 24. Generic positive conclusions

**Words to watch:** In summary, In conclusion, Overall, this marks, The future looks bright, Exciting times ahead, We'll keep you posted, We'll keep everyone updated, Stay tuned

Vague upbeat endings, a recap that repeats what the text already said, or a promise of updates that says neither when nor where. Replace with specifics from the source or cut entirely. A closing line with real information stays ("Next update at 15:00 in #releases"). End after the last fact the reader needs.

> **Before:** The company plans to open two more locations next year. The future looks bright for the company. Exciting times lie ahead as they continue their journey toward excellence.

> **After:** The company plans to open two more locations next year.

---

## Structure patterns

### 25. Buried point

**Words to watch:** Following our recent discussions, After careful consideration, As you may know, I wanted to reach out

The decision, request, result, or blocker comes after a preamble or at the very end. Readers should not dig for it. Move it to the first sentence.

> **Before:** Following our recent discussions about the release process, the team has looked into several aspects of the pipeline. After careful consideration, the v3.2 rollout is blocked until DB-142 is fixed.

> **After:** The v3.2 rollout is blocked until DB-142 is fixed.

### 26. Over-completing

A short answer grows a summary, implications and a recap that nobody asked for. Cut what repeats or inflates, keep any instruction the author gave, and stop when the reader can act.

> **Before:** The fix is in 2.8.1. In summary, this update resolves the issue. Going forward, it is recommended to keep dependencies current. Overall, this represents an important improvement in stability.

> **After:** The fix is in 2.8.1. Keep dependencies current.

### 27. Excessive balance

**Words to watch:** There are advantages and disadvantages, Both approaches have merit, Each has its own strengths, It depends on your needs

Automatic, symmetrical pros and cons or caveats that do not change the decision. Keep a trade-off only when it changes what the reader should do, and never drop one the author meant to raise.

> **Before:** There are advantages and disadvantages to both Redis and Postgres for locking. Each has its own strengths, and the right choice depends on your needs. We need locks across processes, so we chose Redis.

> **After:** We chose Redis because we need locks across processes.

### 28. Generic headings

**Words to watch:** Overview, Introduction, Key Considerations, Key Takeaways, Summary, Conclusion (on short text)

Headings that stand in for substance: a scaffold on a few lines of text, or the same sections on every document. Keep a heading only when it helps the reader find something.

> **Before:** An "Overview" heading over one sentence, a "Key Considerations" heading over one sentence, and a "Conclusion" heading over a sentence that repeats the first.

> **After:** Two sentences, no headings: "The cache now expires after 5 minutes. Restarts drop old entries."

### 29. Unsupported confidence

**Words to watch:** should provide a robust solution, ensures, guarantees, significantly improves, without any issues

Smooth, confident claims that hide missing evidence. When the source gives evidence, state the claim through it and drop the gloss. When it gives none, keep the claim at the strength the source gives it, drop only the decoration ("robust", "seamless"), and list the claim under `Claims without evidence:` in the report so the author can add support. Never invent a number or a test result, never add a hedge, and never cut a substantive claim.

> **Before:** This change should provide a robust solution and significantly improve performance. Load tests show p95 latency dropping from 180 to 122 ms.

> **After:** This change cuts p95 latency from 180 to 122 ms in load tests.

### 30. Needless connectors

**Words to watch:** Additionally, Also (opening a sentence), Furthermore, Moreover, Notably, Importantly, That said, However (when nothing contrasts)

Transitions added where the order of the sentences already shows the relation. Delete them. Keep a connector that carries a contrast or a cause the reader would otherwise miss.

> **Before:** The deploy finished. Additionally, the error rate is flat. Furthermore, no rollbacks were needed.

> **After:** The deploy finished. The error rate is flat, and no rollbacks were needed.

---

## Source

Patterns 1-24 come from [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup, which identified them from thousands of instances of AI-generated text. Patterns 25-30 cover habits of AI agents that answer or edit, drawn from the Google and Microsoft technical-writing guides and published comparisons of human and model text such as HC3. All of them are tendencies across many texts, not signatures of one.

Core principle: "LLMs use statistical algorithms to guess what should come next. The result tends toward the most statistically likely result that applies to the widest variety of cases."
