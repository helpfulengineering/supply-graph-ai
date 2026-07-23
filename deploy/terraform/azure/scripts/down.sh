#!/usr/bin/env bash
# Destroy ephemeral Azure federation stack (entire resource group).
set -euo pipefail

TF_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$TF_DIR"

TFVARS="${TFVARS:-environments/federation-ephemeral.tfvars}"
EXTRA=()
[[ -f "$TFVARS" ]] && EXTRA=(-var-file="$TFVARS")

echo "[fed-azure-down] terraform destroy (resource group + all deps)"
terraform destroy -auto-approve "${EXTRA[@]}" \
  -var '_manual_peers_a=' \
  -var '_manual_peers_b=' \
  -var '_manual_peers_edge=' \
  -var '_manual_peers_relay='

echo "[fed-azure-down] done — verify no leftover RG in the Azure portal if destroy warned"
