#!/usr/bin/env bash
set -euo pipefail

SERVICES_DIR="../services"
DEST_CHECKERS="ansible/roles/forcad-setup/files/checkers"

# pt 0: pack services & checkers
tar -cf "ansible/services.tar" -C "$(dirname "$SERVICES_DIR")" "$(basename "$SERVICES_DIR")"
echo "Services archive created"

if [ -d "$DEST_CHECKERS" ]; then
    echo "[!] $DEST_CHECKERS already exists — replacing it"
    rm -rf "$DEST_CHECKERS"
fi

cp -r "$SRC_CHECKERS" "$DEST_CHECKERS"

# pt 1: create VMs
source terraform/creds.sh
tofu -chdir="./terraform" apply -auto-approve

# pt 2: setup VMs
ANSIBLE_CONFIG=./ansible/ansible.cfg ansible-playbook ./ansible/playbook.yml
