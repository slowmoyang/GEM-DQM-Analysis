#!/usr/bin/env python
"""

TODO
- [ ] certificiate with password
- [ ] lint
- [ ] multiprocessing
- [ ] is it vulnerable to send client secret through env var?
"""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Protocol, Optional
import re
import urllib.parse
import itertools
from bs4 import BeautifulSoup
import tqdm
from gemdqm.auth import open_url
from gemdqm.oms import load_oms_api


CMSWEB_NETLOC = 'https://cmsweb.cern.ch/'
PASSWORD_PROMPT_TIMEOUT = 10 # sec
GEM_DQM_CERN_CERTIFICATE = "GEM_DQM_CERN_CERTIFICATE"


_ERA_TO_RUN_RANGE_LIST: list[tuple[str, int, int]] = []

def _query_era(run: int) -> str:
    omsapi = load_oms_api()
    query = omsapi.query('eras')
    filters = [
        {
            'attribute_name': 'start_run',
            "value": run,
            "operator": "LE"
        },
        {
            "attribute_name": "end_run",
            "value": run,
            "operator": "GE"
        }
    ]
    query.filters(filters)
    data = query.data().json()
    era: str = data['data'][0]['id']
    start_run: int = data['data'][0]['attributes']['start_run']
    end_run: int = data['data'][0]['attributes']['end_run']

    _ERA_TO_RUN_RANGE_LIST.append((era, start_run, end_run))
    return era


def query_era(run: int) -> str:
    for cached_era, start_run, end_run in _ERA_TO_RUN_RANGE_LIST:
        if run >= start_run and run <= end_run:
            return cached_era
    else:
        return _query_era(run)

###############################################################################
# DQM
###############################################################################

class LinkFinderCallable(Protocol):
    def __call__(self, run: int, dataset: str) -> str:
        ...

def _find_file_url(url: str, pattern: re.Pattern) -> str:
    response = open_url(url)
    soup = BeautifulSoup(response, features="html.parser")
    for a_tag in soup.find_all('a'):
        href = a_tag.attrs['href']
        last = href.split('/')[-1]
        if re.match(pattern, last):
            return urllib.parse.urljoin(CMSWEB_NETLOC, href)
    else:
        raise RuntimeError(f"failed to find a filename matched with '{pattern}' from '{url}'") # TODO raise proper error


def find_offline_dqm_file_link(dataset: str, run: int) -> str:
    r"""
    :dataset: primary dataset
    :run: run number
    :returns:
    """
    run_str = f'{run:0>9d}'
    era = query_era(run=run)
    if re.match(r'Run\d{4}[A-Z]', era):
        era = era[:-1]

    url = f"dqm/offline/data/browse/ROOT/OfflineData/{era}/{dataset}/{run_str[:-2]}xx/"
    url = urllib.parse.urljoin(CMSWEB_NETLOC, url)

    # filename pattern
    pattern = re.compile(rf'DQM_V\d{{4}}_R{run_str}__{dataset}__[a-zA-Z0-9\-]+__DQMIO.root')
    return _find_file_url(url=url, pattern=pattern)


def find_online_dqm_file_link(run: int, dataset: str) -> str:
    r'''
    https://cmsweb.cern.ch/dqm/offline/data/browse/ROOT/OnlineData/original/00035xxxx/0003553xx/DQM_V0001_GEM_R000355361.root
    '''
    run_str = str(run)
    url = f"dqm/offline/data/browse/ROOT/OnlineData/original/{run_str[:-4]:0>5}xxxx/{run_str[:-2]:0>7}xx"
    url = urllib.parse.urljoin(CMSWEB_NETLOC, url)
    pattern = re.compile(rf'DQM_V\d{{4}}_{dataset:s}_R{run:0>9}.root')
    return _find_file_url(url=url, pattern=pattern)


def download_root_file(url: str,
                       filename: Optional[str] = None,
                       output_dir: Optional[Path] = None,
) -> Path:
    """docstring TODO"""
    filename = filename or url.split('/')[-1] # FIXME urllib.parse
    output_dir = output_dir or Path.cwd()
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        print(f"created directory '{output_dir}'")
    output_path = output_dir / filename
    assert output_path.suffix == '.root', output_path
    response = open_url(url)
    data = response.read()
    with open(output_path, 'wb') as root_file:
        root_file.write(data)
    return output_path


def interpret_run_expr(expr: str) -> list[int]:
    run_list: list[int] = []
    if re.match(r'\d+-\d', expr):
        start_run, end_run = expr.split('-') # inclusive
        run_list += list(range(int(start_run), int(end_run) + 1))
    elif re.match(r'\d+', expr):
        run_list += [int(expr)]
    else:
        raise RuntimeError('failed to interpret {expr}')
    return run_list


def download_dqm_files(run_expr_list: list[str],
                       dataset_list: list[str],
                       output_dir: Path,
                       link_finder: LinkFinderCallable
) -> None:
    """docstring for download_offline_dqm_files
    """
    # remove duplicates runs and sort
    run_list = sorted(set(run for expr in run_expr_list for run in interpret_run_expr(expr)))
    args_list = list(itertools.product(run_list, dataset_list))

    failures = []
    for run, dataset in (pbar := tqdm.tqdm(args_list)):
        pbar.set_description(f'Run {run}, {dataset}')

        try:
            url = link_finder(run=run, dataset=dataset)
            download_root_file(url=url, output_dir=output_dir)
        except Exception as error:
            failures.append((run, dataset, error))

    if len(failures) > 0:
        print(f'{len(failures)} failures:')
        for run, dataset, error in failures:
            print(f'- {run=}, {dataset=}, {error=}')

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(required=True)

    # Offline DQM
    offline_parser = subparsers.add_parser('offline', aliases=['off'], help='download offline dqm files')
    offline_parser.add_argument("-r", "--run", type=str, nargs="+", required=True, help="runs")
    offline_parser.add_argument("-d", "--dataset", type=str, nargs="+", required=True,
                                help="primary datasets like 'StreamExpress', 'SingleMuon', 'DoubleMuon', and 'Muon'.")
    offline_parser.set_defaults(link_finder=find_offline_dqm_file_link)

    # Online DQM
    online_parser = subparsers.add_parser('online', aliases=['on'], help='download online dqm files')
    online_parser.add_argument("-r", "--run", type=str, nargs="+", required=True, help="runs")
    online_parser.add_argument('-d', '--dataset', type=str, nargs='+', default=['GEM'],
                               help='online dqm clients (https://github.com/cms-sw/cmssw/tree/master/DQM/Integration/python/clients)')
    online_parser.set_defaults(link_finder=find_online_dqm_file_link)

    # common
    for each in [offline_parser, online_parser]:
        each.add_argument('-o', '--output-dir', type=Path, help='output directory')

    # parse
    args = parser.parse_args()

    # Run
    download_dqm_files(run_expr_list=args.run,
                       dataset_list=args.dataset,
                       output_dir=args.output_dir,
                       link_finder=args.link_finder)

if __name__ == '__main__':
    main()
