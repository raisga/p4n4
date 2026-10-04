**p4n4-dashboard 1.1.0** adds a web service and sign-in with p4n4-api accounts. The desktop and mobile apps carry on as before.

```bash
docker pull ghcr.io/raisga/p4n4-dashboard:1.1.0    # amd64 and arm64
```

> **Trusted networks only,** like the rest of p4n4 0.2.x. Keep port 8088 on your LAN. If it must be reachable from elsewhere, serve it over HTTPS (`docker-compose.tls.yml`) with basic auth on.

## Highlights

- **Web service on port 8088:** an nginx-unprivileged image that serves the web build and proxies p4n4-api (`/api/`), Ollama (`/ollama/`) and Letta (`/letta/`) on one origin. It adds runtime `config.json` defaults, `/healthz`, security headers, optional HTTPS (`docker-compose.tls.yml`) and optional basic auth. It runs with a read-only filesystem and no capabilities.
- **Sign-in with p4n4-api accounts.** The role picks the view:
  - **Admin:** every tab, client deployments, stack controls;
  - **Power:** the tabs an admin enables, with no stack controls;
  - **Normie:** a simple "everything is working / something needs attention" home.

  Refresh tokens are kept in secure storage.
- **Admin settings:**
  - **Views:** each view's tabs, with a live preview;
  - **Users:** p4n4-api accounts and their roles;
  - **Diagnostics:** sign-in, token and service checks.
- **Themes:** client brands are installed from a project's `.p4n4.json` (`dashboard.theme`). Only the applied brand is bundled.
- **Project-aware:** reads `.p4n4.json` through p4n4-api to narrow the stacks and tabs it shows and to set the Grafana page.

## Compatibility

- Use with **p4n4-api 0.1.0**: the normie view needs its `normie` role.
- `p4n4 init --layer dashboard` (**CLI 0.2.0**) scaffolds it with this version pinned.
- Embedding Grafana needs `GRAFANA_ALLOW_EMBEDDING=true` in the IoT `.env` (`p4n4 init` sets it when the dashboard layer is enabled).

## Limitations

- The Agent tab defaults to Ollama. Letta is optional and off by default in the AI stack, and the Letta client hasn't been run against a real Letta server yet.
