from pathlib import Path
import json
import sqlite3
import numpy as np


def print_schema(connection):
    for row in connection.execute("select sql from sqlite_master").fetchall():
        print(row[0])


def print_row(row):
    if row is None:
        print('NOT FOUND')
    else:
        for key in row.keys():
            print(f'{key}={row[key]}')


oms_connection = sqlite3.connect('/store/scratch/dqm/OMS/runs_352322_358185.sql')
oms_connection.row_factory = sqlite3.Row
oms = oms_connection.cursor()

hv_db = '/store/scratch/dqm/P5GEMOfflineMonitor/P5_GEM_HV_monitor_UTC_start_2022-04-25_16-07-57_end_2022-08-25_15-22-38.sql'
hv_connection = sqlite3.connect(hv_db)
hv_connection.row_factory = sqlite3.Row
hv_cursor = hv_connection.cursor()


run_query = """
SELECT
    run_number,
    start_time,
    end_time
FROM
    runs
WHERE
    run_number = ?
"""

hv_query = """
SELECT
    chamber, hv
FROM
    hv
WHERE
    time >= ?
    AND time <= ?
    AND region = ?
    AND station = ?
"""
# AND chamber = ?

data_dir = Path('/store/user/jwheo/DQMGUI_data/Run2022/')
data = {}
for path in data_dir.glob('**/*.root'):
    run_number = int(path.stem.split('_')[2][1:])
    print(run_number)
    if run_number not in data.keys():
        run_row = oms.execute(run_query, (run_number, )).fetchone()
        data[run_number] = {}
        for region in [-1, 1]:
            hv_query_parameters = (
                    run_row['start_time'],
                    run_row['end_time'],
                    region,  # region
                    1,  # station
                    # chamber,  # chamber
                )
            hv_row_list = hv_cursor.execute(hv_query, hv_query_parameters).fetchall()
            chamber_list = np.array([row['chamber'] for row in hv_row_list])
            hv_list = np.array([row['hv'] for row in hv_row_list])
            hvs = [np.mean(hv_list[chamber_list == i]) if sum(chamber_list == i) != 0 else -1 for i in range(1, 37)]
            print(hvs)
            data[run_number][f'{region}'] = hvs

file_path = 'hv_by_run.json'
with open(file_path, 'w') as outfile:
    json.dump(data, outfile, indent=2)

