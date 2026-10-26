---
tags: [rightsize]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
disallowed_tools: [Bash]
---

/rightsize audit our purchase request process. We want to buy an RPA bot to automate it, does that make sense?

How it works today at our 40-person company:

1. The requester fills in a Word form and emails it to their manager.
2. The manager approves by replying to the email.
3. Finance copies the form into the purchases spreadsheet.
4. The CFO approves every purchase in the spreadsheet, also the $5 ones.
5. Operations places the order and types it again into the accounting system.
6. Operations emails the requester that the order is placed.

A request takes 6 working days on median, and about 1 in 10 has a typo between the form, the spreadsheet and the accounting system. Our auditors require a recorded second approval for every purchase above $1,000. Last year we had 900 requests, and 85 of them were above $1,000.

The plan: an RPA bot copies the Word form into the spreadsheet and the spreadsheet into the accounting system, so that nobody retypes anything.
