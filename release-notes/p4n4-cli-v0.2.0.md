**p4n4 0.2.0** gives multi-layer projects their own directories, adds the `edge` and `dashboard` layers, and moves the shared logic into p4n4-lib.

```bash
pipx install p4n4==0.2.0    # or: pip install p4n4==0.2.0 (Python 3.11+)
```

> **Trusted networks only.** p4n4 0.2.x is meant for development and trusted local networks. Don't expose its service ports to the internet or to networks you don't control. A security release (0.2.1) follows.

## Highlights

- **Multi-layer projects done right:** `p4n4 init --layer iot,ai` puts each layer in its own directory (`iot/`, `ai/`, …) as a separate Compose project on the shared `p4n4-net` network. `up` and `down` follow dependency order, and `logs`, `status`, `secret` and `validate` work per layer.
- **New layers:**
  - `edge`, the inference runner with ONNX or Edge Impulse models;
  - `dashboard`, the p4n4-dashboard web service on port 8088, which can frame Grafana.

  `--layer all` now includes both.
- **External MQTT broker:** `init` can bridge topics from another broker into the local one (`--mqtt-remote HOST[:PORT]`, with user, password, topics, TLS and CA options).
- **Node-RED requires a login:** `init` generates `NODE_RED_PASSWORD`, `validate` checks for it, and `secret rotate` rotates it.
- **Every service is optional:** the stacks put each service in a Compose profile, and `COMPOSE_PROFILES` in each layer's `.env` picks what starts. The AI layer starts **Ollama only** by default; add `letta,n8n` to enable them (their secrets are already generated).
- **Projects don't share volumes:** each layer's `.env` sets `COMPOSE_PROJECT_NAME` (`<project>-<layer>`), so two projects on one host no longer reuse each other's data.
- **Shared library:** project, scaffolding, validation and Compose logic now live in [`p4n4-lib`](https://pypi.org/project/p4n4-lib/) 0.2.0, which `p4n4` depends on.
- **Windows:** scaffolded scripts keep LF line endings, and commands no longer fail when their output is redirected.

## Compatibility

- Requires **p4n4-lib 0.2.0** (installed with it).
- `p4n4 init --layer dashboard` pins **p4n4-dashboard 1.1.0**. Its sign-in needs **p4n4-api 0.1.0**, which runs next to the project.

## Upgrading from 0.1.x

- **Multi-layer projects** from 0.1.x use the old flat layout. Create a new project with `p4n4 init` and copy your data and `.env` values across.
- **Existing IoT projects** must add `NODE_RED_USER` and `NODE_RED_PASSWORD` to the IoT `.env`. Until then, the Node-RED editor rejects every login.
- **Don't add `COMPOSE_PROJECT_NAME`** to an existing project unless you also move its volumes: Compose would start on new, empty ones.
- **Ollama already on the host?** Set `OLLAMA_PORT` in the AI `.env` (the stack publishes 11434 by default).

Full list: [CHANGELOG.md](https://github.com/raisga/p4n4-cli/blob/main/CHANGELOG.md).
