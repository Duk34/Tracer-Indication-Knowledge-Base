rule download_fda_orange_book:
    output:
        zip="data/raw/orange_book.zip",
    params:
        url=config["sources"]["fda_orange_book"],
    log:
        "logs/download/download_fda_orange_book.log",
    conda:
        "env.yaml"
    shell:
        """
        echo "[$(date -Iseconds)] {params.url}" > {log}
        wget -nv "{params.url}" -O {output.zip} >> {log} 2>&1
        sha256sum {output.zip} >> {log}
        """

rule unzip_fda_orange_book:
    input:
        zip="data/raw/orange_book.zip",
    output:
        products="data/raw/products.txt",
        patent="data/raw/patent.txt",
        exclusivity="data/raw/exclusivity.txt",
    params:
        outdir="data/raw",
    log:
        "logs/download/unzip_fda_orange_book.log",
    conda:
        "../envs/download.yaml"
    shell:
        """
        unzip -o -DD {input.zip} -d {params.outdir} > {log} 2>&1
        """


rule download_ema:


rule download_micad:

