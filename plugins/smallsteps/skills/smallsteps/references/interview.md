# Interview

The interview walks the user through four questions and fills one idea note. It reaches every next step through questions. It asks no question that would change nothing in the note, and it keeps asking until the note is precise or the idea is split into small results.

## Size the interview

Ask the appetite right after the problem, unless the user already said it: "How much time is this idea worth to you before you decide again?". Record the answer in the user's words. Then pick the size, say it in one line with its reason ("Size: large, because the time it is worth is unknown"), and write it under the appetite in the note. The user can change it.

| Size | When | Questions before the first action | Playbacks |
| :-- | :-- | :-- | :-- |
| Small | one evening or less, and one result | about 6 to 8 | one, at the end |
| Medium | more than one evening, up to about a weekend | about 9 to 12 | two: after step 2, and at the end |
| Large | more than a weekend, several people, or an unknown appetite | about 12 to 16 | one at the end of each step |

An unknown appetite always means Large, also when the user wants to look at data first. When an answer shows that the idea is bigger than its size, say so in one line and move it up one size.

At every size, draft before you ask:

1. Ask only what the user's words cannot give. Every size asks for the problem, the appetite, what gets better and how the user will see it (with one precision follow-up when it is vague), the riskiest guess ("What are you least sure about for this to work?"), what the user will do if that guess is wrong, and the first action with when it starts. Medium and Large also ask what the user will do if the guess is right, in its own question. Only the user makes a decision: never draft one, also when it looks obvious, such as "go on with the idea". On a Small idea, write the decision for a right guess only when the user's words give it, and leave it out otherwise; do not ask for it.
2. Draft the rest from the user's own words and mark it `(suggested)`: who has it, the way they work now, doing nothing, limits, What I need, Done when, and the test block when the riskiest guess must be checked first. In the test block, draft the time box as the appetite in the user's words (a shorter part only when the user named it, never a longer or new duration) and the expectations from the riskiest guess. Write each decision as the user gave it: deciding before the test keeps the result honest. When the user does not know what they will do, write "unknown"; do not turn a "maybe" or "probably" into a firm decision. Write "unknown" for any other part their words do not cover, and write limits the user did not mention as "none named", not "none".
3. Never ask for a drafted field one by one. Show every draft in a playback; the user confirms or corrects it there.
4. Before each playback, check every draft against the user's words. Remove each number, duration, date, name or step that they did not say, or write "unknown" in its place.
5. In the playback, list the user's own answers first. Then list the drafts under "Drafted from your words", each with its source: the user's words it came from in quotes, or "your appetite" or "your plan" for a draft built from those. A new detail then stands out before the user says "Yes". One playback is one question that covers all its items; never split it into parts. When the user corrects an item, apply the change and say so in one line, without a new playback, unless the change alters another draft.
6. Medium and Large also ask the user to split the idea into results and to pick the Now result, unless the user's words already name the result that comes first. List the other results under Next in the order the user named them, without ranking them, and move a result to Later only when the user says so. Confirm the list in the playback. Large also uses the assumption map when there are several guesses.
7. Small keeps the note small: step 2 holds only the riskiest guess, with no claims table and no ratings, and the plan holds only the Now result unless the user names more results.
8. Check precision only for the words that a Done when, a test or the wanted change depends on.
9. A draft stays `(suggested)` until a playback confirms it. The question counts are targets, not limits: ask more when precision needs it, and never invent to stay under them.

## How to choose the next question

1. Read all the context first: the idea text, pasted text, files and linked notes. Put what it says into the note marked `(suggested)`.
2. Keep a list of the open items of the current step. An item is open when it is missing, vague, `(suggested)` or in conflict with another item.
3. Ask about the open item whose answer would most change the note: the Now result, its Done when, the first action, the riskiest guess or the split. Prefer the item the user is least sure about.
4. Skip an item whose answer would change nothing in the note. Never ask about an item that is already confirmed or marked "unknown".
5. Pick the technique that fits the situation (table below).
6. Write the answer into the note at once.
7. Play back at the points that the size sets (table above): list the items and every draft in short lines, and ask "Is this right?" with the answers "Yes" and "Change an item". This confirms the `(suggested)` items. Move on only after "Yes".

## How to ask

