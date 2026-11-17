#!/usr/bin/env bash
set -euo pipefail


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${SCRIPT_DIR}/../data/intermediate"

mkdir -p "$OUT_DIR"

URLS=(
    "http://static.radiopharmabank.com/files/GI/general_information_of_TRP.csv"
    "http://static.radiopharmabank.com/files/RI/reference_information_of_TRP.csv"
    "http://static.radiopharmabank.com/files/GI/general_information_of_target.csv"
    "http://static.radiopharmabank.com/files/GI/general_information_of_radionuclide.csv"
    "http://static.radiopharmabank.com/files/GI/general_information_of_ligand.csv"
    "http://static.radiopharmabank.com/files/BA/biological_activity_of_clinical_trail.csv"
)

wget -P "$OUT_DIR" "${URLS[@]}"