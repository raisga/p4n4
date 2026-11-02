"""Golden capture helper for `sim-series`: what v0.4.2's sensor simulator publishes.

`cargo xtask golden capture sim-series` runs it with P4N4_GOLDEN_PYTHON (see emu_limits.py):

    python xtask/golden/sim_series.py --root . --out DIR

Each case runs p4n4_emu.sim.sensor_sim.run() against a recording stand-in for paho's MQTT
client, on a clock that moves only when the simulator waits, so an hour of readings takes
seconds and needs no broker. It writes DIR/<case>.json and prints the manifest inputs on
stdout as one JSON object.

The Rust simulator draws different random numbers, so the series are compared statistically
(RUST_REWRITE_PLAN.md §10). Each topic keeps its full series, except that media feeds keep one
summary per message, with the statistics a comparison starts from. Replays draw no random
numbers, so they can be compared exactly.

A run repeats exactly given the scenario's seed, GLOBAL_SEED for the `random` module the wave
generators draw from, PYTHONHASHSEED=0 and START. A device's phase depends only on its id.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import math
import os
import random
import sys
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest import mock

import common

log = logging.getLogger("sim-series")

# Where the simulated clock starts: 2023-11-14T22:13:20Z
START = 1_700_000_000.0
GLOBAL_SEED = 0
# Vectors up to this long (the accelerometer) keep each component; longer ones (media feeds)
# keep a summary per message
SHORT_VECTOR = 8
EXAMPLE_CHARS = 240
# Waits after which a case is taken to be stuck
MAX_WAITS = 10_000_000


@dataclasses.dataclass(frozen=True)
class Case:
    name: str
    scenario: str | None  # relative to the superproject; None: the built-in default
    duration: float  # simulated seconds
    devices: int | None = None  # devices of the built-in default


CASES = (
    # What `sim start` runs without a scenario: every built-in measurement. 1800 s is six
    # periods of the waves and thirty of the CPU load
    Case("builtin", None, 1800, devices=2),
    # Room sensors, and a device with every fault; 3600 s is six periods of its 600 s wave
    Case("sim-scenario", "tools/emu/examples/sim-scenario.yml", 3600),
    # Firmware-like devices, a camera, a microphone and a looping replay. The media take
    # about 25 ms a round (11 s in all); 900 s covers three wake-ups of the soil sensors
    # and, with seed 7, two Wi-Fi drops
    Case("sim-edge", "tools/emu/examples/sim-edge.yml", 900),
)


class SimClock:
    """time.time() for the simulator, and the stop event run() waits on: waiting moves the
    clock, and the event is set once the case's time is up."""

    def __init__(self, end: float) -> None:
        self.now = START
        self.end = end
        self.waits = 0

    def __call__(self) -> float:
        return self.now

    def is_set(self) -> bool:
        return self.now >= self.end

    def set(self) -> None:
        self.end = self.now

    def wait(self, timeout: float | None = None) -> bool:
        self.waits += 1
        if self.waits > MAX_WAITS:
            raise RuntimeError("the simulator stopped moving the clock")
        self.now = self.end if timeout is None else min(self.now + timeout, self.end)
        return self.is_set()


@dataclasses.dataclass
class Recorder:
    """What the broker sees: messages, and the clients' connections."""

    clock: SimClock
    messages: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    events: list[dict[str, Any]] = dataclasses.field(default_factory=list)

    def ms(self) -> int:
        return round((self.clock() - START) * 1000)

    def message(self, client: str, topic: str, payload: Any, qos: int, retain: bool,
                will: bool = False) -> None:
        if isinstance(payload, bytes | bytearray):
            payload = payload.decode("utf-8", "replace")
        self.messages.append({
            "ms": self.ms(), "client": client, "topic": topic,
            "payload": "" if payload is None else str(payload),
            "qos": qos, "retain": bool(retain), "will": will,
        })

    def event(self, client: str, event: str, detail: Any = None) -> None:
        entry = {"ms": self.ms(), "client": client, "event": event}
        if detail is not None:
            entry["detail"] = detail
        self.events.append(entry)


class Published:
    """paho's MQTTMessageInfo for a message the broker has acknowledged."""

    def __init__(self, mid: int) -> None:
        self.mid = mid
        self.rc = 0

    def wait_for_publish(self, timeout: float | None = None) -> None:
        return None

    def is_published(self) -> bool:
        return True


