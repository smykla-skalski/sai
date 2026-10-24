# Local setup

You'll need Go 1.23 and Docker. Clone the repo, then run `make dev`. The first build takes about two minutes — it pulls the base images.

If `make dev` fails with "port 5432 in use", stop your local Postgres or set `DB_PORT` to another port.

Tests run with `make test`. They need Docker too, so don't stop it.
