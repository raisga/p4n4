#!/usr/bin/env bash
# S1 static checks (RUST_REWRITE_PLAN.md §9.1): run each downloaded Compose binary against
# project/ and probes/ without a Docker engine, then print a result matrix.
#
#   bash static-checks.sh [VERSION...]     default: every $S1_HOME/bin/v*/docker-compose
#   SAVE_FIXTURES="2.39.2 2.21.0" bash static-checks.sh 2.39.2 2.21.0
#                                          also writes fixtures/v<VERSION>/
#
# Commands that need the engine fail against the nonexistent socket and show as "eng".
set -u -o pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
S1_HOME=${S1_HOME:-$HOME/.cache/p4n4-spikes/s1-compose}
BIN=$S1_HOME/bin
WORK=$S1_HOME/work

# Never reach a real engine: a socket that does not exist, no context, an empty config dir.
export DOCKER_HOST=unix:///nonexistent/docker.sock
unset DOCKER_CONTEXT DOCKER_TLS_VERIFY DOCKER_CERT_PATH
while read -r name; do unset "$name"; done < <(compgen -e | grep '^COMPOSE_')
export DOCKER_CONFIG=$S1_HOME/docker-config
mkdir -p "$DOCKER_CONFIG"

if [ $# -gt 0 ]; then
  VERSIONS=("$@")
else
  mapfile -t VERSIONS < <(ls "$BIN" | sed 's/^v//' | sort -V)
fi

ROWS=(
  version-json up-wait up-wait-timeout ps-format images-format ls-format
  config-profiles config-variables config-no-interp config-hash other-flags
  cfg-yaml cfg-json json-ports json-network json-env
  svc-profiles svc-no-profiles svc-profile-star svc-profile-sim target-sim target-sim-prof profiles-list overlay-f ps-json
  cwd-root-abs-f cwd-root-rel-f
  inc-env-file dep-disabled-opt dep-disabled-req dep-undefined-opt dep-generated root-redefines
)
declare -A RES MSG

set_res() { RES["$1|$VER"]=$2; MSG["$1|$VER"]=$3; }

# pycheck MODE FILE [ARG]: check a command's stdout; print a detail, exit 1 on a mismatch.
pycheck() {
  python3 - "$@" <<'PY'
import json, sys

mode, path = sys.argv[1], sys.argv[2]
arg = sys.argv[3] if len(sys.argv) > 3 else ""
text = open(path, encoding="utf-8").read()

def fail(msg):
    print(msg)
    sys.exit(1)

def load():
    try:
        return json.loads(text)
    except ValueError:
        first = text.strip().splitlines()[0] if text.strip() else "(empty)"
        fail("not JSON; first line: " + first[:60])

if mode == "lines":
    got = sorted(l.strip() for l in text.splitlines() if l.strip())
    want = sorted(x for x in arg.split(",") if x)
    if got != want:
        fail("got [" + ",".join(got) + "], want [" + ",".join(want) + "]")
    print(",".join(got))
elif mode == "contains":
    if arg not in text:
        fail("output lacks " + arg)
elif mode == "incenv":
    if "from-include-env-file" in text:
        print("P4N4S1_INC=from-include-env-file")
    elif "unset" in text:
        fail("P4N4S1_INC=unset: include env_file not used")
    else:
        fail("P4N4S1_INC missing from output")
elif mode == "version":
    v = load().get("version")
    if not v:
        fail("no version key")
    print(v)
else:
    doc = load()
    svc = doc.get("services") or {}
    if mode == "json":
        print("services=" + ",".join(sorted(svc)))
    elif mode == "ports":
        def pub(s):
            return sorted("%s:%s->%s" % (p.get("host_ip"), p.get("published"), p.get("target"))
                          for p in (svc.get(s) or {}).get("ports") or [])
        got = {s: pub(s) for s in ("server", "mqtt")}
        if got != {"server": ["127.0.0.1:18100->8080"], "mqtt": ["127.0.0.1:18101->1883"]}:
            fail("ports " + json.dumps(got))
        print("ports " + json.dumps(got))
    elif mode == "network":
        net = (doc.get("networks") or {}).get("default") or {}
        pool = ((net.get("ipam") or {}).get("config") or [{}])[0]
        addr = (((svc.get("server") or {}).get("networks") or {}).get("default") or {}).get("ipv4_address")
        got = [net.get("name"), pool.get("subnet"), pool.get("ip_range"), addr]
        if got != ["p4n4-net", "10.201.1.0/24", "10.201.1.128/25", "10.201.1.2"]:
            fail("network " + json.dumps(got))
        print("network " + json.dumps(got))
    elif mode == "env":
        got = [((svc.get("server") or {}).get("environment") or {}).get("P4N4S1_MSG"),
               ((svc.get("agent") or {}).get("environment") or {}).get("MQTT_HOST")]
        if got != ["from-root-env", "mqtt"]:
            fail("env " + json.dumps(got))
        print("env " + json.dumps(got))
    else:
        fail("unknown mode " + mode)
PY
}

# run ROW DIR ARGS...: run the binary in DIR with a 60 s limit, keeping stdout, stderr and status.
run() {
  local row=$1 dir=$2
  shift 2
  (cd "$dir" && timeout 60 "$DC" "$@") >"$OUT/$row.out" 2>"$OUT/$row.err"
  echo $? >"$OUT/$row.rc"
}

# errline FILE: the first line of an error that is not a warning, with work paths shortened.
errline() {
  grep -v -E '^[[:space:]]*$|level=warn|^WARN|^WARNING' "$1" | head -n 1 \
    | sed -e "s#$W#<work>#g" | cut -c1-150
}

# judge ROW [MODE [ARG]]: classify the last run of ROW; MODE checks stdout when it succeeded.
judge() {
  local row=$1 rc detail
  shift
  rc=$(cat "$OUT/$row.rc")
  if [ "$rc" = 124 ]; then
    set_res "$row" T/O "timed out after 60 s"
  elif [ "$rc" != 0 ]; then
    if grep -q -E 'nonexistent/docker\.sock|Cannot connect to the Docker daemon' "$OUT/$row.err"; then
      set_res "$row" eng "$(errline "$OUT/$row.err")"
    else
      set_res "$row" REJ "$(errline "$OUT/$row.err")"
    fi
  elif [ $# -gt 0 ]; then
    if detail=$(pycheck "$1" "$OUT/$row.out" "${2:-}"); then
      set_res "$row" ok "$detail"
    else
      set_res "$row" BAD "$detail"
    fi
  else
    set_res "$row" ok ""
  fi
}

has_flag() {
  timeout 60 "$DC" "$1" --help 2>&1 | grep -E -q -- "(^|[[:space:],])$2([[:space:],=]|$)"
}

# flag ROW SUBCOMMAND FLAG: whether `SUBCOMMAND --help` lists FLAG.
flag() {
  if has_flag "$2" "$3"; then
    set_res "$1" ok ""
  else
    set_res "$1" n/a "$2 --help does not list $3"
  fi
}

# flags ROW "SUBCOMMAND FLAG"...: like flag, for several flags at once.
flags() {
  local row=$1 pair missing=()
  shift
  for pair in "$@"; do
    has_flag "${pair%% *}" "${pair#* }" || missing+=("$pair")
  done
  if [ ${#missing[@]} -eq 0 ]; then
    set_res "$row" ok ""
  else
    set_res "$row" n/a "--help does not list: $(IFS=,; echo "${missing[*]}")"
  fi
}

for VER in "${VERSIONS[@]}"; do
  DC=$BIN/v$VER/docker-compose
  W=$WORK/v$VER
  OUT=$W/out
  rm -rf "$W"
  mkdir -p "$OUT"
  cp -a "$HERE/project" "$HERE/probes" "$W/"
  P=$W/project
  cp "$P/dot.env" "$P/.env"
  cp -a "$P" "$W/project-noprof"
  grep -v '^COMPOSE_PROFILES=' "$P/dot.env" >"$W/project-noprof/.env"
  # How p4n4 should address a project (§6.1): the cwd is the project directory too, because
  # -f and an include's env_file are resolved against the cwd (see the cwd-root-* rows).
  F=(--project-directory "$P" -f compose.yaml)

  run version-json / version --format json
  judge version-json version
  flag up-wait up --wait
  flag up-wait-timeout up --wait-timeout
  flag ps-format ps --format
  flag images-format images --format
  flag ls-format ls --format
  flag config-profiles config --profiles
  flag config-variables config --variables
  flag config-no-interp config --no-interpolate
  flag config-hash config --hash
  # Flags behind p4n4 up/down/logs/exec/run and V012 (§5.5, §6.3).
  flags other-flags "up --pull" "down --volumes" "logs --follow" "logs --since" "logs --tail" \
    "exec -T" "run --rm" "config --quiet"

  run cfg-yaml "$P" "${F[@]}" config
  judge cfg-yaml
  run cfg-json "$P" "${F[@]}" config --format json
  judge cfg-json json
  for pair in json-ports:ports json-network:network json-env:env; do
    row=${pair%%:*}
    if [ "${RES[cfg-json|$VER]}" != ok ]; then
      set_res "$row" skp "cfg-json is ${RES[cfg-json|$VER]}"
    elif detail=$(pycheck "${pair#*:}" "$OUT/cfg-json.out"); then
      set_res "$row" ok "$detail"
    else
      set_res "$row" BAD "$detail"
    fi
  done

  run svc-profiles "$P" "${F[@]}" config --services
  judge svc-profiles lines agent,mqtt,server
  run svc-no-profiles "$W/project-noprof" --project-directory "$W/project-noprof" -f compose.yaml config --services
  judge svc-no-profiles lines server
  run svc-profile-star "$P" "${F[@]}" --profile '*' config --services
  judge svc-profile-star lines agent,mqtt,server,sim
  # --profile replaces COMPOSE_PROFILES from .env instead of adding to it.
  run svc-profile-sim "$P" "${F[@]}" --profile sim config --services
  judge svc-profile-sim lines server,sim
  run target-sim "$P" "${F[@]}" config sim
  judge target-sim contains p4n4s1-sim
  run target-sim-prof "$P" "${F[@]}" --profile sim config sim
  judge target-sim-prof contains p4n4s1-sim
  if [ "${RES[config-profiles|$VER]}" = ok ]; then
    run profiles-list "$P" "${F[@]}" config --profiles
    judge profiles-list lines agent,mqtt,sim
  else
    set_res profiles-list n/a "no config --profiles"
  fi
  run overlay-f "$P" "${F[@]}" -f .p4n4/emu/compose.emu.yaml config
  judge overlay-f contains memory
  run ps-json "$P" "${F[@]}" ps --format json
  judge ps-json

  # The same project addressed from another cwd: absolute -f, then -f relative to --project-directory.
  run cwd-root-abs-f / --project-directory "$P" -f "$P/compose.yaml" config --services
  judge cwd-root-abs-f lines agent,mqtt,server
  run cwd-root-rel-f / --project-directory "$P" -f compose.yaml config --services
  judge cwd-root-rel-f lines agent,mqtt,server

  D=$W/probes
  run inc-env-file "$D/include-env-file" config
  judge inc-env-file incenv
  run dep-disabled-opt "$D/dep-disabled-optional" config --services
  judge dep-disabled-opt lines app
  run dep-disabled-req "$D/dep-disabled-required" config --services
  judge dep-disabled-req lines app
  run dep-undefined-opt "$D/dep-undefined-optional" config --services
  judge dep-undefined-opt lines agent
  run dep-generated "$D/dep-generated" config
  judge dep-generated contains depends_on
  run root-redefines "$D/root-redefines-included" config
  judge root-redefines

  if [[ " ${SAVE_FIXTURES:-} " == *" $VER "* ]]; then
    if [ "${RES[cfg-json|$VER]}" = ok ] && [ "${RES[version-json|$VER]}" = ok ]; then
      FX=$HERE/fixtures/v$VER
      mkdir -p "$FX"
      sed -e "s#$P#/srv/p4n4s1#g" "$OUT/cfg-json.out" >"$FX/config.json"
      cp "$OUT/version-json.out" "$FX/version.json"
      echo "fixtures written: $FX" >&2
    else
      echo "v$VER: no fixtures, because cfg-json or version-json failed" >&2
    fi
  fi
done

echo "S1 static checks, $(date -u +%Y-%m-%dT%H:%MZ), DOCKER_HOST=$DOCKER_HOST"
echo "ok = accepted (and the output check passed, where the row has one)   REJ = rejected   BAD = accepted, wrong result"
echo "eng = needs the engine   n/a = flag not in --help   skp = prerequisite failed   T/O = timeout"
echo
printf '%-18s' ''
for VER in "${VERSIONS[@]}"; do printf ' %-7s' "$VER"; done
echo
for row in "${ROWS[@]}"; do
  printf '%-18s' "$row"
  for VER in "${VERSIONS[@]}"; do printf ' %-7s' "${RES[$row|$VER]:-?}"; done
  echo
done

echo
echo "Self-reported versions:"
for VER in "${VERSIONS[@]}"; do printf '  %-7s %s\n' "$VER" "${MSG[version-json|$VER]:-?}"; done

echo
echo "Details of the results other than ok (<work> = $WORK/v<VERSION>):"
for row in "${ROWS[@]}"; do
  unset seen order
  declare -A seen=()
  order=()
  for VER in "${VERSIONS[@]}"; do
    code=${RES[$row|$VER]:-?}
    [ "$code" = ok ] && continue
    key="$code ${MSG[$row|$VER]:-}"
    if [ -z "${seen[$key]+x}" ]; then
      order+=("$key")
      seen[$key]=$VER
    else
      seen[$key]+=",$VER"
    fi
  done
  for key in "${order[@]}"; do printf '  %-17s %s  [%s]\n' "$row" "$key" "${seen[$key]}"; done
done