def fake_client(recorder: Recorder) -> type:
    """A stand-in for paho's Client with the calls the simulator makes (sensor_sim.py and
    mcu.py). It connects as soon as its loop starts and runs callbacks at once, so McuNode's
    waits for them return at once. A disconnect with reason code 4 makes the broker publish
    the will, as Mosquitto does."""
    import paho.mqtt.client as mqtt
    from paho.mqtt.packettypes import PacketTypes
    from paho.mqtt.reasoncodes import ReasonCode

    class FakeClient:
        def __init__(self, callback_api_version: Any, client_id: str = "", **_: Any) -> None:
            self.id = client_id or "sim"
            self.connected = False
            self.will: tuple[str, Any, int, bool] | None = None
            self.mid = 0
            self.on_connect = self.on_connect_fail = self.on_disconnect = None
            self.on_message = self.on_subscribe = None

        def reconnect_delay_set(self, *_: Any, **__: Any) -> None:
            pass

        def username_pw_set(self, *_: Any, **__: Any) -> None:
            pass

        def tls_set(self, *_: Any, **__: Any) -> None:
            pass

        def will_set(self, topic: str, payload: Any = None, qos: int = 0,
                     retain: bool = False, properties: Any = None) -> None:
            self.will = (topic, payload, qos, retain)

        def connect_async(self, *_: Any, **__: Any) -> None:
            pass

        def loop_start(self) -> None:
            if self.connected:
                return
            self.connected = True
            recorder.event(self.id, "connect")
            if self.on_connect is not None:
                self.on_connect(self, None, mqtt.ConnectFlags(session_present=False),
                                ReasonCode(PacketTypes.CONNACK, identifier=0), None)

        def loop_stop(self) -> None:
            pass

        def is_connected(self) -> bool:
            return self.connected

        def publish(self, topic: str, payload: Any = None, qos: int = 0, retain: bool = False,
                    properties: Any = None) -> Published:
            self.mid += 1
            if self.connected:
                recorder.message(self.id, topic, payload, qos, retain)
            else:
                recorder.event(self.id, "publish-while-disconnected", topic)
            return Published(self.mid)

        def subscribe(self, topic: str, qos: int = 0, **_: Any) -> tuple[int, int]:
            self.mid += 1
            recorder.event(self.id, "subscribe", topic)
            if self.on_subscribe is not None:
                self.on_subscribe(self, None, self.mid,
                                  [ReasonCode(PacketTypes.SUBACK, identifier=qos)], None)
            return (0, self.mid)

        def disconnect(self, reasoncode: Any = None, properties: Any = None) -> int:
            if not self.connected:
                return mqtt.MQTT_ERR_NO_CONN
            self.connected = False
            code = reasoncode.value if reasoncode is not None else 0
            recorder.event(self.id, "disconnect", code)
            if code == 4 and self.will is not None:
                topic, payload, qos, retain = self.will
                recorder.message(self.id, topic, payload, qos, retain, will=True)
            if self.on_disconnect is not None:
                self.on_disconnect(self, None,
                                   mqtt.DisconnectFlags(is_disconnect_packet_from_server=False),
                                   ReasonCode(PacketTypes.DISCONNECT, identifier=0), None)
            return mqtt.MQTT_ERR_SUCCESS

    return FakeClient


@contextmanager
def simulated(clock: SimClock, recorder: Recorder):
    """time.time() on the simulated clock, the recording client, and none of the settings
    run() reads from the environment."""
    from p4n4_emu.sim import sensor_sim

    with (
        mock.patch.object(time, "time", clock),
        mock.patch.object(sensor_sim.mqtt, "Client", fake_client(recorder)),
        mock.patch.dict(os.environ),
    ):
        for key in [k for k in os.environ if k.startswith(("SIM_", "MQTT_"))]:
            del os.environ[key]
        yield


def classify(topic: str, payload: str) -> tuple[str, dict[str, Any] | None]:
    """The payload's kind and its JSON object. Besides ok and text (availability), the kinds
    are those of the malformed fault (sim/faults.py)."""
    try:
        doc = json.loads(payload)
    except ValueError:
        if payload.startswith("{"):
            return "truncated", None
        if payload.startswith("value="):
            return "not-json", None
        return "text", None
    if not isinstance(doc, dict):
        return "text", None
    if isinstance(doc.get("value"), str):
        return "string-value", doc
    if topic.startswith("sensors/") and "value" not in doc and "values" not in doc:
        return "no-value", doc
    return "ok", doc


def fields(doc: dict[str, Any]) -> tuple[dict[str, float], dict[str, str]]:
    """A payload's numbers, by column, and its strings (unit, firmware, ...). `ts` is left
    out: it becomes the lag."""
    numbers: dict[str, float] = {}
    strings: dict[str, str] = {}
    for key, value in doc.items():
        if key == "ts" or isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            numbers[key] = value
        elif isinstance(value, str):
            if key != "value":  # a string-value fault's value is no constant
                strings[key] = value
        elif isinstance(value, list) and value and all(
            isinstance(v, int | float) and not isinstance(v, bool) for v in value
        ):
            if len(value) <= SHORT_VECTOR:
                numbers.update({f"{key}[{i}]": v for i, v in enumerate(value)})
            else:
                mean = math.fsum(value) / len(value)
                numbers[f"{key}.len"] = len(value)
                numbers[f"{key}.mean"] = mean
                numbers[f"{key}.stdev"] = math.sqrt(
                    math.fsum((v - mean) ** 2 for v in value) / len(value))
                numbers[f"{key}.min"] = min(value)
                numbers[f"{key}.max"] = max(value)
    return numbers, strings


