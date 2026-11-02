"""What the golden capture helpers share: the checks before a capture, and how fixtures and
the manifest inputs are written."""

from __future__ import annotations

import json
import math
import os
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

# Where each package the helpers import must come from, relative to the superproject
PACKAGES = {"p4n4-lib": ("p4n4_lib", "lib"), "p4n4-emu": ("p4n4_emu", "tools/emu")}


def fixed_hash_seed() -> None:
    """Run the helper again with PYTHONHASHSEED=0 unless it is set, so the order of a set can't
    change a fixture. `cargo xtask golden capture` sets it."""
    if os.environ.get("PYTHONHASHSEED") != "0":
        env = {**os.environ, "PYTHONHASHSEED": "0"}
        sys.exit(subprocess.call([sys.executable, *sys.argv], env=env))


def check_checkout(root: Path, *also: str) -> dict[str, str]:
    """The versions of Python, of the packages to capture from and of the distributions in
    *also*. Refuses packages not installed from *root* (`pip install -e lib -e tools/emu`),
    whose submodules xtask has checked are at their pins."""
    if sys.version_info < (3, 11):
        sys.exit(f"Python 3.11+ is needed, this is {platform.python_version()}")
    versions = {"python": platform.python_version()}
    for name, (module, sub) in PACKAGES.items():
        imported = __import__(module)
        where = Path(imported.__file__).resolve()
        if not where.is_relative_to((root / sub).resolve()):
            sys.exit(
                f"{module} is imported from {where}, not from {root / sub}: install it from "
                f"this checkout with `pip install -e {root / sub}`"
            )
        versions[name] = version(name)
    versions.update((name, version(name)) for name in also)
    return versions


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def write_json(path: Path, data: Any, *, indent: int | None = None) -> None:
    """A fixture: sorted keys, LF line endings, a final newline, and no NaN or infinity."""
    separators = (",", ": ") if indent is not None else (",", ":")
    text = json.dumps(
        data, sort_keys=True, indent=indent, separators=separators, ensure_ascii=False,
        allow_nan=False,
    )
    path.write_bytes((text + "\n").encode("utf-8"))


def print_inputs(inputs: dict[str, Any]) -> None:
    """The manifest's inputs, as one JSON object on stdout. MANIFEST.toml is TOML, which has
    no null, so a null is refused here rather than by xtask."""

    def check(value: Any, where: str) -> None:
        if value is None:
            raise ValueError(f"manifest input {where} is null")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"manifest input {where} is {value}")
        if isinstance(value, dict):
            for key, item in value.items():
                check(item, f"{where}.{key}")
        elif isinstance(value, list):
            for i, item in enumerate(value):
                check(item, f"{where}[{i}]")

    check(inputs, "inputs")
    sys.stdout.write(json.dumps(inputs, sort_keys=True, allow_nan=False) + "\n")
