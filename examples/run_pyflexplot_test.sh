#!/bin/bash

n_procs=12
old="v0.15.3-post"
new="v0.15.4-pre"
data="/scratch-shared/meteoswiss/scratch/ruestefa/shared/test/pyflexplot/data"
install="/scratch-shared/meteoswiss/scratch/ruestefa/pyflexplot-test/install"
work="/scratch-shared/meteoswiss/scratch/ruestefa/pyflexplot-test/work"

opts=(
    --num-procs=${n_procs}
    --old-rev="${old}"
    --new-rev="${new}"
    --install-dir="${install}"
    --reuse-installs
    --reuse-plots
)

echo
echo "+++++++++++++++"
echo " all defaults"
echo "+++++++++++++++"
echo

pyflexplot-test "${opts[@]}" --data="${data}" \
    --preset=opr/{cosmo-1e-ctrl,ifs-hres-eu,ifs-hres,cosmo-1e,cosmo-2e}/all_png \
    --work-dir="${work}/"{cosmo-1e-ctrl,ifs-hres-eu,ifs-hres,cosmo-1e,cosmo-2e}"/default" \
|| exit 1

echo
echo "+++++++++++++++"
echo " cosmo-1e-ctrl"
echo "+++++++++++++++"
echo

pyflexplot-test "${opts[@]}" \
    --preset=opr/cosmo-1e-ctrl/all_png \
    --work-dir="${work}/cosmo-1e-ctrl/0996" \
    --infile="${data}/cosmo-1e-ctrl/grid_conc_20201021050000.nc" \
    --work-dir="${work}/cosmo-1e-ctrl/1009" \
    --infile="${data}/cosmo-1e-ctrl/grid_conc_1009_20200910000000.nc" \
    --work-dir="${work}/cosmo-1e-ctrl/xxxx_"{BEZ,BUG,FES,GOE,LEI,MUE} \
    --infile="${data}/cosmo-1e-ctrl/grid_conc_xxxx_20200619030000_"{BEZ,BUG,FES,GOE,LEI,MUE}".nc" \
|| exit 1

echo
echo "+++++++++++++++"
echo " ifs-hres-eu"
echo "+++++++++++++++"
echo

pyflexplot-test "${opts[@]}" \
    --preset=opr/ifs-hres-eu/all_png \
    --work-dir="${work}/ifs-hres-eu/0969" \
    --infile="${data}/ifs-hres-eu/grid_conc_0969_20200628000000.nc" \
    --work-dir="${work}/ifs-hres-eu/0999" \
    --infile="${data}/ifs-hres-eu/grid_conc_0999_20200818000000_fessenheim_5spec.nc" \
    --work-dir="${work}/ifs-hres-eu/1006" \
    --infile="${data}/ifs-hres-eu/grid_conc_1006_20200910000000.nc" \
    --work-dir="${work}/ifs-hres-eu/1023" \
    --infile="${data}/ifs-hres-eu/grid_conc_1023_20201113120000.nc" \
|| exit 1

echo
echo "+++++++++++++++"
echo " ifs-hres"
echo "+++++++++++++++"
echo

pyflexplot-test "${opts[@]}" \
    --preset=opr/ifs-hres/all_png \
    --work-dir="${work}/ifs-hres/1014" \
    --infile="${data}/ifs-hres/grid_conc_1014_20200921000000.nc" \
    --work-dir="${work}/ifs-hres/1018" \
    --infile="${data}/ifs-hres/grid_conc_1018_20200921000000.nc" \
    --work-dir="${work}/ifs-hres/1024" \
    --infile="${data}/ifs-hres/grid_conc_1024_20201208000000_volcano.nc" \
    --work-dir="${work}/ifs-hres/1026" \
    --infile="${data}/ifs-hres/grid_conc_1026_20201216000000.nc" \
   || exit 1
