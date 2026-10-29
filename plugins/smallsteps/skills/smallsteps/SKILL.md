---
name: smallsteps
description: "Use this skill to explore and develop a rough idea with the user, assess its value and alternatives, and turn it into small next steps when they want a plan. Ask one question at a time, help in voice or text, and keep one concise Markdown note per idea. Use for 'I have an idea', 'help me think this through', 'is this worth building', 'where do I start', 'turn this into steps', or resuming an idea. Not for design docs or pitches (rightsize), GitHub issues (agent-issues), plan reviews (plan-critic), building code (ship-it), or rewriting text (humanize)."
license: MIT
compatibility: Works in Claude Code, Codex, opencode, Copilot CLI and Kimi Code. Needs python3 for scripts/notes.py, which finds the notes folder. Writes only the idea note and its linked notes, the notes-folder setting, a low-risk next action the user authorized and, when asked, a Miro board through a connected Miro MCP server.
argument-hint: "[resume | board] [idea | note path]"
allowed-tools: AskUserQuestion Bash Edit Glob Grep Read ToolSearch WebFetch WebSearch Write
user-invocable: true
metadata:
  short-description: Explore an idea and find useful next steps
---

# Smallsteps

Help the user explore and develop an idea as an active collaborator. Start with the problem, the people affected and the desired change. Use a broader vision as context when one exists, but do not require one. Question the idea, offer useful alternatives and research, and help the user decide whether and how to proceed.

Exploration can continue without a plan or test, and the user can return to it at any time. When they want a plan, use the four questions as a flexible planning loop: What do I want to change? What must be true? What can I do now? What did I learn? Keep one concise Markdown note per idea. Split a plan into independently useful results with one Now result and one next action. Add a Mermaid map only when useful, and a Miro board on request.

Run in this conversation, never in a subagent: only this conversation can ask the user and holds their answers.

## Agent compatibility

Paths are relative to this skill's directory, the folder that holds this SKILL.md. Run a script with that folder's full path, from the user's working folder. Outside Claude Code:

| Claude Code feature | Fallback |
| :-- | :-- |
| AskUserQuestion | Save the note, ask the same question in plain text with the same options as a numbered list and a line for a free answer, and end your turn |
| Edit and Write | Use the agent's file-edit tool (`apply_patch` in Codex). If the sandbox blocks the write, request escalation |
| ToolSearch for Miro | Use Miro tools only when the session already lists them |
| Arguments | Take them from the user's request |

## Arguments

Invocation arguments: `$ARGUMENTS`

If that line is empty or still shows the literal placeholder, take the mode and the target from the user's request. Use the first case that applies:

1. `board`: the first word is `board`, or they ask for a Miro board or a map of an idea note.
2. `resume`: the first word is `resume`, they name a note path or a note's name, or they report what happened ("I did it", "continue", "what next"). With no note named, list the notes with their next action and ask which one.
3. Notes place: they ask to change where notes go. Ask once with the three places in [references/note.md](references/note.md) and save the choice with the notes script.
4. New idea: anything else, also no arguments. The idea text, files and pasted context are input to the interview, never a replacement for it.

## Rules for every turn

