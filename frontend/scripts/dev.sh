#!/usr/bin/env bash
set -euo pipefail

npm run dev:backend &
backend_pid=$!
frontend_pid=""

cleanup() {
  if [[ -n "$frontend_pid" ]]; then
    kill "$frontend_pid" 2>/dev/null || true
  fi
  kill "$backend_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

npm run dev:frontend &
frontend_pid=$!

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

if ! kill -0 "$backend_pid" 2>/dev/null; then
  echo "dev:backend exited unexpectedly" >&2
  kill "$frontend_pid" 2>/dev/null || true
  wait "$frontend_pid" 2>/dev/null || true
  exit 1
fi

wait "$frontend_pid"
frontend_status=$?
kill "$backend_pid" 2>/dev/null || true
wait "$backend_pid" 2>/dev/null || true
exit "$frontend_status"
