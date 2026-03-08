# Getting Started

## Prerequisites

- Docker >= 24 with Compose v2 (`docker compose`)
- Python >= 3.11
- Git

## Installation

```bash
pip install p4n4
p4n4 --version
```

## Create a project

```bash
p4n4 init my-project
```

The interactive wizard asks:

1. **Project name** — used as a prefix for container names.
2. **Stacks to enable** — choose one or more of: `iot`, `ai`, `edge`.

It then:

- Renders Docker Compose files from bundled Jinja2 templates.
- Generates cryptographically secure secrets and writes them to `.env`.
- Creates a `.p4n4.json` project manifest.

## Start the stacks

```bash
cd my-project
p4n4 up
```

This starts stacks in the correct order:

1. `iot` — creates the `p4n4-net` Docker bridge network, starts Mosquitto and InfluxDB first.
2. `ai` — attaches to `p4n4-net`.
3. `edge` — attaches to `p4n4-net`.

## Service URLs (default ports)

| Service | URL |
|---------|-----|
| Node-RED | http://localhost:1880 |
| Grafana | http://localhost:3000 |
| InfluxDB | http://localhost:8086 |
| n8n | http://localhost:5678 |
| Letta | http://localhost:8283 |
| Ollama | http://localhost:11434 |

## Stop everything

```bash
p4n4 down
```

## Next steps

- [IoT stack reference](iot-stack.md)
- [AI stack reference](ai-stack.md)
- [CLI reference](cli-reference.md)
