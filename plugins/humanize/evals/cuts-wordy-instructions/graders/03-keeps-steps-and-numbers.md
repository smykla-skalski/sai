---
type: regex
pattern: '^(?=[\s\S]*/etc/app/config\.yaml)(?=[\s\S]*sudo systemctl restart app)(?=[\s\S]*up to 30\s?(seconds|s\b))(?=[\s\S]*\bshould\b)'
flags: i
target:
  source: file
  path: deploy.md
---

deploy.md keeps the config path, the restart command, up to 30 seconds and should
