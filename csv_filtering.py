# Now every file is in good readable .csv format

import pandas as pd
from raw_data_formating import DATA_INTERMEDIATE_PATH
# Columns that are not needed and only dilute the most important data
EMA_DROP = ['Category',
            'Medicine status',
            'Species\n(veterinary)',
            'Patient safety',
            'ATCvet code (veterinary)',
            'Pharmacotherapeutic group\n(veterinary)',
            'Accelerated assessment',
            'Additional monitoring',
            'Advanced therapy',
            'Biosimilar',
            'Conditional approval',
            'Exceptional circumstances',
            'Generic',
            'Orphan medicine',
            'PRIME: priority medicine',
            'Marketing authorisation developer / applicant / holder',
            'European Commission decision date',
            'Start of rolling review date',
            'Start of evaluation date',
            'Opinion adopted date',
            'Withdrawal of application date',
            'Marketing authorisation date',
            'Refusal of marketing authorisation date',
            'Withdrawal / expiry / revocation / lapse of marketing authorisation date',
            'Suspension of marketing authorisation date',
            'First published date',
            'Last updated date',
            ]

# Modalities that are used - key words, that if found, suggest the row should be kept
# So far I simply asked AI to generate common other names for the techniques, to include possibly the most of those synonyms.
# I don't want to remove it from the code yet, but right now using it is resulting in many false positives
MODALITIES = {
    "PET": [
        "PET",
        "Positron Emission Tomography",
        "Positron-Emission Tomography",
    ],
    "SPECT": [
        "SPECT",
        "Single-Photon Emission Computed Tomography",
        "Single Photon Emission Computed Tomography",
        "Scintigraphy",
        "Gamma scintigraphy",
        "Planar scintigraphy",
        "Single-photon emission tomography",
        "Single photon emission tomography",
        "SPET",
    ],
    "MRI": [
        "MRI",
        "Magnetic Resonance Imaging",
        "MRS",
        "Magnetic Resonance Spectroscopy",
        "Magnetic resonance",
        "MR",
    ],
}

def main():
    # Reading the .cvs files from the intermediate data folder.
    df_fda = pd.read_csv(DATA_INTERMEDIATE_PATH/'fda_orange_book.csv')
    df_ema = pd.read_csv(DATA_INTERMEDIATE_PATH/'ema_medicines_output_report.csv')
    df_micad = pd.read_csv(DATA_INTERMEDIATE_PATH/'micad.csv')

    # This is how the EMA medicines output report is filtered, to only keep the relevant rows, and drop the useless columns.
    df_ema = select_relevant_rows_ema(df_ema, only_authorised=True, drop=True, use_modalities=False)
    df_ema.to_csv(DATA_INTERMEDIATE_PATH/'ema_medicines_output_report_filtered.csv', index=False)

    # Next step would be filtering the FDA Orange Book and MICAD database, but that is not implemented yet.
    
    # Final goal of this script is to join all three filtered dataframes into one, with the relevant information. 

    


def select_relevant_rows_ema(df, only_authorised=True, drop=True, use_modalities=False):
    """
    Selects relevant rows from the EMA medicines output report dataframe based on the following criteria:
    - The medicine must belong to the "Diagnostic radiopharmaceuticals" pharmacotherapeutic group, OR
    - The medicine must be indicated for PET, MRI, SPECT imaging
    - If only_authorised is True, only authorised medicines will be selected (there is a handful of medicines that are withdrawn (even over 20yrs ago), but are still in the report)

    param df: pandas DataFrame containing the EMA medicines output report data
    param only_authorised: boolean indicating whether to filter for only authorised medicines
    param drop: dropping the useless columns, as specified in in EMA_DROP variable
    param use_modalities: boolean indicating whether to keep columns that contain the modalities from the MODALITIES variable, if false it will only look for "PET".
    return: pandas DataFrame containing the filtered EMA medicines output report data
    """
    category = df["Pharmacotherapeutic group\n(human)"]
    usage = df["Therapeutic indication"]

    # Convert all the synonyms of different modalities into a RegEx for the .str.contains() method.
    synonyms = []
    for modality in list(MODALITIES.values()):
        synonyms += modality
    modalities = "|".join(synonyms) # joing with RegEx or |

    
    # Depends on the final criteria that we want to use.
    if only_authorised:
        mask = (
            category.str.contains("Diagnostic radiopharmaceuticals", na=False)
            | usage.str.contains(modalities if use_modalities else "PET", na=False)
        ) & df["Medicine status"].str.contains("Authorised", na=False, case=False, regex=True)
    else:
        mask = (
            category.str.contains("Diagnostic radiopharmaceuticals", na=False)
            | usage.str.contains(modalities if use_modalities else "PET", na=False, case=False, regex=True)
        )
    ema_df = df.loc[mask].copy()

    if drop:
        ema_df = ema_df.drop(labels=EMA_DROP, axis=1)

    return ema_df

#TODO: Implement a function, that gets relevant info about entries in the FDA Orange Book from the internet, 
# to be able to filter relevant rows, similar to the EMA function above.

def select_relevant_rows_fda(df):
    """
    Selects relevant rows from the FDA Orange Book dataframe based on the following criteria:
    - The medicine must be indicated for PET, MRI, SPECT imaging

    param df: pandas DataFrame containing the FDA Orange Book data
    return: pandas DataFrame containing the filtered FDA Orange Book data
    """
    pass

#TODO: Implement a function, that filters MICAD database, relevant information should be contained within it.

# For dropping lot of unrelevant rows, the unique entries in some columns can be examined, to see what is of interest. 
def get_unique_entries_df(df, column_name, df_name, save_as_file=False):
    """
    Returns a list of unique entries in a given column of a pandas DataFrame.
    It is meant to be used once, to examine what entries are of the most interest and should be kept.

    param df: pandas DataFrame
    param df_name: string, name of the DataFrame (used for saving the file)
    param column_name: string, name of the column to extract unique entries from
    param save_as_file: boolean indicating whether to save the unique entries to a file
    return: list of unique entries in the specified column
    """
    unique_entries = df[column_name].dropna().unique().tolist()
    unique_entries.sort()
    if save_as_file:
        with open(f"{DATA_INTERMEDIATE_PATH}/unique_{df_name}_{column_name.replace('\n', '_').replace(' ', '_')}.txt", "w") as f:
            f.write(f"Unique entries in column '{column_name.replace('\n', ' ')}' of DataFrame '{df_name}':\n")
            f.write(f"Count: {len(unique_entries)}\n")
            f.write(f"Entries:\n")
            for entry in unique_entries:
                f.write(f"{entry}\n")
    else:
        print(f"Unique entries in column '{column_name.replace('\n', ' ')}' of DataFrame '{df_name}':")
        print(f"Count: {len(unique_entries)}")
        for entry in unique_entries:
            print(entry)

if __name__ == "__main__":
    main()