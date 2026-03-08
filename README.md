# p4n4

> Self-hosted IoT + GenAI + Edge AI platform built on Docker Compose.

p4n4 is an open-source, multi-stack platform for building end-to-end IoT pipelines with local AI inference. It combines a proven IoT data stack (MQTT · InfluxDB · Node-RED · Grafana) with a self-hosted GenAI layer (Ollama · Letta · n8n) and an Edge Impulse inference stack — all wired together through a single CLI.

---

## Table of Contents

- [Repository Map](#repository-map)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start (CLI)](#quick-start-cli)
- [Step-by-Step Guide](#step-by-step-guide)
  - [1. Install the CLI](#1-install-the-cli)
  - [2. Scaffold a project](#2-scaffold-a-project)
  - [3. Review and edit secrets](#3-review-and-edit-secrets)
  - [4. Start the IoT stack](#4-start-the-iot-stack)
  - [5. Verify services](#5-verify-services)
  - [6. Add the AI stack](#6-add-the-ai-stack-optional)
  - [7. Add the Edge stack](#7-add-the-edge-stack-optional)
  - [8. Test the data pipeline](#8-test-the-data-pipeline)
- [Manual Setup (without CLI)](#manual-setup-without-cli)
- [Service URLs](#service-urls)
- [Stack Reference](#stack-reference)
- [Community Templates](#community-templates)
- [Resources](#resources)
- [License](#license)

---

## Repository Map

| Repository | Description |
|------------|-------------|
| **[p4n4](https://github.com/raisga/p4n4)** | This repo — architecture, ADRs, cross-cutting docs |
| [p4n4-iot](https://github.com/raisga/p4n4-iot) | IoT stack: Mosquitto · InfluxDB · Node-RED · Grafana |
| [p4n4-ai](https://github.com/raisga/p4n4-ai) | GenAI stack: Ollama · Letta · n8n |
| [p4n4-edge](https://github.com/raisga/p4n4-edge) | Edge Impulse inference stack |
| [p4n4-cli](https://github.com/raisga/p4n4-cli) | Python CLI (`pip install p4n4`) |
| [p4n4-templates](https://github.com/raisga/p4n4-templates) | Community template registry |
| [p4n4-docs](https://github.com/raisga/p4n4-docs) | Full technical documentation site |

---

## Architecture

```
  Sensors / Devices
        │
        ▼ MQTT
  ┌─────────────┐     ┌────────────┐     ┌──────────┐
  │  Mosquitto  │────►│  Node-RED  │────►│ InfluxDB │
  └─────────────┘     └─────┬──────┘     └────┬─────┘
                            │                 │
                            ▼                 ▼
                         ┌──────┐         ┌─────────┐
                         │  n8n │         │ Grafana │
                         └──┬───┘         └─────────┘
                            │
                    ┌───────┴────────┐
                    ▼                ▼
                 ┌───────┐      ┌────────┐
                 │ Letta │      │ Ollama │
                 └───────┘      └────────┘

  Edge Impulse Runner ──► MQTT (inference/results)
```

**Data flow:**
1. Devices publish sensor readings over MQTT.
2. Node-RED routes data into InfluxDB and triggers automation rules.
3. Grafana visualises time-series data in real time.
4. n8n bridges IoT events to the GenAI layer — enriching alerts, scheduling digests, escalating incidents.
5. Letta agents backed by Ollama LLMs provide long-memory, tool-calling intelligence.
6. The Edge stack runs trained Edge Impulse models on-device and publishes results back to MQTT.

All three stacks communicate over a shared `p4n4-net` Docker bridge network owned by `p4n4-iot`.

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Docker | 24+ (with Compose v2) |
| Python | 3.11+ |
| RAM | 4 GB (8 GB recommended when running Ollama) |
| Disk | 10 GB free |

Verify your setup:

```bash
docker compose version   # should print v2.x
python3 --version        # should print 3.11+
```

---

## Quick Start (CLI)

```bash
pip install p4n4
p4n4 init my-project
cd my-project
p4n4 up
```

The CLI scaffolds compose files, generates secrets, and starts the stacks in the correct dependency order.

---

## Step-by-Step Guide

### 1. Install the CLI

```bash
pip install p4n4
p4n4 --version
```

### 2. Scaffold a project

```bash
p4n4 init my-project
```

The interactive wizard asks:

- **Project name** — used as a prefix for container names.
- **Stacks to enable** — `iot`, `ai`, `edge` (pick one or more; IoT is the foundation).

After completion your project directory looks like this:

```
my-project/
├── .p4n4.json                  ← project manifest
├── .env                        ← generated secrets (never commit)
├── .env.example                ← safe to commit
├── .gitignore
├── docker-compose.iot.yml
├── docker-compose.ai.yml       ← if ai was selected
├── docker-compose.edge.yml     ← if edge was selected
├── mosquitto/config/
│   ├── mosquitto.conf
│   └── acl
├── node-red/
│   ├── flows.json
│   └── settings.js
├── influxdb/config/
│   └── influxdb.conf
└── grafana/provisioning/
    ├── datasources/influxdb.yaml
    └── dashboards/p4n4-base.json
```

### 3. Review and edit secrets

```bash
# See generated values (masked)
p4n4 secret show

# Regenerate all passwords and tokens
p4n4 secret rotate
```

Change any remaining placeholders in `.env` before starting. At minimum confirm:

- `INFLUXDB_ADMIN_TOKEN` — must be the same value in every stack that references it
- `GRAFANA_PASSWORD` — change before exposing to any network

### 4. Start the IoT stack

```bash
cd my-project
p4n4 up iot
```

This automatically creates the `p4n4-net` Docker bridge network, then starts services in order:

1. `mqtt` (Mosquitto) — MQTT broker
2. `influxdb` — waits until `mqtt` is healthy
3. `node-red` — waits until both `mqtt` and `influxdb` are healthy
4. `grafana` — waits until `influxdb` is healthy

Watch startup:

```bash
p4n4 logs iot
```

### 5. Verify services

```bash
p4n4 status
```

All four services should show `running`. Open the dashboards:

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | `GRAFANA_USER` / `GRAFANA_PASSWORD` from `.env` |
| Node-RED | http://localhost:1880 | no auth by default |
| InfluxDB | http://localhost:8086 | `INFLUXDB_USERNAME` / `INFLUXDB_PASSWORD` from `.env` |

### 6. Add the AI stack (optional)

```bash
p4n4 up ai
```

This starts Ollama, Letta, and n8n attached to the existing `p4n4-net` network.

Pull a model for Ollama:

```bash
./ollama/pull-models.sh llama3.2
# or interactively:
docker exec my-project-ollama ollama pull llama3.2
```

| Service | URL | Credentials |
|---------|-----|-------------|
| n8n | http://localhost:5678 | `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` from `.env` |
| Letta | http://localhost:8283 | `LETTA_SERVER_PASSWORD` from `.env` |
| Ollama API | http://localhost:11434 | no auth |

Starter n8n workflows (alert enrichment, scheduled digest, device onboarding, incident escalation) are in `n8n/workflows/` — import them via the n8n UI.

### 7. Add the Edge stack (optional)

Requires an [Edge Impulse](https://edgeimpulse.com/) account and a trained `.eim` model file.

```bash
# Add to existing project
p4n4 add edge

# Deploy your model
p4n4 ei deploy path/to/model.eim

# Start the runner
p4n4 up edge
```

The runner publishes inference results to the `inference/results` MQTT topic. Pick them up in Node-RED to store in InfluxDB or trigger n8n workflows.

Check runner status:

```bash
p4n4 ei status
```

### 8. Test the data pipeline

Publish a test sensor reading:

```bash
docker run --rm --network p4n4-net eclipse-mosquitto:2 \
  mosquitto_pub -h my-project-mqtt -t 'sensors/temperature' \
  -m '{"value": 23.5, "unit": "C", "device": "test-sensor"}'
```

Then:

1. **Node-RED** (http://localhost:1880) — the base flow routes `sensors/#` into InfluxDB.
2. **Grafana** (http://localhost:3000) — open the "p4n4 IoT Overview" dashboard to see the data point appear.
3. **n8n** (http://localhost:5678, if AI stack is running) — the alert-enrichment workflow can subscribe to MQTT and forward enriched data to Letta.

---

## Manual Setup (without CLI)

Prefer working directly with Docker Compose? Clone each repo and bring up stacks in order.

**Step 1 — IoT stack:**

```bash
git clone https://github.com/raisga/p4n4-iot.git
cd p4n4-iot
cp .env.example .env
# Edit .env — change all default passwords
docker network create --driver bridge --subnet 172.20.0.0/16 p4n4-net
docker compose up -d
cd ..
```

**Step 2 — AI stack** (after IoT is healthy):

```bash
git clone https://github.com/raisga/p4n4-ai.git
cd p4n4-ai
cp .env.example .env
# Edit .env — INFLUXDB_ADMIN_TOKEN must match p4n4-iot/.env
docker compose up -d
cd ..
```

**Step 3 — Edge stack** (optional):

```bash
git clone https://github.com/raisga/p4n4-edge.git
cd p4n4-edge
cp .env.example .env
# Edit .env — add EI_API_KEY and EI_PROJECT_ID
cp /path/to/model.eim edge-impulse/models/
docker compose up -d
```

> **Cross-stack secrets:** `INFLUXDB_ADMIN_TOKEN`, `INFLUXDB_ORG`, and `INFLUXDB_BUCKET` must be identical in every stack `.env` that references them. The CLI handles this automatically; manual setup requires you to keep them in sync.

---

## Service URLs

| Service | Port | Stack |
|---------|------|-------|
| Mosquitto — MQTT | `1883` (TCP) · `9001` (WebSocket) | iot |
| InfluxDB | `8086` | iot |
| Node-RED | `1880` | iot |
| Grafana | `3000` | iot |
| n8n | `5678` | ai |
| Letta | `8283` | ai |
| Ollama API | `11434` | ai |
| Edge Impulse Runner | no port (publishes to MQTT) | edge |

---

## Stack Reference

| Repo | Purpose | Quick commands |
|------|---------|---------------|
| [p4n4-iot](https://github.com/raisga/p4n4-iot) | IoT foundation | `make up` · `make status` · `make test-mqtt` |
| [p4n4-ai](https://github.com/raisga/p4n4-ai) | Local LLMs + agents + automation | `docker compose up -d` · `./ollama/pull-models.sh` |
| [p4n4-edge](https://github.com/raisga/p4n4-edge) | On-device ML inference | `p4n4 ei deploy` · `p4n4 ei run` |
| [p4n4-cli](https://github.com/raisga/p4n4-cli) | Project lifecycle management | `p4n4 --help` |

Full CLI reference: [p4n4-docs / cli-reference.md](https://github.com/raisga/p4n4-docs/blob/main/docs/cli-reference.md)

---

## Community Templates

Browse and install pre-built project configurations:

```bash
p4n4 template search
p4n4 template install factory-baseline
```

| Template | Stacks | Description |
|----------|--------|-------------|
| `factory-baseline` | iot + ai + edge | Full stack for discrete manufacturing with vibration monitoring |
| `iot-minimal` | iot | Minimal IoT-only sensor monitoring |

Contribute a template: [p4n4-templates / TEMPLATE_GUIDE.md](https://github.com/raisga/p4n4-templates/blob/main/TEMPLATE_GUIDE.md)

---

## Resources

- [Full documentation](https://raisga.github.io/p4n4-docs) — MkDocs reference site
- [ARCHITECTURE.md](https://github.com/raisga/p4n4-docs/blob/main/ARCHITECTURE.md) — multi-repo design and ADRs
- [MING Stack Tutorial](https://github.com/ArthurKretzer/tutorial-p4n4-stack) — IIoT data stack tutorial (XIV SBESC, 2024)
- [MING Stack + Edge Impulse](https://www.edgeimpulse.com/blog/accelerate-edge-ai-application-development-with-the-p4n4-stack-edge-impulse/) — architecture and integration guide
- [Edge Impulse Linux SDK](https://github.com/edgeimpulse/linux-sdk-python) — Python SDK for on-device inference
- [Eclipse Mosquitto](https://mosquitto.org/) · [InfluxDB](https://docs.influxdata.com/) · [Node-RED](https://nodered.org/docs/) · [Grafana](https://grafana.com/docs/)
- [Ollama](https://github.com/ollama/ollama) · [Letta](https://docs.letta.com/) · [n8n](https://docs.n8n.io/)

---

## License

[MIT](LICENSE)
