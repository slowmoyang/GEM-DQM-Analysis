# [OMS API](https://gitlab.cern.ch/cmsoms/oms-api-client/-/tree/master/omsapi)

## how to fetch runs
```console
$ python fetch-runs.py  -h
usage: fetch-runs.py [-h] [-s START_RUN] [-e END_RUN] [-o OUTPUT_DIR]

optional arguments:
  -h, --help            show this help message and exit
  -s START_RUN, --start-run START_RUN
                        start run. The default is the start of the Run2022A era. (default: 352322)
  -e END_RUN, --end-run END_RUN
                        end run (default: None)
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        The default is the current working directory. (default: None)
$ python fetch-runs.py
OMS API Client ID:
OMS API Client Secret (timeout after 10 sec):
https://cmsoms.cern.ch/agg/api/v1/runs/?filter[run_number][GE]=352322&page[offset]=0&page[limit]=100000
```

## how to convert to a JSON format result file of `fetch-runs.py` into .sql (and .csv)
```console
$ python convert-oms-json-to-sql.py -h                                                                                                                 1 ↵
usage: convert-oms-json-to-sql.py [-h] [--output-path OUTPUT_PATH] [-t TABLE] [--if-exists {fail,replace,append}] [--cols-to-csv [COLS_TO_CSV]] [-s]
                                  input_path

positional arguments:
  input_path            Help text

optional arguments:
  -h, --help            show this help message and exit
  --output-path OUTPUT_PATH, --output-path OUTPUT_PATH
                        a path to output file (default: None)
  -t TABLE, --table TABLE
                        table name (default: oms)
  --if-exists {fail,replace,append}
                        How to behave if the table already exists. (default: fail)
  --cols-to-csv [COLS_TO_CSV]
                        convert selected columns into csv (default: ['run_number', 'start_time', 'end_time', 'GEM', 'CSC', 'DQM', 'cmssw_version',
                        'tier0_transfer'])
  -s, --dump-schema     dump schema (default: False)
$ convert-oms-json-to-sql.py path/to/fetch-runs/result.json
```
