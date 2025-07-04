#!/bin/bash
set -euo pipefail

# Carga la contraseña si viene por archivo
if [ -v PASSWORD_FILE ]; then
    PASSWORD="$(< "$PASSWORD_FILE")"
fi

# Parámetros de conexión a Postgres
: ${HOST:=${DB_PORT_5432_TCP_ADDR:='db'}}
: ${PORT:=${DB_PORT_5432_TCP_PORT:=5432}}
: ${USER:=${DB_ENV_POSTGRES_USER:=${POSTGRES_USER:='odoo'}}}
: ${PASSWORD:=${DB_ENV_POSTGRES_PASSWORD:=${POSTGRES_PASSWORD:='odoo'}}}

DB_ARGS=()
function check_config() {
    local param="$1"; shift
    local value="$1"
    if grep -q -E "^\s*${param}\s*=" "$ODOO_RC"; then
        value="$(grep -E "^\s*${param}\s*=" "$ODOO_RC" \
                  | cut -d= -f2 | tr -d ' \"')"
    fi
    DB_ARGS+=( "--${param}" "${value}" )
}

check_config db_host  "$HOST"
check_config db_port  "$PORT"
check_config db_user  "$USER"
check_config db_password "$PASSWORD"

start_debug() {
    echo "[entrypoint] arrancando debugpy en 0.0.0.0:${DEBUG_PORT} y esperando cliente"
    wait-for-psql.py "${DB_ARGS[@]}" --timeout=30

    # Ejecuta debugpy *como* lanzador de Odoo (módulo)
    exec python3 -Xfrozen_modules=off -m debugpy \
        --listen "0.0.0.0:${DEBUG_PORT}" \
        --wait-for-client \
        --log-to-stderr \
        -m odoo \
            --dev=all \
            "$@" \
            --http-interface=0.0.0.0 \
            --http-port=8069 \
            "${DB_ARGS[@]}"
}

start_odoo() {
    echo "[entrypoint] arrancando Odoo sin debug"
    wait-for-psql.py "${DB_ARGS[@]}" --timeout=30
    exec odoo \
        --http-interface=0.0.0.0 \
        --http-port=8069 \
        "$@" \
        "${DB_ARGS[@]}"
}

if [[ -n "${DEBUG_PORT-}" ]]; then
    start_debug "$@"
else
    start_odoo "$@"
fi

exit 1
