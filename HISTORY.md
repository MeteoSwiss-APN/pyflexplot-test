# History

## v0.4.5 (2021-11-19)

### Command line interface

A couple command line options have been removed, while many new one have been added.

#### Removed options

- `--data-path`: Renamed to `--data`.
- `--force`: Replaced by the `--reuse*` family of options.

#### New options

- `--data`: Formerly `--data-path`.
- `--infiles-old-new`: Alternative to `--infile` when the input file path differs between the old and new pyflexplot version.
- `--install-dir`: Explicitly specify where git clones and venvs are stored; until now hardcoded to `<work-dir>/git`.
- `--new-data`: Like `--data`, but applies only to the old pyflexplot version.
- `--old-data`: Like `--data`, but applies only to the new pyflexplot version.
- `--presets-old-new`: Alternative to `--preset` when the preset differs name between the old and new pyflexplot version.
- `--reuse-installs/--reinstall`: If present at `<install-dir>`, reuse the existing pyflexplot clone and venv.
- `--reuse-new-install/--reinstall-new`: Like `--reuse-installs/...`, but applies only to the new pyflexplot version.
- `--reuse-old-install/--reinstall-old`: Like `--reuse-installs/...`, but applies only to the old pyflexplot version.
- `--reuse-new-plots/--replot-new`: Like `--reuse-plots`, but applies only the new pyflexplot version.
- `--reuse-old-plots/--replot-old`: Like `--reuse-plots`, but applies only the old pyflexplot version.
- `--reuse-plots/replot`: If all plots for a given preset are already present, reuse instead of replotting them.

#### All options

```
$ pyflexplot-test -h
Options:
  --data PATH                     path to data directory; defaults to data;
                                  overridden by --old-data and --new-data;
                                  ignored if --infile and/or --infiles-old-new
                                  are passed

  --infile PATH                   input file path overriding the input file
                                  specified in the preset; incompatible with
                                  --infiles-old-new; may be omitted, passed
                                  once (in which case the same infile is used
                                  for all presets), passed the same number of
                                  times as --preset/--presets-old-new (in
                                  which case the infiles and presets are
                                  paired in order) or passed an arbitrary
                                  number of times if --preset/--presets-old-
                                  new is not passed more than once (in which
                                  case the same preset is used for all
                                  infiles)

  --infiles-old-new PATH...       pair of input file paths overriding the
                                  input file specified in the old and new
                                  preset, respectively; may be repeated (see
                                  --infile for details); equivalent to but
                                  incompatible with --infile

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
                                  plots, respectively; may be repeated (see
                                  --preset for details); equivalent to but
                                  incompatible with --preset

  --old-rev TEXT                  old revision of pyflexplot; defaults to
                                  lanew tag; may be anything that git can
                                  check out (tag name, branch name, commit
                                  hash)

  --only INTEGER                  restrict the number of plots per preset
  --preset TEXT                   preset used to create plots; may be
                                  repeated; equivalent to but incompatible
                                  with --presets-old-new; may be omitted,
                                  passed once (in which case the same preset
                                  is used for all infiles), passed the same
                                  number of times as --infile/--infiles-old-
                                  new (in which case the presets and infiles
                                  are paired in order) or passed an arbitrary
                                  number of times if --infile/--infiles-old-
                                  new is not passed more than once (in which
                                  case the same infile is used for all
                                  presets)

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

### Composite diffs

In addition to a diff plot for every plot that differs between the old and new pyflexplot version, two composite diffs are created in every diff directory:

- Composite diff plot `composite_diff_<n_diff>x.png`: Total diff area across all plots; reveals whether the same small change affects all plots, or whether there's more it.
- Diff animation `animated_diff_<n_diff>x.gif`: All diff plots as an animation; look through all individual diff plots without lifting a finger.

Both composites are always produced if there is at least one diff plot, without an option to disable either or both.
Usage: pyflexplot-test [OPTIONS]
