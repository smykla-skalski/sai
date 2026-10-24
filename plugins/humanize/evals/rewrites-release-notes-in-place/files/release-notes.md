# Release Notes — Version 2.4.0

We're thrilled to announce Version 2.4.0, a groundbreaking release that serves as a testament to our unwavering commitment to developer experience. This update delves into the heart of reliability, showcasing how thoughtful engineering can enhance every workflow in today's rapidly evolving landscape.

## Key Highlights

- **Smarter Retries:** The new `--retry-limit` flag lets you cap retries per request (default: 5), fostering more predictable behavior across distributed systems.
- **Faster Startup:** Cold start time drops from 1.8s to 0.9s, marking a pivotal moment for teams that value speed, efficiency, and scalability.
- **Postgres 16 Support:** The driver now supports Postgres 16 — a crucial step that underscores our dedication to staying current.

## Breaking Changes

Additionally, the deprecated `connect_legacy()` function has been removed. It's important to note that projects still calling it will fail at build time, so migrate to `connect()` before upgrading.

In conclusion, Version 2.4.0 represents not just an update, but a bold step toward the future. The future looks bright, and we can't wait to see what you build! 🚀

I hope this helps! Let me know if you have any questions.
