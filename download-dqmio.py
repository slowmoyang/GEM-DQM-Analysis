#!/usr/bin/env python
"""

TODO
- [ ] certificiate with password
"""
from __future__ import annotations
import os
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import re
import urllib.parse
import urllib.request
import http.client
from http import HTTPStatus
import ssl
import itertools
from bs4 import BeautifulSoup
import tqdm


CMSWEB_NETLOC = 'https://cmsweb.cern.ch/'


@dataclass
class CertChain:
    certfile: str
    keyfile: str


def load_cert_chain() -> CertChain:
    cert_dir = Path(os.getenv('CERN_CERTIFICATE_PATH', Path.home() / '.globus'))
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

@dataclass
class DQMDatasetInfo:
    """https://twiki.cern.ch/twiki/bin/view/CMSPublic/CompOpsTier0Policies#Dataset_Naming_Conventions_for_T"""
    primary: str
    acquisition_era: str
    stream: str
    proc_version: str
    tier: str

    @classmethod
    def from_das_name(cls, dataset) -> DQMDatasetInfo:
        # /[ExpressDataset]/[AcquisitionEra]-Express-[ExpressProcVersion]/DQM
        # /[PrimaryDataset]/[AcquisitionEra]-PromptReco-[RecoProcVersion]/DQM
        _, primary, processed, tier = dataset.split('/')
        acquisition_era, stream, proc_version = processed.split('-')
        instance = cls(primary, acquisition_era, stream, proc_version, tier)
        if dataset != str(instance):
            raise RuntimeError(f"failed to parse dataset: {dataset} ==> {str(instance)}")
        return instance

    @property
    def processed(self) -> str:
        return f'{self.acquisition_era}-{self.stream}-{self.proc_version}'

    def __str__(self) -> str:
        return f'/{self.primary}/{self.processed}/{self.tier}'


def get_offline_dqm_file_link(dataset: str, run: int) -> str:
    info = DQMDatasetInfo.from_das_name(dataset)
    run_str = f'{run:0>9d}'

    # FIXME incorrect terms...
    era = info.acquisition_era
    if re.match(r'Run\d{4}[A-Z]', era):
        era = era[:-1]

    url = f"dqm/offline/data/browse/ROOT/OfflineData/{era}/{info.primary}/{run_str[:-2]}xx/"
    url = urllib.parse.urljoin(CMSWEB_NETLOC, url)

    filename_pattern = re.compile(rf'DQM_V\d{{4}}_R{run_str}__{info.primary}__{info.processed}__{info.tier}.root')

    response = urllib.request.build_opener(HTTPSAuthHandler()).open(url)

    soup = BeautifulSoup(response, features="html.parser")
    for a_tag in soup.find_all('a'):
        href = a_tag.attrs['href']
        last = href.split('/')[-1]
        if re.match(filename_pattern, last):
            return urllib.parse.urljoin(CMSWEB_NETLOC, href)
    else:
        raise RuntimeError(f"failed to find a filename matched with '{filename_pattern}' from '{url}'") # TODO raise proper error


def get_online_dqm_file_link(run: int, client: str) -> str:
    r'''
    https://cmsweb.cern.ch/dqm/offline/data/browse/ROOT/OnlineData/original/00035xxxx/0003553xx/DQM_V0001_GEM_R000355361.root
    '''
    run_str = str(run)
    index_url = f"dqm/offline/data/browse/ROOT/OnlineData/original/{run_str[:-4]:0>5}xxxx/{run_str[:-2]:0>7}xx"
    index_url = urllib.parse.urljoin(CMSWEB_NETLOC, index_url)
    filename_pattern = re.compile(rf'DQM_V\d{{4}}_{client:s}_R{run:0>9}.root')

    try:
        response = urllib.request.build_opener(HTTPSAuthHandler()).open(index_url)
    except Exception as error:
        print(f'got an error while opening {index_url=}')
        raise error

    soup = BeautifulSoup(response, features="html.parser")
    for row in soup.find_all('tr'):
        # link, file size, date
        link, _, _ = row.find_all('td')
        filename = link.text
        if filename_pattern.match(filename):
            url = link.find('a').attrs['href']
            url = urllib.parse.urljoin(CMSWEB_NETLOC, url)
            return url
    else:
        raise RuntimeError(f'{run=} not found on {index_url}')


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


def download_offline_dqm_files(run_list, dataset_list, output_dir):
    args_list = list(itertools.product(run_list, dataset_list))

    failures = []
    for run, dataset in (pbar := tqdm.tqdm(args_list)):
        pbar.set_description(f'{run=}, {dataset=}')
        try:
            url = get_offline_dqm_file_link(run=run, dataset=dataset)
            download_root_file(url=url, output_dir=output_dir)
        except Exception as error:
            failures.append((run, dataset, error))


    for run, dataset, error in failures:
        print(f'{run=}, {dataset=}: {error=}')

def download_online_dqm_files(run_list: list[int], client_list: list[str]):
    args_list = list(itertools.product(run_list, client_list))
    for run, client in (pbar := tqdm.tqdm(args_list)):
        pbar.set_description(f'{run=}')
        try:
            url = get_online_dqm_file_link(run=run, client=client)
        except Exception as error:
            print(error)
            continue

        try:
            download_root_file(url=url)
        except Exception as error:
            print(error)


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(required=True)

    ###########################################################################
    # Offline DQM
    ###########################################################################
    offline_parser = subparsers.add_parser('offline', aliases=['off'],
                                           help='download offline dqm files')
    offline_parser.add_argument("-r", "--run", dest='run_list', type=int,
                                nargs="+", required=True, help="runs")
    offline_parser.add_argument("-d", "--dataset", dest='dataset_list',
                                type=str, nargs="+", required=True,
                                help="datasets, DAS format")
    offline_parser.set_defaults(download_func=download_offline_dqm_files)

    ###########################################################################
    # Online DQM
    ###########################################################################
    online_parser = subparsers.add_parser('online', aliases=['on'],
                                          help='download online dqm files')
    online_parser.add_argument("-r", "--run", dest='run_list',
                               type=int, nargs="+", required=True,
                               help="runs")
    online_parser.add_argument('-c', '--client', dest='client_list',
                               type=str, nargs='+',
                               default=['GEM'],
                               help='online dqm clients')
    online_parser.set_defaults(download_func=download_online_dqm_files)

    parser.add_argument('-o', '--output-dir', type=Path, default='output directory')

    ###########################################################################
    # Run
    ###########################################################################
    args = parser.parse_args()
    args = vars(args)
    download_func = args.pop('download_func')
    download_func(**args)

if __name__ == '__main__':
    main()
