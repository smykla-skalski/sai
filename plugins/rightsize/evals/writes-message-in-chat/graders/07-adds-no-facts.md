---
type: llm
focus: last_message
weight: 1
---

The request, word for word:

> /rightsize write a short message for the #eng Slack channel about the decision: help-center search will use Postgres full-text search instead of Elasticsearch. About 4,000 articles, English only, about 2,000 searches a day. We give up fuzzy matching and better ranking, and we avoid running a new cluster that none of us has run in production. Kasia decided. We look again if search-quality complaints keep coming after launch or we add a second language. Ask people to send search complaints to #help-center by Friday.

PASS if the message states no fact that the request does not give, such as a date other than Friday, a metric, a cost, a launch date or another person.
FAIL if it adds any such fact.
