# IoT Stack

The IoT stack (`p4n4-iot`) is the foundation of every p4n4 deployment. It owns the
`p4n4-net` Docker bridge network that all other stacks attach to.

## Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| Mosquitto | `eclipse-mosquitto:2` | 1883 / 9001 | MQTT broker |
| InfluxDB | `influxdb:2` | 8086 | Time-series database |
| Node-RED | `nodered/node-red:latest` | 1880 | Flow-based data routing |
| Grafana | `grafana/grafana:latest` | 3000 | Dashboarding |

## Network

The IoT stack **creates** `p4n4-net`:

```yaml
networks:
  p4n4-net:
    name: p4n4-net
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

All other stacks declare it as `external: true`.

## Environment variables

| Variable | Description |
|----------|-------------|
| `INFLUXDB_ADMIN_TOKEN` | InfluxDB admin API token |
| `INFLUXDB_ORG` | InfluxDB organisation |
| `INFLUXDB_BUCKET` | Default bucket |
| `MQTT_USER` / `MQTT_PASSWORD` | MQTT broker credentials |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin password |

## Mosquitto ACL

Edit `config/mosquitto/acl` to control topic-level access.
Generate the password file with:

```bash
mosquitto_passwd -c config/mosquitto/passwd <username>
```

Or via CLI: `p4n4 secret mqtt-passwd`
