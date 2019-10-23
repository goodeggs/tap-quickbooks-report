#!/usr/bin/env bash
set -e
set -o pipefail
set -u

CONFIG_PATH=".config/secrets"
mkdir -p "$(dirname "$CONFIG_PATH")"

cmd=$1; shift

case "$cmd" in
  get) cat "$CONFIG_PATH" ;;
  set) echo "$1" > "$CONFIG_PATH" ;;
  *) echo 'usage: <get|set> <token>'; exit 0 ;;
esac