# Security Policy

## Supported Versions

The AI Operations Platform is in early public release (`0.1.0`). Security fixes
are applied to the `main` branch. There is no LTS branch yet.

| Version | Supported          |
|---------|--------------------|
| `main`  | :white_check_mark: |
| `< 0.1` | :x:                |

## Reporting a Vulnerability

**Please do not file public GitHub issues for security vulnerabilities.**

Instead, report privately using one of these channels:

1. GitHub Private Vulnerability Reporting: open the **Security** tab of this
   repository and click **Report a vulnerability**. This is the preferred channel.
2. Email the maintainers (replace with the address you wish to publish before
   publishing the repo): `security@example.com`.

When reporting, please include:

- A description of the vulnerability and its impact.
- Steps to reproduce or a proof-of-concept.
- The affected commit, tag, or version.
- Any suggested mitigation, if known.

## What to expect

- Acknowledgement of your report within **5 business days**.
- A triage and severity assessment within **10 business days**.
- A coordinated fix and disclosure timeline shared with the reporter.
- Credit in the changelog (with your permission) once the fix is released.

## Out of scope

The following are not considered vulnerabilities for the purpose of this policy:

- Findings that require physical access to a developer machine.
- Issues in third-party dependencies that already have an upstream advisory;
  please report those upstream first, then notify us.
- Theoretical issues without a demonstrable exploit path.

## Hardening guidance for operators

Operators deploying the platform should review:

- [`docs/deployment/`](docs/deployment/) — deployment hardening checklists.
- [`docs/development/adrs/ADR-048-Secure-Logging-Redaction.md`](docs/development/adrs/ADR-048-Secure-Logging-Redaction.md)
  — logging redaction rules; set `REDACT_LOGS=true` in production.
- [`docs/development/adrs/ADR-061-HashiCorp-Vault-Secrets-Integration.md`](docs/development/adrs/ADR-061-HashiCorp-Vault-Secrets-Integration.md)
  — secret-management guidance; do not store production secrets in `.env`
  files.
- [`config/env/env.template`](config/env/env.template) — required environment
  variables; rotate `JWT_SECRET`, `POSTGRES_PASSWORD`, and `TOOL_SECRETS_KEY`
  before any shared deployment.
