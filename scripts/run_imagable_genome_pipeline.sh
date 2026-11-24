#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON="${VIRTUAL_ENV}/bin/python"
elif [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="$(command -v python)"
fi



"$PYTHON" scripts/download_imagable_genome_supplementary_data.py
"$PYTHON" scripts/imagable_genome_data_to_curation_scheme.py
"$PYTHON"  scripts/map_target_UniProtKB_ID_and_species.py \
    imageable_genome.csv \
    imageable_genome_mapped_uniprot.csv \
    fill-missing