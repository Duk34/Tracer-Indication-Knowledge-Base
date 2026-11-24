#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

BASH="$(command -v bash)"

if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON="${VIRTUAL_ENV}/bin/python"
elif [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="$(command -v python)"
fi




"$BASH" scripts/download_radiopharma.sh
"$PYTHON" scripts/csv_from_downloaded_radiopharma_csvs.py
"$PYTHON"  scripts/map_target_genes_and_species.py \
    radiopharma_tracers_from_downloaded_csvs.csv \
    radiopharma_tracers_mapped_genes_species.csv \
    fill-missing



