#!/bin/sh
set -eu

SERVICE_USER="babuinterpreter"
SERVICE_UID="$(id -u "${SERVICE_USER}")"
SERVICE_GID="$(id -g "${SERVICE_USER}")"
STORAGE_DIR="/var/lib/babuinterpreter"
PORT="${BABUIN_SERVICE_PORT:-31337}"

if [ "$(id -u)" -eq 0 ]; then
    mkdir -p "${STORAGE_DIR}"
    chown -R "${SERVICE_UID}:${SERVICE_GID}" "${STORAGE_DIR}"
    chmod 0775 "${STORAGE_DIR}"
    find "${STORAGE_DIR}" -type f -exec chmod 0664 {} +

    exec setpriv \
        --reuid="${SERVICE_UID}" \
        --regid="${SERVICE_GID}" \
        --init-groups \
        socat "TCP-LISTEN:${PORT},reuseaddr,fork" EXEC:/service/entrypoint.py,stderr
fi

exec socat "TCP-LISTEN:${PORT},reuseaddr,fork" EXEC:/service/entrypoint.py,stderr