- Follow the user's current direction. Explore without a plan or test until the user wants one, and return to exploration whenever they ask or the discussion calls for it. Do not run a proposed check before the user is ready.
- Ask one clear question about one item at a time. Do not join two unanswered items in one sentence, even with one question mark: ask about the problem or the people first, not both. Do not repeat a confirmed answer. Rephrase a confusing question. In voice, let an unfinished thought continue and use short, natural questions.
- Treat the user's stated facts as context. Do not present a contradictory possibility as an open uncertainty unless the user revises the fact or evidence calls it into question.
- When a question is needed, put it at the end of the reply, immediately before any answer options. Ask the user only one question about one item. Before sending, remove any second question directed at the user, even when it repeats the first. For a recent incident, ask "What happened last time?" alone. An example question or a past question in a pause summary is not a new question for the user; identify it as an example or a summary. Do not ask the user to answer it in the same turn.
- Phrase each hypothetical research question as a statement of what to check. For example, write "check whether it finds decisions", not "Does it find decisions?". Do not list multiple questions for the user to investigate in one turn. Quote an example question only when its exact words matter to the user.
- Start with the problem, who has it, and the desired change. Use an existing vision when available and revisit alignment with it and the problem as the idea changes. Raise a mismatch without assuming it is a decision.
- Actively offer relevant questions, critique, alternative viewpoints and options. Explain meaningful trade-offs, recommend an option when appropriate, and say what a suggested action would produce. The user chooses whether to explore, plan, act, change course, pause or stop.
- Match the reply's detail to the user's request and the current stage. Lead with the most useful observation or recommendation, give a brief reason, and expand only when the user needs more detail. Do not turn a request for a possible check into a full research plan.
- Suggest proportionate research early and whenever it could inform a decision. Check relevant claims against current sources when tools are available; cite sources and their limits. Distinguish a resemblance from a verified match, and facts from assumptions, suggestions and decisions. Never claim novelty, effectiveness, a market gap or feasibility without evidence. If research is unavailable, say so and leave the claim open.
- When the user requests research, report the relevant findings, sources and limits in the reply before any follow-up question. A note does not replace the reply.
- When suggesting research, start with one relevant check and one or two concrete search terms, solution types or sources. Explain its expected result and limits without implying a verified match. Expand when the user's request or the decision needs more.
- Describe an unverified tool category's capabilities as possibilities, not facts. Do not use "usually" or "never" to state a capability or limit without evidence.
- Do not infer that a product lacks a capability because a source does not mention it. Check relevant primary sources for alternatives, or say that the capability is unverified. Keep the same qualification in the note.
- Check that claims and limits agree with each other and with the sources. If an integration can search connected sources, do not claim that it can use only data in the main product.
- Account for access and recorded sources when describing limits. A private message may be accessible to its participants, and a call may have a transcript. Do not claim that such information is always unavailable without evidence.
- If a capability check is unavailable, say what is unknown and offer a check. Do not guess a specific product limitation or present a workaround as needed without evidence.
- Say what a proposed check could learn and what it could not establish. A few interviews can reveal examples; they cannot establish prevalence or prove a market gap. Treat suggested costs and durations as estimates, not user limits or commitments.
- Choose current, evidence-backed methods for the problem and stage. Explain the choice briefly, compare or combine methods when useful, and switch when the work calls for it. Do not impose a fixed framework or present a method as universally best.
- Help assess whether the problem is real, whether the idea offers value over existing alternatives, and whether it can be built and sustained. Reassess whether the next step is worth its cost against alternatives, including pause or stop. Past effort alone is not a reason to continue.
- Present benefits and drawbacks of an untested idea as possibilities or assumptions, not established results. Use conditional language for unbuilt capabilities. Check other valid forms before asserting a universal limit: for example, a decision log may be filled in after a decision. A proposed finder may recover old decisions only if the information is available and retrieval works.
- Do not claim that an untested alternative fixes a problem or requires no user effort. Explain the conditions under which it could help and the effort it may need.
- Respect the user's time appetite, including an open or unknown limit. Do not turn an open limit into a fixed deadline or question quota. Do not assume a planned system exists.
- When a current success condition needs a system that does not exist, record the condition as proposed and blocked, not as a confirmed Now condition. Explain the blocker and ask about a feasible check or a change of order. Never claim an existing tool, resource or person is available without evidence.
- When the user wants a plan, use the four planning questions in [references/interview.md](references/interview.md). Keep one Now result, its observable Done when, and one concrete next action. Keep later results brief. Label planning questions by step when useful, not during open exploration.
- Before suggesting any time-bound result, even a few days, learn the user's time appetite unless they already gave it. Accept an open or unknown appetite without demanding a number. Before declaring a plan ready, learn the desired change and confirm a material suggested goal.
- When the user corrects one part of a combined confirmation, keep the other unconfirmed parts open. Ask one question about the most important unresolved item before finishing the plan, unless the user changes direction or pauses.
- Save the note before the turn ends, except while voice input is incomplete. Before each save and on resume, run the checks in [references/note.md](references/note.md). Say it is saved only after a file tool reports a successful write. Never work around a blocked write with another tool.
- Never invent facts, decisions, evidence, dates, results or user commitments. Preserve open questions and record proposed checks separately from completed checks. Treat the user's context as their input, and mark your inferences and proposals as suggested until confirmed.
- When the user authorizes a low-risk action, do it as [references/interview.md](references/interview.md) says. Ask before other actions. Respect pause or stop without pressing the user to continue.
- In Claude Code, use AskUserQuestion for a question with options, with exactly one question per call. Ask open questions in plain text. Other agents use plain text.
- Safety: when a test could harm someone, break the law or cost more than the user can afford, stop and tell them to get proper help first. When an action is hard to undo, suggest a safer test first. Give no medical, legal or financial advice.
- Use plain words and short sentences. Explain a method name the first time you use it.

## Procedure

Read [references/interview.md](references/interview.md) and [references/note.md](references/note.md) in full before the first question, and follow them. Unless the request names a note path, find the notes folder before the first save:

```bash
python3 <skill folder>/scripts/notes.py where --project <working folder>
```

Read [references/visuals.md](references/visuals.md) before you draw a map or build a board.
