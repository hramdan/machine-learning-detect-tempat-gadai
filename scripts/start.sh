#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

pids=()
cleanup() {
  trap - EXIT INT TERM
  if ((${#pids[@]})); then
    kill "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

(cd backend && exec python -m uvicorn src.main:app --host 127.0.0.1 --port 8000) &
pids+=("$!")
(cd frontend && exec npm run dev) &
pids+=("$!")

set +e
wait -n "${pids[@]}"
status=$?
set -e
exit "$status"