# p4n4

**p4n4** is a self-hosted, open-source platform for IoT, GenAI, and Edge AI — assembled from
best-of-breed open-source services and wired together with Docker Compose.

## What's in the box

| Stack | Services |
|-------|---------|
| [IoT](iot-stack.md) | Eclipse Mosquitto · Node-RED · InfluxDB · Grafana |
| [AI](ai-stack.md) | Ollama · Letta · n8n |
| [Edge](edge-stack.md) | Edge Impulse Linux Runner |

## Quick start

```bash
pip install p4n4
p4n4 init my-project
cd my-project
p4n4 up
```

## Repository map

```
raisga/
├── p4n4            ← umbrella (you are here)
├── p4n4-iot        ← IoT stack
├── p4n4-ai         ← GenAI stack
├── p4n4-edge       ← Edge AI stack
├── p4n4-cli        ← Python CLI (pip install p4n4)
├── p4n4-templates  ← community templates
└── p4n4-docs       ← this documentation
```
