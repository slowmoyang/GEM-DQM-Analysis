git clone https://github.com/gem-dpg-pfa/P5GEMOfflineMonitor.git
```bash
run_2022a_start_run=
now=$(date +%Y-%m-%d_%H:%M:%S)
python GEMDCSP5Monitor.py ${run2022a_start_run} ${now} HV 0
```
