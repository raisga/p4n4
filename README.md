# p4n4

> Self-hosted IoT + GenAI + Edge AI platform built on Docker Compose.

p4n4 is an open-source, multi-stack platform for building end-to-end IoT pipelines with local AI inference. It is composed of three Docker-based service stacks — **MING** (IoT), **GenAI**, and **Edge AI** — exposed to clients through a shared library (`p4n4-lib`) that abstracts all service interactions. Clients interact with the stacks via the `p4n4-cli` command-line tool or the `p4n4-api` REST gateway.

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

**Docker stacks**

| Repository | Description |
|------------|-------------|
| [p4n4-iot](https://github.com/raisga/p4n4-iot) | MING stack: Mosquitto · InfluxDB · Node-RED · Grafana |
| [p4n4-ai](https://github.com/raisga/p4n4-ai) | GenAI stack: Ollama · Letta · n8n |
| [p4n4-edge](https://github.com/raisga/p4n4-edge) | Edge AI stack: Edge Impulse runner |

**Clients**

| Repository | Description |
|------------|-------------|
| [p4n4-cli](https://github.com/raisga/p4n4-cli) | Python CLI (`pip install p4n4`) |
| [p4n4-api](https://github.com/raisga/p4n4-api) | REST API gateway (port 8000) |

**Shared library**

| Repository | Description |
|------------|-------------|
| [p4n4-lib](https://github.com/raisga/p4n4-lib) | Common library — mediates between Docker service stacks and CLI/API clients |

**Other**

| Repository | Description |
|------------|-------------|
| **[p4n4](https://github.com/raisga/p4n4)** | This repo — architecture, ADRs, cross-cutting docs |
| [p4n4-templates](https://github.com/raisga/p4n4-templates) | Community template registry |
| [p4n4-docs](https://github.com/raisga/p4n4-docs) | Full technical documentation site |

---

## Architecture

```
  Sensors / Devices
        │
        ▼ MQTT
  ┌──────────────────────────────────────────────────────┐
  │  p4n4-iot  (MING stack)                              │
  │  ┌─────────────┐  ┌────────────┐  ┌─────────────┐    │
  │  │  Mosquitto  │─►│  Node-RED  │─►│  InfluxDB   │    │
  │  └─────────────┘  └────────────┘  └──────┬──────┘    │
  │                                          │           │
  │                                   ┌──────▼──────┐    │
  │                                   │   Grafana   │    │
  │                                   └─────────────┘    │
  └──────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────┐
  │  p4n4-ai  (GenAI stack)                              │
  │   ┌────────┐      ┌───────┐      ┌──────────────┐    │
  │   │ Ollama │      │ Letta │      │     n8n      │    │
  │   └────────┘      └───────┘      └──────────────┘    │
  └──────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────┐
  │  p4n4-edge  (Edge AI stack)                          │
  │          ┌───────────────────────────┐               │
  │          │   Edge Impulse Runner     │               │
  │          └───────────────────────────┘               │
  └──────────────────────────────────────────────────────┘

  All stacks share the p4n4-net Docker bridge network.

  ┌──────────────────────────────────────────────────────┐
  │  p4n4-lib  (common library)                          │
  │  service clients · auth · manifest · models          │
  └────────────────────┬─────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
    ┌─────────────┐        ┌───────────────┐
    │  p4n4-cli   │        │   p4n4-api    │
    │  (Python)   │        │  (REST :8000) │
    └─────────────┘        └───────────────┘
```

**Data flow:**
1. Devices publish sensor readings over MQTT to Mosquitto.
2. Node-RED routes data into InfluxDB and triggers automation rules.
3. Grafana visualises time-series data in real time.
4. n8n bridges IoT events to the GenAI layer — enriching alerts, scheduling digests, and escalating incidents.
5. Letta agents backed by Ollama LLMs provide long-memory, tool-calling intelligence.
6. The Edge stack runs trained Edge Impulse models on-device and publishes inference results back to MQTT.
7. `p4n4-lib` abstracts all service interactions; both `p4n4-cli` and `p4n4-api` use it as their interface to the stacks.

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

The interactive wizard prompts for InfluxDB org, timezone, and admin passwords. When the `ai` layer is active it also prompts for Letta, n8n, and n8n encryption key values. All secrets default to randomly generated values if left blank.

After completion your project directory looks like this (IoT layer):

```
my-project/
├── .p4n4.json                       ← project manifest
├── .env                             ← generated secrets (never commit)
├── docker-compose.yml               ← sourced from p4n4-iot
├── config/
│   ├── mosquitto/
│   │   ├── mosquitto.conf
│   │   ├── passwd.example
│   │   └── acl.example
│   ├── node-red/
│   │   ├── settings.js
│   │   └── flows.json
│   └── grafana/
│       └── provisioning/
│           ├── datasources/datasources.yml
│           └── dashboards/
└── scripts/
    ├── init-buckets.sh
    └── selector.sh
```

### 3. Review and edit secrets

```bash
# Rotate all passwords and tokens with new random values
p4n4 secret
```

Change any remaining placeholders in `.env` before starting. At minimum confirm:

- `INFLUXDB_TOKEN` — must be the same value in every stack that references it
- `GRAFANA_PASSWORD` — change before exposing to any network

### 4. Start the IoT stack

```bash
cd my-project
p4n4 up
```

This automatically creates the `p4n4-net` Docker bridge network, then starts services in order:

1. `mqtt` (Mosquitto) — MQTT broker
2. `influxdb` — waits until `mqtt` is healthy
3. `node-red` — waits until both `mqtt` and `influxdb` are healthy
4. `grafana` — waits until `influxdb` is healthy

Watch startup:

```bash
p4n4 logs
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
p4n4 up --ai
```

This starts Ollama, Letta, and n8n attached to the existing `p4n4-net` network.

Pull a model for Ollama:

```bash
./scripts/pull-models.sh llama3.2
# or interactively:
docker exec p4n4-ollama ollama pull llama3.2
```

| Service | URL | Credentials |
|---------|-----|-------------|
| n8n | http://localhost:5678 | `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` from `.env` |
| Letta | http://localhost:8283 | `LETTA_SERVER_PASSWORD` from `.env` |
| Ollama API | http://localhost:11434 | no auth |

Starter n8n workflows (alert enrichment, scheduled digest, device onboarding, incident escalation) are in `config/n8n/workflows/` — import them via the n8n UI.

### 7. Add the Edge stack (optional)

Requires an [Edge Impulse](https://edgeimpulse.com/) account and a trained `.eim` model file.

> **Note:** `p4n4 ei` and `p4n4 add` CLI commands are not yet implemented. Use the manual approach below.

```bash
git clone https://github.com/raisga/p4n4-edge.git
cd p4n4-edge
cp .env.example .env
# Edit .env — set MQTT credentials to match p4n4-iot .env
make deploy-model MODEL=~/Downloads/my-model.eim
make up
```

The runner subscribes to `sensors/raw` on MQTT, runs inference, and publishes results to `inference/results`. Pick them up in Node-RED to store in InfluxDB or trigger n8n workflows.

Check runner status:

```bash
p4n4 up --edge
curl http://localhost:8080/health
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
# Edit .env — INFLUXDB_TOKEN must match p4n4-iot/.env
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
| Edge Impulse Runner | `8080` (health endpoint) | edge |
| **p4n4 REST API** | **`8000`** | **api** |

---

## Stack Reference

**Docker stacks**

| Repo | Purpose | Quick commands |
|------|---------|---------------|
| [p4n4-iot](https://github.com/raisga/p4n4-iot) | MING stack — IoT data foundation | `make up` · `make status` · `make test-mqtt` |
| [p4n4-ai](https://github.com/raisga/p4n4-ai) | GenAI stack — local LLMs, agents, automation | `docker compose up -d` · `./ollama/pull-models.sh` |
| [p4n4-edge](https://github.com/raisga/p4n4-edge) | Edge AI stack — on-device ML inference | `docker compose up -d` · `curl localhost:8080/health` |

**Clients**

| Repo | Purpose | Quick commands |
|------|---------|---------------|
| [p4n4-cli](https://github.com/raisga/p4n4-cli) | Python CLI — project lifecycle management | `p4n4 --help` |
| [p4n4-api](https://github.com/raisga/p4n4-api) | REST API gateway (port 8000) | `docker compose up -d` · `curl localhost:8000/health` |

**Shared library**

| Repo | Purpose |
|------|---------|
| [p4n4-lib](https://github.com/raisga/p4n4-lib) | Common library used by `p4n4-cli` and `p4n4-api` to interact with the Docker stacks |

Full CLI reference: [p4n4-docs / cli-reference.md](https://github.com/raisga/p4n4-docs/blob/main/docs/cli-reference.md)

---

## Community Templates

Browse and install pre-built project configurations:

```bash
p4n4 template search
p4n4 template apply factory-baseline
```

> **Note:** `p4n4 template` commands are not yet implemented.

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
