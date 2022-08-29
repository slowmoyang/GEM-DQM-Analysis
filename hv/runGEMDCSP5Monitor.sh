#!/usr/bin/env bash

export GEM_PRODUCTION_DB_COND=
export GEM_PRODUCTION_DB_NAME=

run_2022a_start_run="2022-05-25_16:07:57"
now=$(date +%Y-%m-%d_%H:%M:%S)

echo "start: ${run_2022a_start_run}"
echo "end: ${now}"

python3 GEMDCSP5Monitor.py ${run2022a_start_run} ${now} HV 0
