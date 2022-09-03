#!/usr/bin/env python
import json
from typing import Optional
import argparse
from pathlib import Path
from gemdqm.oms import load_oms_api
from gemdqm.oms import MAX_PER_PAGE

ERA_RUN2022A_START_RUN = 352322

def run(start_run: int,
        end_run: Optional[int] = None,
        output_dir: Optional[Path] = None,
) -> None:
    if end_run is not None and start_run > end_run:
        raise RuntimeError(f"start_run(={end_run}) > end_run(={end_run})")
    output_dir = output_dir or Path.cwd()

    oms_api = load_oms_api()
    query = oms_api.query("runs")
    filters = [
        {
            "attribute_name": "run_number",
            "value": start_run,
            "operator": "GE"
        }
    ]
    if end_run is not None:
        filters.append({
            "attribute_name": "run_number",
            "value": end_run,
            "operator": "LE"
        })
    query.filters(filters)
    query.paginate(per_page=MAX_PER_PAGE)
    response = query.data()
    data = response.json()

    end_run = end_run or data['data'][-1]['id']
    output_path = output_dir / f'runs_{start_run}_{end_run}.json'
    with open(output_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)


def main():
    """TODO: Docstring for main.

    :returns: TODO

    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-s", "--start-run", type=int, default=ERA_RUN2022A_START_RUN,
                        help="start run. The default is the start of the Run2022A era.")
    parser.add_argument("-e", "--end-run", type=int, help="end run")
    parser.add_argument("-o", "--output-dir", type=Path, help="The default is the current working directory.")
    args = parser.parse_args()

    run(start_run=args.start_run,
        end_run=args.end_run,
        output_dir=args.output_dir)

if __name__ == "__main__":
    main()
