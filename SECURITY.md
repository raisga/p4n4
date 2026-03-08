# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.x (latest) | Yes |

## Reporting a vulnerability

**Do not open a public issue for security vulnerabilities.**

Please report security issues by opening a
[private security advisory](https://github.com/raisga/p4n4/security/advisories/new)
in this repository.

Include:

- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

You can expect an acknowledgement within 48 hours and a status update within 7 days.

## Scope

This policy covers all repositories in the `raisga` organisation:

- `raisga/p4n4`
- `raisga/p4n4-iot`
- `raisga/p4n4-ai`
- `raisga/p4n4-edge`
- `raisga/p4n4-cli`
- `raisga/p4n4-templates`
- `raisga/p4n4-docs`

## Security best practices

When deploying p4n4:

1. Change all default passwords in `.env` before first run.
2. Do not expose services directly to the internet without a reverse proxy + TLS.
3. Use `p4n4 secret rotate` regularly to refresh credentials.
4. Keep Docker images up to date (`p4n4 upgrade`).
5. Review Mosquitto ACL rules for your deployment.
