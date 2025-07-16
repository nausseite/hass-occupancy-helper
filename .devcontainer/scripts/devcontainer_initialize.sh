#!/bin/bash

set -euo pipefail

if [[ ! -f .env ]]; then
    echo "Creating .env file as it does not exist." >&2
    echo "# Environment variables for Docker Compose" >.env
    echo "LOCAL_WORKSPACE_FOLDER='${PWD}'" >>.env
fi

# Ensure there is no leftover from previous run
docker compose down --remove-orphans --volumes

# Add LOCAL_WORKSPACE_FOLDER to .env file
readonly wanted_line_key="LOCAL_WORKSPACE_FOLDER"
readonly wanted_line="${wanted_line_key}='${PWD}'"
readonly file=".env"
echo "Writing ${wanted_line} to ${file}" >&2
if [[ -f "${file}" ]] && grep -q "^${wanted_line_key}=" "${file}"; then
    sed -i "s,^${wanted_line_key}=.*,${wanted_line}," "${file}"
else
    echo "${wanted_line}" >>"${file}"
fi

echo "$0 finished." >&2