#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# infra/alratmanager/entrypoint.sh
# Alertmanager Docker Entrypoint
#
# Why this exists:
#   Alertmanager does NOT support environment variable substitution in its
#   config file natively. This script uses `envsubst` to replace all ${VAR}
#   placeholders in alertmanager.yml.template with real values from .env
#   (injected by Docker Compose via env_file), then starts Alertmanager.
#
# How it works:
#   1. Reads /etc/alertmanager/alertmanager.yml.template
#   2. Replaces ${VAR} → actual value
#   3. Writes result to /etc/alertmanager/alertmanager.yml (runtime config)
#   4. Starts alertmanager with the rendered config
# ─────────────────────────────────────────────────────────────────────────────
set -e

TEMPLATE="/etc/alertmanager/alertmanager.yml.template"
OUTPUT="/etc/alertmanager/alertmanager.yml"

echo "⚙️  Rendering alertmanager config from template..."
envsubst < "$TEMPLATE" > "$OUTPUT"
echo "✅ Config rendered to $OUTPUT"

echo "🚀 Starting Alertmanager..."
exec /bin/alertmanager \
  --config.file="$OUTPUT" \
  --storage.path=/alertmanager \
  "$@"
