# Pyflexplot-Test

Compare the plots created by two versions of pyflexplot.

## Features

- Install two versions of pyflexplot (e.g., latest tag and head of dev branch) from github into designated virtual environments.
- Create the same plots with both versions, provided presets and input files.
- Compare the plots between the two versions.
- For plots that differ, create a diff image that highlights the differences.

## Installation

There are dfferent ways how to install the project.

### With pipx

```bash
pipx install git+ssh://git@github.com/MeteoSwiss-APN/pyflexplot-test
```

### Manually

```bash
git clone git+ssh://git@github.com/MeteoSwiss-APN/pyflexplot-test
cd pyflexplot-test
venv_dir=~/local/venvs/pyflexplot-test
make install VENV_DIR=${venv_dir} CHAIN=1
${venv_dir}/bin/pyflexplot-test --help
  ```

### With pip

```bash
venv_dir=~/local/venvs/pyflexplot-test
python -m venv ${venv_dir}
${venv}/bin/python -m pip install git+ssh://git@github.com/MeteoSwiss-APN/pyflexplot-test
${venv_dir}/bin/pyflexplot-test --help
```

## Usage

```
$ pyflexplot-test -V
0.3.2

$ pyflexplot-test -h
Usage: pyflexplot-test [OPTIONS]

Options:
  --data PATH                     path to data directory; defaults to data;
                                  overridden by --old-data and --new-data;
                                  ignored if --infile and/or --infiles-old-new
                                  are passed

  --infile PATH                   input file path overriding the input file
                                  specified in the preset; incompatible with
                                  --infiles-old-new; may be omitted, passed
                                  once or passed the same number of times as
                                  --preset, in which case the infiles and
                                  presets are paired in order

  --infiles-old-new PATH...       pair of input file paths overriding the
                                  input file specified in the old and new
                                  preset, respectively; incompatible with
                                  --infile; may be omitted, passed once or
                                  passed the same number of times as --preset,
                                  in which case the infile pairs and presets
                                  are paired in order

  --new-data PATH                 path to data directory for --old-rev;
                                  overrides or defaults to --data; ignored if
                                  --infile and/or --infiles-old-new are passed

  --new-rev TEXT                  new revision of pyflexplot; defaults to
                                  'dev' (head of development branch); may be
                                  anything that git can check out (tag name,
                                  branch name, commit hash

  --num-procs INTEGER             number of parallel processes during plotting
  --old-data PATH                 path to data directory for --new-rev;
                                  overrides or defaults to --data; ignored if
                                  --infile and/or --infiles-old-new are passed

  --presets-old-new TEXT...       pair of presets used to create old and new
                                  plots, respectively; may be repeated;
                                  equivalent to (but incompatible with)
                                  --preset

  --old-rev TEXT                  old revision of pyflexplot; defaults to
                                  lanew tag; may be anything that git can
                                  check out (tag name, branch name, commit
                                  hash)

  --only INTEGER                  restrict the number of plots per preset
  --preset TEXT                   preset used to create plots; may be
                                  repeated; equivalent to (but incompatible
                                  with) --presets-old-new

  --repo TEXT                     pyflexplot repository path
  --reuse-installs / --reinstall  reuse venvs of existing repo clones instead
                                  of reinstalling them; overriddenby --reuse-(
                                  old|new)-install/--reinstall-(old|new)

  --reuse-new-install / --reinstall-new
                                  reuse venv of existing clones of new repo
                                  instead of reinstalling it; overrides
                                  --reuse-installs/--reinstall for new repo

  --reuse-old-install / --reinstall-old
                                  reuse venv of existing clones of old repo
                                  instead of reinstalling it; overrides
                                  --reuse-installs/--reinstall for old repo

  --reuse-new-plots / --replot-new
                                  reuse existing new plots rather than
                                  recomputing them; overrides --reuse-
                                  plots/--replot for new plots

  --reuse-old-plots / --replot-old
                                  reuse existing old plots rather than
                                  recomputing them; overrides --reuse-
                                  plots/--replot for old plots

  --reuse-plots / --replot        reuse existing plots rather than recomputing
                                  them; overridden by
                                  --reuse-(old|new)-plots/--replot-(old|new)

  -v                              increase verbosity
  -V, --version                   Show the version and exit.
  --work PATH                     working directory
  -h, --help                      Show this message and exit.
```

## Getting started

### Basic usage

Compare the head of the development branch against the latest tag:

```bash
pyflexplot-test -v --num-procs=6 --data-path=/scratch-shared/meteoswiss/scratch/ruestefa/shared/test/pyflexplot/data
```

This will create two separate installs of pyflexplot in `pyflexplot-test/git/` and run each three times, once for each specified preset.
Then the plots created by the two versions in `pyflexplot-test/work/` will be compared, and for those that are not identical, diff images will be produced in `pyflexplot-test/work/v0.13.11_vs_dev/`, on which the differences are highlighted.
The default preset is `--preset=opr/*/all_png`.
The default infiles in the presets are specified relative to a `./data/` directory.
If this directory is not present, the path to it must be supplied with `--data-path`.

### Advanced usage

Example comparing the branch v0.14.0-pre against version v0.13.11:

```bash
pyflexplot-test --num-procs=6 \
  --old-rev=v0.13.11 --new-rev v0.14.0-pre \
  --preset=opr/cosmo-1e-ctrl/all_png --infile=data/cosmo-1e-ctrl/grid_conc_0924_20200301000000.nc \
  --preset=opr/ifs-hres-eu/all_png --infile=data/ifs-hres-eu/grid_conc_0998_20200818000000_goesgen_2spec.nc \
  --preset=opr/ifs-hres/all_png --infile=data/ifs-hres/grid_conc_1000_20200818000000_bushehr_2spec.nc
```

Note:

- At the time of writing, v0.13.11 happened to be the latest version and would thus automatically have been picked as the old version had `--old-ref=v0.13.11` been omitted.
- Parallelization (`--num-procs`) only applies to the individual pyflexplot runs.
  Pyflexplot-test itself always runs sequentially, i.e., one pyflexplot run after the other, only the runs themselves may be parallelized.
- If the `pyflexplot-test` command is used repeatedly, use `-f` to reuse an existing work directory.
  Just make sure not to accidentally delete anything in that directory by doing so.

## Credits

This project was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [MeteoSwiss-APN/mch-python-blueprint](https://github.com/MeteoSwiss-APN/mch-python-blueprint) project template.