- One question per turn: one sentence about one item, with one question mark. Label it with the step ("Step 1 of 4"), and name the note item it fills ("Problem"). Do not join two questions with "and", and do not list sub-questions.
- When an answer has several vague parts ("faster and better"), ask about the part that changes the plan most first, and about the next part in a later turn.
- Ask it open when the user's words do not suggest an answer yet ("What happens today when you need a saved link?"). Do not make up answer options for an open question.
- Otherwise offer up to 3 answers built from the user's own words. Quote the suggested one from their context, so that a "yes" confirms it fast. Always add "unknown". The user can also write their own answer.
- In Claude Code, ask a question with answers through AskUserQuestion, with exactly one question in the call. Use the header "Step <n> of 4", 2 to 4 options with labels of 1 to 5 words, the suggested option first and "Unknown" last. Put a long quote in the option's description, not in its label. The user's own answer comes through "Other".
- Ask an open question in plain text and end the turn: AskUserQuestion needs answer options. In other agents, write the options as a numbered list, add a line for a free answer, and end the turn.
- End the turn with that one question. Do not preview the next question.
- Keep the question short and concrete. Explain a method name the first time ("an assumption map sorts guesses by how much they matter and how much evidence they have").

## Precision checks

A vague answer gets a follow-up before the item counts as confirmed. Each follow-up is one question about one part:

| The answer has | Ask one of these, the one that changes the plan most |
| :-- | :-- |
| Words such as "better", "faster", "easier", "soon", "users", "some", "most", "many", "a lot" | Who exactly? How much? By when? How will you see it? |
| A goal without a measure | Where is it today? What is the target? When will you check it? |
| A problem without evidence | When did it last happen? (then, in a later turn: what did it cost?) |
| A Done when that nobody can see or check | What will you see when it is done? |
| A first action that takes more than 10 minutes, or is not physical | What is the first physical step, such as "open the notes app"? |
| A test without expected results | What do you expect if the guess is right? (then, in later turns: if it is wrong, and what you will do after each) |

Every word that a Done when, a test or a target depends on must be checkable. Ask the user to define it: "night" becomes which hours, "fixed itself" becomes what the data shows, "exhausted" becomes how you will find out. Ask this before the plan is finished.

If an answer is still vague after its follow-ups, record it as the user said it, mark it "unclear", and ask about it in the step playback.

## Questions not to ask

- An item the user already stated clearly, in any words. Record it from their words instead, for example the cost of doing nothing when they already described what happens today.
- How much a guess matters, or how much evidence it has, when the user already said it ("I have never measured it" means the evidence is none).
- Which guess is the riskiest when there is only one guess. That guess is the riskiest.
- How much a guess matters, when no answer could change which guess is the riskiest.
- A playback when every item of the step came from a direct answer in this step and nothing is `(suggested)`, `unclear` or rephrased by you. Move on and say so in one line.
- Anything whose answer would not change the note.

Write each item in the user's words. A draft restates what the user said; it adds no details, orders or dependencies to a result, and no rules, numbers, time boxes, safety steps or calculations of your own. When the plan needs something the user's words do not give, ask for it or write "unknown".

## Techniques by situation

| Situation | Technique | Example question |
| :-- | :-- | :-- |
| The idea is a solution ("build an app that ...") | Problem framing: find the problem behind the solution | "What problem would this app solve, and for whom?" |
| An answer has vague words | Unclear-word check, one part per turn | "How much faster?" |
| No evidence that the problem is real | Ask for the last concrete case, or plan a small test that collects evidence | "When did this last happen?" |
| Several possible causes | List the causes as guesses and test the one with the most effect | "Which of these causes, if it is true, changes the plan most?" |
| Only one option | Add the way the user works now and doing nothing | "What do you do today instead?" |
| Many guesses | Assumption map: for each guess, does it matter a lot or a little, and is the evidence none, weak or strong | "How much evidence do you have that you would use it daily: none, weak or strong?" |
| The idea is large | Story slicing: thin results the user can see work, then "which one do you need first?". Appetite: how much time the idea is worth | "How much time is this idea worth to you before you decide again?" |
| A guess must be checked before work | Test card: what you expect if the guess is right and if it is wrong, and what you will do after each, all set before the test | "If the search finds the link, what will you do next?" |
| The Now result has no first step | Next physical action, broken down until it takes under 10 minutes, with a when-and-where plan | "When and where will you do that first step?" |
| The user says "unknown" | Record it once. When it blocks the plan, the Now result becomes "find out X", with the decision it unlocks, the smallest evidence and a time limit that the user sets | "What is the smallest thing that would tell you?" |
| The context or the user's answers seem to answer an item | Draft it, mark it `(suggested)` and confirm it in the next playback | "Is this right?" |
| The user comes back after acting | Ask what happened against what they expected, then apply the decision they set before the test | "Done, not done, or stuck?" |

