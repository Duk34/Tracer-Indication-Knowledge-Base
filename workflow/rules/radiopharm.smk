# Tracers from Nature tables 2 + 4, enriched with PubChem, MyGene.info and RadioPharm (https://radiopharm.idrblab.cn)


rule radiopharm_parse_tables:
    input:
        table_2="data/raw/nature_tables/table_2.html",
        table_4="data/raw/nature_tables/table_4.html",
    output:
        "data/intermediate/radiopharm/1_tracers.csv",
    script:
        "../scripts/parse_nature_tables.py"


rule radiopharm_pubchem_cid:
    input:
        "data/intermediate/radiopharm/1_tracers.csv",
    output:
        table="data/intermediate/radiopharm/2_cid.csv",
        matches="data/intermediate/radiopharm/2_cid_matches.csv",
    log:
        "logs/radiopharm/pubchem_cid.log",
    shell:
        "tikb pubchem-cid {input} {output.table} --matches {output.matches} >{log} 2>&1"


rule radiopharm_pubchem_sid:
    input:
        "data/intermediate/radiopharm/2_cid.csv",
    output:
        table="data/intermediate/radiopharm/3_sid.csv",
        matches="data/intermediate/radiopharm/3_sid_matches.csv",
    log:
        "logs/radiopharm/pubchem_sid.log",
    shell:
        "tikb pubchem-sid {input} {output.table} --matches {output.matches} >{log} 2>&1"


rule radiopharm_pubchem_synonyms:
    input:
        "data/intermediate/radiopharm/3_sid.csv",
    output:
        "data/intermediate/radiopharm/4_synonyms.csv",
    log:
        "logs/radiopharm/pubchem_synonyms.log",
    shell:
        "tikb pubchem-synonyms {input} {output} >{log} 2>&1"


rule radiopharm_target_ids:
    input:
        "data/intermediate/radiopharm/4_synonyms.csv",
    output:
        "data/intermediate/radiopharm/5_target_ids.csv",
    log:
        "logs/radiopharm/target_ids.log",
    shell:
        "tikb target-ids {input} {output} >{log} 2>&1"


rule radiopharm_ids:
    input:
        "data/intermediate/radiopharm/5_target_ids.csv",
    output:
        "data/intermediate/radiopharm/6_radiopharm_ids.csv",
    log:
        "logs/radiopharm/radiopharm_ids.log",
    shell:
        "tikb radiopharm-ids {input} {output} >{log} 2>&1"


rule radiopharm_data:
    input:
        "data/intermediate/radiopharm/6_radiopharm_ids.csv",
    output:
        "data/intermediate/radiopharm/7_radiopharm_data.csv",
    log:
        "logs/radiopharm/radiopharm_data.log",
    shell:
        "tikb radiopharm-data {input} {output} >{log} 2>&1"


rule radiopharm_diseases:
    input:
        "data/intermediate/radiopharm/7_radiopharm_data.csv",
    output:
        "data/processed/radiopharm_tracers.csv",
    log:
        "logs/radiopharm/radiopharm_diseases.log",
    shell:
        "tikb radiopharm-diseases {input} {output} >{log} 2>&1"
