# Security

## Default credentials

All default passwords (`changeme`, `adminpassword`) are **placeholders only**.
Change them before first run:

```bash
# Auto-generate strong secrets
p4n4 secret rotate
```

Or set them manually in `.env`.

## Network exposure

By default, all services bind to `0.0.0.0`. In production:

- Place a reverse proxy (Nginx, Caddy, Traefik) in front with TLS termination.
- Restrict inbound ports with firewall rules.
- Do not expose InfluxDB (8086) or Mosquitto (1883) directly to the internet.

## Mosquitto authentication

The default `mosquitto.conf` ships with `allow_anonymous true` for easy development.
For production, disable anonymous access and use password + ACL files:

```conf
allow_anonymous false
password_file /mosquitto/config/passwd
acl_file /mosquitto/config/acl
```

Generate the password file:

```bash
mosquitto_passwd -c config/mosquitto/passwd <username>
```

## Secret rotation

Rotate all secrets periodically:

```bash
p4n4 secret rotate
p4n4 down && p4n4 up
```

## `.env` file

- Never commit `.env` to version control — it is in `.gitignore`.
- Only `.env.example` (with placeholder values) is committed.
- Use `p4n4 secret show` to audit current secrets (values are masked).

## Reporting vulnerabilities

See [SECURITY.md](https://github.com/raisga/p4n4/blob/main/SECURITY.md) in the umbrella repo.
