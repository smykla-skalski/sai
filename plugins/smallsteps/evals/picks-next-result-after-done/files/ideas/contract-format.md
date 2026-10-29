---
step: 3 of 4
updated: 2026-10-28
---

## Goal

A contract format that people can understand and that a future system can use to check work.

## Idea

**Raw idea:** define a contract format that people understand and a system checks automatically

A Markdown document with YAML front matter: YAML holds the facts a tool can read, and Markdown explains the purpose.

## Process

**Now:** an example of one operation with its inputs and results

**Done when:** the example names one operation, its inputs with their types and its results, and lists the open gaps

**Need:** the candidate format and one real operation

**Main uncertainty:** a system can check a contract written in this format. Evidence: none, the system does not exist yet. Matters: a lot

**Guesses:**

- the team can understand an example contract: guess. Evidence: none, no reader test yet. Matters: a lot

**Decisions:** Use Markdown with YAML front matter for the candidate. Earlier, consider YAML alone; the user changed that choice to keep the explanation in Markdown.

**Checks:**

- Author reviewed a sample YAML file: done. Showed: the author could write the fields. Did not prove: another reader can understand it.

**Next results:**

- A review of the example for gaps, needs the example
- Rules that a future system could check, needs the review

**Later:**

- A system that checks contracts automatically, needs the rules

**Next action:** When I sit at my desk tomorrow at 9:00, I will open the payment notes and copy one operation name into a new file.

### Background

**Problem:** our contracts are free text, so people read them differently and nothing can check them. It affects my team.

**Appetite:** as much time as needed

**Size:** large, because there is no time limit

**Limits:** an author needs only simple Markdown

**Other options:** the way I work now: free-text contracts in the wiki. Do nothing or wait: contracts stay free text.
