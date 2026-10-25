## Summary

This PR introduces a groundbreaking new caching layer for the `/search` endpoint, seamlessly integrating with our existing Redis cluster. It significantly improves performance and makes the search experience more reliable for all users. Additionally, it adds a `SEARCH_CACHE_TTL` setting (default 300 seconds) and fixes the bug where empty queries returned a 500 error.

I hope this helps reviewers understand the change!
