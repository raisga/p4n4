# p4n4

> Self-hosted IoT + GenAI + Edge AI platform built on Docker Compose.

p4n4 is an open-source, multi-stack platform for building end-to-end IoT pipelines with local AI inference, composed of three Docker-based service stacks — **MING** (IoT), **GenAI**, and **Edge AI**.

---

## Repository Map

| Repository | Description |
|------------|-------------|
| [p4n4-iot](https://github.com/raisga/p4n4-iot) | MING stack: Mosquitto · InfluxDB · Node-RED · Grafana |
| [p4n4-ai](https://github.com/raisga/p4n4-ai) | GenAI stack: Ollama · Letta · n8n |
| [p4n4-edge](https://github.com/raisga/p4n4-edge) | Edge AI stack: Edge Impulse runner |
| [p4n4-cli](https://github.com/raisga/p4n4-cli) | Python CLI (`pip install p4n4`) |
| [p4n4-api](https://github.com/raisga/p4n4-api) | REST API gateway (port 8000) |
| [p4n4-lib](https://github.com/raisga/p4n4-lib) | Common library — mediates between stacks and CLI/API clients |
| [p4n4-docs](https://github.com/raisga/p4n4-docs) | Full technical documentation site |

---

## Architecture

```
  Sensors / Devices
        │ MQTT
        ▼
  ┌─────────────────────────────────────────┐
  │  p4n4-iot  (MING stack)                 │
  │  Mosquitto ──► Node-RED ──► InfluxDB    │
  │                                Grafana  │
  └─────────────────────────────────────────┘
  ┌─────────────────────────────────────────┐
  │  p4n4-ai  (GenAI stack)                 │
  │  Ollama · Letta · n8n                   │
  └─────────────────────────────────────────┘
  ┌─────────────────────────────────────────┐
  │  p4n4-edge  (Edge AI stack)             │
  │  Edge Impulse Runner                    │
  └─────────────────────────────────────────┘

  All stacks share the p4n4-net Docker bridge network.

  p4n4-lib ──► p4n4-cli · p4n4-api
```

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Docker | 24+ (with Compose v2) |
| Python | 3.11+ |
| RAM | 4 GB (8 GB recommended with Ollama) |
| Disk | 10 GB free |

---

## Getting Started

### Clone with submodules

```bash
git clone --recurse-submodules https://github.com/raisga/p4n4.git
cd p4n4

# If already cloned without submodules:
git submodule update --init --recursive
```

### Quick Start (CLI)

```bash
pip install p4n4
p4n4 init my-project
cd my-project
p4n4 up
```

The CLI scaffolds compose files, generates secrets, and starts the stacks in the correct order.

### Manual Setup (without CLI)

```bash
# IoT stack
git clone https://github.com/raisga/p4n4-iot.git && cd p4n4-iot
cp .env.example .env  # edit passwords
docker network create --driver bridge --subnet 172.20.0.0/16 p4n4-net
docker compose up -d && cd ..

# AI stack (after IoT is healthy)
git clone https://github.com/raisga/p4n4-ai.git && cd p4n4-ai
cp .env.example .env  # INFLUXDB_TOKEN must match p4n4-iot/.env
docker compose up -d && cd ..

# Edge stack (optional, requires Edge Impulse account + .eim model)
git clone https://github.com/raisga/p4n4-edge.git && cd p4n4-edge
cp .env.example .env
docker compose up -d
```

> **Cross-stack secrets:** `INFLUXDB_ADMIN_TOKEN`, `INFLUXDB_ORG`, and `INFLUXDB_BUCKET` must be identical across all stack `.env` files.

---

## Service URLs

| Service | Port | Stack |
|---------|------|-------|
| Mosquitto (MQTT) | `1883` · `9001` (WS) | iot |
| InfluxDB | `8086` | iot |
| Node-RED | `1880` | iot |
| Grafana | `3000` | iot |
| n8n | `5678` | ai |
| Letta | `8283` | ai |
| Ollama API | `11434` | ai |
| Edge Impulse Runner | `8080` | edge |
| p4n4 REST API | `8000` | api |

---

## License

[MIT](LICENSE)
