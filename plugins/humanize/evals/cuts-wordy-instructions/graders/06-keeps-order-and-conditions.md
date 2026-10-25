---
type: llm
focus:
  source: file
  path: deploy.md
weight: 1
---

The original deploy.md says: back up the configuration file at /etc/app/config.yaml before deploying; then run `sudo systemctl restart app` in a terminal to restart the service; the restart can take up to 30 seconds, and during that time the service cannot accept incoming requests; if the service fails to start, you should decide whether to restore the backup.

PASS if the file keeps all of this: the backup comes before the deployment, the restart takes "up to" 30 seconds (not exactly 30), the service cannot accept requests during the restart, and the restore stays a decision the reader should make only if the service fails to start (not an order to restore). It must add no command, path, time or step the original lacks.
FAIL if any of this is missing or changed, or anything new is added.
