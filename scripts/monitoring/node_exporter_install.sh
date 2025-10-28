#!/usr/bin/env bash
set -e

# Installe Node Exporter en service systemd sur Raspberry Pi (armv7/arm64)

if [ "${EUID}" -ne 0 ]; then
  echo "Ce script doit être exécuté en root"
  exit 1
fi

ARCH=$(uname -m)
case "$ARCH" in
  armv7l) PKG_ARCH="armv7" ;;
  aarch64) PKG_ARCH="arm64" ;;
  *) echo "Architecture $ARCH non gérée automatiquement. Installez manuellement node_exporter." ; exit 1 ;;
esac

VERSION="1.8.2"
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "Téléchargement node_exporter $VERSION pour $PKG_ARCH..."
URL="https://github.com/prometheus/node_exporter/releases/download/v${VERSION}/node_exporter-${VERSION}.linux-${PKG_ARCH}.tar.gz"
wget -q "$URL"
tar xzf "node_exporter-${VERSION}.linux-${PKG_ARCH}.tar.gz"
install -m 0755 "node_exporter-${VERSION}.linux-${PKG_ARCH}/node_exporter" /usr/local/bin/node_exporter

useradd -r -s /usr/sbin/nologin nodeexp || true

cat >/etc/systemd/system/node_exporter.service <<'SERVICE'
[Unit]
Description=Prometheus Node Exporter
After=network-online.target
Wants=network-online.target

[Service]
User=nodeexp
Group=nodeexp
Type=simple
ExecStart=/usr/local/bin/node_exporter --collector.systemd
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable node_exporter
systemctl restart node_exporter

echo "Node Exporter installé et démarré sur port 9100."

