"""Golden capture helper for `emu-limits`: the limits v0.4.2's emulator renders.

`cargo xtask golden capture emu-limits` runs it with P4N4_GOLDEN_PYTHON, a Python 3.11+ with
lib and tools/emu installed from this checkout (`pip install -e lib -e tools/emu`):

    python xtask/golden/emu_limits.py --root . --out DIR

It writes DIR/<profile>.json for each built-in profile, and prints the manifest inputs on
stdout as one JSON object. Nothing runs Docker: a case's services are the generator's
defaults, or a compose file's services as `docker compose config --services` lists them with
every Compose profile enabled.

Each case is one `p4n4-emu up` of a project: its stacks, which share the board's budget, and
the options. What is recorded is what the overlays mean, per service: the limits `emu
report` checks (utils.usage.expected_limits), the platform, the GPU reservation,
oom_score_adj and the blkio weight, and each overlay's x-p4n4-emu block. The Rust port
writes one overlay per project (RUST_REWRITE_PLAN.md §6.6), so the YAML text is not kept.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from pathlib import Path
from typing import Any

import common

log = logging.getLogger("emu-limits")

BLKIO_DEVICE = "/dev/sda"
CPU_FACTOR = 0.5
CPUSET = "0,2"
# A project's .p4n4-emu/config.yml, as in profiles/shares.py's docstring: one service changed
# on both fields, one on a single field, and the share of services with no default
PROJECT_OVERRIDES = {
    "influxdb": {"cpu": 0.5, "memory": 0.4},
    "node-red": {"memory": 0.25},
    "*": {"cpu": 0.05},
}
# The compose files whose services the cases render, relative to the superproject. The extras
# stack includes no extra at v0.4.2, so obd2 is read from its own directory.
COMPOSE_FILES = {
    "iot": "stacks/iot/docker-compose.yml",
    "ai": "stacks/ai/docker-compose.yml",
    "extras": "stacks/extras/docker-compose.yml",
    "obd2": "stacks/extras/obd2/docker-compose.yml",
}


@dataclasses.dataclass(frozen=True)
class Case:
    name: str
    # The project's stacks, in STACKS order: their services, None for the generator's defaults
    stacks: dict[str, list[str] | None]
    overrides: dict[str, dict[str, float]] = dataclasses.field(default_factory=dict)
    arch: str = ""  # --arch
    native: bool = False  # --native
    gpu: bool = False  # the host passes the profile's GPU through
    blkio_device: str | None = BLKIO_DEVICE
    cpu_factor: float = 1.0
    cpuset: str | None = None  # --cpuset


def compose_services(path: Path) -> list[str]:
    """The services of a compose file and of the files it includes, in file order."""
    import yaml

    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    names: list[str] = []
    for entry in doc.get("include") or []:
        paths = entry.get("path") if isinstance(entry, dict) else entry
        for sub in [paths] if isinstance(paths, str) else paths:
            names += compose_services(path.parent / sub)
    names += list(doc.get("services") or {})
    return list(dict.fromkeys(names))


def cases(root: Path, gpu: bool) -> list[Case]:
    compose = {stack: compose_services(root / path) for stack, path in COMPOSE_FILES.items()}
    project = {"iot": compose["iot"], "ai": compose["ai"], "extras": compose["obd2"],
               "dashboard": None}
    out = [Case(f"default/{s}", {s: None}) for s in ("iot", "ai", "edge", "extras", "dashboard")]
    out += [
        Case("compose/iot", {"iot": compose["iot"]}),
        Case("compose/ai", {"ai": compose["ai"]}),
        Case("compose/extras", {"extras": compose["extras"]}),
        Case("compose/extras-obd2", {"extras": compose["obd2"]}),
        Case("project", project),
        Case("project/overrides", project, overrides=PROJECT_OVERRIDES),
        Case("project/native", project, native=True),
        Case("project/arch-armv7", project, arch="armv7"),
        Case("project/cpu-factor", project, cpu_factor=CPU_FACTOR),
        Case("project/cpuset-auto", project, cpuset="auto"),
        Case("project/cpuset-list", project, cpuset=CPUSET),
        Case("project/no-blkio", project, blkio_device=None),
    ]
    if gpu:
        # A GPU reaches containers only when they run natively
        out.append(Case("project/gpu", project, native=True, gpu=True))
    return out


def meaning(doc: dict[str, Any]) -> dict[str, Any]:
    """What an overlay asks of each service, as `emu report` and Compose read it."""
    from p4n4_emu.utils.usage import expected_limits

    services = {}
    for name, limits in expected_limits(doc).items():
        svc = doc["services"][name] or {}
        resources = (svc.get("deploy") or {}).get("resources") or {}
        devices = (resources.get("reservations") or {}).get("devices") or []
        blkio = svc.get("blkio_config") or {}
        paths = {e.get("path") for key in ("device_read_bps", "device_write_bps")
                 for e in blkio.get(key) or []}
        services[name] = {
            **dataclasses.asdict(limits),
            "platform": svc.get("platform"),
            "gpu": devices or None,
            "oom_score_adj": svc.get("oom_score_adj"),
            "blkio_weight": blkio.get("weight"),
            "blkio_device": paths.pop() if len(paths) == 1 else sorted(paths) or None,
        }
    return {"x-p4n4-emu": doc.get("x-p4n4-emu"), "services": services}


def run_case(prof, case: Case) -> dict[str, Any]:
    """Render the case's overlays the way `p4n4-emu up` does (commands/up.py)."""
    import yaml
    from p4n4_emu.commands.up import resolve_platform
    from p4n4_emu.overlays.generator import (
        budget_scale,
        fixed_warnings,
        render_overlay,
        resolve_cpuset,
        service_shares,
    )
    from p4n4_emu.profiles.shares import merge

    overrides = merge(prof.shares, case.overrides)
    platform = resolve_platform(prof, case.arch, case.native)
    cores = resolve_cpuset(case.cpuset, prof, None) if case.cpuset else None
    gpu = prof.gpu if case.gpu else None
    shares = {s: service_shares(s, services, overrides, prof)
              for s, services in case.stacks.items()}
    scale = budget_scale(shares.values())
    overlays: dict[str, Any] = {}
    for stack, services in case.stacks.items():
        if services == []:
            overlays[stack] = None  # `up` skips a stack with no services enabled
            continue
        text = render_overlay(
            prof,
            stack,
            case.blkio_device,
            services=shares[stack].keys(),
            platform=platform,
            scale=scale,
            gpu=gpu,
            overrides=overrides,
            cpu_factor=case.cpu_factor,
            cpuset=cores,
            cpuset_auto=case.cpuset == "auto",
        )
        overlays[stack] = meaning(yaml.safe_load(text))
    return {
        "name": case.name,
        "stacks": case.stacks,
        "overrides": case.overrides,
        "options": {
            "arch": case.arch or None,
            "native": case.native,
            "gpu": case.gpu,
            "blkio_device": case.blkio_device,
            "cpu_factor": case.cpu_factor,
            "cpuset": case.cpuset,
        },
        "platform": platform,
        "cpuset": cores,
        "scale": dataclasses.asdict(scale),
        "warnings": fixed_warnings(prof, shares.values()),
        "overlays": overlays,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, required=True, help="the superproject")
    parser.add_argument("--out", type=Path, required=True, help="where the fixtures go")
    args = parser.parse_args()
    common.fixed_hash_seed()
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s", stream=sys.stderr)
    versions = common.check_checkout(args.root, "PyYAML", "Jinja2")

    from p4n4_emu.profiles import loader

    definitions = Path(loader.__file__).parent / "definitions"
    args.out.mkdir(parents=True, exist_ok=True)
    profiles, names = [], set()
    for path in sorted(definitions.glob("*.yml")):
        # From the file, not load_profile(): a profile in ~/.p4n4-emu would shadow it
        prof = loader.load_profile_file(path)
        record = {**prof.as_dict(), "memory_mb": prof.memory_mb,
                  "source": common.relative(path, args.root)}
        results = [run_case(prof, case) for case in cases(args.root, prof.gpu is not None)]
        common.write_json(args.out / f"{prof.name}.json", {"profile": record, "cases": results},
                          indent=1)
        log.info("%s: %d cases", prof.name, len(results))
        profiles.append(prof.name)
        names.update(r["name"] for r in results)

    common.print_inputs({
        "helper": "xtask/golden/emu_limits.py",
        "versions": versions,
        "profiles": profiles,
        "cases": sorted(names),
        "compose_files": sorted(COMPOSE_FILES.values()),
        "blkio_device": BLKIO_DEVICE,
        "cpu_factor": CPU_FACTOR,
        "cpuset": CPUSET,
        "project_overrides": PROJECT_OVERRIDES,
    })


if __name__ == "__main__":
    main()
