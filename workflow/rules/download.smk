# Each download log holds wget's line (date, URL, size) and the file's sha256,
# so we can tell later which version of a source was used.


rule download_fda_orange_book:
    output:
        "data/raw/orange_book.zip",
    log:
        "logs/download/download_fda_orange_book.log",
    params:
        url=config["sources"]["fda_orange_book"],
    shell:
        """
        wget -nv "{params.url}" -O {output} 2>{log}
        sha256sum {output} >>{log}
        """


rule unzip_fda_orange_book:
    input:
        "data/raw/orange_book.zip",
    output:
        "data/raw/products.txt",
        "data/raw/patent.txt",
        "data/raw/exclusivity.txt",
    log:
        "logs/download/unzip_fda_orange_book.log",
    shell:
        "unzip -o -DD {input} -d data/raw >{log} 2>&1"


rule download_nature_table:
    output:
        "data/raw/nature_tables/{table}.html",
    log:
        "logs/download/download_nature_table_{table}.log",
    params:
        url=lambda wc: config["sources"]["nature_tables"][wc.table],
    shell:
        """
        wget -nv "{params.url}" -O {output} 2>{log}
        sha256sum {output} >>{log}
        """


rule download_radiopharmabank:
    output:
        "data/raw/radiopharmabank/{table}.csv",
    log:
        "logs/download/download_radiopharmabank_{table}.log",
    params:
        url=lambda wc: config["sources"]["radiopharmabank"][wc.table],
    shell:
        """
        wget -nv "{params.url}" -O {output} 2>{log}
        sha256sum {output} >>{log}
        """
