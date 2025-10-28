#!/usr/bin/env bash
set -e

# Orchestration simple: installe le maître localement et déploie node_exporter + dispynode sur chaque worker via SSH

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}/.."

INV_FILE="${ROOT_DIR}/inventory/nodes.yaml"

if [ ! -f "$INV_FILE" ]; then
  echo "Inventaire introuvable: $INV_FILE"
  exit 1
fi

mapfile -t NODES < <(grep -E "^\s*-\s+node[0-9]+\.lan" "$INV_FILE" | sed -E 's/^\s*-\s+//')

echo "Installation du maître locale..."
sudo bash "${SCRIPT_DIR}/install_master.sh"

echo "Déploiement sur workers..."
for host in "${NODES[@]}"; do
  echo "- $host"
  scp -r "${ROOT_DIR}/scripts" "${USER}@${host}:/tmp/" || true
  ssh "${USER}@${host}" "sudo bash /tmp/scripts/install_node.sh"
done

echo "Cluster installé. Pensez à lancer le monitoring: cd monitoring && docker compose up -d"

