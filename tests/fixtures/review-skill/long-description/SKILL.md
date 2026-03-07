---
name: long-description
description: This is an extremely long description field that is intentionally written to exceed the 1024 character limit imposed by the agent skills specification. The purpose of this fixture is to verify that the FM-desc-length check correctly identifies descriptions that are too long for efficient auto-invocation matching. When Claude Code loads skill descriptions for auto-invocation, long descriptions waste valuable context window space without improving match accuracy. This description continues with additional filler text to ensure it crosses the threshold. Adding more words here to pad the length. The quick brown fox jumps over the lazy dog. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. This should now be well over the limit.
allowed-tools: Read
user-invocable: true
---

# Long description

This skill has a description exceeding 1024 chars.

## Workflow

1. Read input
2. Process