def describe(values: list[float]) -> dict[str, float] | None:
    """Count, mean, population standard deviation, extremes and nearest-rank percentiles."""
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mean = math.fsum(s) / n

    def rank(q: float) -> float:
        return s[min(n - 1, max(0, math.ceil(q * n) - 1))]

    return {
        "n": n, "mean": mean, "stdev": math.sqrt(math.fsum((x - mean) ** 2 for x in s) / n),
        "min": s[0], "p05": rank(0.05), "p50": rank(0.5), "p95": rank(0.95), "max": s[-1],
    }


def topics(messages: list[dict[str, Any]]) -> dict[str, Any]:
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for m in messages:
        by_topic.setdefault(m["topic"], []).append(m)
    return {topic: topic_summary(topic, ms) for topic, ms in sorted(by_topic.items())}


def topic_summary(topic: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    kinds: Counter[str] = Counter()
    texts: Counter[str] = Counter()
    examples: dict[str, str] = {}
    strings: dict[str, set[str]] = {}
    rows: list[tuple[int, int | None, dict[str, float]]] = []
    for m in messages:
        kind, doc = classify(topic, m["payload"])
        kinds[kind] += 1
        examples.setdefault(kind, m["payload"][:EXAMPLE_CHARS])
        if kind == "text":
            texts[m["payload"]] += 1
        numbers, lag = {}, None
        if doc is not None:
            numbers, found = fields(doc)
            for key, value in found.items():
                strings.setdefault(key, set()).add(value)
            if isinstance(doc.get("ts"), int):
                lag = int(START * 1000) + m["ms"] - doc["ts"]
        rows.append((m["ms"], lag, numbers))

    publish = [r[0] for r in rows]
    series: dict[str, list[Any]] = {"publish_ms": publish}
    if any(r[1] is not None for r in rows):
        series["ts_lag_ms"] = [r[1] for r in rows]
    for column in sorted({key for r in rows for key in r[2]}):
        series[column] = [r[2].get(column) for r in rows]
    stats = {
        column: describe([v for v in values if v is not None])
        for column, values in series.items() if column != "publish_ms"
    }
    stats["interval_ms"] = describe([b - a for a, b in zip(publish, publish[1:], strict=False)])
    return {
        "count": len(messages),
        "clients": sorted({m["client"] for m in messages}),
        "qos": sorted({m["qos"] for m in messages}),
        "retain": sorted({m["retain"] for m in messages}),
        "will": sum(m["will"] for m in messages),
        "kinds": dict(sorted(kinds.items())),
        "texts": dict(sorted(texts.items())),
        "constants": {key: sorted(values) for key, values in sorted(strings.items())},
        "examples": examples,
        "series": series,
        "stats": stats,
    }


def run_case(root: Path, case: Case) -> dict[str, Any]:
    from p4n4_emu.sim import sensor_sim
    from p4n4_emu.sim.scenario import load_scenario

    scenario = load_scenario(root / case.scenario) if case.scenario else None
    clock = SimClock(START + case.duration)
    recorder = Recorder(clock)
    random.seed(GLOBAL_SEED)
    with simulated(clock, recorder):
        sensor_sim.run(host="golden", port=1883, devices=case.devices, stop=clock,
                       scenario=scenario, auth=sensor_sim.BrokerAuth(), clock=clock)
    return {
        "case": case.name,
        "scenario": case.scenario,
        "seed": scenario.seed if scenario is not None else None,
        "devices": case.devices,
        "start": START,
        "duration_s": case.duration,
        "messages": len(recorder.messages),
        "topics": topics(recorder.messages),
        "events": recorder.events,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, required=True, help="the superproject")
    parser.add_argument("--out", type=Path, required=True, help="where the fixtures go")
    parser.add_argument("--case", action="append", choices=[c.name for c in CASES],
                        help="run only this case (repeatable)")
    parser.add_argument("--max-duration", type=float, metavar="SECONDS",
                        help="cap each case's simulated time, for a quick try (recorded)")
    args = parser.parse_args()
    common.fixed_hash_seed()
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s", stream=sys.stderr)
    # run() logs every Wi-Fi drop and reconnection
    logging.getLogger("p4n4_emu").setLevel(logging.WARNING)
    versions = common.check_checkout(args.root, "paho-mqtt", "PyYAML")

    args.out.mkdir(parents=True, exist_ok=True)
    inputs: dict[str, Any] = {}
    for case in CASES:
        if args.case and case.name not in args.case:
            continue
        if args.max_duration:
            case = dataclasses.replace(case, duration=min(case.duration, args.max_duration))
        began = time.perf_counter()
        fixture = run_case(args.root, case)
        common.write_json(args.out / f"{case.name}.json", fixture)
        log.info("%s: %d messages on %d topics in %.1f s", case.name, fixture["messages"],
                 len(fixture["topics"]), time.perf_counter() - began)
        inputs[case.name] = {
            key: value for key, value in (
                ("scenario", case.scenario or "builtin"),
                ("seed", fixture["seed"]),
                ("devices", case.devices),
                ("duration_s", case.duration),
            ) if value is not None
        }

    common.print_inputs({
        "helper": "xtask/golden/sim_series.py",
        "versions": versions,
        "start": START,
        "global_seed": GLOBAL_SEED,
        "hash_seed": 0,
        "cases": inputs,
    })


if __name__ == "__main__":
    main()
