# CLI Reference

Install: `pip install p4n4`

## Global options

```
p4n4 [--version] [--help]
```

---

## `p4n4 init [PATH]`

Interactive project wizard. Scaffolds compose files, generates secrets, writes `.p4n4.json`.

```bash
p4n4 init                  # scaffold in current directory
p4n4 init my-project       # scaffold in ./my-project
```

---

## `p4n4 add STACK`

Add a stack to an existing project.

```bash
p4n4 add ai
p4n4 add edge --path /srv/my-project
```

---

## `p4n4 remove STACK`

Remove a stack from an existing project.

```bash
p4n4 remove edge
p4n4 remove ai --yes       # skip confirmation
```

---

## `p4n4 up [STACK]`

Start one or all enabled stacks (in dependency order).

```bash
p4n4 up                    # all stacks
p4n4 up iot                # IoT stack only
p4n4 up --no-detach        # foreground mode
```

---

## `p4n4 down [STACK]`

Stop one or all stacks.

```bash
p4n4 down
p4n4 down ai
p4n4 down --volumes        # also remove volumes
```

---

## `p4n4 status`

Show container status for all enabled stacks.

---

## `p4n4 logs STACK`

Tail logs for a stack.

```bash
p4n4 logs iot
p4n4 logs ai --tail 50 --no-follow
```

---

## `p4n4 validate`

Validate `.p4n4.json`, compose files, and `.env` presence.

---

## `p4n4 upgrade [STACK]`

Pull latest Docker images.

```bash
p4n4 upgrade               # all stacks
p4n4 upgrade iot
```

---

## `p4n4 secret ACTION`

| Action | Description |
|--------|-------------|
| `show` | Show masked secrets from `.env` |
| `rotate` | Re-generate all password/token values |
| `generate` | Print new secrets to stdout |

---

## `p4n4 ei`

| Subcommand | Description |
|------------|-------------|
| `deploy MODEL` | Copy a `.eim` model and restart the runner |
| `run` | Start the Edge Impulse runner |
| `status` | Show runner container status |

---

## `p4n4 template`

| Subcommand | Description |
|------------|-------------|
| `search [QUERY]` | List templates from the community registry |
| `install NAME` | Install a template into the current project |
| `list` | Show installed templates |
