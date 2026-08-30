---
paths:
  - "**/.env*"
  - "**/secrets*"
  - "**/*credentials*"
  - "**/id_rsa*"
  - "**/id_ed25519*"
  - "**/*.pem"
  - "**/*.key"
  - "**/kubeconfig*"
  - "**/application-prod*"
  - "**/values-prod.yaml"
  - "**/SECRETS.md"
---

# Secrets and sensitive files

Loads when env, key, or prod-values files are in play.

- Never commit private keys, `.env` with real values, cloud access keys, or dumped kubeconfigs. Rotate anything that was pasted into chat.
- Example files use `__SET_ME__` or empty placeholders. `SECRETS.md` lists names only, not values.
- Do not print secrets in logs, test output, or README snippets. Redact in screenshots.
- Prod Helm values and `application-prod.yml` get the same treatment as `.env`.
- If a secret is already in git history, stop and tell the user — do not “fix” by deleting the file in a follow-up commit alone.
