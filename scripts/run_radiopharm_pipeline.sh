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

"$PYTHON" scripts/parse_html.py
"$PYTHON" scripts/correct_names.py
"$PYTHON" scripts/cid_import.py
"$PYTHON" scripts/sid_import.py
"$PYTHON" scripts/synonyms_from_pubchem.py
"$PYTHON" scripts/target_id_fill.py
"$PYTHON" scripts/fetch_radiopharm_id.py
"$PYTHON" scripts/radiopharm_data_fill.py
"$PYTHON" scripts/radiopharm_disease_fill.py
