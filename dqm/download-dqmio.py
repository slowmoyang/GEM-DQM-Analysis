#!/usr/bin/env python
"""

TODO
- [ ] certificiate with password
- [ ] lint
- [ ] multiprocessing
"""
from __future__ import annotations
import os
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Protocol, Optional
import re
import urllib.parse
import urllib.request
import http.client
from http import HTTPStatus
import ssl
import itertools
from bs4 import BeautifulSoup
import tqdm
from omsapi import OMSAPI
import json
from functools import cache


CMSWEB_NETLOC = 'https://cmsweb.cern.ch/'

###############################################################################
# OMS 
###############################################################################
@cache
def load_oms_api():
    api_url = "https://cmsoms.cern.ch/agg/api"
    api_version = "v1"
    omsapi = OMSAPI(api_url, api_version, cert_verify=False)
    with open('./test/oms-test/oms-api-client-auth.json', 'r') as json_file:
        auth = json.load(json_file)
    omsapi.auth_oidc(client_id=auth['id'], client_secret=auth['secret'])
    return omsapi

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
# CERN CERTIFICATION
###############################################################################
@dataclass
class CertChain:
    certfile: str
    keyfile: str


def load_cert_chain() -> CertChain:
    if (cert_dir := os.getenv('CERN_CERTIFICATE_PATH')) is not None:
        cert_dir = Path(cert_dir)
    else:
        cert_dir = Path.home() / '.globus'
        print(f"The environment variable 'CERN_CERTIFICATE_PATH' is not set. It fallbacks to '{str(cert_dir)}'")
    if not cert_dir.exists():
        raise FileNotFoundError(cert_dir)

    certfile = cert_dir / 'usercert.pem'
    if not certfile.exists():
        raise FileNotFoundError(certfile)
    keyfile = cert_dir / 'userkey.pem'
    if not keyfile.exists():
        raise FileNotFoundError(keyfile)
    return CertChain(str(certfile), str(keyfile))


class HTTPSAuthConnection(http.client.HTTPSConnection):
    def __init__(self,
                 host: str,
                 context: Optional[ssl.SSLContext] = None,
                 **kwargs
    ) -> None:
        context = context or ssl._create_default_https_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        cert_chain = load_cert_chain()
        context.load_cert_chain(certfile=cert_chain.certfile,
                                keyfile=cert_chain.keyfile,
                                password=None)

        super().__init__(host, context=context, **kwargs)


class HTTPSAuthHandler(urllib.request.AbstractHTTPHandler):
    def default_open(self, req):
        return self.do_open(http_class=HTTPSAuthConnection, # type: ignore
                            req=req)

###############################################################################
# DQM
###############################################################################

class LinkFinderCallable(Protocol):
    def __call__(self, run: int, dataset: str) -> str:
        ...


def _find_file_url(url: str, pattern: re.Pattern) -> str:
    try:
        response = urllib.request.build_opener(HTTPSAuthHandler()).open(url)
    except Exception as error:
        print(f'got exception: {url=:s}')
        raise error
    if response.status != HTTPStatus.OK:
        raise RuntimeError(f'[{response.status=}] {url=:s}')

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

    try:
        response = urllib.request.build_opener(HTTPSAuthHandler()).open(url)
    except Exception as error:
        print(f'got exception: {url=:s}')
        raise error
    if response.status != HTTPStatus.OK:
        raise RuntimeError(f'[{response.status=}] {url=:s}')

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
            print(f'- Run {run}, {dataset}: {error=}')

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
