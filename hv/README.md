# [gem-dpg-pfa/P5GEMOfflineMonitor](https://github.com/gem-dpg-pfa/P5GEMOfflineMonitor.git)

## how to fetch HV records on lxplus
```zsh
bash runGEMDCSP5Monitor.sh
```


## how to convert a result root file into .sql file
```console
$ python convert-hv-root-to-sql.py -h                                                                                                                  1 ↵
usage: convert-hv-root-to-sql.py [-h] [-o OUTPUT_DIR] [--to-csv] [-v] input_path

positional arguments:
  input_path            'GEMDCSP5Monitor.py' output root file

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        output directory
  --to-csv              to csv
  -v, --verbose         verbose
$ python convert-hv-root-to-sql.py path/to/runGEMDCSP5Monitor/result.root
```
