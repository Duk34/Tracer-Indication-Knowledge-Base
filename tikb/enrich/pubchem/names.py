"""Find a tracer in PubChem by trying several spellings of its name (shared by cid and sid).

Tracer names like "[18F]FDG" are written in many ways, so every name is tried
in several spellings (permutations) until PubChem finds it.
"""

import re

import pandas as pd


def remove_brackets_from_compound_names(compound_name: str) -> str:
    """PubChem writes nuclides as (18F) instead of [18F]."""
    return compound_name.replace("[", "(", 1).replace("]", ")", 1)


def generate_permutations(compound_name: str) -> list[str]:
    """Spellings of a tracer name to try in PubChem. The last one is the name without nuclide."""
    permutations = []
    compound_name = remove_brackets_from_compound_names(compound_name)
    permutations.append(compound_name)

    # Split "(18F)-FDG" into nuclide "18F" and core "FDG".
    match = re.match(r"^\((\d+m?[A-Za-z]+)\)-?(.*)$", compound_name)
    if not match:
        return permutations

    nuclide = match.group(1)
    core = (
        match.group(2).lstrip(" -_")
        if "Zr" not in nuclide
        else match.group(2).lstrip(" -_").split("-")[-1]
    )

    isotope_match = re.match(r"^(\d+m?)([A-Za-z]+)$", nuclide)
    mass_number = isotope_match.group(1)
    element_symbol = isotope_match.group(2)
    inverted_nuclide = f"{element_symbol}{mass_number}"
    inverted_nuclide_with_space = f"{element_symbol} {mass_number}"
    inverted_nuclide_with_dash = f"{element_symbol}-{mass_number}"
    core_with_removed_nuclide = re.sub(
        rf"^{element_symbol}(?=-|[A-Z])", "", core
    ).lstrip(" -_")

    permutations.append(f"[{nuclide}]{core}")
    permutations.append(f"({nuclide})-{core}")
    permutations.append(f"{nuclide}-{core}")
    permutations.append(f"{nuclide} {core}")
    permutations.append(f"{core} {nuclide}")
    permutations.append(f"{core} ({nuclide})")
    permutations.append(f"{core} [{inverted_nuclide}]")
    permutations.append(f"{core} {inverted_nuclide}")
    permutations.append(f"{core} ({inverted_nuclide})")
    permutations.append(f"{core} {inverted_nuclide_with_space}")
    permutations.append(f"{core} {inverted_nuclide_with_dash}")

    permutations.append(f"{nuclide} {core_with_removed_nuclide}")
    permutations.append(f"{nuclide}-{core_with_removed_nuclide}")
    permutations.append(f"{core_with_removed_nuclide} {nuclide}")
    permutations.append(f"{core_with_removed_nuclide} ({nuclide})")
    permutations.append(f"{core_with_removed_nuclide} {inverted_nuclide}")
    permutations.append(f"{core_with_removed_nuclide} ({inverted_nuclide})")
    permutations.append(f"{core_with_removed_nuclide} {inverted_nuclide_with_space}")
    permutations.append(f"{core_with_removed_nuclide} {inverted_nuclide_with_dash}")

    # Some additional permutations for specific cases.
    if "·H2O" in core:
        core = core.replace("·H2O", "").strip()
        permutations.append(f"({mass_number}){core}")
    if "DOTA-TATE" in core:
        core_with_removed_nuclide = core_with_removed_nuclide.replace(
            "DOTA-TATE", "DOTATATE"
        ).strip()
        permutations.append(f"{nuclide}-{core_with_removed_nuclide}")

    if "Tc" in nuclide:
        permutations.append(f"Technetium ({nuclide}) {core_with_removed_nuclide}")
        permutations.append(
            f"Technetium {inverted_nuclide_with_dash} {core_with_removed_nuclide}"
        )
        permutations.append(
            f"{inverted_nuclide_with_dash.replace('Tc', 'Technetium')} {core}"
        )
        permutations.append(f"Technetium-{nuclide}-{core_with_removed_nuclide}")
        permutations.append(f"Technetium {inverted_nuclide_with_space} {core}")

    permutations.append(core)
    return permutations


def look_up_tracers(tracers, lookup, id_column: str) -> tuple[dict, pd.DataFrame]:
    """Try the permutations of every tracer until lookup finds an ID.

    Returns {tracer: id} and a table that shows which spelling matched.
    """
    ids = {}
    matches = []
    for tracer in tracers:
        names = generate_permutations(tracer)
        found_id, used_name, nuclide_cleaved_off = None, "not found", False
        for i, name in enumerate(names):
            found_id = lookup(name)
            if found_id:
                used_name = name
                # The last permutation is the name without nuclide.
                nuclide_cleaved_off = len(names) > 1 and i == len(names) - 1
                break
        ids[tracer] = found_id
        matches.append(
            {
                "Tracer_ID": tracer,
                "Name_used": used_name,
                id_column: found_id,
                "Nuclide_cleaved_off": nuclide_cleaved_off,
                "Permutations": ";".join(names),
            }
        )
    return ids, pd.DataFrame(matches)


def summary(matches: pd.DataFrame, id_column: str) -> str:
    """Short text summary of a matches table from add_cids or add_sids."""
    total = len(matches)
    found = matches[id_column].notna().sum()
    cleaved = matches.loc[matches["Nuclide_cleaved_off"], "Tracer_ID"]
    percent = found / total * 100 if total else 0
    lines = [
        f"Total tracers processed: {total}",
        f"Tracers with {id_column} found: {found} ({percent:.2f}%)",
        f"{id_column} found only after removing the nuclide ({len(cleaved)}):",
    ]
    lines += [f" - {tracer}" for tracer in cleaved]
    return "\n".join(lines)
