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
0.4.1

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

  --install-dir PATH              install directory in which git clones and
                                  their venvs are saved

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

  --repo TEXT                     pyflexplot repository URL
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
  --work-dir PATH                 working directory in which plots and diffs
                                  are saved in subdirectories; may be passed
                                  repeatedly, specifically once for every
                                  --preset/--presets-old-new in order to
                                  prevent plots based on the same prefix but
                                  different input files from overwriting each
                                  other

  -h, --help                      Show this message and exit.

```

## Getting started

### Basic usage

Compare the head of the development branch against the latest tag:

```bash
data="/scratch-shared/meteoswiss/scratch/ruestefa/shared/test/pyflexplot/data"
pyflexplot-test -v --num-procs=6 --data-path="${data}"
```

This will create two separate installs of pyflexplot in `./pyflexplot-test/install/` and run each three times, once for each specified preset.
Then the plots created by the two versions in `./pyflexplot-test/work/` will be compared, and for those that are not identical, diff images will be produced in `pyflexplot-test/work/v0.13.11_vs_dev/`, on which the differences are highlighted.
The default preset is `--preset=opr/*/all_png`.
The default infiles in the presets are specified relative to a `./data/` directory.
If this directory is not present, the path to it must be supplied with `--data-path`.

### Advanced usage

#### Example 1

Multiple presets can be compared in one run, and for each, a separate input file can be specified, which override the defaults specified in the preset setup files.

```bash
pyflexplot-test --num-procs=6 \
  --old-rev=v0.13.11 --new-rev=v0.14.0-pre \
  --preset=opr/cosmo-1e-ctrl/all_png --infile=data/cosmo-1e-ctrl/grid_conc_0924_20200301000000.nc \
  --preset=opr/ifs-hres-eu/all_png --infile=data/ifs-hres-eu/grid_conc_0998_20200818000000_goesgen_2spec.nc \
  --preset=opr/ifs-hres/all_png --infile=data/ifs-hres/grid_conc_1000_20200818000000_bushehr_2spec.nc
```

Notes:

- A separate input file is specified for each preset. The matching only depends on the respective order of the `--preset` and `--infile` flags among themselves; passing first all `--preset` flags and then all `--infile` flags or any other combination would yield the same result.
- If only one input file is specified, it is applied to all presets. This of course only works, if all presets apply to the same model (which is not the case in this example).
- If v0.13.11 is the current latest tag, `--new-ref` can be omitted.
- Parallelization (`--num-procs`) only applies to the individual pyflexplot runs.
  Pyflexplot-test itself always runs sequentially, i.e., one pyflexplot run after the other, only the runs themselves may be parallelized.

#### Example 2

If the same preset is repeated for different input files, chances are some plots will be overwritten. To avoid this, a separate work directory can be specified for each.

```bash
data="/scratch-shared/meteoswiss/scratch/ruestefa/shared/test/pyflexplot/data"
file1="${data}/cosmo-1e-ctrl/grid_conc_xxxx_20200619030000_BEZ.nc"
file2="${data}/cosmo-1e-ctrl/grid_conc_xxxx_20200619030000_BUG.nc"
file3="${data}/cosmo-1e-ctrl/grid_conc_xxxx_20200619030000_FES.nc"
pyflexplot-test \
  --reuse-installs \
  --work-dir=test/work/cosmo-1e-ctrl/BEZ --preset=opr/cosmo-1e-ctrl/all_png --infile="${file1}" \
  --work-dir=test/work/cosmo-1e-ctrl/BUG --preset=opr/cosmo-1e-ctrl/all_png --infile="${file2}" \
  --work-dir=test/work/cosmo-1e-ctrl/FES --preset=opr/cosmo-1e-ctrl/all_png --infile="${file3}"
```

Notes:

- If pyflexplot-test has previously been run with the same versions (and those have not changed), `--reuse-installs` will reuse existing installations instead of reinstalling pyflexplot, which saves time.
- If there have been changes to the new version (`--new-rev`), but the old reference version (`--old-rev`) is still the same, only the latter is reused with `--reuse-old-install`, while the former is reinstalled (thanks to an implied `--reinstall-old`).
- Reinstallation only works if the install directory (`--install-dir`) stays the same (e.g., the default `./pyflexplot-test/install/`).
- Likewise, existing plots may be reused with `--reuse-plots` etc., for instance to only recreate the diff plots. Like for installs, this requires the same work directory (`--work-dir`).
- By taking advantage of some bash notation tricks and the fact that only the raltive order of the same flags matters, the command can be shortened as follows:

  ```bash
  pyflexplot-test \
    --work-dir=test/work/cosmo-1e-ctrl/{BEZ,BUG,FES} \
    --preset=opr/cosmo-1e-ctrl/all_png{,,} \
    --infile="${file1}" --infile="${file2}" --infile="${file3}"
  ```

## Credits

This project was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [MeteoSwiss-APN/mch-python-blueprint](https://github.com/MeteoSwiss-APN/mch-python-blueprint) project template.
