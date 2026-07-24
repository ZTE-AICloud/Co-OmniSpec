# Security

This document explains how to report a vulnerability to the Co-OmniSpec
maintainers and what to do if you accidentally commit a credential or other
sensitive material to this repository.

> **中文说明** — 报告漏洞前请先去除任何公司内部主机名、内网地址、token
> 等敏感信息。建议使用英文撰写初始报告。

---

## Supported versions

Only the latest tagged release of each plugin receives security fixes. Older
versions are not patched; please upgrade first.

| Plugin | Latest | Security-fixed versions |
|--------|--------|-------------------------|
| `omni-dsdd` | the most recent `omni-dsdd-vX.Y.Z` tag | latest only |
| `omni-reverse` | the most recent `omni-reverse-vX.Y.Z` tag | latest only |

## Reporting a vulnerability

Please report vulnerabilities **privately** through GitHub Security Advisories
so we can work on a fix before public disclosure:

1. Go to <https://github.com/ZTE-AICloud/Co-OmniSpec/security/advisories/new>.
2. Fill in the affected plugin(s), the affected versions, a minimal
   reproduction, and the impact you observed.
3. Wait for an acknowledgement before posting details publicly.

If GitHub Security Advisories is unavailable, open a GitHub issue that **omits
all sensitive details** (no real tokens, no internal URLs, no stack traces
embedding credentials) and request a private channel.

### What to include

- Plugin name(s) and version(s) (`omni-dsdd` / `omni-reverse`).
- A minimal, sanitized reproduction (commands run, expected vs. actual
  behaviour).
- The impact (information disclosure, RCE, privilege escalation, …).
- Whether the issue is currently being exploited.

### What **not** to include

- Real credentials, tokens, API keys, cookies, SSH keys, or PII.
- Internal hostnames, intranet URLs, VPN endpoints, staging URLs.
- Captured network traffic. Sanitize or summarise instead.

Use placeholders such as `PLACEHOLDER_TOKEN`, `PLACEHOLDER_HOST`,
`PLACEHOLDER_URL` whenever an example is necessary.

## Coordinated disclosure timeline

- **Day 0** — You file the advisory.
- **Within 5 business days** — Maintainers acknowledge and assign an owner.
- **Within 30 days** — Maintainers either publish a fix or set a disclosure
  date with the reporter.
- **After the fix ships** — Coordinated public disclosure in a GitHub Security
  Advisory, plus a release note on the affected plugin.

## What to do if you accidentally committed a credential

Treat the credential as compromised the moment it lands in the repository's
history. **Do not** try to "rewrite the commit away quietly" — the secret can
already have been scraped by automated scanners.

1. **Rotate the credential first.** Generate a new token/key/password
   immediately, even before telling anyone.
2. **Invalidate the old credential.** Revoke it server-side and look for signs
   of abuse (audit logs, signed-in sessions, repo clones).
3. **Notify the right owners.** Tell the operator that issued the credential
   (cloud provider, internal IdP, package registry, …). The maintainers of
   Co-OmniSpec do not own your secrets.
4. **Purge history only after rotation.** Use
   [`git filter-repo`](https://github.com/newren/git-filter-repo) or
   `BFG Repo-Cleaner` to remove the secret from history, then force-push and
   ask any collaborator to re-clone.
5. **Open a private report** through GitHub Security Advisories (see above) if
   the commit was already public, so we can document the incident and remind
   other contributors.
6. **Audit downstream.** If a release was published before the rotation, file
   a public incident report and notify downstream consumers.

## Hardening tips for users

- Treat every artefact under `.omni-infra/` and `changes/` as project
  artefacts; they may contain function names, feature descriptions, or quoted
  source code from your codebase. Add `.omni-infra/` to your local
  `.gitignore` if you do not want them committed.
- The agents operating on this plugin run with the same privileges as your
  shell. Do not point them at repositories containing credentials in clear
  text.
- Pin the plugin version. Prefer `omni-dsdd-vX.Y.Z` tags over `main` for
  production use.

## Acknowledgements

We follow responsible-disclosure norms. Reporters who follow this policy will
be credited in the release notes (unless they prefer to remain anonymous) and
will not face legal action for their good-faith research.