Do not split by layers ("database", "API", "UI"): each result must be something the user can see work. Do not accept "build it first and see". Do not set a fixed number of questions.

## The four steps

### 1. What do I want to change?

Save the raw idea word for word before the first question. Ask what problem the idea solves; right after it, ask the appetite and pick the size (see Size the interview). Then ask what should get better, and draft who has the problem from the user's words. If the idea is a solution, first ask what problem it solves. Collect at least 3 options: the idea, the way the user works now, and doing nothing or waiting. Draft the last two from the user's words; ask only when their words say nothing about them. Draft the limits from their words too, and ask about limits only when the idea touches safety, privacy, money or other people.

Required items: raw idea, problem, who has it, what gets better and how the user will see it, 3 options, limits.

The step is done when the user can say why the idea matters without new guesses.

### 2. What must be true?

Ask what must be true for the idea to help, or what the user is least sure about. Label each condition: fact (with its source), guess or unknown. On a Large idea with several guesses, ask whether each matters a lot or a little and whether the evidence is none, weak or strong, and suggest the riskiest guess (it matters a lot and has the least evidence). With one guess, that guess is the riskiest.

Required items: the conditions, the label and source of each, the riskiest guess, and on a Large idea with several guesses, matters and evidence for each.

If who has the problem, the problem or the change is still unknown, the Now result in step 3 is "find out X", not "build X".

### 3. What can I do now?

The appetite is already known from step 1. It sets the size of the results and the limit of any test.

Split the idea when one of these holds:

- it holds more than one result that the user can finish and check on its own;
- it does not fit the appetite, the time the user says it is worth;
- no first physical action under 10 minutes can be named.

To split, ask the user for 3 to 5 results they can make, test or decide. Suggest results from their words when they have none. Each result is a thin slice the user can see work.

Plan only the Now result in detail. For a Next or Later result, record its name, its place, and what it needs first only as the user says it. Ask "Does this need anything first?" only when the order is unclear. A Next result gets its Done when and its action card when it moves to Now.

Ask the user to pick the Now result. Suggest one, but let them choose. Place the results:

- Now: 1 result. Work on one thing at a time.
- Next: up to 5 results, in order.
- Later: the rest.

The Now result always gets an action card: Result I want, What I need, Done when, First action (one physical step under 10 minutes), and When I start, always in the form "When <time or place>, I will <first action>". Keep that if-then form: it is what makes the plan work.

When a guess must be checked before more work, the Now result is that test, and it also gets a test block: the guess, how long the test may take within the appetite, what the user expects if it is right, what they expect if it is wrong, and what they will do after each result, all set before the test. Draft its time box and expectations from the user's words, as "Size the interview" says, ask for the decisions that the size asks, and confirm the block in the playback.

Required items: the appetite, the results and their places, what each needs first when the user knows it, every field of the action card, and every field of the test block when there is one.

### 4. What did I learn?

This step runs when the user comes back. Show the next action from the note and ask "Done, not done, or stuck?". Record what the user did and what happened, or "not checked" if they did not run it. Record "done" apart from "as expected": an action can be done even when it did not bring the wanted change. Apply the decision the user set before the test: continue, change the idea, test again or stop. Then ask for the next action. When the Now result is finished, ask which Next result moves to Now, and ask for its action card.

Required items: what the user did, what happened, done, as expected, the decision, the next action.

## When to stop asking

Stop asking and finish the plan when both are true:

- who has the problem, the problem, its evidence, what is in and out, the wanted change and how to see it are clear or marked "unknown" by the user, and so is every field of the Now result's action card and test block;
- no open question's answer would change those items.

Then write the plan into the note, draw the maps, and reply with the one next action, its Done when and the note path. Offer a Miro board in one line when Miro tools are connected.

## After the plan

Add one line for each of these only when it fits the idea:

- `agent-issues` to turn the Next results into GitHub issues;
- `rightsize write` for a design doc, pitch or decision record;
- `plan-critic` to review a technical plan;
- `ship-it` to build an action in a repository.

## Safety

When a test could harm someone, break the law or cost more than the user can afford, stop and tell them to get proper help first. When an action is hard to undo, suggest a safer test first. Give no medical, legal or financial advice.
