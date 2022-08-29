import datetime
from dataclasses import dataclass
import sqlite3
from pathlib import Path
import argparse
import ROOT
import numpy as np
import pandas as pd

@dataclass
class GEMChamberId:
    region: int
    station: int
    layer: int
    chamber: int

def parse_chamber_name(chamber_name: str) -> GEMChamberId:
    """

    :chamber_name: str. e.g. 'GE_P1_1_01'
    """
    _, (region, station), layer, chamber = chamber_name.split('_')
    region = 1 if region == 'P' else -1
    station = int(station)
    layer = int(layer)
    chamber = int(chamber)
    return GEMChamberId(region, station, layer, chamber)

def to_numpy(arr, dtype) -> np.ndarray:
    """

    :arr: cppyy.LowLevelView
    """
    shape = (len(arr), )
    arr.reshape(shape)
    return np.array(arr, dtype=dtype)

fromtimestamp = np.vectorize(datetime.datetime.fromtimestamp)

def process_chamber(root_file, chamber_name: str, verbose: bool):
    graph = root_file.Get(f'{chamber_name}/HV_VmonChamber{chamber_name}_Drift_UTC_time')
    size = graph.GetN()
    timestamp_arr = to_numpy(graph.GetX(), dtype=int) # unix timestamp
    hv_arr = to_numpy(graph.GetY(), dtype=np.float64) # high voltage
    timestamp_arr = fromtimestamp(timestamp_arr)

    if verbose:
        print(f'{chamber_name}: {timestamp_arr[0]} - {timestamp_arr[-1]} ({size} records)')

    chamber_id = parse_chamber_name(chamber_name)
    region_arr = np.full(size, chamber_id.region, dtype=int)
    station_arr = np.full(size, chamber_id.station, dtype=int)
    layer_arr = np.full(size, chamber_id.layer, dtype=int)
    chamber_arr = np.full(size, chamber_id.chamber, dtype=int)

    # NOTE
    data = {
        'region': region_arr,
        'station': station_arr,
        'layer': layer_arr,
        'chamber': chamber_arr,
        'time': timestamp_arr,
        'hv': hv_arr,
    }
    return data


def run(input_path: Path,
        output_dir: Path,
        to_csv: bool,
        verbose: bool
) -> None:
    """
    """
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    output_dir = output_dir or input_path.parent

    root_file = ROOT.TFile(str(input_path)) # type: ignore
    key_list = [key.GetName() for key in root_file.GetListOfKeys()]
    data = [process_chamber(root_file, key, verbose) for key in key_list]
    data = {key: np.concatenate([each[key] for each in data]) for key in data[0].keys()}
    data = pd.DataFrame(data)

    sql_path = output_dir / input_path.with_suffix('.sql').name
    connection = sqlite3.connect(sql_path)
    data.to_sql(name='hv', con=connection)
    connection.commit()
    connection.close()

    if to_csv:
        csv_path = output_dir / input_path.with_suffix('.csv').name
        data.to_csv(csv_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", type=Path, help="'GEMDCSP5Monitor.py' output root file")
    parser.add_argument("-o", "--output-dir", type=Path, help="output directory")
    parser.add_argument("--to-csv", action="store_true", default=False, help="to csv")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="verbose")
    args = parser.parse_args()

    run(input_path=args.input_path,
        output_dir=args.output_dir,
        to_csv=args.to_csv,
        verbose=args.verbose)


if __name__ == "__main__":
    main()
