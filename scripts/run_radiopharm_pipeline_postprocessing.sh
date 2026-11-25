#!/usr/bin/env bash

# Run run_imagable_genome_pipeline.sh before this script to generate the required input file.

# This pipeline further populates integrated_table_radiopharm_populated.csv with Uniprot IDs collected from the imageable genome data and maps target gene IDs, symbols and species for each entry.

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



"$PYTHON" scripts/fill_protein_ids_from_reference_table.py integrated_table_radiopharm_populated.csv imageable_genome_mapped_uniprot.csv
"$PYTHON" scripts/map_target_genes_and_species.py integrated_table_radiopharm_populated_filled_protein_ids.csv
