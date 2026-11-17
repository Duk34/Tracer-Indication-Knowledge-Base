#This scripts brings the downloaded CSV files from RadiopharmaBank into our curation scheme.
# Synonyms coulumns holds synonyms and also Tracer name.
# Gene_IDs, Gene names and target species are mapped from the UniProtKB ID using MyGene.info.
# Evidence levels are mapped from the clinical phase.

#before running the script, download following files from http://www.radiopharmabank.com/upload-download and place them into the data/intermediate folder:
# radiopharma_general_information_of_TRP.csv
# radiopharma_reference_information_of_TRP.csv
# radiopharma_general_information_of_target.csv
# radiopharma_general_information_of_radionuclide.csv
# radiopharma_general_information_of_ligand.csv
# radiopharma_biological_activity_of_clinical_trail.csv


import re
from pathlib import Path

import mygene
import numpy as np
import pandas as pd


def main():
    # define input files
    file_trp = Path("data/intermediate/radiopharma_general_information_of_TRP.csv")
    file_ref = Path("data/intermediate/radiopharma_reference_information_of_TRP.csv")
    file_target = Path("data/intermediate/radiopharma_general_information_of_target.csv")
    file_rad = Path("data/intermediate/radiopharma_general_information_of_radionuclide.csv")
    file_ligand = Path("data/intermediate/radiopharma_general_information_of_ligand.csv")
    file_clinical = Path("data/intermediate/radiopharma_biological_activity_of_clinical_trail.csv")

    # read input CSV files into DataFrames
    df_trp = pd.read_csv(file_trp)
    df_ref = pd.read_csv(file_ref)
    df_target = pd.read_csv(file_target)
    df_rad = pd.read_csv(file_rad)
    df_ligand = pd.read_csv(file_ligand)
    df_clinical = pd.read_csv(file_clinical)




    #build synonyms column by combining TRP Name and TRP Synonyms
    def build_synonyms(row):
        name = (str(row['TRP Name']).strip() if pd.notna(row['TRP Name']) else '')
        syns = (str(row['TRP Synonyms']).strip() if pd.notna(row['TRP Synonyms']) else '')
        items = [name] if name else []
        if syns:
            for s in syns.split(';'):
                s_clean = s.strip()
                if s_clean and s_clean not in items:
                    items.append(s_clean)
        return '; '.join(items) if items else np.nan

    df_trp['Synonyms'] = df_trp.apply(build_synonyms, axis=1)

    # extract relevant columns and rename them for consistency
    df_trp_sub = df_trp[
        [
            'Number',
            'TRP Name',
            'Synonyms',
            'Specific Indication',
            'Diagnostic Functions',
        ]
    ].rename(
        columns={
            'TRP Name': 'Tracer_Name',
            'Specific Indication': 'Disease name',
            'Diagnostic Functions': 'Modality',
        }
    )

    # extract publication year from references
    def extract_year(text):
        if pd.isna(text):
            return np.nan
        match = re.search(r'\b(19\d\d|20\d\d)\b', str(text))
        return match.group(1) if match else np.nan

    df_ref['Year'] = df_ref['Ref'].apply(extract_year)
    df_ref_sub = df_ref[['Number', 'DOI', 'Year']].rename(
        columns={'DOI': 'Source (URL)'}
    )

    # Target Info: Specific target -> Target protein name, UniprotKB Entry -> Target protein_ID
    df_target_sub = df_target[
        ['Number', 'Specific target', 'UniprotKB Entry']
    ].rename(
        columns={
            'Specific target': 'Target protein name',
            'UniprotKB Entry': 'Target protein_ID',
        }
    )

    # Radionuclide Info: Radioisotope Name -> Radionuclide_ID
    df_rad_sub = df_rad[['Number', 'Radioisotope Name']].rename(columns={'Radioisotope Name': 'Radionuclide_ID'})

    # Ligand Info: Ligand Types -> Type
    df_ligand_sub = df_ligand[['Number', 'Ligand Types']].rename(columns={'Ligand Types': 'Type'})

    # Clinical Trials Info: Phases -> Phases
    df_clinical_sub = df_clinical[['Number', 'Phases']].rename(columns={'Phases': 'Phases'})

    # merge on Number, using outer join to keep all records
    merged_df = df_trp_sub
    for sub_df in [
        df_ref_sub,
        df_target_sub,
        df_rad_sub,
        df_ligand_sub,
        df_clinical_sub,
    ]:
        merged_df = pd.merge(merged_df, sub_df, on='Number', how='outer')


    # remove whitespace from UniProt IDs before mapping
    merged_df['Target protein_ID'] = merged_df['Target protein_ID'].astype('string').str.strip()

    # map UniProt IDs to gene IDs and gene symbols
    print("Mapping UniProt IDs to gene IDs and gene symbols...")
    mg = mygene.MyGeneInfo()
    uniprot_ids = merged_df['Target protein_ID'].dropna().unique().tolist()
    res = mg.querymany(
        uniprot_ids,
        scopes='uniprot',
        fields='entrezgene,symbol,taxid',
        species='all',   
        as_dataframe=True,
    )
    res = res[~res.index.duplicated(keep='first')]

    # map species
    species_map = res['taxid'].replace({
        9606: 'Homo sapiens', 9606.0: 'Homo sapiens',
        10029: 'Cricetulus griseus', 10029.0: 'Cricetulus griseus',
        10090: 'Mus musculus', 10090.0: 'Mus musculus',
        10116: 'Rattus norvegicus', 10116.0: 'Rattus norvegicus',
    })
    
    merged_df['Target gene_ID'] = merged_df['Target protein_ID'].map(res['entrezgene']) #maps entrez gene IDs to the corresponding UniProt IDs
    merged_df['Target gene symbol'] = merged_df['Target protein_ID'].map(res['symbol']) #maps gene symbols to the corresponding UniProt IDs
    merged_df['Target_species'] = merged_df['Target protein_ID'].map(species_map)     #maps target species from NCBI taxonomy IDs to the corresponding UniProt IDs. If the mapping fails, taxidid is kept.


    #map evidence levels
    def map_evidence_level(phase_text):
        if pd.isna(phase_text):
            return pd.NA
        text = str(phase_text).lower().strip()

        if 'approved' in text:
            return 4
        if re.search(r'phase\s*(3|4|iii|iv)\b', text):
            return 3
        if re.search(r'phase\s*(0|1|2|i|ii)\b', text):
            return 2
        if 'preclinical' in text or 'pre-clinical' in text:
            return 1

        return pd.NA

    merged_df['Evidence Level'] = merged_df['Phases'].apply(map_evidence_level).astype('Int64')


    # sort columns
    columns_order = [
        'Tracer_ID',
        'Tracer_Name',
        'Synonyms',
        'Type',
        'CID',
        'SID',
        'Modality',
        'Radionuclide_ID',
        'Phases',
        'Evidence Level',
        'Target protein_ID',
        'Target protein name',
        'Target gene_ID',
        'Target gene symbol',
        'Disease_ID',
        'Disease name',
        'Target_species',
        'Source (URL)',
        'Mechanism',
        'Year',
        'Curation Notes',
        'Review Status',
    ]

    # fill empty columns with NaN if they don't exist in the merged DataFrame
    for col in columns_order:
        if col not in merged_df.columns:
            merged_df[col] = np.nan


    # remove duplicates
    final_df = merged_df[columns_order].drop_duplicates().copy()

    # add curation notes and review status
    final_df['Curation Notes'] = "Curated from RadioPharmaBank, http://www.radiopharmabank.com/upload-download"
    final_df['Review Status'] = "Not reviewed"

    # export to csv
    output_filename = Path("data/intermediate/radiopharma_tracers_from_downloaded_csvs.csv")
    final_df.to_csv(output_filename, index=False)
    print(f"file successfully created: {output_filename}")


if __name__ == '__main__':
    main()