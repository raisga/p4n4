# Edge Stack

The Edge stack (`p4n4-edge`) runs Edge Impulse model inference inside Docker.
It is fully independent and can operate standalone or alongside the IoT and AI stacks.

## Services

| Service | Image | Role |
|---------|-------|------|
| edge-impulse-runner | `edgeimpulse/linux-runner:latest` | Runs `.eim` model inference |

## Model deployment

`.eim` model binaries are **never committed** to the repository. They must be provided at deploy time.

Using the CLI:

```bash
p4n4 ei deploy path/to/model.eim
```

Manually:

```bash
cp model.eim edge-impulse/models/
p4n4 ei run
```

## Camera / sensor access

Uncomment the `devices` block in `docker-compose.override.yml` to pass a USB camera
or other device into the container.

## Environment variables

| Variable | Description |
|----------|-------------|
| `EI_API_KEY` | Edge Impulse API key (optional for offline inference) |
| `EI_PROJECT_ID` | Edge Impulse project ID |
| `EI_RUNNER_LOG_LEVEL` | Log verbosity: `debug` \| `info` \| `warn` |

## Standalone mode

The edge stack works without `p4n4-net`. Remove the `networks` section from
`docker-compose.yml` or create a local network:

```bash
docker network create p4n4-edge-net
```
