import sys
import json
import sqlite3


oms_db = '/store/scratch/dqm/OMS/runs_352322_358185.sql'
oms_connection = sqlite3.connect(oms_db)
oms_connection.row_factory = sqlite3.Row
oms = oms_connection.cursor()

query = """
SELECT
    run_number
FROM
    runs
WHERE
    end_time IS NOT NULL
    AND tier0_transfer = 1
    AND GEM = 1
    AND CSC = 1
    AND DQM = 1
    AND DAQ = 1
    AND duration > ?
"""

min_duration = int(sys.argv[-1])

data = {'run': [row['run_number'] for row in oms.execute(query, (min_duration, )).fetchall()]}
print('good runs :', len(data['run']))

file_path = f'./good_runs/good_runs_{min_duration}.json'
with open(file_path, 'w') as outfile:
    json.dump(data, outfile, indent=2)


