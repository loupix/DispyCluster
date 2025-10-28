#!/usr/bin/env bash
set -e

# Vérifie SSH et node_exporter pour chaque noeud listé dans inventory/nodes.yaml

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INV_FILE="${SCRIPT_DIR}/../inventory/nodes.yaml"

if [ ! -f "$INV_FILE" ]; then
  echo "Inventaire introuvable: $INV_FILE"
  exit 1
fi

mapfile -t NODES < <(grep -E "^\s*-\s+node[0-9]+\.lan" "$INV_FILE" | sed -E 's/^\s*-\s+//')

ok=0
fail=0
for host in "${NODES[@]}"; do
  echo "Test $host..."
  if timeout 3 bash -c "</dev/tcp/$host/22" 2>/dev/null; then
    echo "  SSH: OK"
  else
    echo "  SSH: KO"
  fi
  if timeout 3 bash -c "</dev/tcp/$host/9100" 2>/dev/null; then
    echo "  node_exporter: OK"
    ok=$((ok+1))
  else
    echo "  node_exporter: KO"
    fail=$((fail+1))
  fi
done

echo "Résumé: $ok OK, $fail KO"

