# Tracer-Indication-Knowledge-Base


## Requirements
`Tracer-Indication-Knowledge-Base` works on Linux operating systems and was tested with following dependencies:
  - beautifulsoup4=4.15.0
  - conllu=6.0.0        
  - httpx=0.28.1
  - numpy=1.26.4     
  - openpyxl=3.1.5      
  - pandas=2.3.3          
  - pip=26.2.2
  - pysbd=0.3.4       
  - pytest=9.1.1
  - python=3.11.17        
  - scikit-learn=1.9.1   
  - scipy=1.17.1          
  - snakefmt=2.1.0
  - snakemake=9.27.1
  - spacy=3.7.6  

## Installation

1. Clone this repository:

```
git clone https://github.com/Duk34/Tracer-Indication-Knowledge-Base.git
cd Tracer-Indication-Knowledge-Base
```

2. Set up the environment with **either** conda (option A) **or** uv (option B).
Both give the same Python version and the same versions of the packages listed in `env.yaml` and `pyproject.toml`.

### Option A: conda

1. Install [miniforge](https://github.com/conda-forge/miniforge/releases). [Miniforge3 (version 26.7.2-0)](https://github.com/conda-forge/miniforge/releases/download/26.7.2-0/Miniforge3-26.7.2-0-Linux-x86_64.sh) was used for analysis.

2. Create the environment:

```
mamba env create -f env.yaml
```

3. Activate the environment:

```
conda activate tikb
```

### Option B: uv

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/). uv 0.13.1 was used for analysis:

```
curl -LsSf https://astral.sh/uv/0.13.1/install.sh | sh
```

2. Create the environment. `uv` downloads Python 3.11.17 and installs the packages from `uv.lock` into `.venv/`:

```
uv sync
```

3. Activate the environment:

```
source .venv/bin/activate
```

## Help
