# raisga

**p4n4** is an open-source, self-hosted IoT + GenAI + Edge AI platform built on Docker Compose.

## Repositories

| Repo | Description |
|------|-------------|
| [p4n4](https://github.com/raisga/p4n4) | Umbrella: architecture, ADRs, cross-cutting docs |
| [p4n4-iot](https://github.com/raisga/p4n4-iot) | IoT stack: Mosquitto · Node-RED · InfluxDB · Grafana |
| [p4n4-ai](https://github.com/raisga/p4n4-ai) | GenAI stack: Ollama · Letta · n8n |
| [p4n4-edge](https://github.com/raisga/p4n4-edge) | Edge Impulse inference stack |
| [p4n4-cli](https://github.com/raisga/p4n4-cli) | Python CLI (`pip install p4n4`) |
| [p4n4-templates](https://github.com/raisga/p4n4-templates) | Community template registry |
| [p4n4-docs](https://github.com/raisga/p4n4-docs) | Full technical documentation |

## Quick Start

```bash
pip install p4n4
p4n4 init my-project
cd my-project
p4n4 up
```
