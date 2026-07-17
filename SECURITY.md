# Security Policy

## Supported versions

NexusIQ is developed as a rolling release. Security fixes are applied to the
`main` branch only; there are no long-term support branches.

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ |
| older commits | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report privately through GitHub's built-in flow:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability** (Private Vulnerability Reporting).
3. Include a description, reproduction steps, affected component, and impact.

We aim to acknowledge a report within **72 hours** and to provide a remediation
timeline after triage. Please give us a reasonable window to ship a fix before
any public disclosure.

## Scope

In scope: the FastAPI backend (`backend/`), the Next.js frontend (`frontend/`),
authentication and session handling, rate limiting, SSRF guards, and the
data-ingestion pipeline.

Out of scope: attacks requiring local access to a developer machine, issues in
third-party services (Yahoo Finance, Google, Binance, etc.), and denial of
service through unrealistic request volume against a local dev instance.

## Handling of secrets

This repository never commits secrets. `.env` files are git-ignored; only
`*.env.example` templates with empty/placeholder values are tracked. If you
believe a secret has been committed, report it privately as above and do **not**
reference the value in a public issue or pull request.
