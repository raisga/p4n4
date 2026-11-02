# Spike S1: Compose

Code for spike S1 of the [Rust rewrite plan](../../RUST_REWRITE_PLAN.md#91-spikes-p0) (§9.1). The spike asks three things: the oldest Compose version p4n4 can use, how the `p4n4-net` network behaves, and what `down` does with inactive profiles. The results are in the docs submodule, at `docs/decisions/spikes/s1-compose.md`. P1 deletes this directory.

There is no Rust here. The spike runs released Compose binaries against a small project and a few probes. So far only the static part has run. Every command points at a Docker socket that doesn't exist, so nothing reaches an engine; a command that needs one shows as `eng`. The engine checks wait for the hands-on run (see [the last section](#left-for-the-hands-on-run)).

## Layout

- **`project/`.** A project shaped like the generated `compose.yaml` in plan §5.3.
  - `compose.yaml`:
    - `name: p4n4s1-main`;
    - three `include` entries, each with `env_file: .env`. Two of them list the layer file and then its ports file;
    - the `default` network, named `p4n4-net` (override it with `P4N4S1_NETWORK`), with subnet 10.201.1.0/24 and `ip_range` 10.201.1.128/25.
  - `core/compose.yaml` defines two services:
    - `server`: busybox httpd with a healthcheck, at the fixed address 10.201.1.2;
    - `sim`: in the `sim` profile, depending on `mqtt` with `required: false`.
  - `iot/compose.yaml`: `mqtt`, in the `mqtt` profile.
  - `ai/compose.yaml`: `agent` (alpine), in the `agent` profile. It depends on `server` (`service_healthy`) and on `mqtt`, both with `required: false`.
  - `.p4n4/ports/core.yaml` and `.p4n4/ports/iot.yaml`: the published ports, 127.0.0.1:18100 and 127.0.0.1:18101.
  - `.p4n4/emu/compose.emu.yaml`: an emulator overlay (§6.6) with CPU and memory limits for `server`, passed as a second `-f`.
  - `dot.env`: `COMPOSE_PROFILES=mqtt,agent`, and two variables that the layer files interpolate. The script copies it to `.env`, which the superproject's `.gitignore` ignores.
- **`probes/`.** One question each, checked with `config` only.
  - `include-env-file/`: does an include's `env_file` reach the included file's interpolation? Here the file is `include.env`, not the root `.env`.
  - `dep-disabled-optional/`: a dependency whose profile is inactive, with `required: false`.
  - `dep-disabled-required/`: the same dependency without `required: false`, as a control.
  - `dep-undefined-optional/`: `required: false` on a service that no file defines, as when a layer is absent (V004).
  - `dep-generated/`: the cross-layer `depends_on` moves out of the layer file into a generated file in the same include entry. This is the V004 fix that the note proposes.
  - `root-redefines-included/`: the root file adds ports to an included service (§5.3).
- **`static-checks.sh`.** Runs every check for each binary and prints the result matrix.
- **`fixtures/v2.39.2/` and `fixtures/v2.21.0/`.** The first `FakeDriver` fixtures (§6.1):
  - `config.json`: the output of `config --format json`. The script would replace the work directory with `/srv/p4n4s1`, but this project's output contains no paths;
  - `version.json`: the output of `version --format json`.

**Names on an engine:**
- projects `p4n4s1-*` and containers `p4n4s1-*`;
- images `busybox:1.36` and `alpine:3.20`;
- subnet 10.201.1.0/24;
- host ports 18100, 18101 and (in one probe) 18110, all on 127.0.0.1.

## Running the static checks

In WSL or Linux, with bash and python3:

```sh
bash static-checks.sh                   # every binary under bin/
bash static-checks.sh 2.21.0 2.39.2     # only these versions
SAVE_FIXTURES="2.39.2 2.21.0" bash static-checks.sh 2.39.2 2.21.0   # also rewrites fixtures/
```

**What the script does:**
- It exports `DOCKER_HOST=unix:///nonexistent/docker.sock`, unsets `DOCKER_CONTEXT` and every `COMPOSE_*` variable, and points `DOCKER_CONFIG` at an empty directory.
- It runs each command under `timeout 60`.
- It copies `project/` and `probes/` to `work/v<version>/` and runs there, so the repository stays clean.

**Result codes:**
- `ok`: accepted. For the rows that check the output, it's also as expected. `cfg-yaml` checks only the exit status, and the flag rows only `--help`;
- `REJ`: rejected;
- `BAD`: accepted, with a wrong result;
- `eng`: needs the engine;
- `n/a`: the flag isn't in `--help`;
- `skp`: a prerequisite failed;
- `T/O`: timed out.

Below the matrix, the script prints each binary's self-reported version and the first line of each error.

The main rows address the project from the project directory, the way p4n4 should (§6.1):

```sh
cd <project> && docker compose --project-directory <project> -f compose.yaml ...
```

The cwd matters for two reasons:
- `-f` is resolved against the cwd;
- until 2.24.6, an include's `env_file` is resolved against the cwd too.

The `cwd-root-*` rows show what happens when Compose runs from another directory.

## Binaries

The binaries stay outside the repository, in `$HOME/.cache/p4n4-spikes/s1-compose/`. Set `S1_HOME` to use another directory.

- **`bin/v<version>/docker-compose`.** The upstream `docker-compose-linux-x86_64` release asset, checked against its `.sha256`, which is kept beside it.
  - 14 versions, 793 MB in all: 2.17.3, 2.19.1, 2.20.0, 2.20.2, 2.20.3, 2.21.0, 2.23.3, 2.24.0, 2.24.6, 2.24.7, 2.25.0, 2.27.1, 2.39.2 and 5.6.1.
- **`ubuntu/`.** Ubuntu 24.04's builds of `docker-compose-v2`, 2.24.6+ds1-0ubuntu2 and 2.40.3+ds1-0ubuntu1~24.04.1, 117 MB with their run.
  - They were unpacked with `dpkg-deb -x`, not installed.
  - `ubuntu/home/bin/v<version>u/docker-compose` links to them, so the script runs on them too:

    ```sh
    S1_HOME=$HOME/.cache/p4n4-spikes/s1-compose/ubuntu/home bash static-checks.sh 2.24.6u 2.40.3u
    ```
  - Their results are in `ubuntu/static-matrix.txt`, and match upstream 2.24.6 and 2.39.2.
- **`work/` and `docker-config/`.** The script's scratch directories.
- **`static-matrix.txt`.** The output of the last full run.

To add a version:

```sh
v=2.22.0; d=$HOME/.cache/p4n4-spikes/s1-compose/bin/v$v
mkdir -p "$d" && cd "$d"
u=https://github.com/docker/compose/releases/download/v$v/docker-compose-linux-x86_64
curl -fsSLO "$u" && curl -fsSLO "$u.sha256"
sha256sum -c docker-compose-linux-x86_64.sha256 \
  && mv docker-compose-linux-x86_64 docker-compose \
  && mv docker-compose-linux-x86_64.sha256 docker-compose.sha256 \
  && chmod +x docker-compose
```

## Left for the hands-on run

These checks need a Docker engine, so they wait for the BIOS update. The note lists them under each question. In short:

- **`up --wait`.** With `server`'s healthcheck, and `agent`'s `service_healthy` dependency on it.
- **JSON fixtures.**
  - `ps --format json` from 2.21.0, from 2.24.0 or later, and from 2.39.2, including the output when nothing is running.
  - `images --format json`.
- **The network.** `docker network inspect` of the network: its subnet, `IPRange` and labels, and `server` at 10.201.1.2.
- **Inactive profiles.** On 2.21.0, 2.23.3 and 2.39.2:
  1. Run `up -d sim`.
  2. Run `ps`, `restart sim`, `logs sim`, `down sim` and `down`, with and without `--profile '*'`.
- **Network edge cases.** A leftover network that carries v0.4's label, and a subnet change between two `up`s.
- **Orphans.** What `down` and `up` do with the containers of an include entry that was removed.
- **Docker Desktop.** Its `docker compose version --format json`.

**Before starting:**
- **The owner's network.** The engine may hold the owner's v0.4 `p4n4-net` network and running containers.
  1. List networks and containers first, read-only.
  2. If `p4n4-net` exists, set `P4N4S1_NETWORK=p4n4s1-net` in the project's `.env`.
  3. Never touch `p4n4-net`, or anything not named `p4n4s1-*`.
- **Free resources.** Check that 10.201.1.0/24 and ports 18100–18110 are free.
- **A separate copy.** Work on a copy of `project/`, because the script deletes and recreates `work/`.

**Cleaning up:**
- Run `down --volumes --profile '*'` for each `p4n4s1-*` project.
- Remove any throwaway network.
