# AI Stack

The AI stack (`p4n4-ai`) provides local LLM inference (Ollama), agent memory (Letta),
and workflow automation (n8n). It attaches to `p4n4-net` as an external network.

## Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| Ollama | `ollama/ollama:latest` | 11434 | Local LLM runtime |
| Letta | `letta/letta:latest` | 8283 | AI agent framework with memory |
| n8n | `n8nio/n8n:latest` | 5678 | Workflow automation |

## Prerequisites

The IoT stack must be running (to provide `p4n4-net`) or the network must exist:

```bash
docker network create p4n4-net  # if not using p4n4-iot
```

Or start everything with: `p4n4 up --all`

## Pull models

```bash
./ollama/pull-models.sh llama3.2
# or
docker exec p4n4-ollama ollama pull llama3.2
```

## n8n workflows

Starter workflows are in `n8n/workflows/`:

| Workflow | Description |
|----------|-------------|
| `alert-enrichment.json` | Enrich MQTT alerts with LLM analysis |
| `scheduled-digest.json` | Periodic telemetry summary via Ollama |
| `device-onboarding.json` | Auto-register new MQTT devices |
| `incident-escalation.json` | Classify and escalate critical alerts |

Import them via the n8n UI or mount the directory as a volume.

## GPU support

Uncomment the `deploy.resources` block in `docker-compose.override.yml` for NVIDIA GPU.

## Environment variables

| Variable | Description |
|----------|-------------|
| `N8N_BASIC_AUTH_USER` / `_PASSWORD` | n8n UI credentials |
| `N8N_ENCRYPTION_KEY` | n8n data encryption key |
| `LETTA_SERVER_PASSWORD` | Letta API password |
| `INFLUXDB_ADMIN_TOKEN` | Shared with IoT stack (must match) |
