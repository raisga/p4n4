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
- `raisga/p4n4-lib`
- `raisga/p4n4-hw`
- `raisga/p4n4-cli`
- `raisga/p4n4-api`
- `raisga/p4n4-dashboard`
- `raisga/p4n4-templates`
- `raisga/p4n4-emu`
- `raisga/p4n4-docs`

## Security best practices

When deploying p4n4:

1. Run p4n4 0.2.x on trusted networks only. Its services listen on all interfaces, and
   several of them (MQTT, InfluxDB, Ollama, n8n) aren't hardened for untrusted networks yet.
2. Use the secrets `p4n4 init` generates, or change every default password in `.env`
   before the first run.
3. Do not expose services directly to the internet without a reverse proxy + TLS.
4. `p4n4 secret rotate` only updates `.env`. InfluxDB, Grafana and n8n read most of those
   values at first setup only, so rotate those credentials inside the services as well.
5. Review Mosquitto ACL rules for your deployment.
