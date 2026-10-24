# Composition principles

Distilled from William Strunk Jr.'s "The Elements of Style" (1918) and current technical-writing guidance from Google and Microsoft. Apply these during the rewrite phase after removing AI patterns. They address how to write well, not just how to avoid writing badly. The target in one line: answer first, use concrete words, include only useful context, match the audience, stop.

## Contents

1. [Lead with the point](#lead-with-the-point)
2. [Use the active voice](#use-the-active-voice)
3. [Put statements in positive form](#put-statements-in-positive-form)
4. [Use concrete language](#use-concrete-language)
5. [Use plain words, keep needed jargon](#use-plain-words-keep-needed-jargon)
6. [Omit needless words](#omit-needless-words)
7. [One main idea per sentence](#one-main-idea-per-sentence)
8. [Vary sentence structure](#vary-sentence-structure)
9. [Keep related words together](#keep-related-words-together)
10. [Place emphasis at the end](#place-emphasis-at-the-end)
11. [One paragraph, one topic](#one-paragraph-one-topic)
12. [Needless expressions](#needless-expressions)

---

## Lead with the point

The first sentence answers the reader's question: what happened, what they must do, or what was decided. Context and evidence follow. When the source buries the point, move it up, using only the source's own facts.

> **Before:** Following our recent discussions, we have made several updates to the API. As part of this work, v1 will shut down on 15 November.
>
> **After:** API v1 shuts down on 15 November.

## Use the active voice

The active voice is more direct and vigorous than the passive. AI text defaults to passive constructions that weaken the writing.

> **Before:** The deploy was approved by Marta after the review was completed.
>
> **After:** Marta approved the deploy after the review.

> **Before:** There were a great number of dead leaves lying on the ground.
>
> **After:** Dead leaves covered the ground.

> **Before:** The reason that he left college was that his health became impaired.
>
> **After:** Failing health compelled him to leave college.

Do not chain one passive on another. "Gold was not allowed to be exported" becomes "It was forbidden to export gold."

The passive is fine when the receiver of the action is the topic of the paragraph. "The dramatists of the Restoration are little esteemed today" is correct in a paragraph about those dramatists.

## Put statements in positive form

Make definite assertions. Use "not" for denial or antithesis, never for evasion. AI text hedges with negative phrasing where a direct positive statement works better.

| Negative form | Positive form |
| :-- | :-- |
| He was not very often on time | He usually came late |
| did not remember | forgot |
| did not pay any attention to | ignored |
| did not have much confidence in | distrusted |
| not important | trifling |

This applies to whole passages too:

> **Before:** The Taming of the Shrew is rather weak in spots. Shakespeare does not portray Katharine as a very admirable character, nor does Bianca remain long in memory.
>
> **After:** The women in The Taming of the Shrew are unattractive. Katharine is disagreeable, Bianca insignificant.

## Use concrete language

Prefer the specific to the general, the definite to the vague, the concrete to the abstract. AI text gravitates toward generic abstractions. Counter this by grounding statements in observable details.

| Abstract | Concrete |
| :-- | :-- |
| A period of unfavorable weather set in | It rained every day for a week |
| He showed satisfaction as he took possession of his well-earned reward | He grinned as he pocketed the coin |

The surest way to hold the reader's attention is being specific. When dealing with general principles, give particular instances. The instances must come from the source: concrete language never means inventing a number, a name, or a result.

> **Before:** Additionally, this groundbreaking framework serves as a testament to the team's commitment to fostering innovation, showcasing how modern tools can enhance developer productivity in today's rapidly evolving landscape.
>
> **After:** The team built this framework to help developers get more done.

The source names no concrete gains, so the rewrite invents none. Adding "cuts build time by 40%" would read better and be false.

## Use plain words, keep needed jargon

Prefer the shortest familiar word that stays precise: "use" over "utilize", "help" over "facilitate", "benchmark" over "perform an evaluation of". Simple words read faster for everyone, including readers working in a second language.

Keep a technical term when the audience would use it. "Redis" beats "a data storage intermediary", and "p95 latency" beats "how slow the slower requests are". Precision wins over artificial simplicity.

## Omit needless words

A sentence should contain no unnecessary words, a paragraph no unnecessary sentences. This does not mean making all sentences short or avoiding detail - it means making every word tell. Concision is less text, not less information: remove a word, and restore it only if the meaning changes.

| Wordy | Concise |
| :-- | :-- |
| the question as to whether | whether |
| there is no doubt but that | no doubt |
| used for fuel purposes | used for fuel |
| he is a man who | he |
| in a hasty manner | hastily |
| this is a subject which | this subject |
| His story is a strange one. | His story is strange. |

Revise "the fact that" out of every sentence:

| Expression | Replacement |
| :-- | :-- |
| owing to the fact that | since, because |
| in spite of the fact that | though |
| call your attention to the fact that | remind you |
| I was unaware of the fact that | I did not know |
| the fact that he had not succeeded | his failure |

"Who is" and "which was" are often superfluous:

| Wordy | Concise |
| :-- | :-- |
| His brother, who is a member of the same firm | His brother, a member of the same firm |
| Trafalgar, which was Nelson's last battle | Trafalgar, Nelson's last battle |

Combine choppy step-by-step sentences when the relationship between them matters, as cause and sequence do here:

> **Before (51 words):** Macbeth was very ambitious. This led him to wish to become king of Scotland. The witches told him that this wish of his would come true. The king of Scotland at this time was Duncan. Encouraged by his wife, Macbeth murdered Duncan. He was thus enabled to succeed Duncan as king.
>
> **After (26 words):** Encouraged by his wife, Macbeth achieved his ambition and realized the prediction of the witches by murdering Duncan and becoming king of Scotland in his place.

## One main idea per sentence

A sentence that strings independent clauses together with "and" is hard to scan. Split it, and combine clauses only when the link between them matters.

> **Before:** We deployed v4, and the metrics look good, and the old worker is still available, and we will keep monitoring.
>
> **After:** v4 is live. Metrics look good. The old worker stays available while we monitor.

## Vary sentence structure

Avoid a succession of loose sentences with two co-ordinate clauses joined by a conjunction. This creates monotony:

> The third concert was given last evening, and a large audience was in attendance. Mr. Appleton was the soloist, and the Boston Symphony Orchestra furnished the music. The former showed himself an artist of the first rank, while the latter proved fully deserving of its reputation.

Every sentence follows the same "X happened, and Y happened" pattern. Recast some as simple sentences, some as periodic sentences, some with semicolons. The variety should reflect the actual relationships between ideas, not a mechanical template.

AI text produces this kind of structural monotony frequently, and it tires the reader. Vary structure because the ideas differ, not to hit a length target or to look human.

## Keep related words together

The position of words in a sentence shows their relationship. Keep together what belongs together.

Subject and verb should not be separated by a clause that can move to the beginning:

| Separated | Together |
| :-- | :-- |
| Wordsworth, in the fifth book of The Excursion, gives a minute description | In the fifth book of The Excursion, Wordsworth gives a minute description |

Relative pronouns should follow their antecedent immediately:

| Ambiguous | Clear |
| :-- | :-- |
| He wrote three articles about his adventures in Spain, which were published in Harper's | He published in Harper's three articles about his adventures in Spain |

Modifiers should sit next to what they modify:

| Misplaced | Correct |
| :-- | :-- |
| He only found two mistakes | He found only two mistakes |

## Place emphasis at the end

The end of a sentence is its most prominent position. Put the word or phrase you want to emphasize there.

| Weak ending | Strong ending |
| :-- | :-- |
| Humanity has hardly advanced in fortitude since that time, though it has advanced in many other ways | Humanity has advanced in many other ways, but it has hardly advanced in fortitude |
| This steel is principally used for making razors, because of its hardness | Because of its hardness, this steel is principally used in making razors |

The beginning of a sentence is the second most prominent position. Any element other than the subject becomes emphatic when placed first.

This principle applies equally to sentences within a paragraph and paragraphs within a composition. End paragraphs with your strongest point, not a trailing detail. It does not move the main point of a message to the end: the first sentence still states it (see [Lead with the point](#lead-with-the-point)), and the text stops after the last fact the reader needs.

## One paragraph, one topic

Each paragraph should cover one topic. Begin with a topic sentence that signals what the paragraph is about. End in a way that reinforces the opening, not with a digression.

AI text often produces paragraphs that drift between topics or end with unrelated observations. When rewriting, check that each paragraph has a clear subject and that the final sentence relates to it.

Single-sentence paragraphs are acceptable as transitions but should not be the norm.

## Needless expressions

Words and phrases that add nothing. Replace or remove.

| Expression | Problem | Fix |
| :-- | :-- | :-- |
| case | usually redundant ("in many cases") | rewrite ("many rooms") |
| character | wordiness ("acts of a hostile character") | cut ("hostile acts") |
| factor | hackneyed ("the great factor in") | rewrite ("he won by") |
| feature | adds nothing ("a feature worthy of mention") | describe the thing |
| interesting | lazy intro ("an interesting story") | just tell the story |
| nature | same as character ("of a hostile nature") | cut ("hostile") |
| along these lines | overworked ("spoke along the same lines") | rewrite ("to the same effect") |
| worth while | vague approval | be specific about the value |
| very | use sparingly; prefer strong words | cut or choose a stronger word |
| certainly | false intensifier, like "very" | cut |

---

## Source

Strunk, William Jr. "The Elements of Style." 1918. Adapted from [obra/the-elements-of-style](https://github.com/obra/the-elements-of-style) skill reference. "Lead with the point", "Use plain words, keep needed jargon" and "One main idea per sentence" follow the [Google](https://developers.google.com/tech-writing) and [Microsoft](https://learn.microsoft.com/style-guide/welcome/) technical-writing guides.
