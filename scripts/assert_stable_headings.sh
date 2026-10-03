#!/usr/bin/env bash
# Run the handoff brief CLI twice and require all six H2 headings.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
export PATH="${HOME}/.grok/bin:${PATH}"

HANDOFF="$ROOT/examples/sample-handoff.md"
ROLE="$ROOT/examples/sample-role.md"
CONSTRAINTS="$ROOT/examples/sample-constraints.md"

if [[ ! -f "$HANDOFF" ]]; then
  echo "FAIL"
  echo "missing fixture: $HANDOFF" >&2
  exit 1
fi

OUT1="$(mktemp "${TMPDIR:-/tmp}/handoff-brief-1-XXXXXX.md")"
OUT2="$(mktemp "${TMPDIR:-/tmp}/handoff-brief-2-XXXXXX.md")"
cleanup() {
  rm -f "$OUT1" "$OUT2"
}
trap cleanup EXIT

run_one() {
  local out="$1"
  local -a cmd=(
    python3 -m handoff_brief_engine
    --handoff-file "$HANDOFF"
    --out "$out"
  )
  if [[ -f "$ROLE" ]]; then
    cmd+=(--role-file "$ROLE")
  fi
  if [[ -f "$CONSTRAINTS" ]]; then
    cmd+=(--constraints-file "$CONSTRAINTS")
  fi
  "${cmd[@]}"
}

if ! run_one "$OUT1"; then
  echo "FAIL"
  exit 1
fi
if ! run_one "$OUT2"; then
  echo "FAIL"
  exit 1
fi

HEADINGS=(
  "## 交接对象与一句话状态"
  "## 已完成（可核对）"
  "## 未决与阻塞"
  "## 请接收方立刻做什么"
  "## 风险与过期信息"
  "## 明确不做"
)

fail=0
for f in "$OUT1" "$OUT2"; do
  if [[ ! -s "$f" ]]; then
    echo "empty output: $f" >&2
    fail=1
    continue
  fi
  for h in "${HEADINGS[@]}"; do
    if ! grep -qF -- "$h" "$f"; then
      echo "missing heading in $f: $h" >&2
      fail=1
    fi
  done
done

if [[ "$fail" -ne 0 ]]; then
  echo "FAIL"
  exit 1
fi

echo "PASS"
exit 0
