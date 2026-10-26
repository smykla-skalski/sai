# Composition principles

Distilled from William Strunk Jr.'s "The Elements of Style" (1918, rules 8-18), plain-language guidance from Digital.gov and W3C, and the Google and Microsoft technical-writing guides. Apply them to every sentence you rewrite or draft. The target in one line: answer first, use concrete words, include only useful context, match the audience, stop.

Every principle here works under one limit: the result keeps every fact, condition, number, modal verb and tone of its source. When a principle would change the meaning, keep the meaning.

## Contents

1. [Lead with the point](#lead-with-the-point)
2. [Use the active voice](#use-the-active-voice)
3. [Put statements in positive form](#put-statements-in-positive-form)
4. [Use concrete language](#use-concrete-language)
5. [Use plain words, keep needed jargon](#use-plain-words-keep-needed-jargon)
6. [Omit needless words](#omit-needless-words)
7. [One main idea per sentence](#one-main-idea-per-sentence)
8. [Express parallel ideas in parallel form](#express-parallel-ideas-in-parallel-form)
9. [Vary sentence structure](#vary-sentence-structure)
10. [Keep related words together](#keep-related-words-together)
11. [Keep to one tense](#keep-to-one-tense)
12. [Place emphasis at the end](#place-emphasis-at-the-end)
13. [One paragraph, one topic](#one-paragraph-one-topic)

---

## Lead with the point

The first sentence answers the reader's question: what happened, what they must do, or what was decided. Order the rest by what the reader needs: result or action, then conditions, then explanation, then background. When the source buries the point, move it up, using only the source's own facts.

> **Before:** Following our recent discussions, we have made several updates to the API. As part of this work, v1 will shut down on 15 November.
>
> **After:** API v1 shuts down on 15 November.

## Use the active voice

The active voice is more direct and vigorous than the passive, and it shows who is responsible. Prefer actor, action, object, condition.

> **Before:** Upon completion of the verification procedure, notification will be provided to the applicant by the department.
>
> **After:** The department will notify the applicant after verification.

> **Before:** The deploy was approved by Marta after the review was completed.
>
> **After:** Marta approved the deploy after the review.

> **Before:** There were a great number of dead leaves lying on the ground.
>
> **After:** Dead leaves covered the ground.

Do not chain one passive on another. "Gold was not allowed to be exported" becomes "It was forbidden to export gold."

Keep the passive when the actor is unknown, irrelevant, deliberately in the background or legally significant, or when the receiver of the action is the topic of the paragraph. "The dramatists of the Restoration are little esteemed today" is correct in a paragraph about those dramatists. Never invent an actor to make a sentence active.

## Put statements in positive form

Make definite assertions. Use "not" for denial or antithesis, never for evasion. Switch to the positive only when it means exactly the same, including the degree:

| Negative form | Positive form |
| :-- | :-- |
| He was not very often on time | He usually came late |
| did not remember | forgot |
| did not succeed | failed |
| not the same | different |

"Not important" and "trifling", or "did not pay attention" and "ignored", differ in strength or intent. Keep the negation there.

> **Before:** The Taming of the Shrew is rather weak in spots. Shakespeare does not portray Katharine as a very admirable character, nor does Bianca remain long in memory.
>
> **After:** The women in The Taming of the Shrew are unattractive. Katharine is disagreeable, Bianca insignificant.

## Use concrete language

Prefer the specific to the general, the definite to the vague, the concrete to the abstract. Ground statements in observable details.

| Abstract | Concrete |
| :-- | :-- |
| A period of unfavorable weather set in | It rained every day for a week |
| He showed satisfaction as he took possession of his well-earned reward | He grinned as he pocketed the coin |

The details must come from the source: concrete language never means inventing a number, a name or a result.

> **Before:** Additionally, this groundbreaking framework serves as a testament to the team's commitment to fostering innovation, showcasing how modern tools can enhance developer productivity in today's rapidly evolving landscape.
>
> **After:** The team built this framework to help developers get more done.

The source names no concrete gains, so the rewrite invents none. Adding "cuts build time by 40%" would read better and be false.

## Use plain words, keep needed jargon

Use the shortest familiar word that is equally precise. If the plain word has exactly the same meaning and implications here, use it. Otherwise keep the precise term and explain it once if the reader needs that.

| Prefer | Instead of |
| :-- | :-- |
| use | utilize, leverage |
| help | facilitate |
| about | with respect to, regarding |
| before | prior to |
| start | commence, initiate |
| buy | purchase (when no technical distinction exists) |
| change | modify (when no technical distinction exists) |
| can | has the ability to |

Turn hidden verbs back into verbs: "make a decision" is "decide", "conduct an investigation" is "investigate", "provide an explanation of" is "explain", "perform an evaluation of" is "evaluate". In "there are three services that call it", make the services the subject: "Three services call it."

Unpack a long noun chain into its relations: "user session token refresh failure alert" becomes "an alert when a user's session token fails to refresh". Replace a vague "it", "this" or "that" with its noun when the reference is unclear. Move essential content out of parentheses into the sentence.

Keep a technical term when the audience uses it. "Redis" beats "a data storage intermediary", and "p95 latency" beats "how slow the slower requests are". Simple words read faster for everyone, including readers working in a second language, but precision wins over artificial simplicity.

## Omit needless words

A sentence should contain no unnecessary words, a paragraph no unnecessary sentences. This does not mean making all sentences short or avoiding detail. It means making every word tell. Concision is less text, not less information: remove a word, and restore it only if the meaning changes.

Delete repeated conclusions, sentences that restate the previous one, empty introductions ("It is important to note that"), intensifiers that add nothing, metadiscourse ("As mentioned previously") and a second statement of a date or qualification when one clear statement is enough.

| Wordy | Concise |
| :-- | :-- |
| the question as to whether | whether |
| there is no doubt but that | no doubt |
| used for fuel purposes | used for fuel |
| he is a man who | he |
| in a hasty manner | hastily |
| this is a subject which | this subject |
| His story is a strange one. | His story is strange. |
| in order to | to |
| at this point in time | now |
| in the event that | if |

Revise "the fact that" out of every sentence:

| Expression | Replacement |
| :-- | :-- |
| owing to the fact that, due to the fact that | because |
| in spite of the fact that | though |
| call your attention to the fact that | remind you |
| I was unaware of the fact that | I did not know |
| the fact that he had not succeeded | his failure |

"Who is" and "which was" are often superfluous:

| Wordy | Concise |
| :-- | :-- |
| His brother, who is a member of the same firm | His brother, a member of the same firm |
| Trafalgar, which was Nelson's last battle | Trafalgar, Nelson's last battle |

> **Before:** Prior to initiating the deployment process, it is necessary to ensure that you have created a backup copy of the configuration file. Once this has been done, execute the following command in a terminal window in order to restart the service.
>
> **After:** Back up the configuration file before deployment. Then run the following command in a terminal to restart the service.

"It is necessary to" becomes a command, which has the same force, and the order, backup before deployment, stays.

Combine choppy step-by-step sentences when the relationship between them matters, as cause and sequence do here:

> **Before (51 words):** Macbeth was very ambitious. This led him to wish to become king of Scotland. The witches told him that this wish of his would come true. The king of Scotland at this time was Duncan. Encouraged by his wife, Macbeth murdered Duncan. He was thus enabled to succeed Duncan as king.
>
> **After (26 words):** Encouraged by his wife, Macbeth achieved his ambition and realized the prediction of the witches by murdering Duncan and becoming king of Scotland in his place.

## One main idea per sentence

A sentence that strings independent clauses together with "and" is hard to scan. Split it, and combine clauses only when the link between them matters.

> **Before:** We deployed v4, and the metrics look good, and the old worker is still available, and we will keep monitoring.
>
> **After:** v4 is live. Metrics look good. The old worker stays available while we monitor.

## Express parallel ideas in parallel form

Ideas with the same content and function take the same grammatical form, so the reader sees the likeness. Do not vary the form for variety's sake.

| Unlike forms | Parallel forms |
| :-- | :-- |
| Formerly, science was taught by the textbook method, while now the laboratory method is employed. | Formerly, science was taught by the textbook method. Now it is taught by the laboratory method. |
| It was both a long ceremony and very tedious. | The ceremony was both long and tedious. |
| A time not for words, but action. | A time not for words, but for action. |
| Either you must grant his request or incur his ill will. | You must either grant his request or incur his ill will. |
| My objections are, first, the injustice of the measure; second, that it is unconstitutional. | My objections are, first, that the measure is unjust; second, that it is unconstitutional. |

Use an article or a preposition before the first term of a series only, or before every term: "in spring, summer, or winter", or "in spring, in summer, or in winter". Follow correlatives (both...and, not...but, not only...but also, either...or, first...second) with the same construction. Start every item of a list with the same part of speech, such as a verb for steps. When many similar ideas pile up, group them, or put them in a table.

## Vary sentence structure

Avoid a succession of loose sentences with two co-ordinate clauses joined by a conjunction. This creates monotony:

> The third concert was given last evening, and a large audience was in attendance. Mr. Appleton was the soloist, and the Boston Symphony Orchestra furnished the music. The former showed himself an artist of the first rank, while the latter proved fully deserving of its reputation.

Every sentence follows the same "X happened, and Y happened" pattern. Recast some as simple sentences and some as periodic sentences, whichever best shows the real relations of the thought.

AI text produces this kind of structural monotony often, and it tires the reader. Vary structure because the ideas differ, not to hit a length target or to look human.

## Keep related words together

The position of words in a sentence shows their relationship. Keep together what belongs together.

Do not separate subject and verb by a phrase that can move to the beginning:

| Separated | Together |
| :-- | :-- |
| Wordsworth, in the fifth book of The Excursion, gives a minute description | In the fifth book of The Excursion, Wordsworth gives a minute description |
| Cast iron, when treated in a Bessemer converter, is changed into steel | By treatment in a Bessemer converter, cast iron is changed into steel |

Put a relative pronoun right after its antecedent:

| Ambiguous | Clear |
| :-- | :-- |
| He wrote three articles about his adventures in Spain, which were published in Harper's | He published in Harper's three articles about his adventures in Spain |
| This is a portrait of Benjamin Harrison, grandson of William Henry Harrison, who became President in 1889 | This is a portrait of Benjamin Harrison, grandson of William Henry Harrison. He became President in 1889 |

Put a modifier next to what it modifies, and watch the scope of "not" and "only":

| Misplaced | Correct |
| :-- | :-- |
| He only found two mistakes | He found only two mistakes |
| All the members were not present | Not all the members were present |

## Keep to one tense

In a summary, report or changelog, pick one tense and keep it: shifting tenses looks uncertain. Technical text usually takes the present tense ("The command returns"). In a present-tense summary, put earlier events in the perfect ("has been compelled"); in a past-tense one, the past perfect. A past tense in reported speech stays: "The Friar confesses that it was he who married them."

When you summarize someone else's statements, say once that what follows is their view. Do not repeat "he said", "the author adds" or "the speaker went on to say" in every sentence.

## Place emphasis at the end

The end of a sentence is its most prominent position. Put the word or phrase you want to emphasize there, usually the new element.

| Weak ending | Strong ending |
| :-- | :-- |
| Humanity has hardly advanced in fortitude since that time, though it has advanced in many other ways | Humanity has advanced in many other ways, but it has hardly advanced in fortitude |
| This steel is principally used for making razors, because of its hardness | Because of its hardness, this steel is principally used in making razors |

The beginning of a sentence is the second most prominent position. Any element other than the subject becomes emphatic when placed first.

This applies to sentences within a paragraph and to paragraphs within a text too: end a paragraph on its strongest point, not a trailing detail. It does not move the main point of a message to the end. The first sentence still states it (see [Lead with the point](#lead-with-the-point)), and the text stops after the last fact the reader needs.

## One paragraph, one topic

Each paragraph covers one topic. Begin with a topic sentence that says what the paragraph is about, develop it, and end in a way that reinforces the opening or states a consequence, not with a digression or an unimportant detail. A short text on one subject needs only one paragraph.

AI text often produces paragraphs that drift between topics or end with unrelated observations. When rewriting, check that each paragraph has a clear subject and that the final sentence relates to it.

Single-sentence paragraphs are acceptable as transitions, and in short media such as chat, but should not be the norm in longer prose.

---

## Source

Strunk, William Jr. "The Elements of Style." 1918. Adapted from [obra/the-elements-of-style](https://github.com/obra/the-elements-of-style) skill reference. "Lead with the point", "Use plain words, keep needed jargon" and "One main idea per sentence" follow the [Google](https://developers.google.com/tech-writing) and [Microsoft](https://learn.microsoft.com/style-guide/welcome/) technical-writing guides, [Digital.gov](https://digital.gov/guides/plain-language/writing) and [W3C](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o3p01-clear-words/).
