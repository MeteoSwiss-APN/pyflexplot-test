# Pyflexplot-Test

Compare the plots created by two versions of pyflexplot.

## Features

- Install two versions of pyflexplot (e.g., latest tag and head of dev branch) from github into designated virtual environments.
- Create the same plots with both versions, provided presets and input files.
- Compare the plots between the two versions.
- For plots that differ, create a diff image that highlights the differences.

## Installation

There are dfferent ways how to install the project:

- With pipx:

  ```bash
  pipx install git+ssh://git@github.com/MeteoSwiss-APN/pyflexplot-test
  ```

- Manually:

  ```bash
  git clone git+ssh://git@github.com/MeteoSwiss-APN/pyflexplot-test
  cd pyflexplot-test
  venv_dir=~/local/venvs/pyflexplot-test
  make install VENV_DIR=${venv_dir} CHAIN=1
  ${venv_dir}/bin/pyflexplot-test --help
  ```

- With pip:

  ```bash
  venv_dir=~/local/venvs/pyflexplot-test
  python -m venv ${venv_dir}
  ${venv}/bin/python -m pip install git+ssh://git@github.com/MeteoSwiss-APN/pyflexplot-test
  ${venv_dir}/bin/pyflexplot-test --help
  ```

- ...

## Usage

```
$ pyflexplot-test -V
0.1.0

$ pyflexplot-test -h
Usage: pyflexplot-test [OPTIONS]

Options:
  --data-path PATHLIB.PATH  path to data directory
  -f, --force               overwrite existing repos etc.
  --infile TEXT             input file (netcdf) overriding that specified in
                            the preset; --infile must not be passed more often
                            than --preset; if both --preset and --infile are
                            passed more than once, their numbers must match

  --only INTEGER            restrict the number of plots per preset
  --preset TEXT             preset used to create plots; may be repeated
  --num-procs INTEGER       number of parallel processes during plotting
  --old-rev TEXT            old revision of pyflexplot; defaults to lanew tag;
                            may be anything that git can check out (tag name,
                            branch name, commit hash)

  --repo TEXT               pyflexplot repository path
  --new-rev TEXT            new revision of pyflexplot; defaults to 'dev'
                            (head of development branch); may be anything that
                            git can check out (tag name, branch name, commit
                            hash

  --work-dir PATHLIB.PATH   working directory
  -v                        verbose output
  -V, --version             Show the version and exit.
  -h, --help                Show this message and exit.
```

## Getting started

Example comparing the branch v0.14.0-pre against version v0.13.11:

```bash
pyflexplot-test -v --force --num-procs=8 --work-dir=pyflexplot-test \
  --old-ref=v0.13.11 --new-rev v0.14.0-pre \
  --preset=opr/cosmo-1e-ctrl/all_png --infile=data/cosmo-1e-ctrl/grid_conc_0924_20200301000000.nc \
  --preset=opr/ifs-hres-eu/all_png --infile=data/ifs-hres-eu/grid_conc_0998_20200818000000_goesgen_2spec.nc \
  --preset=opr/ifs-hres/all_png --infile=data/ifs-hres/grid_conc_1000_20200818000000_bushehr_2spec.nc
```

This will create two separate installs of pyflexplot in `pyflexplot-test/git/` and run each three times, once for each specified preset.
Then the plots created by the two versions in `pyflexplot-test/work/` will be compared, and for those that are not identical, diff images will be produced in `pyflexplot-test/work/v0.13.11_vs_v0.14.0-pre/`, on which the differences are highlighted.

Note:

- At the time of writing, v0.13.11 happened to be the latest version and would thus automatically have been picked as the old version had `--old-ref=v0.13.11` been omitted.
- Parallelization (`--num-procs`) only applies to the individual pyflexplot runs.
  Pyflexplot-test itself always runs sequentially, i.e., one pyflexplot run after the other, only the runs themselves may be parallelized.

## Credits

This project was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [MeteoSwiss-APN/mch-python-blueprint](https://github.com/MeteoSwiss-APN/mch-python-blueprint) project template.
