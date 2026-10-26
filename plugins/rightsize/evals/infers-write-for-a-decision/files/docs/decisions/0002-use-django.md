# 2. Use Django for the help center

Date: 2026-03-09

## Status

Accepted

## Context

All three of us know Django well, and the help center is a content site with an admin area.

## Decision

We build the help center as one Django app with one Postgres database.

## Consequences

The Django admin gives editors a working back office on day one. A second service needs its own decision record.
